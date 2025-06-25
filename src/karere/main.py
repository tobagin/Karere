# frontend/karere/main.py

import sys
import os
import gi
import subprocess
import signal
import atexit
import time

import argparse
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

# Import modules with template decorators AFTER resources are loaded
from window import KarereWindow
from chat_list_page import ChatListPage
from chat_page import ChatPage

class KarereApplication(Adw.Application):
    """The main Karere Application class."""

    def __init__(self, **kwargs):
        super().__init__(application_id='io.github.tobagin.Karere', **kwargs)
        self.win = None
        self.ws_client = None
        self.backend_process = None
        self.backend_ready = False
        self.connected = False  # Track backend connection state
        self.was_previously_connected = False  # Track if we were connected before
        self.syncing = False  # Track sync state

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
        if not self.win:
            self.win = KarereWindow(application=self)
            self.load_css()
            # Set up WebSocket client for the window
            from websocket_client import WebSocketClient
            self.win.websocket_client = WebSocketClient(self.win)
            # Pass application reference to window for accessing connected state
            self.win.app = self
            self.setup_websocket()
            # Set up application actions
            self.setup_actions()
        self.win.present()

    def setup_actions(self):
        """Set up application actions."""
        # Settings action
        settings_action = Gio.SimpleAction.new('settings', None)
        settings_action.connect('activate', self.on_settings_action)
        self.add_action(settings_action)

        # About action
        about_action = Gio.SimpleAction.new('about', None)
        about_action.connect('activate', self.on_about_action)
        self.add_action(about_action)

        # New chat action (placeholder)
        new_chat_action = Gio.SimpleAction.new('new-chat', None)
        new_chat_action.connect('activate', self.on_new_chat_action)
        self.add_action(new_chat_action)

        # New group action (placeholder)
        new_group_action = Gio.SimpleAction.new('new-group', None)
        new_group_action.connect('activate', self.on_new_group_action)
        self.add_action(new_group_action)

    def on_settings_action(self, action, param):
        """Handle settings action."""
        from settings_dialog import SettingsDialog
        settings_dialog = SettingsDialog()
        settings_dialog.set_transient_for(self.win)
        settings_dialog.present()

    def on_about_action(self, action, param):
        """Handle about action."""
        # Load about dialog from resources
        builder = Gtk.Builder()
        resource_base = f'/{APP_ID.replace(".", "/")}'
        builder.add_from_resource(f'{resource_base}/ui/dialogs/about.ui')
        about_dialog = builder.get_object('about_dialog')

        # Set transient for main window
        about_dialog.set_transient_for(self.win)

        # Present the dialog
        about_dialog.present()

    def on_new_chat_action(self, action, param):
        """Handle new chat action."""
        # TODO: Implement new chat functionality
        print("New chat action triggered")

    def on_new_group_action(self, action, param):
        """Handle new group action."""
        # TODO: Implement new group functionality
        print("New group action triggered")

    def start_backend(self):
        """Start the Node.js backend process."""
        try:
            print("🚀 Starting Node.js backend process...")

            # Look for Node.js backend source
            backend_dir = '/app/share/karere/backend'
            backend_script = os.path.join(backend_dir, 'src', 'backend.js')

            if not os.path.exists(backend_script):
                print(f"ERROR: Backend script not found at: {backend_script}")
                print(f"Looking for backend directory at: {backend_dir}")
                if os.path.exists('/app/share/karere'):
                    print(f"Contents of /app/share/karere: {os.listdir('/app/share/karere')}")
                return False

            print(f"✅ Found Node.js backend: {backend_script}")

            # Set up data directory
            data_dir = os.environ.get('KARERE_DATA_DIR', os.path.expanduser('~/.local/share/karere'))
            os.makedirs(data_dir, exist_ok=True)

            # Create subdirectories that the backend needs
            backend_data_dir = os.path.join(data_dir, 'data')
            os.makedirs(backend_data_dir, exist_ok=True)

            # Set permissions to ensure the backend can write
            os.chmod(data_dir, 0o755)
            os.chmod(backend_data_dir, 0o755)

            print(f"📁 Data directory: {data_dir}")
            print(f"📁 Backend data directory: {backend_data_dir}")

            # Set up environment
            env = os.environ.copy()
            env['KARERE_DATA_DIR'] = data_dir

            # Start the Node.js backend process
            print(f"🚀 Starting Node.js backend: node src/backend.js")
            self.backend_process = subprocess.Popen(
                ['node', 'src/backend.js'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=backend_dir,  # Run from backend directory so node can find node_modules
                preexec_fn=os.setsid,  # Create new process group
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            print(f"✅ Backend started with PID: {self.backend_process.pid}")

            # Check if backend started successfully
            print("✅ Backend process started successfully")

            # Wait a moment for backend to start
            time.sleep(2)

            # Check if backend process is still running
            if self.backend_process.poll() is not None:
                print(f"ERROR: Backend process exited with code: {self.backend_process.returncode}")
                # Try to read any error output
                try:
                    stdout, stderr = self.backend_process.communicate(timeout=1)
                    if stdout:
                        print(f"Backend stdout: {stdout}")
                    if stderr:
                        print(f"Backend stderr: {stderr}")
                except:
                    pass
                return False

            # Start checking for backend readiness
            GLib.timeout_add(1000, self._check_backend_ready)

            return True

        except Exception as e:
            print(f"Failed to start backend: {e}")
            import traceback
            traceback.print_exc()
            return False



    def _check_backend_ready(self):
        """Simple check if backend is ready by attempting WebSocket connection."""
        print("🔍 Checking if backend is ready...")
        # Give backend a moment to start up
        GLib.timeout_add(3000, self._delayed_websocket_setup)
        return False  # Don't repeat

    def _delayed_websocket_setup(self):
        """Setup WebSocket connection after giving backend time to start."""
        print("🔌 Setting up WebSocket connection...")
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
        # Connect new download and sync signals
        self.ws_client.connect('initial-download-started', self.on_initial_download_started)
        self.ws_client.connect('download-progress', self.on_download_progress)
        self.ws_client.connect('download-complete', self.on_download_complete)
        self.ws_client.connect('download-error', self.on_download_error)
        self.ws_client.connect('sync-started', self.on_sync_started)
        self.ws_client.connect('sync-progress', self.on_sync_progress)
        self.ws_client.connect('sync-complete', self.on_sync_complete)
        self.ws_client.connect('sync-error', self.on_sync_error)
        self.ws_client.connect('chats-updated', self.on_chats_updated)
        # Connect session disconnection signals
        self.ws_client.connect('auth-failure', self.on_auth_failure)
        self.ws_client.connect('session-logout', self.on_session_logout)
        self.ws_client.connect('connection-lost', self.on_connection_lost)
        self.ws_client.connect('connection-status', self.on_connection_status)
        self.ws_client.start()
        print("WebSocket client setup and started.")

    def on_qr_received(self, _, qr_url):
        """Handler for when QR code is received from backend."""
        # Only show QR view if we're connected to backend
        if self.connected:
            self.win.show_qr_view()
            self.win.show_qr_code(qr_url)
        else:
            print("QR code received but not connected to backend, ignoring.")

    def on_status_update(self, _, message):
        self.win.show_toast(message)

    def on_connection_opened(self, _):
        """Handler for when the WebSocket connection to the backend is established."""
        print("WebSocket connection to backend service is open.")
        self.connected = True  # Set connected to True when connection is established
        self.was_previously_connected = True  # Mark that we've been connected

        # Update view based on connection state
        if self.win:
            # Check if we're currently on the reconnecting page and switch back to loading
            current_content = self.win.split_view.get_content()
            if current_content == self.win.reconnecting_page:
                print("Connection restored! Switching from reconnecting to loading view.")
                self.win.show_loading_view()
                # Uncollapse sidebar if we were in chat view before
                if hasattr(self.win, 'chat_list_page') and self.win.chat_list_page:
                    self.win.split_view.set_collapsed(False)

            self.win.update_view_based_on_connection()

    def on_connection_closed(self, _):
        """Handler for when the connection to the backend is lost."""
        self.connected = False  # Set connected to False when connection is lost

        # Show reconnecting view if we were previously connected, loading view if we never connected
        if self.win:
            if self.was_previously_connected:
                print("Connection lost! Showing reconnecting view.")
                self.win.show_reconnecting_view()
            else:
                print("Initial connection failed. Showing loading view.")
                self.win.show_loading_view()

    def is_connected(self):
        """Returns True if connected to backend, False otherwise."""
        return self.connected

    def is_syncing(self):
        """Returns True if sync is in progress, False otherwise."""
        return self.syncing

    def on_baileys_ready(self, _):
        """
        Handler for when the backend is fully connected to WhatsApp.
        Request initial chats from the backend.
        """
        print("Backend is ready and connected to WhatsApp.")

        # Request initial chats from the backend
        if self.ws_client:
            print("Requesting initial chats from backend...")
            self.ws_client.send_command('get_initial_chats')
        else:
            print("ERROR: WebSocket client not available to request chats")

    def on_initial_chats(self, _, chats):
        """Handler for receiving the initial list of chats."""
        print(f"Received {len(chats)} initial chats.")

        # Switch to chat view when we receive initial chats
        if self.win:
            self.win.show_chat_view()

        # Sort chats by timestamp (latest first) to ensure proper ordering
        sorted_chats = sorted(chats, key=lambda x: x.get('timestamp', 0), reverse=True)
        print(f"Sorted {len(sorted_chats)} chats by timestamp")

        for chat in sorted_chats:
            # Use contact name if available and different from JID, otherwise use formatted phone number
            name = chat.get('name')
            jid = chat['jid']
            if name and name != jid:
                contact_name = name
            else:
                # Format the phone number from JID for display
                contact_name = self.format_phone_number(jid)

            # Check both avatar fields - prefer chatAvatarBase64 for groups, avatarBase64 for contacts
            avatar_base64 = chat.get('chatAvatarBase64') or chat.get('avatarBase64')
            # Don't pass 'None' string, pass actual None
            if avatar_base64 == 'None' or avatar_base64 == '':
                avatar_base64 = None

            # Debug avatar data
            if avatar_base64:
                print(f"Chat {jid} has avatar data: {len(avatar_base64)} characters")
            else:
                print(f"Chat {jid} has no avatar data. chatAvatarBase64: {chat.get('chatAvatarBase64')}, avatarBase64: {chat.get('avatarBase64')}")

            # Get message type and sender information
            message_type = chat.get('lastMessageType', 'text')
            last_message_from = chat.get('lastMessageFrom')
            from_me = last_message_from == 'me' if last_message_from else False

            self.win.add_or_update_chat(
                chat['jid'],
                chat['lastMessage'],
                chat.get('timestamp'),
                chat.get('unreadCount', 0),
                contact_name,
                avatar_base64,
                message_type,
                from_me,
                is_initial=True
            )

    def on_new_message(self, _, from_jid, body, timestamp=None, contact_name=None, avatar_base64=None, message_type='text'):
        print(f"New message from {from_jid}: {body}")
        # Use provided timestamp or current time
        if timestamp is None:
            import time
            timestamp = time.time() * 1000

        # Don't pass 'None' string, pass actual None
        if avatar_base64 == 'None':
            avatar_base64 = None

        # Use contact name if provided, otherwise format phone number
        if contact_name and contact_name != from_jid:
            display_name = contact_name
        else:
            display_name = self.format_phone_number(from_jid)

        # New messages from others are not from me
        self.win.add_or_update_chat(from_jid, body, timestamp, 0, display_name, avatar_base64, message_type, False)

    def on_message_sent(self, _, to_jid, message_text):
        """Handle message sent confirmation from backend."""
        print(f"Message sent successfully to {to_jid}: {message_text}")
        # Update message status in the chat page
        if self.win:
            self.win.update_message_status(to_jid, message_text, 'sent')

    def on_message_error(self, _, error_message):
        """Handle message sending error from backend."""
        print(f"Message sending failed: {error_message}")
        # Show error toast
        if self.win:
            self.win.show_toast(f"Failed to send message: {error_message}")
            # Update message status to failed
            # Note: We'd need more info from backend to identify which message failed

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

    def on_initial_download_started(self, _, message):
        """Handle initial download started signal."""
        print(f"Initial download started: {message}")
        self.win.show_download_progress_view(message)

    def on_download_progress(self, _, progress_data):
        """Handle download progress updates."""
        print(f"Download progress: {progress_data}")
        self.win.update_download_progress(progress_data)

    def on_download_complete(self, _, completion_data):
        """Handle download completion."""
        print(f"Download complete: {completion_data}")
        stats = completion_data.get('stats', {})
        message = completion_data.get('message', 'Download complete!')

        # Show completion message briefly, then switch to chat view
        self.win.show_toast(f"{message} - {stats.get('chats', 0)} chats, {stats.get('messages', 0)} messages")

        # Switch to chat view after a short delay
        from gi.repository import GLib
        GLib.timeout_add_seconds(2, self._switch_to_chat_view_after_download)

    def on_download_error(self, _, error_message):
        """Handle download errors."""
        print(f"Download error: {error_message}")
        self.win.show_toast(f"Download failed: {error_message}")
        # Stay on download page to show error state

    def on_sync_started(self, _, message):
        """Handle sync started signal."""
        print(f"Sync started: {message}")
        self.syncing = True  # Set syncing state to True
        self.win.show_sync_progress_view(message)

    def on_sync_progress(self, _, progress_data):
        """Handle sync progress updates."""
        print(f"Sync progress: {progress_data}")
        self.win.update_sync_progress(progress_data)

    def on_sync_complete(self, _, message):
        """Handle sync completion."""
        print(f"Sync complete: {message}")
        self.syncing = False  # Set syncing state to False
        self.win.show_toast("Sync complete!")

        # Switch to chat view after sync
        from gi.repository import GLib
        GLib.timeout_add_seconds(1, self._switch_to_chat_view_after_sync)

    def on_sync_error(self, _, error_message):
        """Handle sync errors."""
        print(f"Sync error: {error_message}")
        self.syncing = False  # Set syncing state to False even on error
        self.win.show_toast(f"Sync failed: {error_message}")
        # Switch to chat view even if sync failed
        from gi.repository import GLib
        GLib.timeout_add_seconds(2, self._switch_to_chat_view_after_sync)

    def on_chats_updated(self, _, chats):
        """Handle updated chat list from backend."""
        print(f"Chats updated: {len(chats)} chats")
        # Sort chats by timestamp (latest first) to ensure proper ordering
        sorted_chats = sorted(chats, key=lambda x: x.get('timestamp', 0), reverse=True)
        print(f"Sorted {len(sorted_chats)} chats by timestamp")

        # Process updated chats similar to initial chats
        for chat in sorted_chats:
            jid = chat.get('jid')
            name = chat.get('name')
            last_message = chat.get('lastMessage', 'No messages yet')
            timestamp = chat.get('timestamp')
            unread_count = chat.get('unreadCount', 0)
            avatar_base64 = chat.get('avatarBase64')
            # Don't pass 'None' string, pass actual None
            if avatar_base64 == 'None':
                avatar_base64 = None

            # Get message type and sender information
            message_type = chat.get('lastMessageType', 'text')
            last_message_from = chat.get('lastMessageFrom')
            from_me = last_message_from == 'me' if last_message_from else False

            if jid:
                # Use contact name if available and different from JID, otherwise use formatted phone number
                if name and name != jid:
                    contact_name = name
                else:
                    contact_name = self.format_phone_number(jid)

                self.win.add_or_update_chat(jid, last_message, timestamp, unread_count, contact_name, avatar_base64, message_type, from_me, is_initial=True)

    def on_auth_failure(self, _, message):
        """Handle authentication failure."""
        print(f"Authentication failed: {message}")
        if self.win:
            self.win.show_toast(f"Authentication failed: {message}")
            # Show QR view again for re-authentication
            self.win.show_qr_view()

    def on_session_logout(self, _, message):
        """Handle session logout (user disconnected from phone)."""
        print(f"Session logged out: {message}")
        if self.win:
            self.win.show_toast(f"Logged out: {message}")
            # Clear chat data and show QR view
            if hasattr(self.win, 'clear_chat_data'):
                self.win.clear_chat_data()
            self.win.show_qr_view()
            # Show a more prominent notification
            if hasattr(self.win, 'show_logout_notification'):
                self.win.show_logout_notification(message)

    def on_connection_lost(self, _, message):
        """Handle connection lost (temporary disconnection)."""
        print(f"Connection lost: {message}")
        if self.win:
            self.win.show_toast(f"Connection lost: {message}")
            # Show reconnecting view
            self.win.show_reconnecting_view()

    def on_connection_status(self, _, status_data):
        """Handle connection status updates."""
        status = status_data.get('status', 'unknown')
        reason = status_data.get('reason', '')
        print(f"Connection status: {status}, reason: {reason}")

        if self.win:
            if status == 'closed':
                self.win.show_toast(f"Connection closed: {reason}")
                self.win.show_reconnecting_view()
            elif status == 'open':
                self.win.show_toast("Connected to WhatsApp")
            elif status == 'connecting':
                self.win.show_toast("Connecting to WhatsApp...")

    def _switch_to_chat_view_after_download(self):
        """Switch to chat view after download completion."""
        self.win.show_chat_view()
        return False  # Don't repeat

    def format_phone_number(self, jid):
        """Format a phone number from JID for display."""
        if '@' in jid:
            phone = jid.split('@')[0]
            if phone.startswith('55'):  # Brazilian number
                if len(phone) >= 11:
                    return f"+{phone[:2]} ({phone[2:4]}) {phone[4:9]}-{phone[9:]}"
                else:
                    return f"+{phone}"
            elif phone.startswith('351'):  # Portuguese number
                if len(phone) >= 9:
                    return f"+{phone[:3]} {phone[3:6]} {phone[6:]}"
                else:
                    return f"+{phone}"
            elif phone.startswith('1'):  # US/Canada number
                if len(phone) >= 11:
                    return f"+{phone[0]} ({phone[1:4]}) {phone[4:7]}-{phone[7:]}"
                else:
                    return f"+{phone}"
            else:
                return f"+{phone}"
        return jid

    def _switch_to_chat_view_after_sync(self):
        """Switch to chat view after sync completion."""
        self.win.show_chat_view()
        return False  # Don't repeat

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
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Karere - WhatsApp Desktop Client (Baileys Backend)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Karere uses the Baileys backend for native WhatsApp Web API access.
Baileys provides a lightweight, pure Node.js implementation that works
across all architectures without requiring a browser.

Features:
  - Native WhatsApp Web API integration
  - Cross-platform compatibility (x86_64, ARM64)
  - No browser dependencies
  - Efficient message handling
  - QR code authentication

Examples:
  python -m frontend.karere.main              # Start Karere
  flatpak run io.github.tobagin.Karere        # Run as Flatpak
        """
    )

    # Keep --baileys for backward compatibility but make it default
    parser.add_argument(
        '--baileys',
        action='store_true',
        help='Use Baileys backend (default and only supported backend)'
    )

    args = parser.parse_args()

    # Always use Baileys backend
    print("⚡ Using Baileys backend - Native WhatsApp Web API")

    # Create and run application
    # Only pass the application name to GTK, not our custom arguments
    app = KarereApplication()
    return app.run([sys.argv[0]])

if __name__ == '__main__':
    sys.exit(main())
