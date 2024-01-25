import asyncio
import websockets

async def send_messages():
    uri = "ws://localhost:8001"  # 替換成實際的WebSocket服務器地址

    async with websockets.connect(uri) as websocket:
        while True:
            message = input("輸入訊息 (或輸入 'exit' 來結束): ")
            if message == "exit":
                break
            await websocket.send(message)  # 向伺服器發送訊息

# 開始連接到WebSocket伺服器並持續發送訊息
asyncio.get_event_loop().run_until_complete(send_messages())

