from weasyprint import HTML
from io import BytesIO
from flask import Flask, request, jsonify, send_file
import os
import dotenv
import asyncio
import datetime
import zipfile
import shutil
import markdown
import json

import base64
from flaskr import dcbot
from flaskr.db import init_db
from flaskr.dcbot_websocket import DCBotWebSocket

dotenv.load_dotenv()

init_db()

def create_app(test_config=None) -> Flask:
    # asyncio event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # flask app
    app = Flask(__name__)

    # websocket
    # websocket.enableTrace(True)
    DCBotWebSocket.connect_dcbot()

    # flask route
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    @app.route('/dcbot/message', methods=['POST'])
    def dcbot_send():
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

        result = DCBotWebSocket.send(json.dumps(ws_message))
        if not result:
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
            def ws():
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
                b64file = base64.b64encode(buffer.getvalue())
                ws_message = {
                    'channel_id': request.form['channel_id'],
                    'file_base64': b64file,
                    'reply_to': request.form['reply_to']
                } 
                DCBotWebSocket.send(json.dumps(ws_message))
            th = threading.Thread(target=ws)
            th.daemon = True
            th.start()
            return jsonify({'message': 'ok'}), 200

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
