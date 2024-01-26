import os
import websocket
from flask import Flask, request, jsonify
from flaskr import hello as h
import dotenv
import threading
import asyncio

dotenv.load_dotenv()

DCBOT_SOCKET_URI = os.getenv('DCBOT_SOCKET_URI')

def create_app(test_config=None) -> Flask:
    # asyncio event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # flask app
    app = Flask(__name__)

    # websocket
    def connect_dcbot():
        print(f'connecting dcbot to {DCBOT_SOCKET_URI}')
        connected_event = asyncio.Event()

        def on_open(ws):
            print("dcbot opened")
            connected_event.set()

        def on_message(ws, message):
            print(f"dcbot received: {message}")

        def on_error(ws, error):
            print(f'error: {error}')

        def on_close(ws, close_status_code, close_msg):
            print("dcbot closed")

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
        return 'Hello, World!!'

    @app.route('/hello/<name>')
    def hello_name(name):
        return h.hello(name)

    @app.route('/dcbot/message', methods=['POST'])
    def dcbot_send():
        nonlocal ws
        data = request.get_json()
        if 'message' not in data:
            return jsonify({'message': 'message is required'}), 400

        try:
            print('sending message to dcbot')
            ws.send(data['message'])
        except Exception as e:
            print(e)
            print('reconnecting dcbot')
            try:
                ws = connect_dcbot()
                ws.send(data['message'])
            except Exception as e:
                print(e)
                return jsonify({'message': 'cannot send message'}), 500

        return jsonify({'message': 'ok'}), 200

    return app
