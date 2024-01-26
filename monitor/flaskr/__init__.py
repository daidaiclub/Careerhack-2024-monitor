import os
import websocket
from flask import Flask, request, jsonify, g, send_file
from flaskr import hello as h
from flaskr import tmp as t
from flaskr import dcbot as d
import dotenv
import threading
import asyncio
import datetime
import zipfile
import shutil
from weasyprint import HTML
import markdown
from io import BytesIO

dotenv.load_dotenv()

t.init_db()

DCBOT_SOCKET_URI = os.getenv('DCBOT_SOCKET_URI')

def create_app(test_config=None) -> Flask:
    # asyncio event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # flask app
    app = Flask(__name__)

    # websocket
    def connect_dcbot():
        print(f'connecting dcbot to {DCBOT_SOCKET_URI}', flush=True)
        connected_event = asyncio.Event()

        def on_open(ws):
            print("dcbot opened", flush=True)
            connected_event.set()

        def on_message(ws, message):
            print(f"dcbot received: {message}", flush=True)

        def on_error(ws, error):
            print(f'error: {error}', flush=True)

        def on_close(ws, close_status_code, close_msg):
            print("dcbot closed", flush=True)

        ws = websocket.WebSocketApp(
            DCBOT_SOCKET_URI,
            on_message = on_message,
            on_error = on_error,
            on_open = on_open,
            on_close = on_close
        )
        wst = threading.Thread(target=ws.run_forever)
        wst.daemon = True
        wst.start()
        return ws

    # websocket.enableTrace(True)
    ws = connect_dcbot()

    # flask route
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    @app.route('/hello/<name>')
    def hello_name(name):
        return h.hello(name)

    @app.route('/dcbot/message', methods=['POST'])
    def dcbot_send():
        nonlocal ws
        data = request.get_json()
        print(data, flush=True)
        if not isinstance(data, dict):
            return jsonify({'message': 'invalid json'}), 400
        if 'message' not in data:
            return jsonify({'message': 'message is required'}), 400

        try:
            print('sending message to dcbot', flush=True)
            ws.send(data['message'])
        except Exception as e:
            print(e, flush=True)
            print('reconnecting dcbot', flush=True)
            try:
                ws = connect_dcbot()
                ws.send(data['message'])
            except Exception as e:
                print(e, flush=True)
                return jsonify({'message': 'cannot send message'}), 500

        return jsonify({'message': 'ok'}), 200
    
    @app.route('/gen', methods=['POST'])
    def gen():
        if 'file' not in request.files:
            return jsonify({'message': 'file is required'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'message': 'file is required'}), 400
        if file and file.filename.endswith('.zip'):
            # save zip to temp with now datetime dir
            now = datetime.datetime.now()
            temp_dir = f'temp-{now.strftime("%Y-%m-%d-%H-%M-%S")}'
            os.makedirs(temp_dir)
            zip_path = os.path.join(temp_dir, file.filename)
            file.save(zip_path)
            # unzip
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            # remove zip
            os.remove(zip_path)
            # 確認長度是否為 6
            mdpdf = d.gen(temp_dir)
            shutil.rmtree(temp_dir)
            html = markdown.markdown(mdpdf)
            pdf = HTML(string=html).write_pdf()
            buffer = BytesIO(pdf)
            return send_file(buffer, as_attachment=True, download_name="output.pdf", mimetype='application/pdf')
        return jsonify({'message': 'invalid file'}), 400
    @app.route('/dcbot/guilds/<guild_id>/channels/<channel_id>/cloud_run_services/<region>/<project_id>/<service_name>', methods=['POST'])
    def register_cloud_run_service(guild_id, channel_id, region, project_id, service_name):
        return t.register_cloud_run_service(guild_id, channel_id, region, project_id, service_name)
    
    @app.route('/dcbot/guilds/<guild_id>/channels/<channel_id>/cloud_run_services/<region>/<project_id>/<service_name>', methods=['DELETE'])
    def unregister_cloud_run_service(guild_id, channel_id, region, project_id, service_name):
        return t.unregister_cloud_run_service(guild_id, channel_id, region, project_id, service_name)
    
    @app.route('/dcbot/guilds/<guild_id>/channels/<channel_id>/cloud_run_services', methods=['GET'])
    def list_cloud_run_services(guild_id, channel_id):
        return t.list_cloud_run_services(guild_id, channel_id)
    
    @app.teardown_appcontext
    def close_db(error):
        # 如果這個請求中用到了資料庫連接，就關閉它
        if 'db' in g:
            g.db.close()

         
    return app
