import sqlite3

from flask import jsonify, g

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

def register_cloud_run_service(guild_id, channel_id, region, project_id, service_name):
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
