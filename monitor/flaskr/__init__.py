""" The flask application package """

import asyncio
import datetime
import base64
import json
import shutil
import threading
import logging
import os
import zipfile
from io import BytesIO
import dotenv
import markdown
from weasyprint import HTML
from flask import Flask, request, jsonify, send_file
from flaskr import dcbot
from flaskr.db import init_db
from flaskr.dcbot_websocket import DCBotWebSocket

dotenv.load_dotenv()

# --- logger

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s [%(funcName)s]: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

init_db()

def create_app() -> Flask:
    """
    Creates and configures the Flask application.

    Returns:
        Flask: The configured Flask application.
    """
    # asyncio event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # flask app
    app = Flask(__name__)
    logger.debug('create_app')

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
        logger.debug('dcbot_send: %s', data)
        if not isinstance(data, dict):
            logger.warning('invalid json: %s', data)
            return jsonify({'message': 'invalid json'}), 400

        if 'channel_id' not in data:
            logger.warning('channel_id is required: %s', data)
            return jsonify({'message': 'channel_id is required'}), 400

        logger.debug('sending message to dcbot')
        ws_message = {
            'channel_id': data['channel_id']
        }
        if 'message' in data:
            ws_message['message'] = data['message']
        if 'file_base64' in data:
            ws_message['file_base64'] = data['file_base64']
        if 'reply_to' in data:
            ws_message['reply_to'] = data['reply_to']

        logger.debug('ws_message: %s', ws_message)
        result = DCBotWebSocket.send(json.dumps(ws_message))
        if not result:
            logger.warning('cannot send message: %s', ws_message)
            return jsonify({'message': 'cannot send message'}), 500
        return jsonify({'message': 'ok'}), 200

    @app.route('/gen', methods=['POST'])
    def gen():
        # Validate file
        if 'file' not in request.files:
            logger.warning('file is required')
            return jsonify({'message': 'file is required ss'}), 400

        file = request.files['file']
        channel_id = request.form['channel_id']
        reply_to = request.form['original_response_id']
        if file.filename == '':
            logger.warning('file is required')
            return jsonify({'message': 'file is required'}), 400

        if file and file.filename.endswith('.zip'):
            now = datetime.datetime.now()
            temp_dir = f'temp-{now.strftime("%Y-%m-%d-%H-%M-%S")}'
            os.makedirs(temp_dir)
            zip_path = os.path.join(temp_dir, file.filename)
            logger.debug('zip_path: %s', zip_path)
            file.save(zip_path)
            # unzip
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            # remove zip
            os.remove(zip_path)

            def ws(temp_dir, channel_id, reply_to):
                logger.debug('ws: %s', temp_dir)
                # gen AI report
                mdpdf = dcbot.genai(temp_dir)
                shutil.rmtree(temp_dir)
                html = markdown.markdown(mdpdf)
                pdf = HTML(string=html).write_pdf()

                buffer = BytesIO(pdf)
                b64file = base64.b64encode(buffer.getvalue())
                ws_message = {
                    'channel_id': channel_id,
                    'file_base64': b64file.decode(),
                    'reply_to': reply_to,
                }
                DCBotWebSocket.send(json.dumps(ws_message))

            th = threading.Thread(target=ws, args=(
                temp_dir, channel_id, reply_to))
            th.daemon = True
            th.start()
            return jsonify({'message': 'ok'}), 200

        return jsonify({'message': 'invalid file'}), 400

    @app.route(
        '/dcbot/guilds/<guild_id>/channels/<channel_id>/' + 
        'cloud_run_services/<region>/<project_id>/<service_name>',
        methods=['POST'])
    def register_cloud_run_service(guild_id, channel_id, region, project_id, service_name):
        return dcbot.register_cloud_run_service(
            guild_id, channel_id, region, project_id, service_name)

    @app.route(
        '/dcbot/guilds/<guild_id>/channels/<channel_id>/' +
        'cloud_run_services/<region>/<project_id>/<service_name>',
        methods=['DELETE'])
    def unregister_cloud_run_service(guild_id, channel_id, region, project_id, service_name):
        return dcbot.unregister_cloud_run_service(
            guild_id, channel_id, region, project_id, service_name)

    @app.route(
        '/dcbot/guilds/<guild_id>/channels/<channel_id>/cloud_run_services',
        methods=['GET'])
    def list_cloud_run_services(guild_id, channel_id):
        return dcbot.list_cloud_run_services(guild_id, channel_id)

    dcbot.init_already_registered_services()
    return app
