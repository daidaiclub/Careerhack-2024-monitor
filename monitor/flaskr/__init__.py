from weasyprint import HTML
from io import BytesIO
from flask import Flask, request, jsonify, send_file
import os
import websocket
import dotenv
import threading
import asyncio
import datetime
import zipfile
import shutil
import markdown
import json

from flaskr import dcbot
from flaskr.db import init_db

dotenv.load_dotenv()
DCBOT_SOCKET_URI = os.getenv('DCBOT_SOCKET_URI')

init_db()

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

    @app.route('/dcbot/message', methods=['POST'])
    def dcbot_send():
        nonlocal ws
        data = request.get_json()
        print(data, flush=True)
        if not isinstance(data, dict):
            return jsonify({'message': 'invalid json'}), 400

        if 'channel_id' not in data:
            return jsonify({'message': 'channel_id is required'}), 400

        print('sending message to dcbot', flush=True)
        ws_message = {
            'channel_id': data['channel_id']
        }
        if 'message' in data:
            ws_message['message'] = data['message']
        if 'file_base64' in data:
            ws_message['file_base64'] = data['file_base64']
        if 'reply_to' in data:
            ws_message['reply_to'] = data['reply_to']

        try:
            ws.send(json.dumps(ws_message))
        except Exception as e:
            print(f'error: {e}', flush=True)
            print('reconnecting dcbot', flush=True)
            try:
                ws = connect_dcbot()
                ws.send(json.dumps(ws_message))
            except Exception as e:
                print(e, flush=True)
                return jsonify({'message': 'cannot send message'}), 500

        return jsonify({'message': 'ok'}), 200
    
    @app.route('/gen', methods=['POST'])
    def gen():
        # Validate file
        if 'file' not in request.files:
            return jsonify({'message': 'file is required ss'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'message': 'file is required'}), 400
        
        if file and file.filename.endswith('.zip'):
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

            # gen AI report
            mdpdf = dcbot.genai(temp_dir)
            shutil.rmtree(temp_dir)
            html = markdown.markdown(mdpdf)
            pdf = HTML(string=html).write_pdf()
            buffer = BytesIO(pdf)

            return send_file(buffer, as_attachment=True, download_name="output.pdf", mimetype='application/pdf')
        
        return jsonify({'message': 'invalid file'}), 400
    
    @app.route('/dcbot/guilds/<guild_id>/channels/<channel_id>/cloud_run_services/<region>/<project_id>/<service_name>', methods=['POST'])
    def register_cloud_run_service(guild_id, channel_id, region, project_id, service_name):
        return dcbot.register_cloud_run_service(guild_id, channel_id, region, project_id, service_name)
    
    @app.route('/dcbot/guilds/<guild_id>/channels/<channel_id>/cloud_run_services/<region>/<project_id>/<service_name>', methods=['DELETE'])
    def unregister_cloud_run_service(guild_id, channel_id, region, project_id, service_name):
        return dcbot.unregister_cloud_run_service(guild_id, channel_id, region, project_id, service_name)
    
    @app.route('/dcbot/guilds/<guild_id>/channels/<channel_id>/cloud_run_services', methods=['GET'])
    def list_cloud_run_services(guild_id, channel_id):
        return dcbot.list_cloud_run_services(guild_id, channel_id)

    return app
