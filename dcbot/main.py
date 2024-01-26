import os
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import websockets
import dotenv
import requests
import json

dotenv.load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))
WEBSOCKET_PORT = int(os.getenv('WEBSOCKET_PORT'))
MONITOR_URL = os.getenv('MONITOR_URL')

discord_channel = None

# --- websockets ----

async def response(websocket, path):
    global discord_channel

    async for message in websocket:
        print(f"[ws server] message  < {message}", flush=True)

        if not discord_channel:
            print('[ws server] getting discord channel:', DISCORD_CHANNEL_ID, flush=True)
            discord_channel = client.get_channel(DISCORD_CHANNEL_ID)
        if not discord_channel:
            print("[ws server] [ERROR] can't access channel:", DISCORD_CHANNEL_ID, flush=True)
        else:
            print('[ws server] channel:', discord_channel, 'message:', message, flush=True)
            await discord_channel.send(message)
            print('[ws server] message sent', flush=True)

# --- discord ---

intents = discord.Intents.all()
client = commands.Bot(command_prefix='!', intents=intents)

@client.event
async def on_ready():
    global discord_channel

    if not discord_channel:
        print('[on_ready] getting discord channel:', DISCORD_CHANNEL_ID, flush=True)
        discord_channel = client.get_channel(DISCORD_CHANNEL_ID)

    if not discord_channel:
        print("[on_ready] can't access channel:", DISCORD_CHANNEL_ID, flush=True)
    else:
        print('[on_ready] channel:', discord_channel, flush=True)
    
    try:
        synced = await client.tree.sync()
        print('[on_ready] synced:', synced, flush=True)
    except Exception as e:
        print('[on_ready] [ERROR] sync failed:', e, flush=True)

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    print('[on_message] message.content:', message.content, flush=True)
    await client.process_commands(message)

@client.command()
async def ping(ctx, arg=''):
    print(f'[ping] ping {arg}', flush=True)
    await ctx.send(f'pong {arg}')

@client.tree.command()
async def echo_by_monitor(interaction):
    url = MONITOR_URL + '/dcbot/message'
    payload = {
        'message': 'hello to monitor'
    }
    headers = {
        'Content-Type': 'application/json'
    }
    print('[echo_by_monitor] url:', url, flush=True)
    print('[echo_by_monitor] payload:', payload, flush=True)
    print('[echo_by_monitor] headers:', headers, flush=True)
    response = requests.post(url, json=payload, headers=headers)
    print('[echo_by_monitor] response:', response, flush=True)
    await interaction.response.send_message(f'echo_by_monitor: {response}', ephemeral = True)

@client.tree.command()
async def slash_ping(interaction: discord.interactions.Interaction, arg: str = ''):
    print(f'[slash_ping] ping {arg}', flush=True)
    print(type(interaction), flush=True)
    print(f'interaction.guild_id: {interaction.guild_id}', flush=True)
    print(f'interaction.channel_id: {interaction.channel_id}', flush=True)
    await interaction.response.send_message(f'pong {arg}', ephemeral = True)

@client.tree.command()
async def gen_report_by_csv(interaction, zip_file: discord.Attachment = None):
    if zip_file:
        print('[gen_report_by_csv] zip_file:', zip_file, flush=True)
        await interaction.response.send_message('attachment received')
    else:
        print('[gen_report_by_csv] no file', flush=True)
        await interaction.response.send_message('no file, try again')

@client.tree.command()
async def login_gcp(interaction, email: str = '', password: str = ''):
    print(f'[login_gcp] email: {email}, password: {password}', flush=True)
    await interaction.response.send_message('login success', ephemeral = True)

@client.tree.command()
async def logout_gcp(interaction):
    print('[logout_gcp]', flush=True)
    await interaction.response.send_message('logout success', ephemeral = True)

@client.tree.command()
async def register_cloud_run(interaction, region: str = '', project_id: str = '', service_name: str = ''):
    print(f'[register_cloud_run] region: {region}, project_id: {project_id}, service_name: {service_name}', flush=True)
    await interaction.response.send_message('logout success', ephemeral = True)

@client.tree.command()
async def unregister_cloud_run(interaction, region: str = '', project_id: str = '', service_name: str = ''):
    print(f'[unregister_cloud_run] region: {region}, project_id: {project_id}, service_name: {service_name}', flush=True)
    await interaction.response.send_message('unregister_cloud_run', ephemeral = True)

@client.tree.command()
async def list_cloud_run(interaction):
    print('[list_cloud_run]', flush=True)
    await interaction.response.send_message('list_cloud_run', ephemeral = True)

# --- start ---

def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # - websockets -

    print(f'running websockets on port {WEBSOCKET_PORT}', flush=True)
    server = websockets.serve(response, '', WEBSOCKET_PORT)
    loop.run_until_complete(server)

    # - discord -

    print('running discord', flush=True)
    loop.run_until_complete(client.start(DISCORD_TOKEN))
    loop.run_forever()

if __name__ == '__main__':
    main()