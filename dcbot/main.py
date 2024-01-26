import os
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import websockets
import dotenv

dotenv.load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))
WEBSOCKET_PORT = int(os.getenv('WEBSOCKET_PORT'))

discord_channel = None

# --- websockets ----

async def response(websocket, path):
    global discord_channel

    async for message in websocket:
        print(f"[ws server] message  < {message}")

        if not discord_channel:
            print('[ws server] getting discord channel:', DISCORD_CHANNEL_ID)
            discord_channel = client.get_channel(DISCORD_CHANNEL_ID)
        
        if not discord_channel:
            print("[ws server] [ERROR] can't access channel:", DISCORD_CHANNEL_ID)
        else:
            print('[ws server] channel:', discord_channel, 'message:', message)
            await discord_channel.send(message)
            print('[ws server] message sent')

# --- discord ---

intents = discord.Intents.all()
client = commands.Bot(command_prefix='!', intents=intents)

@client.event
async def on_ready():
    global discord_channel

    if not discord_channel:
        print('[on_ready] getting discord channel:', DISCORD_CHANNEL_ID)
        discord_channel = client.get_channel(DISCORD_CHANNEL_ID)

    if not discord_channel:
        print("[on_ready] can't access channel:", DISCORD_CHANNEL_ID)
    else:
        print('[on_ready] channel:', discord_channel)
    
    try:
        synced = await client.tree.sync()
        print('[on_ready] synced:', synced)
    except Exception as e:
        print('[on_ready] [ERROR] sync failed:', e)

@client.command()
async def ping(ctx, arg=''):
    print(f'[ping] ping {arg}')
    await ctx.send(f'pong {arg}')

@client.tree.command()
async def slash_ping(interaction):
    print('[slash_ping] ping')
    await interaction.response.send_message('pong')

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    print('[on_message] message.content:', message.content)
    await client.process_commands(message)

# --- start ---

def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # - websockets -

    print(f'running websockets on port {WEBSOCKET_PORT}')
    server = websockets.serve(response, '', WEBSOCKET_PORT)
    loop.run_until_complete(server)

    # - discord -

    print('running discord')
    loop.run_until_complete(client.start(DISCORD_TOKEN))
    loop.run_forever()

if __name__ == '__main__':
    main()