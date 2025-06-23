# frontend/karere/window.py

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GObject, Gio, GdkPixbuf
import base64
from io import BytesIO

# Dynamic app ID for Flatpak compatibility
# This will be automatically detected at runtime, but we need a default for the template decorator
import os
APP_ID = os.environ.get('FLATPAK_ID', 'io.github.tobagin.Karere')

# Import our custom components
from chat_list_page import ChatListPage
from chat_page import ChatPage

class ChatRow(Gtk.ListBoxRow):
    def __init__(self, jid, last_message, timestamp=None, unread_count=0):
        super().__init__()
        self.jid = jid
        self.unread_count = unread_count

        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_margin_top(8)
        main_box.set_margin_bottom(8)

        # Left side - chat info
        chat_info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        chat_info_box.set_hexpand(True)

        # Contact name
        self.jid_label = Gtk.Label(halign=Gtk.Align.START, ellipsize=3)
        self.jid_label.get_style_context().add_class('title-4')
        self.update_contact_name(jid)

        # Last message
        self.last_message_label = Gtk.Label(label=last_message, halign=Gtk.Align.START, ellipsize=3)
        self.last_message_label.get_style_context().add_class('body')
        self.last_message_label.get_style_context().add_class('dim-label')

        chat_info_box.append(self.jid_label)
        chat_info_box.append(self.last_message_label)
        main_box.append(chat_info_box)

        # Right side - timestamp and unread indicator
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        right_box.set_valign(Gtk.Align.START)

        # Timestamp
        self.timestamp_label = Gtk.Label()
        self.timestamp_label.get_style_context().add_class('caption')
        self.timestamp_label.get_style_context().add_class('dim-label')
        self.timestamp_label.set_halign(Gtk.Align.END)
        if timestamp:
            self.update_timestamp(timestamp)

        # Unread count badge
        self.unread_badge = Gtk.Label()
        self.unread_badge.get_style_context().add_class('unread-badge')
        self.unread_badge.set_halign(Gtk.Align.END)
        self.update_unread_count(unread_count)

        right_box.append(self.timestamp_label)
        right_box.append(self.unread_badge)
        main_box.append(right_box)

        self.set_child(main_box)

        # Add CSS class
        self.get_style_context().add_class('chat-row')

    def update_contact_name(self, jid):
        """Update the contact name display."""
        display_name = self.get_display_name(jid)
        self.jid_label.set_label(display_name)

    def get_display_name(self, jid):
        """Get a display name for a JID (phone number)."""
        if '@' in jid:
            phone_number = jid.split('@')[0]
            # Format phone number nicely
            if phone_number.startswith('55'):  # Brazilian numbers
                return f"+{phone_number[:2]} ({phone_number[2:4]}) {phone_number[4:9]}-{phone_number[9:]}"
            else:
                return f"+{phone_number}"
        return jid

    def update_last_message(self, last_message, timestamp=None):
        """Update the last message and timestamp."""
        self.last_message_label.set_label(last_message)
        if timestamp:
            self.update_timestamp(timestamp)

    def update_timestamp(self, timestamp):
        """Update the timestamp display."""
        from datetime import datetime, timedelta

        try:
            if isinstance(timestamp, str):
                # Try to parse if it's a string
                try:
                    dt = datetime.fromisoformat(timestamp)
                except:
                    self.timestamp_label.set_label(timestamp)
                    return
            elif isinstance(timestamp, (int, float)):
                dt = datetime.fromtimestamp(timestamp)
            else:
                dt = timestamp

            now = datetime.now()
            diff = now - dt

            if diff.days == 0:
                # Today - show time
                self.timestamp_label.set_label(dt.strftime("%H:%M"))
            elif diff.days == 1:
                # Yesterday
                self.timestamp_label.set_label("Yesterday")
            elif diff.days < 7:
                # This week - show day name
                self.timestamp_label.set_label(dt.strftime("%a"))
            else:
                # Older - show date
                self.timestamp_label.set_label(dt.strftime("%m/%d"))
        except:
            self.timestamp_label.set_label("")

    def update_unread_count(self, count):
        """Update the unread message count."""
        self.unread_count = count
        if count > 0:
            if count > 99:
                self.unread_badge.set_label("99+")
            else:
                self.unread_badge.set_label(str(count))
            self.unread_badge.set_visible(True)
        else:
            self.unread_badge.set_visible(False)



@Gtk.Template(resource_path=f'/{APP_ID.replace(".", "/")}/ui/window.ui')
class KarereWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'KarereWindow'

    split_view = Gtk.Template.Child()
    chat_list_box = Gtk.Template.Child()
    search_bar = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    search_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._chat_rows = {}
        self._current_chat_jid = None
        self._message_history = {}  # Store message history per chat
        self._chat_pages = {}  # Store navigation pages for each chat
        self._typing_timeout = None
        self._emoji_popover = None
        self._current_emoji_page = None  # Track current page for emoji insertion

        # Verify template children are loaded
        if not self.split_view:
            raise RuntimeError("UI template failed to load - split_view is None")

        # Load individual page UI files and add them to navigation view
        self._load_pages()

        # Create and initialize ChatListPage
        self.chat_list_page = ChatListPage()
        self.chat_list_page.set_window(self)

        # Start with loading page (connected is false initially)
        self.show_loading_view()

        # Connect signals for old chat list box (will be removed later)
        self.chat_list_box.connect('row-selected', self.on_chat_selected)

        # Search functionality (will be handled by ChatListPage)
        self.search_button.connect('toggled', self.on_search_toggled)
        self.search_entry.connect('search-changed', self.on_search_changed)
        self.search_bar.connect_entry(self.search_entry)

        # Set up search filtering (will be handled by ChatListPage)
        self.chat_list_box.set_filter_func(self.filter_chat_row)

        # Initialize WebSocket client (will be set by main app)
        self.websocket_client = None

    def _load_pages(self):
        """Load individual page UI files from resources and add them to navigation view."""
        builder = Gtk.Builder()

        # Use the same dynamic resource path pattern
        resource_base = f'/{APP_ID.replace(".", "/")}'

        # Load loading page
        builder.add_from_resource(f'{resource_base}/ui/pages/loading_page.ui')
        self.loading_page = builder.get_object('loading_page')
        self.loading_spinner = builder.get_object('loading_spinner')

        # Load QR page
        builder.add_from_resource(f'{resource_base}/ui/pages/qr_page.ui')
        self.qr_page = builder.get_object('qr_page')
        print(type(self.qr_page))
        self.qr_image = builder.get_object('qr_image')
        print(type(self.qr_image))
        self.qr_spinner = builder.get_object('qr_spinner')
        print(type(self.qr_spinner))

        # Load reconnecting page
        builder.add_from_resource(f'{resource_base}/ui/pages/reconnecting_page.ui')
        self.reconnecting_page = builder.get_object('reconnecting_page')
        print(type(self.reconnecting_page))
        self.reconnecting_spinner = builder.get_object('reconnecting_spinner')
        print(type(self.reconnecting_spinner))

        # Load welcome page
        builder.add_from_resource(f'{resource_base}/ui/pages/welcome_page.ui')
        self.welcome_page = builder.get_object('welcome_page')
        print(type(self.welcome_page))

        # Load download progress page
        builder.add_from_resource(f'{resource_base}/ui/pages/download_progress_page.ui')
        self.download_progress_page = builder.get_object('download_progress_page')
        self.download_progress_bar = builder.get_object('download_progress_bar')
        self.download_progress_label = builder.get_object('download_progress_label')
        self.download_details_label = builder.get_object('download_details_label')
        self.chats_count_label = builder.get_object('chats_count_label')
        self.messages_count_label = builder.get_object('messages_count_label')
        self.avatars_count_label = builder.get_object('avatars_count_label')
        self.download_spinner = builder.get_object('download_spinner')

        # Load sync progress page
        builder.add_from_resource(f'{resource_base}/ui/pages/sync_progress_page.ui')
        self.sync_progress_page = builder.get_object('sync_progress_page')
        self.sync_progress_bar = builder.get_object('sync_progress_bar')
        self.sync_progress_label = builder.get_object('sync_progress_label')
        self.sync_details_label = builder.get_object('sync_details_label')
        self.sync_chats_count_label = builder.get_object('sync_chats_count_label')
        self.sync_messages_count_label = builder.get_object('sync_messages_count_label')
        self.sync_contacts_count_label = builder.get_object('sync_contacts_count_label')
        self.sync_spinner = builder.get_object('sync_spinner')

    def on_chat_selected(self, list_box, row):
        """Handle chat selection from the chat list."""
        if row is None:
            return

        chat_row = row
        jid = chat_row.jid
        self._current_chat_jid = jid

        # Navigate to existing page (should already exist from add_or_update_chat)
        if jid in self._chat_pages:
            chat_page = self._chat_pages[jid]
            print(f"DEBUG: Navigating to existing page for {jid}")

            # Check if this page is already the visible page
            visible_page = self.navigation_view.get_visible_page()
            print(f"DEBUG: Current visible page: {visible_page}")
            print(f"DEBUG: Target page: {chat_page}")

            if visible_page != chat_page:
                # Simply push the chat page - AdwNavigationView will handle the navigation
                try:
                    self.navigation_view.push(chat_page)
                    print(f"DEBUG: Successfully pushed target page")
                except Exception as e:
                    print(f"ERROR: Could not navigate to page: {e}")
            else:
                print(f"DEBUG: Target page is already visible")
        else:
            print(f"ERROR: No navigation page found for {jid}")

        # Load message history for this chat
        self.load_message_history(jid)

        print(f"Selected chat: {jid}")

    def on_chat_selected_from_list(self, row):
        """Handle chat selection from ChatListPage."""
        if row is None:
            return

        chat_row = row
        jid = chat_row.jid
        self._current_chat_jid = jid

        # Navigate to existing page (should already exist from add_or_update_chat)
        if jid in self._chat_pages:
            chat_page = self._chat_pages[jid]
            print(f"DEBUG: Navigating to existing page for {jid}")

            # Use set_content to show the chat page
            self.split_view.set_content(chat_page)
            print(f"DEBUG: Successfully set chat page as content")
        else:
            print(f"ERROR: No navigation page found for {jid}")

        # Load message history for this chat
        self.load_message_history(jid)

        print(f"Selected chat from list: {jid}")

    def create_chat_page(self, jid):
        """Create a ChatPage for a chat."""
        # Create ChatPage instance
        chat_page = ChatPage(jid)
        chat_page.set_window(self)

        return chat_page





    def get_display_name(self, jid):
        """Get a display name for a JID (phone number)."""
        # For now, just clean up the JID format
        if '@' in jid:
            phone_number = jid.split('@')[0]
            # Format phone number nicely
            if phone_number.startswith('55'):  # Brazilian numbers
                return f"+{phone_number[:2]} ({phone_number[2:4]}) {phone_number[4:9]}-{phone_number[9:]}"
            else:
                return f"+{phone_number}"
        return jid

    def add_or_update_chat(self, jid, last_message, timestamp=None, unread_count=0, contact_name=None, avatar_base64=None, message_type='text', from_me=False, is_initial=False):
        # Use ChatListPage to add or update chat
        self.chat_list_page.add_or_update_chat(jid, last_message, timestamp, unread_count, contact_name, avatar_base64, message_type, from_me, is_initial)

        # Create navigation page for this chat if it doesn't exist
        if jid not in self._chat_pages:
            chat_page = self.create_chat_page(jid)
            self._chat_pages[jid] = chat_page

        # Update contact information in existing chat page
        if jid in self._chat_pages:
            chat_page = self._chat_pages[jid]
            chat_page.set_contact_info(contact_name, avatar_base64)

        # If this is the currently selected chat, add the message to the view
        if jid == self._current_chat_jid and message_type == 'text':
            self.add_message_to_chat(jid, last_message, is_from_me=from_me)

    def show_loading_view(self):
        """Switches to the loading page."""
        self.split_view.set_content(self.loading_page)
        self.loading_spinner.start()
        # Ensure sidebar is collapsed when loading
        self.split_view.set_collapsed(True)
        print("Switched to loading view.")

    def update_view_based_on_connection(self):
        """Updates the view based on the current connection and sync state."""
        if hasattr(self, 'app') and self.app:
            if not self.app.is_connected():
                # Not connected to backend - show loading page
                self.show_loading_view()
            elif self.app.is_syncing():
                # Connected but syncing - sync view will be shown by sync handlers
                pass
            # If connected and not syncing, the appropriate view will be set by other handlers
            # (QR, welcome, etc.)

    def show_reconnecting_view(self):
        """Switches to the reconnecting page."""
        self.split_view.set_content(self.reconnecting_page)
        self.reconnecting_spinner.start()
        # Collapse sidebar when reconnecting
        self.split_view.set_collapsed(True)
        print("Switched to reconnecting view.")

    def show_qr_view(self):
        """Switches to the QR code page."""
        self.split_view.set_content(self.qr_page)
        self.qr_spinner.start()
        # Collapse sidebar when showing QR (not fully authenticated yet)
        self.split_view.set_collapsed(True)
        print("Switched to QR view.")

    def show_qr_code(self, qr_data_url):
        if not qr_data_url or not qr_data_url.startswith('data:image/png;base64,'):
            return
        base64_data = qr_data_url.split(',')[1]
        image_data = base64.b64decode(base64_data)
        loader = GdkPixbuf.PixbufLoader.new_with_type('png')
        loader.write(image_data)
        loader.close()
        pixbuf = loader.get_pixbuf()
        self.qr_spinner.stop()
        self.qr_spinner.set_visible(False)
        self.qr_image.set_from_pixbuf(pixbuf)
        self.qr_image.set_visible(True)
        print("QR Code displayed.")

    def show_chat_view(self):
        """Enable sidebar with ChatListPage and switch to welcome page."""
        print("Enabling sidebar and switching to chat view.")

        # Set ChatListPage as sidebar
        self.split_view.set_sidebar(self.chat_list_page)

        # Enable sidebar (show chat list)
        self.split_view.set_collapsed(False)

        # Switch to welcome page
        self.split_view.set_content(self.welcome_page)
        print("Switched to chat view with welcome page and ChatListPage sidebar.")

    def show_download_progress_view(self, message="Downloading your WhatsApp data..."):
        """Switch to the download progress page."""
        self.split_view.set_content(self.download_progress_page)
        self.download_progress_label.set_text("Starting download...")
        self.download_details_label.set_text(message)
        self.download_progress_bar.set_fraction(0.0)
        self.download_spinner.start()
        # Collapse sidebar during download (not ready for chat yet)
        self.split_view.set_collapsed(True)

        # Reset counters
        self.chats_count_label.set_text("0")
        self.messages_count_label.set_text("0")
        self.avatars_count_label.set_text("0")

        print("Switched to download progress view.")

    def show_sync_progress_view(self, message="Syncing your WhatsApp data..."):
        """Switch to the sync progress page."""
        self.split_view.set_content(self.sync_progress_page)
        self.sync_progress_label.set_text("Starting sync...")
        self.sync_details_label.set_text(message)
        self.sync_progress_bar.set_fraction(0.0)
        self.sync_spinner.start()
        # Collapse sidebar during sync (not ready for chat yet)
        self.split_view.set_collapsed(True)

        # Reset counters
        self.sync_chats_count_label.set_text("0")
        self.sync_messages_count_label.set_text("0")
        self.sync_contacts_count_label.set_text("0")

        print("Switched to sync progress view.")

    def update_download_progress(self, progress_data):
        """Update the download progress display."""
        stage = progress_data.get('stage', 'downloading')
        message = progress_data.get('message', 'Downloading...')
        progress = progress_data.get('progress', 0) / 100.0  # Convert to 0-1 range
        stats = progress_data.get('stats', {})

        self.download_progress_label.set_text(message)
        self.download_progress_bar.set_fraction(progress)

        # Update statistics if available
        if 'chats' in stats:
            self.chats_count_label.set_text(str(stats.get('chats', 0)))
        if 'messages' in stats:
            self.messages_count_label.set_text(str(stats.get('messages', 0)))
        if 'avatars' in stats:
            self.avatars_count_label.set_text(str(stats.get('avatars', 0)))

        # Update details based on stage
        if stage == 'starting':
            self.download_details_label.set_text("Initializing data download...")
        elif stage == 'downloading':
            processed = progress_data.get('processedChats', 0)
            total = progress_data.get('totalChats', 0)
            if total > 0:
                self.download_details_label.set_text(f"Processing {processed}/{total} chats")
            else:
                self.download_details_label.set_text("Downloading data...")
        elif stage == 'complete':
            self.download_details_label.set_text("Download complete!")
            self.download_spinner.stop()

        print(f"Updated download progress: {progress*100:.1f}% - {message}")

    def update_sync_progress(self, progress_data):
        """Update the sync progress display."""
        stage = progress_data.get('stage', 'syncing')
        message = progress_data.get('message', 'Syncing...')
        progress = progress_data.get('progress', 0) / 100.0  # Convert to 0-1 range
        stats = progress_data.get('stats', {})

        self.sync_progress_label.set_text(message)
        self.sync_progress_bar.set_fraction(progress)

        # Update statistics if available
        if 'updatedChats' in stats:
            self.sync_chats_count_label.set_text(str(stats.get('updatedChats', 0)))
        if 'newMessages' in stats:
            self.sync_messages_count_label.set_text(str(stats.get('newMessages', 0)))
        if 'updatedContacts' in stats:
            self.sync_contacts_count_label.set_text(str(stats.get('updatedContacts', 0)))

        # Update details based on stage
        if stage == 'starting':
            self.sync_details_label.set_text("Checking for updates...")
        elif stage == 'syncing':
            processed = progress_data.get('processedChats', 0)
            total = progress_data.get('totalChats', 0)
            if total > 0:
                self.sync_details_label.set_text(f"Syncing {processed}/{total} chats")
            else:
                self.sync_details_label.set_text("Syncing data...")
        elif stage == 'complete':
            self.sync_details_label.set_text("Sync complete!")
            self.sync_spinner.stop()

        print(f"Updated sync progress: {progress*100:.1f}% - {message}")

    def show_toast(self, message):
        toast_overlay = self.get_content()
        toast_overlay.add_toast(Adw.Toast.new(message))
        print(f"Toast: {message}")

    def add_message_to_chat(self, jid, message_text, is_from_me=False):
        """Add a message to the message history and UI."""
        # Store in message history
        if jid not in self._message_history:
            self._message_history[jid] = []

        message_data = {
            'text': message_text,
            'is_from_me': is_from_me,
            'timestamp': self.get_current_timestamp()
        }
        self._message_history[jid].append(message_data)

        # If there's a page for this chat, add to UI
        if jid in self._chat_pages:
            page = self._chat_pages[jid]
            self.add_message_to_chat_page(page, message_text, is_from_me)

    def add_message_to_chat_page(self, page, message_text, is_from_me=False):
        """Add a message to a specific chat page."""
        status = 'sending' if is_from_me else None
        page.add_message(
            message_text,
            is_from_me=is_from_me,
            timestamp=self.get_current_timestamp(),
            status=status
        )

    def load_message_history(self, jid):
        """Load message history for a chat."""
        if jid not in self._chat_pages:
            return

        page = self._chat_pages[jid]

        # Load messages from local history first
        if jid in self._message_history:
            page.load_messages(self._message_history[jid])

        # Request message history from backend
        app = self.get_application()
        if app and app.ws_client:
            app.ws_client.send_command('get_message_history', {
                'jid': jid,
                'limit': 50,
                'offset': 0
            })



    def load_message_history_from_backend(self, jid, messages):
        """Load message history received from backend."""
        if jid not in self._chat_pages:
            return

        page = self._chat_pages[jid]
        print(f"Loading {len(messages)} messages for {jid}")

        # Clear local message history for this chat
        self._message_history[jid] = []

        # Process messages from backend
        processed_messages = []
        for msg in messages:
            # Convert timestamp to readable format
            timestamp = self.format_timestamp(msg.get('timestamp'))

            # Store in local history
            message_data = {
                'text': msg['text'],
                'fromMe': msg['fromMe'],
                'timestamp': timestamp,
                'status': msg.get('status', 'sent' if msg['fromMe'] else None)
            }
            self._message_history[jid].append(message_data)
            processed_messages.append(message_data)

        # Load messages into the chat page
        page.load_messages(processed_messages)

        # If no messages from backend, add a sample message for testing
        if len(messages) == 0:
            print(f"No messages found for {jid}, adding sample message")
            sample_message = {
                'text': 'This is a sample message to test the message display',
                'fromMe': False,
                'timestamp': self.get_current_timestamp(),
                'status': None
            }
            self._message_history[jid] = [sample_message]
            page.load_messages([sample_message])

    def format_timestamp(self, timestamp):
        """Format timestamp from backend to readable format."""
        if timestamp:
            try:
                from datetime import datetime
                # Convert from milliseconds to seconds if needed
                if timestamp > 1e12:  # Likely milliseconds
                    timestamp = timestamp / 1000
                dt = datetime.fromtimestamp(timestamp)
                return dt.strftime("%H:%M")
            except (ValueError, TypeError):
                pass
        return self.get_current_timestamp()



    def get_current_timestamp(self):
        """Get current timestamp as a formatted string."""
        from datetime import datetime
        return datetime.now().strftime("%H:%M")

    def send_message_to_backend(self, jid, message_text):
        """Send message to backend via WebSocket."""
        # This will be called by the main application
        app = self.get_application()
        if app and app.ws_client:
            app.ws_client.send_command('send_message', {
                'to': jid,
                'message': message_text
            })

    def update_message_status(self, jid, message_text, status):
        """Update the status of a message in the chat page."""
        if jid in self._chat_pages:
            chat_page = self._chat_pages[jid]
            chat_page.update_message_status(message_text, status)

    def on_search_toggled(self, button):
        """Handle search button toggle."""
        is_active = button.get_active()
        self.search_bar.set_search_mode(is_active)
        if is_active:
            self.search_entry.grab_focus()
        else:
            self.search_entry.set_text("")

    def on_search_changed(self, entry):
        """Handle search text changes."""
        # Trigger filter update
        self.chat_list_box.invalidate_filter()

    def filter_chat_row(self, row):
        """Filter function for chat list based on search."""
        search_text = self.search_entry.get_text().lower().strip()

        # If no search text, show all rows
        if not search_text:
            return True

        # Get chat row data
        chat_row = row
        if not hasattr(chat_row, 'jid'):
            return True

        # Search in contact name and last message
        display_name = self.get_display_name(chat_row.jid).lower()
        last_message = chat_row.last_message_label.get_text().lower()

        # Return True if search text is found in either field
        return (search_text in display_name or
                search_text in last_message or
                search_text in chat_row.jid.lower())



    def _stop_typing_timeout(self):
        """Timeout callback to stop typing indicator."""
        self._send_stop_typing()
        self._typing_timeout = None
        return False  # Don't repeat

    def _send_stop_typing(self):
        """Send stop typing command to backend."""
        if self._current_chat_jid:
            app = self.get_application()
            if app and app.ws_client:
                app.ws_client.send_command('typing_stop', {
                    'to': self._current_chat_jid
                })

    def show_emoji_popover(self, button, chat_page):
        """Show emoji popover for a chat page."""
        if self._emoji_popover is None:
            self._create_emoji_popover()

        self._emoji_popover.set_parent(button)
        self._emoji_popover.popup()
        # Store current chat page for emoji insertion
        self._current_emoji_page = chat_page



    def _create_emoji_popover(self):
        """Create the emoji picker popover."""
        self._emoji_popover = Gtk.Popover()
        self._emoji_popover.set_position(Gtk.PositionType.TOP)

        # Create emoji grid
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_size_request(300, 200)

        grid = Gtk.FlowBox()
        grid.set_max_children_per_line(8)
        grid.set_selection_mode(Gtk.SelectionMode.NONE)

        # Common emojis
        emojis = [
            "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣",
            "😊", "😇", "🙂", "🙃", "😉", "😌", "😍", "🥰",
            "😘", "😗", "😙", "😚", "😋", "😛", "😝", "😜",
            "🤪", "🤨", "🧐", "🤓", "😎", "🤩", "🥳", "😏",
            "😒", "😞", "😔", "😟", "😕", "🙁", "☹️", "😣",
            "😖", "😫", "😩", "🥺", "😢", "😭", "😤", "😠",
            "😡", "🤬", "🤯", "😳", "🥵", "🥶", "😱", "😨",
            "😰", "😥", "😓", "🤗", "🤔", "🤭", "🤫", "🤥",
            "👍", "👎", "👌", "🤌", "🤏", "✌️", "🤞", "🤟",
            "🤘", "🤙", "👈", "👉", "👆", "🖕", "👇", "☝️",
            "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍",
            "🤎", "💔", "❣️", "💕", "💞", "💓", "💗", "💖",
            "💘", "💝", "💟", "☮️", "✝️", "☪️", "🕉️", "☸️"
        ]

        for emoji in emojis:
            button = Gtk.Button(label=emoji)
            button.get_style_context().add_class('flat')
            button.connect('clicked', self.on_emoji_selected, emoji)
            grid.append(button)

        scrolled.set_child(grid)
        self._emoji_popover.set_child(scrolled)

    def on_emoji_selected(self, button, emoji):
        """Handle emoji selection."""
        # Use the current emoji page if available
        if hasattr(self, '_current_emoji_page') and self._current_emoji_page:
            page = self._current_emoji_page
            entry = page.message_entry
        else:
            # Fallback - shouldn't happen with navigation pages
            return

        # Insert emoji at cursor position
        current_text = entry.get_text()
        cursor_pos = entry.get_position()

        new_text = current_text[:cursor_pos] + emoji + current_text[cursor_pos:]
        entry.set_text(new_text)
        entry.set_position(cursor_pos + len(emoji))

        # Close popover and focus entry
        self._emoji_popover.popdown()
        entry.grab_focus()
