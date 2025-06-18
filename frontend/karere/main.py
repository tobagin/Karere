# frontend/karere/main.py

import sys
import os
import gi
import subprocess
import signal
import atexit
import time
import threading
from pathlib import Path

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib, Gdk

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from websocket_client import WebSocketClient

# Dynamic app ID for Flatpak compatibility
# This will be automatically detected at runtime, but we need a default for resource paths
APP_ID = os.environ.get('FLATPAK_ID', 'io.github.tobagin.Karere')

# Load resources early, before any template decorators are evaluated
def _load_resources_early():
    """Load GResource files before any modules with template decorators are imported."""
    resource_locations = [
        # Flatpak paths
        '/app/share/karere/karere-resources.gresource',
        # Development paths
        'karere-resources.gresource',
        'frontend/karere-resources.gresource',
        '../frontend/karere-resources.gresource',
        os.path.join(os.path.dirname(__file__), '..', '..', 'builddir', 'frontend', 'karere-resources.gresource'),
        # System installation paths
        '/usr/share/karere/karere-resources.gresource',
        '/usr/local/share/karere/karere-resources.gresource',
    ]

    for location in resource_locations:
        if os.path.exists(location):
            try:
                res = Gio.Resource.load(location)
                Gio.resources_register(res)
                print(f"Resources loaded early from: {location}")
                return True
            except Exception as e:
                print(f"Failed to load resources from {location}: {e}")

    print("WARNING: No resource file found during early loading")
    return False

# Load resources immediately
_load_resources_early()

class KarereApplication(Adw.Application):
    """The main Karere Application class."""

    def __init__(self, **kwargs):
        super().__init__(application_id='io.github.tobagin.Karere', **kwargs)
        self.win = None
        self.ws_client = None
        self.backend_process = None
        self.backend_ready = False

        # Register cleanup handlers
        atexit.register(self.cleanup_backend)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def do_startup(self):
        Adw.Application.do_startup(self)

        # Try to find the resource file in different locations
        resource_locations = [
            # Flatpak paths
            '/app/share/karere/karere-resources.gresource',
            # Development paths
            'karere-resources.gresource',
            'frontend/karere-resources.gresource',
            '../frontend/karere-resources.gresource',
            os.path.join(os.path.dirname(__file__), '..', '..', 'builddir', 'frontend', 'karere-resources.gresource'),
            # System installation paths
            '/usr/share/karere/karere-resources.gresource',
            '/usr/local/share/karere/karere-resources.gresource',
        ]

        resource_file = None
        for location in resource_locations:
            if os.path.exists(location):
                resource_file = location
                break

        if resource_file:
            res = Gio.Resource.load(resource_file)
            Gio.resources_register(res)
            print(f"Resources loaded successfully from: {resource_file}")
        else:
            print("WARNING: Resource file not found, continuing without resources")
            print(f"Searched in: {resource_locations}")

        # Load CSS styling
        self.load_css()

        # Start backend process
        self.start_backend()

    def do_activate(self):
        from window import KarereWindow
        if not self.win:
            self.win = KarereWindow(application=self)
            self.load_css()
            # Set up WebSocket client for the window
            from websocket_client import WebSocketClient
            self.win.websocket_client = WebSocketClient(self.win)
            self.setup_websocket()
        self.win.present()

    def start_backend(self):
        """Start the backend Node.js process."""
        try:
            # Find the backend directory
            backend_paths = [
                # Development paths
                os.path.join(os.path.dirname(__file__), '..', '..', 'backend'),
                # Flatpak paths
                '/app/share/karere-backend',
                # System installation paths
                '/usr/share/karere-backend',
                '/usr/local/share/karere-backend',
                # Relative paths
                'backend',
                '../backend',
                '../../backend'
            ]

            backend_dir = None
            for path in backend_paths:
                if os.path.exists(os.path.join(path, 'backend.js')):
                    backend_dir = path
                    break

            if not backend_dir:
                print(f"ERROR: Backend not found in any of these locations: {backend_paths}")
                return False

            print(f"Starting backend from: {backend_dir}")

            # Start the backend process
            self.backend_process = subprocess.Popen(
                ['node', 'backend.js'],
                cwd=backend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group
            )

            print(f"Backend process started with PID: {self.backend_process.pid}")

            # Start a thread to monitor backend output
            threading.Thread(target=self._monitor_backend_output, daemon=True).start()

            # Wait a moment for backend to start
            time.sleep(2)

            return True

        except Exception as e:
            print(f"Failed to start backend: {e}")
            return False

    def _monitor_backend_output(self):
        """Monitor backend process output for debugging."""
        if not self.backend_process:
            return

        try:
            while self.backend_process.poll() is None:
                output = self.backend_process.stdout.readline()
                if output:
                    print(f"Backend: {output.decode().strip()}")

                    # Check if backend is ready
                    if b"WebSocket server started" in output:
                        self.backend_ready = True
                        GLib.idle_add(self._on_backend_ready)

        except Exception as e:
            print(f"Error monitoring backend output: {e}")

    def _on_backend_ready(self):
        """Called when backend is ready to accept connections."""
        print("Backend is ready, setting up WebSocket connection...")
        # Small delay to ensure backend is fully ready
        GLib.timeout_add(1000, self._delayed_websocket_setup)

    def _delayed_websocket_setup(self):
        """Setup WebSocket connection after backend is ready."""
        self.setup_websocket()
        return False  # Don't repeat the timeout

    def setup_websocket(self):
        """Initializes and connects signals for the WebSocket client."""
        if self.ws_client:
            return  # Already setup

        self.ws_client = WebSocketClient()
        self.ws_client.connect('qr-received', self.on_qr_received)
        self.ws_client.connect('status-update', self.on_status_update)
        self.ws_client.connect('connection-opened', self.on_connection_opened)
        self.ws_client.connect('connection-closed', self.on_connection_closed)
        self.ws_client.connect('new-message', self.on_new_message)
        self.ws_client.connect('initial-chats', self.on_initial_chats)
        self.ws_client.connect('baileys-ready', self.on_baileys_ready)
        self.ws_client.connect('message-sent', self.on_message_sent)
        self.ws_client.connect('message-error', self.on_message_error)
        self.ws_client.connect('message-history', self.on_message_history)
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
        # Check if we're currently on the reconnecting page and switch back to loading
        if self.win and hasattr(self.win, 'navigation_view') and self.win.navigation_view:
            current_page = self.win.navigation_view.get_visible_page()
            if current_page == self.win.reconnecting_page:
                self.win.navigation_view.replace([self.win.loading_page])

    def on_connection_closed(self, _):
        """Handler for when the connection to the backend is lost."""
        self.win.show_reconnecting_view()
        
    def on_baileys_ready(self, _):
        """
        Handler for when the backend is fully connected to WhatsApp.
        Now we request the initial chats.
        """
        print("Backend is ready. Switching to chat view and requesting chats.")
        if self.win:
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

    def on_message_sent(self, _, to_jid, message):
        """Handler for when a message is successfully sent."""
        print(f"Message sent to {to_jid}: {message}")
        self.win.show_toast("Message sent")

    def on_message_error(self, _, error):
        """Handler for message sending errors."""
        print(f"Message error: {error}")
        self.win.show_toast(f"Error: {error}")

    def on_message_history(self, _, jid, messages):
        """Handler for receiving message history."""
        print(f"Received {len(messages)} messages for {jid}")
        # Load message history into the window
        self.win.load_message_history_from_backend(jid, messages)

    def load_css(self):
        """Load CSS styling for the application."""
        try:
            css_provider = Gtk.CssProvider()
            css_provider.load_from_resource(f'/{APP_ID.replace(".", "/")}/style.css')

            display = Gdk.Display.get_default()
            Gtk.StyleContext.add_provider_for_display(
                display,
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            print("CSS styling loaded successfully.")
        except Exception as e:
            print(f"Failed to load CSS: {e}")

    def cleanup_backend(self):
        """Clean up the backend process."""
        if self.backend_process:
            try:
                print("Shutting down backend process...")

                # Try graceful shutdown first
                self.backend_process.terminate()

                # Wait for graceful shutdown
                try:
                    self.backend_process.wait(timeout=5)
                    print("Backend process terminated gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    print("Backend process didn't terminate gracefully, forcing shutdown...")
                    os.killpg(os.getpgid(self.backend_process.pid), signal.SIGKILL)
                    self.backend_process.wait()
                    print("Backend process killed")

            except Exception as e:
                print(f"Error during backend cleanup: {e}")
            finally:
                self.backend_process = None

    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown."""
        print(f"Received signal {signum}, shutting down...")
        self.cleanup_backend()
        sys.exit(0)

def main():
    app = KarereApplication()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main())
