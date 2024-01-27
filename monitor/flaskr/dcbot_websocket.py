""" dcbot websocket """

import os
import asyncio
import threading
import logging
import websocket

from websocket import WebSocketException

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
            logging.debug('dcbot opened')
            connected_event.set()

        def on_message(ws, message):
            logging.debug('dcbot message: %s', message)

        def on_error(ws, error):
            logging.error('dcbot error: %s', error)

        def on_close(ws, close_status_code, close_msg):
            if close_status_code == 1006:
                logging.error('dcbot closed: %s', close_msg)

            logging.debug('dcbot closed')
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
        logging.debug('sending message to dcbot: %s', message)
        try:
            DCBotWebSocket._ws.send(message)
        except WebSocketException as e:
            logging.error('error: %s', e)
            try:
                DCBotWebSocket.connect_dcbot()
                DCBotWebSocket._ws.send(message)
            except WebSocketException as inner_e:
                logging.error('error: %s', inner_e)
                return False
        return True
