# Path: genAI/main.py

from concurrent.futures import ThreadPoolExecutor, as_completed
from llm import LLM
import pandas as pd
from functools import reduce
import os
import time
from functools import wraps
import threading

from cloud import CloudRun, CloudRunResourceManager, CloudRunPerformanceMonitor, UntilNowTimeRange


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

    # data_frames = list(map(lambda df: df.assign(Time=pd.to_datetime(df['Time'])), data_frames))

    merged_data = reduce(lambda left, right: pd.merge(
        left, right, on=['Time'], how='outer'), data_frames)
    # merged_data = merged_data.set_index('Time')

    for _, row in merged_data.iterrows():
        yield row
        time.sleep(0.02)

# {'Container CPU Utilization (%)': 16.0875, 'Container Memory Utilization (%)': 56.99, 'Container Startup Latency (ms)': nan, 'Instance Count (active)': 1.0, 'Instance Count (idle)': 1.0, 'Request Count (1xx)': 0.0, 'Request Count (2xx)': 5.0, 'Request Count (3xx)': 0.0, 'Request Count (4xx)': 4.0, 'Request Latency (ms)': 31.2701591}
# 檢查指標是否異常
class MetrixUtil:
    times_dict = {'cpu': 0, 'memory': 0}

    @staticmethod
    def check_metrics_abnormalities(metrics: dict):
        if metrics['Container Startup Latency (ms)'] > 0:
            return True

        if metrics['Instance Count (active)'] > 2:
            return True

        if metrics['Request Count (4xx)'] > 5:
            return True

        cpu_abnormal = metrics['Container CPU Utilization (%)'] > 60
        memory_abnormal = metrics['Container Memory Utilization (%)'] > 80

        if cpu_abnormal:
            MetrixUtil.times_dict['cpu'] += 1
        else:
            MetrixUtil.times_dict['cpu'] = 0

        if memory_abnormal:
            MetrixUtil.times_dict['memory'] += 1
        else:
            MetrixUtil.times_dict['memory'] = 0

        return MetrixUtil.times_dict['cpu'] >= 2 or MetrixUtil.times_dict['memory'] >= 2


def get_metric_wrapper(crpm: CloudRunPerformanceMonitor, metric_type: str, until_now, options: dict):
    return crpm.get_metric(metric_type, until_now, options=options)


def polling_metric(crpm: CloudRunPerformanceMonitor):
    until_now = UntilNowTimeRange(minutes=5)
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
    ignore_dropna_fields = ['startup_latency']
    res = res.dropna(
        subset=[col for col in res.columns if not col in ignore_dropna_fields])
    res = res[sorted(res.columns)]

    return res.iloc[-1].to_dict()


def main():
    cr = CloudRun(region='us-central1',
                  project_id='tsmccareerhack2024-icsd-grp3',
                  service_name='sso-tsmc-2')
    crpm = CloudRunPerformanceMonitor(cr)
    result = polling_metric(crpm)
    if MetrixUtil.check_metrics_abnormalities(result):
        print('abnormal')
    print(result)


if __name__ == '__main__':
    # main()
    interval_seconds = 30

    def run_timer():
        while True:
            timer = threading.Timer(interval_seconds, main)
            timer.start()
            timer.join()

    timer_thread = threading.Thread(target=run_timer)
    timer_thread.daemon = True
    timer_thread.start()
    timer_thread.join()
