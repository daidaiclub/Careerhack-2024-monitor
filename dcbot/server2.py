import asyncio

import websockets
from websockets.legacy.server import WebSocketServerProtocol


class CustomClientProtocol(WebSocketServerProtocol):
    async def ping(self, data: bytes = b'') -> None:
        print("收到 ping")
        await super().ping(data)


async def handler(websocket):
    async for message in websocket:
        print(message)
        await websocket.send(message + " (伺服器回應)")


async def main():
    async with websockets.serve(handler, "", 8001, create_protocol=CustomClientProtocol):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())