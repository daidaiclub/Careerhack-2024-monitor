import os
import pytest
from genAI.main import simulate_realtime_csv, check_metrics_abnormalities
import pandas as pd

@pytest.fixture
def fake_abspath(monkeypatch):
    def fake_abspath_impl(path):
        return "/fake/directory/"
    
    monkeypatch.setattr(os.path, "abspath", fake_abspath_impl)
    return fake_abspath_impl


@pytest.fixture
def fake_read_csv(monkeypatch):
    def fake_read_csv_impl(filepath, *args, **kwargs):
        # 創建一個預設的 DataFrame
        data = {'Time': ['Thu Dec 07 2023 09:00:00', 'Thu Dec 07 2023 09:01:00', 'Thu Dec 07 2023 09:02:00'], f'{filepath}': ['0', '0', '0']}
        return pd.DataFrame(data)

    monkeypatch.setattr(pd, "read_csv", fake_read_csv_impl)
    return fake_read_csv_impl


def test_simulate_realtime_csv(fake_abspath, fake_read_csv):
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


@pytest.mark.parametrize(
        ("container", "instance", "count", "container_cpu", "container_memory", "cpu", "memory"),
        [
            (1, 0, 0, 60, 80, 0, 0),
            (0, 3, 0, 60, 80, 0, 0),
            (0, 0, 6, 60, 80, 0, 0),
            (0, 0, 0, 70, 80, 1, 1),
            (0, 0, 0, 60, 90, 1, 1),
        ],
    )
def test_check_metrics_abnormalities_abnormal(container, instance, count, container_cpu, container_memory, cpu, memory):
    metrics = {
        'Container Startup Latency (ms)': container,
        'Instance Count (active)': instance,
        'Request Count (4xx)': count,
        'Container CPU Utilization (%)': container_cpu,
        'Container Memory Utilization (%)': container_memory,
    }
    times_dict = {'cpu': cpu, 'memory': memory}
    assert check_metrics_abnormalities(metrics, times_dict), "Should return True for abnormal metrics"