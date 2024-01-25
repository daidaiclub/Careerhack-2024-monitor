import os
import asyncio
import discord
from discord.ext import commands
import websockets

# --- websockets ----

async def response(websocket, path): 
    global channel

    message = await websocket.recv()
    print(f"[ws server] message  < {message}")
    
    #answer = f"my answer: [{message}]"
    
    #await websocket.send(answer)   # if client expect `response` then server has to send `response`
    #print(f"[ws server] answer > {answer}")    

    # `get_channel()` has to be used after `client.run()`
    
    if not channel:
        print('[ws server] getting discord channel:', MY_CHANNEL_ID)
        channel = bot.get_channel(MY_CHANNEL_ID)  # access to channel

    if not channel:
        print("[ws server] can't access channel:", MY_CHANNEL_ID)
    else:        
        print('[ws server] channel:', channel, 'message:', message)
        #await channel.send(f'websockets: {message}')
        await channel.send(message)
    
# --- discord ---

MY_CHANNEL_ID = 709507681441808388  # you have to use own number

bot = commands.Bot(command_prefix="!")

# `get_channel()` has to be used after `client.run()`
#print(client.get_channel(MY_CHANNEL_ID))  # None

@bot.event
async def on_ready():
    global channel 
    
    if not channel:
        print('[on_ready] getting discord channel:', MY_CHANNEL_ID)
        channel = bot.get_channel(MY_CHANNEL_ID)  # access to channel
    
    if not channel:
        print("[on_ready] can't access channel:", MY_CHANNEL_ID)
    else:        
        print('[on_ready] channel:', channel)

#@bot.event
#async def on_message(message):
#    if message.author != bot.user:   
#        print('message.content:', message.content)

@bot.command()
async def ping(ctx):
    await ctx.send('pong')
    
# --- start ---

# - websockets -

print('running websockets ws://0.0.0.0:8000')
server = websockets.serve(response, '0.0.0.0', '8000')
asyncio.get_event_loop().run_until_complete(server)
# without `run_forever()` because `client.run()` will run `run_forever()`

# - discord -

channel = None   # set default value at start

print('running discord')
TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)