""" dcbot websocket """

import os
import asyncio
import threading
import websocket
from websocket import WebSocketException
import logging

# --- logger

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s [%(funcName)s]: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

DCBOT_SOCKET_URI = os.getenv('DCBOT_SOCKET_URI')

class DCBotWebSocket:
    """
    A class representing a WebSocket connection to the DCBot server.
    """

    _ws = None

    @staticmethod
    def connect_dcbot():
        """
        Connects to the DCBot server using WebSocket.
        """
        print(f'connecting dcbot to {DCBOT_SOCKET_URI}', flush=True)
        connected_event = asyncio.Event()

        def on_open(ws):
            logger.debug('dcbot connected %s', ws)
            connected_event.set()

        def on_message(ws, message):
            logger.debug('dcbot message: %s', message)

        def on_error(ws, error):
            logger.error('dcbot error: %s', error)

        def on_close(ws, close_status_code, close_msg):
            if close_status_code == 1006:
                logger.error('dcbot closed: %s', close_msg)

            logger.debug('dcbot closed: %s', close_msg)
            connected_event.clear()
            DCBotWebSocket._ws = None

        DCBotWebSocket._ws = websocket.WebSocketApp(
            DCBOT_SOCKET_URI,
            on_message = on_message,
            on_error = on_error,
            on_open = on_open,
            on_close = on_close
        )
        wst = threading.Thread(target=DCBotWebSocket._ws.run_forever)
        wst.daemon = True
        wst.start()

    @staticmethod
    def send(message: str):
        """
        Sends a message to the DCBot server.

        Args:
            message (str): The message to send.

        Returns:
            bool: True if the message was sent successfully, False otherwise.
        """
        logger.debug('sending message to dcbot: %s', message)
        try:
            DCBotWebSocket._ws.send(message)
        except WebSocketException as e:
            logger.error('error: %s', e)
            try:
                DCBotWebSocket.connect_dcbot()
                DCBotWebSocket._ws.send(message)
            except WebSocketException as inner_e:
                logger.error('error: %s', inner_e)
                return False
        return True
