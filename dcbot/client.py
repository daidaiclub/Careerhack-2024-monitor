import websocket
import threading
import time

def on_message(ws, message):
    print("Received message: " + message)

def on_error(ws, error):
    print("Error: " + str(error))

def on_close(ws, close_status_code, close_msg):
    print("### WebSocket Closed ###")

def on_open(ws):
    def run(*args):
        for i in range(3):
            time.sleep(1)
            ws.send("Hello %d" % i)
        time.sleep(1)
        message = input("Enter message: ")
        ws.send(message)
        time.sleep(1)
        ws.close()
    threading.Thread(target=run).start()

if __name__ == "__main__":
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp("ws://localhost:8765",
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)

    ws.run_forever()
