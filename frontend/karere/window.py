# frontend/karere/window.py

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GObject, Gio, GdkPixbuf
import base64
from io import BytesIO

class ChatRow(Gtk.ListBoxRow):
    def __init__(self, jid, last_message):
        super().__init__()
        self.jid = jid
        self.jid_label = Gtk.Label(label=jid, halign=Gtk.Align.START, ellipsize=3)
        self.jid_label.get_style_context().add_class('title-4')
        self.last_message_label = Gtk.Label(label=last_message, halign=Gtk.Align.START, ellipsize=3)
        self.last_message_label.get_style_context().add_class('body')
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, margin_start=12, margin_end=12, margin_top=8, margin_bottom=8)
        box.append(self.jid_label)
        box.append(self.last_message_label)
        self.set_child(box)

        # Add CSS class
        self.get_style_context().add_class('chat-row')

    def update_last_message(self, last_message):
        self.last_message_label.set_label(last_message)

class MessageRow(Gtk.ListBoxRow):
    def __init__(self, message_text, is_from_me=False, timestamp=None):
        super().__init__()
        self.message_text = message_text
        self.is_from_me = is_from_me

        # Create message bubble
        message_label = Gtk.Label(label=message_text)
        message_label.set_wrap(True)
        message_label.set_wrap_mode(3)  # WORD_CHAR
        message_label.set_xalign(0.0)
        message_label.set_selectable(True)

        # Create bubble container
        bubble = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        bubble.append(message_label)

        # Add timestamp if provided
        if timestamp:
            time_label = Gtk.Label(label=timestamp)
            time_label.get_style_context().add_class('caption')
            time_label.set_xalign(1.0 if is_from_me else 0.0)
            bubble.append(time_label)

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

    def add_or_update_chat(self, jid, last_message):
        if jid in self._chat_rows:
            self._chat_rows[jid].update_last_message(last_message)
        else:
            new_row = ChatRow(jid, last_message)
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
            message_row = MessageRow(
                message_text,
                is_from_me=is_from_me,
                timestamp=message_data['timestamp']
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
                message_row = MessageRow(
                    message_data['text'],
                    is_from_me=message_data['is_from_me'],
                    timestamp=message_data['timestamp']
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
