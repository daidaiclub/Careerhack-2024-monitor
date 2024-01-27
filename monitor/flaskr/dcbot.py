""" This module contains the functions for monitoring Cloud Run services. """
import threading
import os
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import reduce
from flask import jsonify
import pandas as pd
import logging

from flaskr.genAI.llm import LLM
from flaskr.db import get_db
from flaskr.genAI.cloud import (CloudRun, CloudRunPerformanceMonitor,
                                UntilNowTimeRange, SpecificTimeRange, CloudRunResourceManager)
from flaskr.dcbot_websocket import DCBotWebSocket

# --- logger

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s [%(funcName)s]: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def check_metrics_abnormalities(metrics: list[dict]):
    """
    Checks if the given metrics indicate abnormalities.

    Args:
        metrics (list[dict]): List of metric dictionaries.

    Returns:
        bool: True if abnormalities are detected, False otherwise.
    """
    if len(metrics) == 0:
        return False
    logger.debug('check_metrics_abnormalities: %s', metrics)
    metric = metrics[-1]

    if metric.get('Container Startup Latency (ms)', 0) > 0:
        return True

    if metric.get('Instance Count (active)', 0) > 2:
        return True

    if metric.get('Request Count (4xx)', 0) > 5:
        return True

    if metric.get('Request Count (5xx)', 0) > 5:
        return True

    times_dict = {'cpu': 0, 'memory': 0}

    if len(metrics) >= 2:
        for metric in metrics[-2:]:
            cpu_abnormal = metric.get(
                'Container CPU Utilization (%)', 0) > 60
            memory_abnormal = metric.get(
                'Container Memory Utilization (%)', 0) > 60

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
    """
    Polls various metrics from a CloudRunPerformanceMonitor object.

    Args:
        crpm (CloudRunPerformanceMonitor): The CloudRunPerformanceMonitor object 
        to poll metrics from.

    Returns:
        pandas.DataFrame: A DataFrame containing the polled metrics.
    """
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
                'metric_label': 'Request Latency (ms)',
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

    def get_metric_wrapper(crpm: CloudRunPerformanceMonitor,
                           metric_type: str, until_now, options: dict):
        return crpm.get_metric(metric_type, until_now, options=options)

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


def get_lastest_llm_query_time(region, project_id, service_name):
    """
    Retrieve the latest LLM query time for a specific cloud run service.

    Args:
        region (str): The region of the cloud run service.
        project_id (str): The project ID of the cloud run service.
        service_name (str): The name of the cloud run service.

    Returns:
        str: The latest LLM query time.

    """
    logger.debug('get_lastest_llm_query_time: %s, %s, %s',
                  region, project_id, service_name)
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
    SELECT lastest_llm_query_time FROM cloud_run_service WHERE region=? AND project_id=? AND service_name=?
    ''', (region, project_id, service_name))

    return cursor.fetchone()[0]


def set_lastest_llm_query_time(region, project_id, service_name, lastest_llm_query_time):
    """
    Update the lastest_llm_query_time for a specific cloud_run_service.

    Args:
        region (str): The region of the cloud_run_service.
        project_id (str): The project ID of the cloud_run_service.
        service_name (str): The name of the cloud_run_service.
        lastest_llm_query_time (str): The lastest_llm_query_time to be set.

    Returns:
        None
    """
    logger.debug('set_lastest_llm_query_time: %s, %s, %s, %s',
                  region, project_id, service_name, lastest_llm_query_time)
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
    UPDATE cloud_run_service SET lastest_llm_query_time=? WHERE region=? AND project_id=? AND service_name=?
    ''', (lastest_llm_query_time, region, project_id, service_name))

    db.commit()


def is_cloud_run_service_registered(guild_id, channel_id, region, project_id, service_name):
    """
    Check if a Cloud Run service is registered in the database.

    Args:
        guild_id (int): The ID of the guild.
        channel_id (int): The ID of the channel.
        region (str): The region of the Cloud Run service.
        project_id (str): The ID of the project.
        service_name (str): The name of the Cloud Run service.

    Returns:
        bool: True if the Cloud Run service is registered, False otherwise.
    """
    logger.debug('is_cloud_run_service_registered: %s, %s, %s, %s, %s',
                  guild_id, channel_id, region, project_id, service_name)
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
    SELECT * FROM cloud_run_service WHERE guild_id=? AND channel_id=? AND region=? AND project_id=? AND service_name=?
    ''', (guild_id, channel_id, region, project_id, service_name))

    return cursor.fetchone() is not None


def query(cr: CloudRun, channel_id):
    """
    Queries the CloudRun instance for metrics and performs scaling operations based on the metrics.

    Args:
        cr (CloudRun): The CloudRun instance to query.
        channel_id (str): The ID of the channel to send the message to.

    Returns:
        None
    """
    logger.debug('query: %s', cr)
    lastest_llm_query_time = get_lastest_llm_query_time(
        cr.region, cr.project_id, cr.service_name)
    query_time = datetime.fromisoformat(
        lastest_llm_query_time) if lastest_llm_query_time else None
    if not query_time is None and (datetime.now() - query_time).total_seconds() < 600:
        return

    crpm = CloudRunPerformanceMonitor(cr)
    result = polling_metric(crpm)

    metrics = [item.to_dict() for item in result.iloc]
    if check_metrics_abnormalities(metrics):
        # 獲取該 metrixs 的 第一筆資料 和 最後一筆資料 的時間
        start_time, end_time = result.index[0], result.index[-1]
        time_range = SpecificTimeRange(start_time, end_time)
        logs = crpm.get_logs(time_range)

        if logs is []:
            logs = '沒有 log'

        text = LLM.AnalysisError.gen(
            data=f'指標：\b{result.to_dict()}\n錯誤訊息:\n{logs}')
        set_lastest_llm_query_time(
            cr.region, cr.project_id, cr.service_name, datetime.now().isoformat())

        message = f'- service name: **{cr.service_name}**\n'
        message += f'  - project id: **{cr.project_id}**\n'
        message += f'  - region: **{cr.region}**\n'
        message += text

        ws_message = {
            'channel_id': channel_id,
            'message': message
        }
        DCBotWebSocket.send(json.dumps(ws_message))

    cpu_util = metrics[-1].get('Container CPU Utilization (%)', 0)
    mem_util = metrics[-1].get('Container Memory Utilization (%)', 0)
    crm = CloudRunResourceManager(cr)
    # if cpu_util > 50:
    #     crm.cpu.scale_up()
    # elif cpu_util < 30:
    #     crm.cpu.scale_down()

    # if mem_util > 50:
    #     crm.memory.scale_up()
    # elif mem_util < 30:
    #     crm.memory.scale_down()

    request_count = metrics[-1].get('Request Count', 50)
    request_latencies = metrics[-1].get('Request Latency (ms)', 0)
    instance_count = metrics[-1].get('Instance Count', 1)
    container_startup_latencies = metrics[-1].get('Container Startup Latency (ms)', 0)
    cpu, mem = 0, 0

    if cpu_util > 50:
        cpu += 1
    elif cpu_util < 30:
        cpu -= 1
    
    if mem_util > 50:
        mem += 1
    elif mem_util < 30:
        mem -= 1
    
    if request_count > 100:
        cpu += 1
        mem += 1
    elif request_count < 50:
        cpu -= 1
        mem -= 1
    
    if request_latencies > 100:
        cpu += 1
    elif request_latencies < 50:
        cpu -= 1

    if instance_count > 2:
        cpu += 1
        mem += 1
    elif instance_count < 1:
        cpu -= 1
        mem -= 1

    if container_startup_latencies > 100:
        cpu += 1
        mem += 1
    elif container_startup_latencies == 0:
        cpu -= 1
        mem -= 1

    message = f'- service name: **{cr.service_name}**\n'
    message += f'  - project id: **{cr.project_id}**\n'
    message += f'  - region: **{cr.region}**\n'
    
    if cpu > 0:
        crm.cpu.scale_up()
        DCBotWebSocket.send(json.dumps({
            'channel_id': channel_id,
            'message': message + 'CPU **增加**資源'
        }))
    elif cpu < 0:
        crm.cpu.scale_down()
        DCBotWebSocket.send(json.dumps({
            'channel_id': channel_id,
            'message': message + 'CPU **減少**資源'
        }))
    if mem > 0:
        crm.memory.scale_up()
        DCBotWebSocket.send(json.dumps({
            'channel_id': channel_id,
            'message': message + 'Memory **增加**資源'
        }))
    elif mem < 0:
        crm.memory.scale_down()
        DCBotWebSocket.send(json.dumps({
            'channel_id': channel_id,
            'message': message + 'Memory **減少**資源'
        }))

def run_timer(guild_id, channel_id, cr: CloudRun):
    """
    Run a timer that periodically executes the query function for a given CloudRun instance.

    Args:
        guild_id (str): The ID of the guild.
        channel_id (str): The ID of the channel.
        cr (CloudRun): The CloudRun instance.

    Returns:
        None
    """
    if not is_cloud_run_service_registered(
            guild_id, channel_id, cr.region, cr.project_id, cr.service_name):
        return
    timer = threading.Timer(30, run_timer, [guild_id, channel_id, cr])
    timer.daemon = True
    timer.start()
    query(cr, channel_id)

def init_already_registered_services():
    """
    Initializes the already registered Cloud Run services.

    Returns:
        None
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
    SELECT * FROM cloud_run_service
    ''')

    for row in cursor.fetchall():
        guild_id = row[5]
        channel_id = row[3]
        region = row[0]
        project_id = row[1]
        service_name = row[2]
        cr = CloudRun(region, project_id, service_name)
        timer_thread = threading.Thread(target=run_timer, args=(
            guild_id, channel_id, cr))
        timer_thread.daemon = True
        timer_thread.start()

def genai(temp_dir: str):
    """
    Generate a markdown report based on the data frames in the given directory.

    Args:
        temp_dir (str): The directory path containing the data frames.

    Returns:
        str: The generated markdown report.
    """
    data_frames = []
    for entry in os.listdir(temp_dir):
        data_frames.append(pd.read_csv(os.path.join(temp_dir, entry)))
    data_frames = list(map(lambda df: df.assign(
        Time=pd.to_datetime(df['Time'])), data_frames))
    merged_data = reduce(lambda left, right: pd.merge(
        left, right, on=['Time'], how='outer'), data_frames)
    merged_data = merged_data.set_index('Time')

    # Generate markdown
    mdpdf = "# 報告書\n"
    i = 2
    while i < len(merged_data):
        metrics = [item.to_dict() for item in merged_data.iloc][i-2:i]
        if check_metrics_abnormalities(metrics):
            mdpdf += f'## 異常時間: {merged_data.index[i-1]}\n'
            mdpdf += LLM.AnalysisError.gen(data=f'指標：{metrics}')
            mdpdf += '\n'
            i += 10
            cpu_util = metrics[-1].get('Container CPU Utilization (%)', 0)
            mem_util = metrics[-1].get('Container Memory Utilization (%)', 0)

            if cpu_util > 50 or cpu_util < 30:
                mdpdf += '### CPU 自動調整操作\n'
                mdpdf += f'CPU 建議**{"增加" if cpu_util > 50 else "減少"}**資源˙\n'

            if mem_util > 50 or mem_util < 30:
                mdpdf += '### Memory 自動調整操作\n'
                mdpdf += f'Memory 建議**{"增加" if mem_util > 50 else "減少"}**資源\n'
        i += 1
    return mdpdf


def register_cloud_run_service(guild_id, channel_id, region, project_id, service_name):
    """
    Registers a Cloud Run service in the database and starts 
    a timer to periodically query the service.

    Args:
        guild_id (int): The ID of the guild.
        channel_id (int): The ID of the channel.
        region (str): The region where the Cloud Run service is deployed.
        project_id (str): The ID of the project where the Cloud Run service is deployed.
        service_name (str): The name of the Cloud Run service.

    Returns:
        tuple: A tuple containing the response message and status code.
    """
    db = get_db()
    cursor = db.cursor()

    # 插入資料前，先檢查是否已存在相同的主鍵組合
    cursor.execute('''
  SELECT * FROM cloud_run_service WHERE region=? AND project_id=? AND service_name=?
  ''', (region, project_id, service_name))

    if cursor.fetchone():
        return jsonify({'message': 'Service already registered'}), 400
    else:
        # 插入新的記錄
        cursor.execute('''
    INSERT INTO cloud_run_service (guild_id, channel_id, region, project_id, service_name)
    VALUES (?, ?, ?, ?, ?)
    ''', (guild_id, channel_id, region, project_id, service_name))
        db.commit()
        timer_thread = threading.Thread(target=run_timer, args=(
            guild_id, channel_id, CloudRun(region, project_id, service_name)))
        timer_thread.daemon = True
        timer_thread.start()
        return jsonify({'message': 'Service registered'}), 201


def unregister_cloud_run_service(guild_id, channel_id, region, project_id, service_name):
    """
    Unregisters a cloud run service based on the provided parameters.

    Args:
        guild_id (int): The ID of the guild.
        channel_id (int): The ID of the channel.
        region (str): The region of the cloud run service.
        project_id (str): The ID of the project.
        service_name (str): The name of the cloud run service.

    Returns:
        tuple: A tuple containing the JSON response message and the HTTP status code.
    """
    db = get_db()
    cursor = db.cursor()
    # Delete records that match the given conditions
    cursor.execute('''
    DELETE FROM cloud_run_service WHERE guild_id=? AND channel_id=? AND region=? AND project_id=? AND service_name=?
    ''', (guild_id, channel_id, region, project_id, service_name))

    if cursor.rowcount > 0:
        # If records were deleted, commit the changes and return a success message
        db.commit()
        return jsonify({'message': 'Service unregistered'}), 200
    # If no records match the conditions, return an error message
    return jsonify({'message': 'Service not found'}), 404


def list_cloud_run_services(guild_id, channel_id):
    """
    Retrieve a list of cloud run services based on the guild ID and channel ID.

    Args:
        guild_id (int): The ID of the guild.
        channel_id (int): The ID of the channel.

    Returns:
        tuple: A tuple containing the JSON representation of 
        the cloud run services and the HTTP status code.
    """
    db = get_db()
    cursor = db.cursor()

    # 查詢符合條件的記錄
    cursor.execute('''
    SELECT * FROM cloud_run_service WHERE guild_id=? AND channel_id=?
    ''', (guild_id, channel_id))

    services = []
    for row in cursor.fetchall():
        # 將查詢結果轉換為字典
        service = {
            'region': row[0],
            'project_id': row[1],
            'service_name': row[2],
            'channel_id': row[3],
            'lastest_llm_query_time': row[4],
            'guild_id': row[5]
        }
        services.append(service)

    # 返回查詢結果作為 JSON
    return jsonify(services), 200
