import os
import asyncio
import discord
import websockets
import dotenv

dotenv.load_dotenv()

# --- websockets ----

async def response(websocket, path):
    global channel

    while True:
        try:
            message = await websocket.recv()

            print(f"[ws server] message  < {message}")

            #answer = f"my answer: [{message}]"
            #await websocket.send(answer)   # if client expect `response` then server has to send `response`
            #print(f"[ws server] answer > {answer}")

            if not channel:
                print('[ws server] getting discord channel:', CHANNEL_ID)
                channel = client.get_channel(CHANNEL_ID)

            if not channel:
                print("[ws server] can't access channel:", CHANNEL_ID)
            else:
                print('[ws server] channel:', channel, 'message:', message)
                #await channel.send(f'websockets: {message}')
                await channel.send(message)
        except websockets.exceptions.ConnectionClosedOK:
            print('[ws server] connection closed')
            break

# --- discord ---

intents = discord.Intents.all()
client = discord.Client(intents=intents)

# `get_channel()` has to be used after `client.run()`
#print(client.get_channel(MY_CHANNEL_ID))  # None

@client.event
async def on_ready():
    global channel

    if not channel:
        print('[on_ready] getting discord channel:', CHANNEL_ID)
        channel = client.get_channel(CHANNEL_ID)  # access to channel

    if not channel:
        print("[on_ready] can't access channel:", CHANNEL_ID)
    else:
        print('[on_ready] channel:', channel)

@client.event
async def on_message(message):
    if message.author != client.user:
        print('[on_message] message.content:', message.content)

# --- start ---

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# - websockets -

print('running websockets ws://0.0.0.0:8000')
server = websockets.serve(
    response,
    '0.0.0.0',
    '8000',
    ping_interval=10,
    ping_timeout=5,
)
loop.run_until_complete(server)
# without `run_forever()` because `client.run()` will run `run_forever()`

# - discord -

channel = None   # set default value at start

print('running discord')
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))
loop.run_until_complete(client.start(TOKEN))
loop.run_forever()