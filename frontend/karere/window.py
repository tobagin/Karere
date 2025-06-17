# frontend/karere/window.py

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GObject, Gio, GdkPixbuf
import base64
from io import BytesIO

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

class MessageRow(Gtk.ListBoxRow):
    def __init__(self, message_text, is_from_me=False, timestamp=None, status=None):
        super().__init__()
        self.message_text = message_text
        self.is_from_me = is_from_me
        self.status = status

        # Create message bubble
        message_label = Gtk.Label(label=message_text)
        message_label.set_wrap(True)
        message_label.set_wrap_mode(3)  # WORD_CHAR
        message_label.set_xalign(0.0)
        message_label.set_selectable(True)

        # Create bubble container
        bubble = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        bubble.append(message_label)

        # Create timestamp and status row
        if timestamp or (is_from_me and status):
            time_status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

            # Add timestamp
            if timestamp:
                time_label = Gtk.Label(label=self.format_timestamp(timestamp))
                time_label.get_style_context().add_class('caption')
                time_label.get_style_context().add_class('dim-label')
                time_status_box.append(time_label)

            # Add status indicator for sent messages
            if is_from_me and status:
                status_icon = Gtk.Image()
                status_icon.get_style_context().add_class('caption')

                if status == 'sending':
                    status_icon.set_from_icon_name('content-loading-symbolic')
                    status_icon.set_tooltip_text('Sending...')
                elif status == 'sent':
                    status_icon.set_from_icon_name('emblem-ok-symbolic')
                    status_icon.set_tooltip_text('Sent')
                elif status == 'delivered':
                    status_icon.set_from_icon_name('emblem-ok-symbolic')
                    status_icon.set_tooltip_text('Delivered')
                elif status == 'read':
                    status_icon.set_from_icon_name('emblem-ok-symbolic')
                    status_icon.get_style_context().add_class('accent')
                    status_icon.set_tooltip_text('Read')
                elif status == 'error':
                    status_icon.set_from_icon_name('dialog-error-symbolic')
                    status_icon.get_style_context().add_class('error')
                    status_icon.set_tooltip_text('Failed to send')

                time_status_box.append(status_icon)

            # Align timestamp/status to the right for sent messages
            time_status_box.set_halign(Gtk.Align.END if is_from_me else Gtk.Align.START)
            bubble.append(time_status_box)

        # Style the bubble
        if is_from_me:
            bubble.get_style_context().add_class('message-bubble-sent')
            bubble.set_halign(Gtk.Align.END)
        else:
            bubble.get_style_context().add_class('message-bubble-received')
            bubble.set_halign(Gtk.Align.START)

        # Add margins
        bubble.set_margin_start(12)
        bubble.set_margin_end(12)
        bubble.set_margin_top(4)
        bubble.set_margin_bottom(4)

        self.set_child(bubble)
        self.set_selectable(False)

    def format_timestamp(self, timestamp):
        """Format timestamp for display."""
        from datetime import datetime, timedelta

        if isinstance(timestamp, str):
            # If it's already a formatted string, return as-is
            return timestamp

        try:
            if isinstance(timestamp, (int, float)):
                # Unix timestamp
                dt = datetime.fromtimestamp(timestamp)
            else:
                dt = timestamp

            now = datetime.now()
            diff = now - dt

            if diff.days == 0:
                # Today - show time
                return dt.strftime("%H:%M")
            elif diff.days == 1:
                # Yesterday
                return "Yesterday"
            elif diff.days < 7:
                # This week - show day name
                return dt.strftime("%A")
            else:
                # Older - show date
                return dt.strftime("%m/%d")
        except:
            return str(timestamp)

@Gtk.Template(resource_path='/io/github/tobagin/Karere/karere.ui')
class KarereWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'KarereWindow'

    main_stack = Gtk.Template.Child()
    chat_list_box = Gtk.Template.Child()
    qr_image = Gtk.Template.Child()
    qr_spinner = Gtk.Template.Child()
    message_stack = Gtk.Template.Child()
    messages_list_box = Gtk.Template.Child()
    chat_title_label = Gtk.Template.Child()
    message_entry = Gtk.Template.Child()
    send_button = Gtk.Template.Child()
    messages_scrolled = Gtk.Template.Child()
    search_bar = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    search_button = Gtk.Template.Child()
    typing_revealer = Gtk.Template.Child()
    typing_label = Gtk.Template.Child()
    emoji_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._chat_rows = {}
        self._current_chat_jid = None
        self._message_history = {}  # Store message history per chat

        self.main_stack.set_visible_child_name('connecting_view')
        self.qr_spinner.start()

        # Connect signals
        self.chat_list_box.connect('row-selected', self.on_chat_selected)
        self.send_button.connect('clicked', self.on_send_message)
        self.message_entry.connect('activate', self.on_send_message)

        # Search functionality
        self.search_button.connect('toggled', self.on_search_toggled)
        self.search_entry.connect('search-changed', self.on_search_changed)
        self.search_bar.connect_entry(self.search_entry)

        # Set up search filtering
        self.chat_list_box.set_filter_func(self.filter_chat_row)

        # Typing indicators
        self.message_entry.connect('changed', self.on_message_entry_changed)
        self._typing_timeout = None

        # Emoji picker
        self.emoji_button.connect('clicked', self.on_emoji_button_clicked)
        self._emoji_popover = None

    def on_chat_selected(self, list_box, row):
        """Handle chat selection from the chat list."""
        if row is None:
            return

        chat_row = row
        jid = chat_row.jid
        self._current_chat_jid = jid

        # Update chat title
        display_name = self.get_display_name(jid)
        self.chat_title_label.set_label(display_name)

        # Switch to message view
        self.message_stack.set_visible_child_name('message_view')

        # Load message history for this chat
        self.load_message_history(jid)

        # Focus message entry
        self.message_entry.grab_focus()

        print(f"Selected chat: {jid}")

    def on_send_message(self, widget):
        """Handle sending a message."""
        if not self._current_chat_jid:
            return

        message_text = self.message_entry.get_text().strip()
        if not message_text:
            return

        # Clear the entry
        self.message_entry.set_text("")

        # Add message to UI immediately (optimistic update)
        self.add_message_to_chat(self._current_chat_jid, message_text, is_from_me=True)

        # Send message to backend
        self.send_message_to_backend(self._current_chat_jid, message_text)

        print(f"Sending message to {self._current_chat_jid}: {message_text}")

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

    def add_or_update_chat(self, jid, last_message, timestamp=None, unread_count=0):
        if jid in self._chat_rows:
            self._chat_rows[jid].update_last_message(last_message, timestamp)
            if unread_count > 0:
                self._chat_rows[jid].update_unread_count(unread_count)
        else:
            new_row = ChatRow(jid, last_message, timestamp, unread_count)
            self._chat_rows[jid] = new_row
            self.chat_list_box.prepend(new_row)

        # If this is the currently selected chat, add the message to the view
        if jid == self._current_chat_jid:
            self.add_message_to_chat(jid, last_message, is_from_me=False)

    def show_reconnecting_view(self):
        """Switches the stack to the reconnecting view."""
        self.main_stack.set_visible_child_name('reconnecting_view')
        print("Switched to reconnecting view.")

    def show_qr_view(self):
        self.main_stack.set_visible_child_name('qr_view')
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
        self.main_stack.set_visible_child_name('chat_view')
        print("Switched to chat view.")

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

        # If this is the currently selected chat, add to UI
        if jid == self._current_chat_jid:
            status = 'sending' if is_from_me else None
            message_row = MessageRow(
                message_text,
                is_from_me=is_from_me,
                timestamp=message_data['timestamp'],
                status=status
            )
            self.messages_list_box.append(message_row)

            # Scroll to bottom
            self.scroll_to_bottom()

    def load_message_history(self, jid):
        """Load message history for a chat."""
        # Clear current messages
        while True:
            row = self.messages_list_box.get_first_child()
            if row is None:
                break
            self.messages_list_box.remove(row)

        # Load messages from history
        if jid in self._message_history:
            for message_data in self._message_history[jid]:
                status = message_data.get('status', 'sent' if message_data['is_from_me'] else None)
                message_row = MessageRow(
                    message_data['text'],
                    is_from_me=message_data['is_from_me'],
                    timestamp=message_data['timestamp'],
                    status=status
                )
                self.messages_list_box.append(message_row)

        # Scroll to bottom
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        """Scroll the message view to the bottom."""
        def do_scroll():
            vadj = self.messages_scrolled.get_vadjustment()
            vadj.set_value(vadj.get_upper() - vadj.get_page_size())
            return False

        # Use idle_add to ensure the UI is updated first
        from gi.repository import GLib
        GLib.idle_add(do_scroll)

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

    def show_typing_indicator(self, contact_name=None):
        """Show typing indicator."""
        if contact_name:
            self.typing_label.set_label(f"{contact_name} is typing...")
        else:
            self.typing_label.set_label("typing...")
        self.typing_revealer.set_reveal_child(True)

    def hide_typing_indicator(self):
        """Hide typing indicator."""
        self.typing_revealer.set_reveal_child(False)

    def on_message_entry_changed(self, entry):
        """Handle message entry text changes for typing indicators."""
        from gi.repository import GLib

        # Cancel previous timeout
        if self._typing_timeout:
            GLib.source_remove(self._typing_timeout)
            self._typing_timeout = None

        text = entry.get_text()
        if text and self._current_chat_jid:
            # Send typing indicator to backend
            app = self.get_application()
            if app and app.ws_client:
                app.ws_client.send_command('typing_start', {
                    'to': self._current_chat_jid
                })

            # Set timeout to stop typing indicator
            self._typing_timeout = GLib.timeout_add_seconds(3, self._stop_typing_timeout)
        else:
            # Send stop typing to backend immediately
            self._send_stop_typing()

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

    def on_emoji_button_clicked(self, button):
        """Handle emoji button click."""
        if self._emoji_popover is None:
            self._create_emoji_popover()

        self._emoji_popover.set_parent(button)
        self._emoji_popover.popup()

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
        # Insert emoji at cursor position
        current_text = self.message_entry.get_text()
        cursor_pos = self.message_entry.get_position()

        new_text = current_text[:cursor_pos] + emoji + current_text[cursor_pos:]
        self.message_entry.set_text(new_text)
        self.message_entry.set_position(cursor_pos + len(emoji))

        # Close popover and focus entry
        self._emoji_popover.popdown()
        self.message_entry.grab_focus()
