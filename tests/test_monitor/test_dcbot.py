import pytest
from unittest.mock import Mock, patch
import pandas as pd
from flaskr.dcbot import check_metrics_abnormalities, polling_metric, get_lastest_llm_query_time

def test_empty_metrics_list():
    assert check_metrics_abnormalities([]) == False

def test_container_startup_latency_abnormal():
    metrics = [{'Container Startup Latency (ms)': 10}]
    assert check_metrics_abnormalities(metrics) == True

def test_instance_count_abnormal():
    metrics = [{'Instance Count (active)': 3}]
    assert check_metrics_abnormalities(metrics) == True

def test_request_count_4xx_abnormal():
    metrics = [{'Request Count (4xx)': 6}]
    assert check_metrics_abnormalities(metrics) == True

def test_request_count_5xx_abnormal():
    metrics = [{'Request Count (5xx)': 6}]
    assert check_metrics_abnormalities(metrics) == True

def test_cpu_memory_utilization_normal():
    metrics = [
        {'Container CPU Utilization (%)': 50, 'Container Memory Utilization (%)': 50},
        {'Container CPU Utilization (%)': 50, 'Container Memory Utilization (%)': 50}
    ]
    assert check_metrics_abnormalities(metrics) == False

def test_cpu_memory_utilization_abnormal():
    metrics = [
        {'Container CPU Utilization (%)': 70, 'Container Memory Utilization (%)': 70},
        {'Container CPU Utilization (%)': 70, 'Container Memory Utilization (%)': 70}
    ]
    assert check_metrics_abnormalities(metrics) == True

def mock_get_metric(*arg, **kargs):
    return pd.DataFrame([
        {'Container Startup Latency (ms)': 10},
        {'Instance Count (active)': 3},
        {'Request Count (4xx)': 6},
        {'Request Count (5xx)': 6},
        {'Container CPU Utilization (%)': 70, 'Container Memory Utilization (%)': 70},
        {'Container CPU Utilization (%)': 70, 'Container Memory Utilization (%)': 70}
    ])

def test_polling_metric_normal():
    crpm = Mock()
    crpm.get_metric = Mock(side_effect=mock_get_metric)

    df = polling_metric(crpm)
    assert isinstance(df, pd.DataFrame)
    # 更多的斷言，檢查 DataFrame 的內容是否符合預期

def test_polling_metric_empty():
    crpm = Mock()
    crpm.get_metric = Mock(return_value=pd.DataFrame())

    df = polling_metric(crpm)
    assert df.empty

    # 創建一個模擬 cursor 和 db

    monkeypatch.setattr('flaskr.db.get_db', Mock())
    cursor = Mock()

    # 模擬 cursor.execute() 的回傳值
    cursor.execute.return_value = [
        ('2021-01-01 00:00:00',),
        ('2021-01-02 00:00:00',),
        ('2021-01-03 00:00:00',),
    ]

    # 模擬 db.cursor() 的回傳值
    db = Mock()
    db.cursor.return_value = cursor

    # 模擬 get_db() 的回傳值
    get_db = Mock(return_value=db)

    # 執行 get_lastest_llm_query_time()
    with patch('flaskr.db.get_db', get_db):
        result = get_lastest_llm_query_time(
            'us-central1',
            'dcbot-llm',
            'llm',
        )

    # 檢查回傳值是否符合預期
    assert result == '2021-01-03 00:00:00'

    # 檢查是否有呼叫過 db.cursor()
    db.cursor.assert_called_once()

    # 檢查是否有呼叫過 cursor.execute()
    cursor.execute.assert_called_once()

    # 檢查是否有呼叫過 cursor.close()
    cursor.close.assert_called_once()