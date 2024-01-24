import discord
from discord.ext import commands, tasks
import asyncio
import json

import pandas as pd

from llm import gen_solution
from main import simulate_realtime_csv, check_metrics_abnormalities
import os

from dotenv import load_dotenv
load_dotenv()

# 設置 Discord Bot 的 Token
TOKEN = os.getenv('DISCORD_TOKEN')

# 創建一個 bot 實例
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())


async def check_alerts():
    metrics_datas: list[pd.DataFrame] = []
    times = {
        'cpu': 0,
        'memory': 0,
    }
    channel = bot.get_channel(1199285805760401449)

    for metrics in simulate_realtime_csv():
        metrics_datas.append(metrics)
        if check_metrics_abnormalities(metrics, times):
            alert_metrics = metrics_datas[-2:]
            metrics_json = json.dumps([metrice.to_dict()
                                      for metrice in alert_metrics], indent=2)
            alert = gen_solution('', metrics_json)

            alert_metrics = [metrice.to_string() for metrice in alert_metrics]

            await channel.send('異常指標\n' + str(alert_metrics))
            await channel.send(alert)
            break

# 當 bot 啟動並準備好後，開始執行定時任務


@bot.event
async def on_ready():
    print(f'{bot.user.name} 已連線到 Discord!')
    await check_alerts()

# 啟動 bot
bot.run(TOKEN)
