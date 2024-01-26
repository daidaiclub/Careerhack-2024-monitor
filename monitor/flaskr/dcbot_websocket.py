import os
import asyncio
import websocket
import threading

DCBOT_SOCKET_URI = os.getenv('DCBOT_SOCKET_URI')

class DCBotWebSocket:
    _ws = None

    @staticmethod
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

        DCBotWebSocket._ws = websocket.WebSocketApp(
            DCBOT_SOCKET_URI,
            on_message = on_message,
            on_error = on_error,
            on_open = on_open,
            on_close = on_close
        )
        wst = threading.Thread(target=DCBotWebSocket._ws.run_forever)
        wst.daemon = True
        wst.start()
    
    @staticmethod
    def send(message: str):
        print(f'sending message to dcbot: {message}', flush=True)
        try:
            DCBotWebSocket._ws.send(message)
        except Exception as e:
            print(f'error: {e}', flush=True)
            try:
                DCBotWebSocket.connect_dcbot()
                DCBotWebSocket._ws.send(message)
            except Exception as e:
                print(f'error: {e}', flush=True)
                return False
        return True