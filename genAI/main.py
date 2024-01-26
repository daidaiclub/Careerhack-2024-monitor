# Path: genAI/main.py

from llm import LLM
import pandas as pd
from functools import reduce
import os
import time

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


def check_metrics_abnormalities(metrics: dict, times_dict: dict = {'cpu': 0, 'memory': 0}):
    if metrics['Container Startup Latency (ms)'] > 0:
        return True

    if metrics['Instance Count (active)'] > 2:
        return True

    if metrics['Request Count (4xx)'] > 5:
        return True

    cpu_abnormal = metrics['Container CPU Utilization (%)'] > 60
    memory_abnormal = metrics['Container Memory Utilization (%)'] > 80

    if cpu_abnormal:
        times_dict['cpu'] += 1
    else:
        times_dict['cpu'] = 0

    if memory_abnormal:
        times_dict['memory'] += 1
    else:
        times_dict['memory'] = 0

    return times_dict['cpu'] >= 2 or times_dict['memory'] >= 2


def polling_metric(crpm: CloudRunPerformanceMonitor):
    until_now = UntilNowTimeRange(minutes=5)
    metries_datas = []
    metries_types_and_name = [
        ('run.googleapis.com/request_count', 'response_code_class'),
        ('run.googleapis.com/request_latencies', 'latency'),
        ('run.googleapis.com/container/instance_count', 'instance_count'),
        ('run.googleapis.com/container/cpu/utilizations', 'cpu_utilization'),
        ('run.googleapis.com/container/memory/utilizations', 'memory_utilization'),
        ('run.googleapis.com/container/startup_latencies', 'startup_latency')
    ]

    for metric_type, metric_label in metries_types_and_name:
        metries_datas.append(
            crpm.get_metric(metric_type, until_now, metric_label)
        )

    res = pd.concat(metries_datas, axis=1)
    ignore_dropna_fields = ['startup_latency']
    res = res.dropna(
        subset=[col for col in res.columns if not col in ignore_dropna_fields])

    return res


if __name__ == '__main__':
    cr = CloudRun(region='us-central1',
                  project_id='tsmccareerhack2024-icsd-grp3',
                  service_name='sso-tsmc-2')
    crpm = CloudRunPerformanceMonitor(cr)

    result = polling_metric(crpm)
    print(result)
    pass
