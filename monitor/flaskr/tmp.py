import sqlite3
import threading
from flask import jsonify, g
from genAI.cloud import CloudRun,  CloudRunPerformanceMonitor, UntilNowTimeRange, SpecificTimeRange
from genAI.llm import LLM
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
def get_db():
    # if 'db' not in g:
    #     # 假設你的資料庫連接函式是這樣的
    #     g.db = sqlite3.connect('monitor.db')
    #     g.db.row_factory = sqlite3.Row
    # return g.db

    db = sqlite3.connect('monitor.db')
    db.row_factory = sqlite3.Row
    return db



def init_db():
    db = get_db()
    with open('schema.sql') as f:
        db.executescript(f.read())
    db.commit()

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


def query(cr: CloudRun):
    crpm = CloudRunPerformanceMonitor(cr)
    result = polling_metric(crpm)

    metrcis = [item.to_dict() for item in result.iloc]
    if MetrixUtil.check_metrics_abnormalities(metrcis):
        # 獲取該 metrixs 的 第一筆資料 和 最後一筆資料 的時間
        start_time, end_time = result.index[0], result.index[-1]
        time_range = SpecificTimeRange(start_time, end_time)
        logs = crpm.get_logs(time_range)

        if logs is []:
            logs = '沒有 log'

        text = LLM.AnalysisError.gen(data=f'指標：\b{result.to_dict()}\n錯誤訊息:\n{logs}')
        # todo: send to discord by websocket
        print(text)
    pass

interval_seconds = 30
def register_cloud_run_service(guild_id, channel_id, region, project_id, service_name):
    def run_timer(guild_id, channel_id, cr: CloudRun):
        query()
        timer = threading.Timer(interval_seconds, run_timer, [guild_id, channel_id, region, project_id, service_name])
        timer.daemon = True
        timer.start()


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
        cr = CloudRun(region=region, project_id=project_id, service_name=service_name)
        timer_thread = threading.Thread(target=run_timer, args=(guild_id, channel_id, cr))
        timer_thread.daemon = True
        timer_thread.start()
        return jsonify({'message': 'Service registered'}), 201

def unregister_cloud_run_service(guild_id, channel_id, region, project_id, service_name):
    db = get_db()
    cursor = db.cursor()
    
    # 刪除符合條件的記錄
    cursor.execute('''
    DELETE FROM cloud_run_service WHERE guild_id=? AND channel_id=? AND region=? AND project_id=? AND service_name=?
    ''', (guild_id, channel_id, region, project_id, service_name))
    
    if cursor.rowcount > 0:
        # 如果有刪除記錄，提交變更並返回成功消息
        db.commit()
        return jsonify({'message': 'Service unregistered'}), 200
    else:
        # 如果沒有符合條件的記錄，返回錯誤消息
        return jsonify({'message': 'Service not found'}), 404
    
def list_cloud_run_services(guild_id, channel_id):
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
