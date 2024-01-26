# Path: genAI/main.py

from concurrent.futures import ThreadPoolExecutor, as_completed
from llm import LLM
import pandas as pd
from functools import reduce
import os
import time
from functools import wraps
import threading

from cloud import CloudRun, CloudRunResourceManager, CloudRunPerformanceMonitor, UntilNowTimeRange, SpecificTimeRange

def simulate_realtime_csv() -> pd.DataFrame:
    csv_dir = os.path.join(os.path.dirname(__file__),
                           '..', 'ICSD Cloud Resource Sample')

    cpu_utilization = pd.read_csv(os.path.join(
        csv_dir, 'Container CPU Utilization.csv'))
    memory_utilization = pd.read_csv(os.path.join(
        csv_dir, 'Container Memory Utilization.csv'))
    startup_latenecy = pd.read_csv(os.path.join(
        csv_dir, 'Container Startup Latency.csv'))
    instance_count = pd.read_csv(os.path.join(csv_dir, 'Instance Count.csv'))
    request_count = pd.read_csv(os.path.join(csv_dir, 'Request Count.csv'))
    request_latency = pd.read_csv(os.path.join(csv_dir, 'Request Latency.csv'))

    data_frames = [
        cpu_utilization,
        memory_utilization,
        startup_latenecy,
        instance_count,
        request_count,
        request_latency,
    ]

    data_frames = list(map(lambda df: df.assign(Time=pd.to_datetime(df['Time'])), data_frames))
    merged_data = reduce(lambda left, right: pd.merge(
        left, right, on=['Time'], how='outer'), data_frames)
    merged_data = merged_data.set_index('Time')

    return merged_data

# 檢查指標是否異常
class MetrixUtil:

    @staticmethod
    def check_metrics_abnormalities(metrics: list):
        metric = metrics[-1]

        if metric['Container Startup Latency (ms)'] > 0:
            return True

        if metric['Instance Count (active)'] > 4:
            return True

        if metric['Request Count (4xx)'] > 5:
            return True
        
        if metric['Request Count (5xx)'] > 5:
            return True

        times_dict = {'cpu': 0, 'memory': 0}

        if len(metrics) >= 2:
            for metric in metrics[-2:]:
                cpu_abnormal = metric['Container CPU Utilization (%)'] > 60
                memory_abnormal = metric['Container Memory Utilization (%)'] > 80

                if cpu_abnormal:
                    times_dict['cpu'] += 1
                else:
                    times_dict['cpu'] = 0

                if memory_abnormal:
                    times_dict['memory'] += 1
                else:
                    times_dict['memory'] = 0

        return times_dict['cpu'] >= 2 or times_dict['memory'] >= 2

def get_metric_wrapper(crpm: CloudRunPerformanceMonitor, metric_type: str, until_now, options: dict):
    return crpm.get_metric(metric_type, until_now, options=options)

def polling_metric(crpm: CloudRunPerformanceMonitor):
    until_now = UntilNowTimeRange(minutes=10)
    metries_datas = []

    metries_types_and_name = [
        {
            'metric_type': 'run.googleapis.com/request_count',
            'options': {
                'metric_label': 'response_code_class',
                'metric_new_label': 'Request Count'
            }
        },
        {
            'metric_type': 'run.googleapis.com/request_latencies',
            'options': {
                'metric_label': 'Container Startup Latency (ms)',
            }
        },
        {
            'metric_type': 'run.googleapis.com/container/instance_count',
            'options': {
                'metric_label': 'state',
                'metric_new_label': 'Instance Count'
            }
        },
        {
            'metric_type': 'run.googleapis.com/container/cpu/utilizations',
            'options': {
                'metric_label': 'Container CPU Utilization (%)',
                'multiply': 100
            }
        },
        {
            'metric_type': 'run.googleapis.com/container/memory/utilizations',
            'options': {
                'metric_label': 'Container Memory Utilization (%)',
                'multiply': 100
            }
        },
        {
            'metric_type': 'run.googleapis.com/container/startup_latencies',
            'options': {
                'metric_label': 'Container Startup Latency (ms)',
            }
        }
    ]

    with ThreadPoolExecutor(max_workers=len(metries_types_and_name)) as executor:
        future_to_metric = {
            executor.submit(get_metric_wrapper,
                            crpm,
                            mt['metric_type'],
                            until_now,
                            options=mt['options']
                            ): mt for mt in metries_types_and_name}

        metries_datas = []
        for future in as_completed(future_to_metric):
            metries_datas.append(future.result())

    res = pd.concat(metries_datas, axis=1)
    ignore_dropna_fields = ['Container Startup Latency (ms)']
    res = res.dropna(
        subset=[col for col in res.columns if not col in ignore_dropna_fields])
    res = res[sorted(res.columns)]
    return res

if __name__ == '__main__':

    def main():
        cr = CloudRun(region='us-central1',
                    project_id='tsmccareerhack2024-icsd-grp3',
                    service_name='sso-tsmc-2')
        crpm = CloudRunPerformanceMonitor(cr)
        result = polling_metric(crpm)

        # 如果最後兩筆的指標有異常的話，就會丟到 llm 讓他生成的錯誤報告
        metrcis = [item.to_dict() for item in result.iloc]
        if MetrixUtil.check_metrics_abnormalities(metrcis):
            # 獲取該 metrixs 的 第一筆資料 和 最後一筆資料 的時間
            start_time, end_time = result.index[0], result.index[-1]
            time_range = SpecificTimeRange(start_time, end_time)
            logs = crpm.get_logs(time_range)

            if logs is []:
                logs = '沒有 log'

            text = LLM.AnalysisError.gen(data=f'指標：\b{result.to_dict()}\n錯誤訊息:\n{logs}')
            print(text)

        # handel auto scaling cloud run resource
        # crm = CloudRunResourceManager(cr)
        # resource_data = result.iloc[-1].to_dict()
        # if resource_data['Container CPU Utilization (%)'] > 50:
        #     crm.cpu.scale_up()
        # elif resource_data['Container CPU Utilization (%)'] < 30:
        #     crm.cpu.scale_down()

        # if resource_data['Container Memory Utilization (%)'] > 50:
        #     crm.memory.scale_up()
        # elif resource_data['Container Memory Utilization (%)'] < 30:
        #     crm.memory.scale_down()

    main()
    # interval_seconds = 30

    # def run_timer():
    #     while True:
    #         timer = threading.Timer(interval_seconds, main)
    #         timer.start()
    #         timer.join()

    # timer_thread = threading.Thread(target=run_timer)
    # timer_thread.daemon = True
    # timer_thread.start()
    # timer_thread.join()
