import pytest
import os
from unittest.mock import MagicMock, patch, AsyncMock
import websockets
from dcbot.main import client, response
from dcbot import main 
import discord
from discord.ext import commands


@pytest.fixture
def mock_discord_bot(monkeypatch):
    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    mock_discord_channel = AsyncMock(send=AsyncMock())
    mock_client.get_channel = MagicMock(return_value=mock_discord_channel)
    monkeypatch.setattr(main, 'client', mock_client)
    return mock_client
    

@pytest.fixture
def mock_websocket(monkeypatch):
    # 模擬 WebSocket
    async_mock = MagicMock()
    monkeypatch.setattr("websockets.serve", async_mock)
    return async_mock

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setattr(main, "DISCORD_TOKEN", "fake_token")
    monkeypatch.setattr(main, "DISCORD_CHANNEL_ID", "123456789")
    monkeypatch.setattr(main, "WEBSOCKET_PORT", "8000")

@pytest.mark.asyncio
async def test_websocket_response(monkeypatch, mock_discord_bot, mock_env):
    async def mock_websocket():
        yield "message 1"
    
    monkeypatch.setattr(main, "discord_channel", None)

    await response(mock_websocket(), '')

    mock_discord_bot.get_channel.assert_called_with("123456789")
    mock_discord_bot.get_channel.return_value.send.assert_called_once()

def test_env_variables_loaded(mock_env):
    # 測試環境變量是否載入
    assert main.DISCORD_TOKEN == 'fake_token'
    assert main.DISCORD_CHANNEL_ID == '123456789'
    assert main.WEBSOCKET_PORT == '8000'


