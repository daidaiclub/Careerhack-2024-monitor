import os
import pytest
from genAI.main import simulate_realtime_csv, check_metrics_abnormalities
import pandas as pd

def fake_abspath(path):
    return "/fake/directory/"

def fake_read_csv(filepath, *args, **kwargs):
    # 創建一個預設的 DataFrame
    data = {'Time': ['Thu Dec 07 2023 09:00:00', 'Thu Dec 07 2023 09:01:00', 'Thu Dec 07 2023 09:02:00'], f'{filepath}': ['0', '0', '0']}
    return pd.DataFrame(data)

def test_simulate_realtime_csv(monkeypatch):
    monkeypatch.setattr(os.path, "abspath", fake_abspath)
    monkeypatch.setattr(pd, "read_csv", fake_read_csv)
     
    data_generator = simulate_realtime_csv()


    data = next(data_generator)
    assert isinstance(data, pd.Series), "Generated data should be Pandas Series"


def test_check_metrics_abnormalities_normal():
    metrics = {
        'Container Startup Latency (ms)': 0,
        'Instance Count (active)': 1,
        'Request Count (4xx)': 1,
        'Container CPU Utilization (%)': 50,
        'Container Memory Utilization (%)': 70,
    }
    times_dict = {'cpu': 0, 'memory': 0}
    assert not check_metrics_abnormalities(metrics, times_dict), "Should return False for normal metrics"

def test_check_metrics_abnormalities_abnormal():
    metrics = {
        'Container Startup Latency (ms)': 0,
        'Instance Count (active)': 1,
        'Request Count (4xx)': 1,
        'Container CPU Utilization (%)': 70,
        'Container Memory Utilization (%)': 90,
    }
    times_dict = {'cpu': 1, 'memory': 1}
    assert check_metrics_abnormalities(metrics, times_dict), "Should return True for abnormal metrics"