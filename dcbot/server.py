import asyncio
import websockets
from websockets.legacy.server import WebSocketServerProtocol

class CustomClientProtocol(WebSocketServerProtocol):
    async def ping(self, data: bytes = b'') -> None:
        print("收到 ping")
        await super().ping(data)


async def echo(websocket: WebSocketServerProtocol, path: str) -> None:
    async for message in websocket:
        print(message)
        await websocket.send(message)


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

start_server = websockets.serve(
    echo,
    port=8000,
    ping_interval=20,
    ping_timeout=10,
    create_protocol=CustomClientProtocol
)

loop.run_until_complete(start_server)
loop.run_forever()
