import asyncio
import websockets
from websockets.legacy.client import Connect, WebSocketClientProtocol

uri = 'ws://localhost:8000'

class CustomClientProtocol(WebSocketClientProtocol):
    async def ping(self, data: bytes = b'') -> None:
        print("收到 ping")
        await super().ping(data)

async def send_message():
    async with websockets.connect(
        uri,
        create_protocol=CustomClientProtocol
    ) as websocket:
        while True:
            message = input("msg: ")
            if message == 'exit':
                break

            await websocket.send(message)
            print(f"[ws client] message  > {message}")

            answer = await websocket.recv()
            print(f"[ws client] answer < {answer}")

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(send_message())
loop.run_forever()

#########

# import asyncio
# import websockets

# async def client():
#     uri = "ws://0.0.0.0:8000"
#     async with websockets.connect(uri) as websocket:
#         while True:
#             message = input("請輸入要發送的消息: ")
#             await websocket.send(message)
#             response = await websocket.recv()
#             print(f"收到回應: {response}")

# asyncio.run(client())

# loop = asyncio.new_event_loop()
# asyncio.set_event_loop(loop)
# loop.run_until_complete(hello())