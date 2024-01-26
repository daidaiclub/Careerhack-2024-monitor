"""discord bot with slash commands and websockets"""
import os
import asyncio
import logging
import discord
from discord.ext import commands
from discord import HTTPException
import websockets
import dotenv
import requests

# --- env

dotenv.load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))
WEBSOCKET_PORT = int(os.getenv('WEBSOCKET_PORT'))
MONITOR_URL = os.getenv('MONITOR_URL')

# --- logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s [%(funcName)s]: %(message)s')

# --- global vars

discord_channel = None

# --- websockets

async def websocket_handler(websocket, path):
    """handle websocket messages"""
    global discord_channel

    async for message in websocket:
        logging.debug("received message:\n%s", message)

        if not discord_channel:
            logging.error("can't access channel: %s, retrying...", DISCORD_CHANNEL_ID)
            discord_channel = client.get_channel(DISCORD_CHANNEL_ID)

        if not discord_channel:
            logging.error("can't access channel: %s", DISCORD_CHANNEL_ID)
        else:
            await discord_channel.send(message)
            logging.debug("sent message to discord channel: %s", DISCORD_CHANNEL_ID)

# --- discord

intents = discord.Intents.all()
client = commands.Bot(command_prefix='!', intents=intents)

@client.event
async def on_ready():
    """called when discord bot is ready"""
    global discord_channel

    if not discord_channel:
        logging.debug('getting channel: %s', DISCORD_CHANNEL_ID)
        discord_channel = client.get_channel(DISCORD_CHANNEL_ID)

    if not discord_channel:
        logging.error("can't access channel: %s", DISCORD_CHANNEL_ID)
    else:
        logging.debug('got channel: %s', DISCORD_CHANNEL_ID)

    try:
        synced = await client.tree.sync()
        logging.debug('synced: %s', synced)
    except HTTPException as e:
        logging.error('sync failed: %s', e)


@client.event
async def on_message(message):
    """called when discord bot receives a message"""
    if message.author == client.user:
        return
    logging.debug("received user message:\n%s", message)
    await client.process_commands(message)

@client.command()
async def ping(ctx, arg=''):
    """test ping pong"""
    logging.debug('ping %s', arg)
    await ctx.send(f'pong {arg}')

@client.tree.command()
async def echo_by_monitor(interaction):
    """test send message to monitor to echo back"""
    url = MONITOR_URL + '/dcbot/message'
    payload = {
        'message': 'hello to monitor'
    }
    headers = {
        'Content-Type': 'application/json'
    }
    logging.debug('url: %s', url)
    logging.debug('payload: %s', payload)
    logging.debug('headers: %s', headers)
    response = requests.post(url, json=payload, headers=headers, timeout=5)
    logging.debug('response: %s', response)
    await interaction.response.send_message(f'echo_by_monitor: {response}', ephemeral=True)

@client.tree.command()
async def slash_ping(interaction: discord.interactions.Interaction, arg: str = ''):
    """test slash ping pong"""
    logging.debug('slash_ping %s', arg)
    await interaction.response.send_message(f'pong {arg}', ephemeral = True)

@client.tree.command()
async def gen_report_by_csv(interaction, zip_file: discord.Attachment = None):
    """send zip file containing csv to generate report"""
    if zip_file:
        logging.debug('received file: %s', zip_file)
        await interaction.response.send_message('attachment received')
    else:
        logging.debug('no file received')
        await interaction.response.send_message('no file, try again')

# @client.tree.command()
# async def login_gcp(interaction, email: str = '', password: str = ''):
#     print(f'[login_gcp] email: {email}, password: {password}', flush=True)
#     await interaction.response.send_message('login success', ephemeral = True)

# @client.tree.command()
# async def logout_gcp(interaction):
#     print('[logout_gcp]', flush=True)
#     await interaction.response.send_message('logout success', ephemeral = True)

@client.tree.command()
async def register_cloud_run(interaction, region: str = '', project_id: str = '', service_name: str = ''):
    """register cloud run service in this channel"""
    logging.debug('region: %s', region)
    logging.debug('project_id: %s', project_id)
    logging.debug('service_name: %s', service_name)
    await interaction.response.send_message('logout success', ephemeral = True)

@client.tree.command()
async def unregister_cloud_run(interaction, region: str = '', project_id: str = '', service_name: str = ''):
    """unregister cloud run service in this channel"""
    logging.debug('region: %s', region)
    logging.debug('project_id: %s', project_id)
    logging.debug('service_name: %s', service_name)
    await interaction.response.send_message('unregister_cloud_run', ephemeral = True)

@client.tree.command()
async def list_cloud_run(interaction):
    """list all cloud run services in this channel"""
    print('[list_cloud_run]', flush=True)
    await interaction.response.send_message('list_cloud_run', ephemeral = True)

# --- start ---

def main():
    """main"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # - websockets -

    print(f'running websockets on port {WEBSOCKET_PORT}', flush=True)
    server = websockets.serve(websocket_handler, '', WEBSOCKET_PORT)
    loop.run_until_complete(server)

    # - discord -

    print('running discord', flush=True)
    loop.run_until_complete(client.start(DISCORD_TOKEN))
    loop.run_forever()

if __name__ == '__main__':
    main()
