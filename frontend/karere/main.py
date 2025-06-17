# frontend/karere/main.py

import sys
import os
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib
from .websocket_client import WebSocketClient

class KarereApplication(Adw.Application):
    """The main Karere Application class."""

    def __init__(self, **kwargs):
        super().__init__(application_id='io.github.tobagin.Karere', **kwargs)
        self.win = None
        self.ws_client = None

    def do_startup(self):
        Adw.Application.do_startup(self)
        resource_file = 'karere-resources.gresource'
        if not os.path.exists(resource_file):
            print(f"ERROR: Resource file not found at: {os.path.abspath(resource_file)}")
            sys.exit(1)
        res = Gio.Resource.load(resource_file)
        Gio.resources_register(res)
        print("Resources loaded successfully.")

    def do_activate(self):
        from .window import KarereWindow
        if not self.win:
            self.win = KarereWindow(application=self)
            self.setup_websocket()
        self.win.present()

    def setup_websocket(self):
        """Initializes and connects signals for the WebSocket client."""
        self.ws_client = WebSocketClient()
        self.ws_client.connect('qr-received', self.on_qr_received)
        self.ws_client.connect('status-update', self.on_status_update)
        self.ws_client.connect('connection-opened', self.on_connection_opened)
        self.ws_client.connect('connection-closed', self.on_connection_closed)
        self.ws_client.connect('new-message', self.on_new_message)
        self.ws_client.connect('initial-chats', self.on_initial_chats)
        self.ws_client.connect('baileys-ready', self.on_baileys_ready)
        self.ws_client.start()
        print("WebSocket client setup and started.")

    def on_qr_received(self, _, qr_url):
        self.win.show_qr_view()
        self.win.show_qr_code(qr_url)

    def on_status_update(self, _, message):
        self.win.show_toast(message)

    def on_connection_opened(self, _):
        """Handler for when the WebSocket connection to the backend is established."""
        print("WebSocket connection to backend service is open.")
        if self.win.main_stack.get_visible_child_name() == 'reconnecting_view':
            self.win.main_stack.set_visible_child_name('connecting_view')

    def on_connection_closed(self, _):
        """Handler for when the connection to the backend is lost."""
        self.win.show_reconnecting_view()
        
    def on_baileys_ready(self, _):
        """
        Handler for when the backend is fully connected to WhatsApp.
        Now we request the initial chats.
        """
        print("Backend is ready. Switching to chat view and requesting chats.")
        self.win.show_chat_view()
        self.ws_client.send_command('get_initial_chats') # Request chats

    def on_initial_chats(self, _, chats):
        """Handler for receiving the initial list of chats."""
        print(f"Received {len(chats)} initial chats.")
        for chat in chats:
            self.win.add_or_update_chat(chat['jid'], chat['lastMessage'])

    def on_new_message(self, _, from_jid, body):
        print(f"New message from {from_jid}: {body}")
        self.win.add_or_update_chat(from_jid, body)

def main():
    app = KarereApplication()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main())
