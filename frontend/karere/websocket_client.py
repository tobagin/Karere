# frontend/karere/websocket_client.py

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GObject, GLib

import json
import threading
import websocket # Make sure to install websocket-client: pip install websocket-client
import time

class WebSocketClient(GObject.Object):
    """
    Handles the connection to the Node.js backend in a separate thread
    and emits GObject signals to communicate with the GTK main thread.
    """
    __gsignals__ = {
        'connection-opened': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'connection-closed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'qr-received': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'status-update': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'new-message': (GObject.SignalFlags.RUN_FIRST, None, (str, str,)),
        'initial-chats': (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT,)),
        'baileys-ready': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'message-sent': (GObject.SignalFlags.RUN_FIRST, None, (str, str,)),
        'message-error': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'message-history': (GObject.SignalFlags.RUN_FIRST, None, (str, GObject.TYPE_PYOBJECT,)),
    }

    def __init__(self, url="ws://localhost:8765"):
        super().__init__()
        self.ws_app = None
        self.url = url
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while True:
            print("Attempting to connect to WebSocket server...")
            self.ws_app = websocket.WebSocketApp(
                self.url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            self.ws_app.run_forever()
            print("WebSocket disconnected. Retrying in 5 seconds...")
            time.sleep(5)

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            msg_data = data.get('data')

            print(f"Received message type: {msg_type}")

            if msg_type == 'qr':
                GLib.idle_add(self.emit, 'qr-received', msg_data['url'])
            elif msg_type == 'status':
                GLib.idle_add(self.emit, 'status-update', msg_data['message'])
            elif msg_type == 'baileys_ready':
                GLib.idle_add(self.emit, 'baileys-ready')
            elif msg_type == 'newMessage':
                GLib.idle_add(self.emit, 'new-message', msg_data['from'], msg_data['body'])
            elif msg_type == 'initial_chats':
                GLib.idle_add(self.emit, 'initial-chats', msg_data['chats'])
            elif msg_type == 'message_sent':
                GLib.idle_add(self.emit, 'message-sent', msg_data['to'], msg_data['message'])
            elif msg_type == 'message_error':
                GLib.idle_add(self.emit, 'message-error', msg_data['error'])
            elif msg_type == 'message_history':
                GLib.idle_add(self.emit, 'message-history', msg_data['jid'], msg_data['messages'])
        except Exception as e:
            print(f"Error processing message: {e}")

    def _on_open(self, ws):
        print("WebSocket connection opened.")
        GLib.idle_add(self.emit, 'connection-opened')

    def _on_error(self, ws, error):
        print(f"WebSocket Error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        print("WebSocket connection closed.")
        GLib.idle_add(self.emit, 'connection-closed')

    def send_command(self, command_type, data=None):
        """Sends a generic command to the backend."""
        if self.ws_app and self.ws_app.sock and self.ws_app.sock.connected:
            message = { "type": command_type, "data": data or {} }
            self.ws_app.send(json.dumps(message))
            print(f"Sent command to backend: {command_type}")
        else:
            print("Cannot send command, WebSocket is not connected.")
