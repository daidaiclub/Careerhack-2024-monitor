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
import json
import base64
import io


# --- env

dotenv.load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
WEBSOCKET_PORT = int(os.getenv('WEBSOCKET_PORT'))
MONITOR_URL = os.getenv('MONITOR_URL')

# --- logging

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s [%(funcName)s]: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# --- global vars


# --- websockets


async def websocket_handler(websocket, path):
    """handle websocket messages"""
    async for ws_message in websocket:
        # logger.debug("received message:\n%s", ws_message)
        try:
            ws_message_json = json.loads(ws_message)
        except json.decoder.JSONDecodeError as e:
            logger.error('json decode error: %s', e)
            continue
        if not isinstance(ws_message_json, dict):
            logger.error('message is not dict: %s', ws_message_json)
            continue

        if 'channel_id' not in ws_message_json:
            logger.error('message does not contain "channel_id": %s', ws_message_json)
            continue
        message = ws_message_json.get('message', None)
        file_base64 = ws_message_json.get('file_base64', None)
        channel_id = ws_message_json['channel_id']
        reply_to = ws_message_json.get('reply_to', None)
        try:
            channel_id = int(channel_id)
        except ValueError as e:
            logger.error('channel_id is not int: %s', e)
            continue
        if reply_to is not None:
            try:
                reply_to = int(reply_to)
            except ValueError as e:
                logger.error('reply_to is not int: %s', e)
                continue

        channel = client.get_channel(channel_id)
        if not channel:
            logger.error("can't access channel: %s", channel_id)
            continue
        if not isinstance(channel, discord.TextChannel):
            logger.error('channel is not TextChannel: %s', channel)
            continue
        if not channel.permissions_for(channel.guild.me).send_messages:
            logger.error("can't send message to channel: %s", channel_id)
            continue

        file = None
        if file_base64:
            try:
                file_bytes = base64.b64decode(file_base64)
            except Exception as e:
                logger.error('base64 decode error: %s', e)
                continue
            file = discord.File(io.BytesIO(file_bytes), 'report.pdf')
        if reply_to:
            try:
                message_to_reply = await channel.fetch_message(reply_to)
            except discord.NotFound:
                logger.error('message to reply not found: %s', reply_to)
                continue
            if not message_to_reply:
                logger.error('message to reply not found: %s', reply_to)
                continue

            await message_to_reply.reply(message, file=file)
            logger.debug('replied to channel: %s, message: %s, file: %s', channel_id, reply_to, file)
            continue
        await channel.send(message, file=file)
        logger.debug('sent to channel: %s', channel_id)

# --- discord

intents = discord.Intents.all()
client = commands.Bot(command_prefix='!', intents=intents)


@client.event
async def on_ready():
    """called when discord bot is ready"""
    try:
        synced = await client.tree.sync()
        logger.debug('synced: %s', synced)
    except HTTPException as e:
        logger.error('sync failed: %s', e)


@client.event
async def on_message(message):
    """called when discord bot receives a message"""
    if message.author == client.user:
        return
    logger.debug("received user message:\n%s", message)
    await client.process_commands(message)


@client.command()
async def ping(ctx, arg=''):
    """test ping pong"""
    logger.debug('ping %s', arg)
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
    logger.debug('url: %s', url)
    logger.debug('payload: %s', payload)
    logger.debug('headers: %s', headers)
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    logger.debug('response: %s', response)
    await interaction.response.send_message(f'echo_by_monitor: {response}', ephemeral=True)


@client.tree.command()
async def slash_ping(interaction: discord.interactions.Interaction, arg: str = ''):
    """test slash ping pong"""
    logger.debug('slash_ping %s', arg)
    await interaction.response.send_message(f'pong {arg}')
    message = await interaction.original_response()
    channel = message.channel
    message_id = message.id
    await interaction.followup.send(f'saved message {message_id}')

    try:
        message = await channel.fetch_message(message_id)
        await message.reply(f'reply pong {arg}')
        await message.edit(content=f'edited message {message_id}')
    except discord.NotFound:
        logger.error('message not found')


@client.tree.command()
async def gen_report_by_csv(interaction: discord.interactions.Interaction, zip_file: discord.Attachment = None):
    """send zip file containing csv to generate report"""
    if zip_file:
        logger.debug('received file: %s', zip_file)
        await interaction.response.send_message(f'attachment received: {zip_file}')
        original_response = await interaction.original_response()
        original_response_id = original_response.id
        channel_id = original_response.channel.id

        # send request to monitor
        await zip_file.save('tmp.zip')
        url = MONITOR_URL + '/gen'
        files = {
            'file': ('tmp.zip', open('tmp.zip', 'rb'), 'application/zip')
        }
        data = {
            'channel_id': channel_id,
            'original_response_id': original_response_id,
        }
        logger.debug('url: %s', url)
        logger.debug('files: %s', files)
        logger.debug('data: %s', data)
        response = requests.post(url, files=files, data=data, timeout=10)
        os.remove('tmp.zip')
        await interaction.followup.send(f'sent request to monitor, waiting for response...')
    else:
        logger.debug('no file received')
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
async def register_cloud_run(
        interaction: discord.interactions.Interaction,
        region: str = '',
        project_id: str = '',
        service_name: str = ''):
    """register cloud run service in this channel"""
    guild_id = interaction.guild.id
    channel_id = interaction.channel.id
    logger.debug('region: %s', region)
    logger.debug('project_id: %s', project_id)
    logger.debug('service_name: %s', service_name)
    url = f'{MONITOR_URL}/dcbot/guilds/{guild_id}/channels/{channel_id}/cloud_run_services/{region}/{project_id}/{service_name}'
    requests.post(url, timeout=10)
    await interaction.response.send_message('register success')


@client.tree.command()
async def unregister_cloud_run(
        interaction,
        region: str = '',
        project_id: str = '',
        service_name: str = ''):
    """unregister cloud run service in this channel"""
    guild_id = interaction.guild.id
    channel_id = interaction.channel.id
    logger.debug('region: %s', region)
    logger.debug('project_id: %s', project_id)
    logger.debug('service_name: %s', service_name)
    url = f'{MONITOR_URL}/dcbot/guilds/{guild_id}/channels/{channel_id}/cloud_run_services/{region}/{project_id}/{service_name}'
    requests.delete(url, timeout=10)
    await interaction.response.send_message('unregister success')


@client.tree.command()
async def list_cloud_run(interaction):
    """list all cloud run services in this channel"""
    guild_id = interaction.guild.id
    channel_id = interaction.channel.id
    url = f'{MONITOR_URL}/dcbot/guilds/{guild_id}/channels/{channel_id}/cloud_run_services'
    response = requests.get(url, timeout=10)
    cloud_run_services = response.json()
    logger.debug('type(cloud_run_services): %s', type(cloud_run_services))
    logger.debug('cloud_run_services: %s', cloud_run_services)
    response_message = 'cloud run services:\n'
    for cloud_run_service in cloud_run_services:
        response_message += f'- service name: **{cloud_run_service['service_name']}**\n'
        response_message += f'  - project id: **{cloud_run_service['project_id']}**\n'
        response_message += f'  - region: **{cloud_run_service['region']}**\n'
    await interaction.response.send_message(response_message)

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
