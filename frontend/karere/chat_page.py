#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GObject, GdkPixbuf
import os
import base64

# Dynamic app ID for Flatpak compatibility
APP_ID = os.environ.get('FLATPAK_ID', 'io.github.tobagin.Karere')


class MessageRow(Gtk.ListBoxRow):
    """A message row widget for displaying individual messages in a chat."""
    
    def __init__(self, message_text, is_from_me=False, timestamp=None, status=None):
        super().__init__()
        self.message_text = message_text
        self.is_from_me = is_from_me
        self.status = status
        self.timestamp = timestamp

        # Create main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_margin_top(4)
        main_box.set_margin_bottom(4)

        # Create message bubble
        message_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        message_box.set_hexpand(True)

        # Create message content
        message_label = Gtk.Label(label=message_text)
        message_label.set_wrap(True)
        message_label.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        message_label.set_xalign(0.0 if not is_from_me else 1.0)
        message_label.set_selectable(True)

        # Create timestamp and status box
        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        
        if timestamp:
            time_label = Gtk.Label(label=timestamp)
            time_label.add_css_class("caption")
            time_label.add_css_class("dim-label")
            info_box.append(time_label)

        if is_from_me and status:
            status_icon = Gtk.Image()
            if status == "sending":
                status_icon.set_from_icon_name("content-loading-symbolic")
            elif status == "sent":
                status_icon.set_from_icon_name("emblem-ok-symbolic")
            elif status == "delivered":
                status_icon.set_from_icon_name("emblem-ok-symbolic")
            elif status == "read":
                status_icon.set_from_icon_name("emblem-ok-symbolic")
                status_icon.add_css_class("accent")
            info_box.append(status_icon)

        # Style message based on sender
        if is_from_me:
            message_label.add_css_class("message-outgoing")
            message_box.set_halign(Gtk.Align.END)
            info_box.set_halign(Gtk.Align.END)
        else:
            message_label.add_css_class("message-incoming")
            message_box.set_halign(Gtk.Align.START)
            info_box.set_halign(Gtk.Align.START)

        message_box.append(message_label)
        message_box.append(info_box)
        main_box.append(message_box)

        self.set_child(main_box)
        self.set_selectable(False)


@Gtk.Template(resource_path=f'/{APP_ID.replace(".", "/")}/ui/pages/chat_page.ui')
class ChatPage(Adw.NavigationPage):
    """Individual chat page for displaying messages and sending new ones."""
    
    __gtype_name__ = 'ChatPage'
    
    # Template children
    chat_header = Gtk.Template.Child()
    chat_avatar = Gtk.Template.Child()
    chat_title = Gtk.Template.Child()
    chat_subtitle = Gtk.Template.Child()
    chat_menu_button = Gtk.Template.Child()
    messages_scrolled = Gtk.Template.Child()
    messages_list_box = Gtk.Template.Child()
    message_input_box = Gtk.Template.Child()
    attachment_button = Gtk.Template.Child()
    message_entry = Gtk.Template.Child()
    emoji_button = Gtk.Template.Child()
    send_button = Gtk.Template.Child()
    
    def __init__(self, jid, **kwargs):
        super().__init__(**kwargs)
        
        # Store chat data
        self.jid = jid
        self._window = None
        self._message_history = []
        
        # Initialize UI
        self.setup_chat_info(jid)
        
        # Connect signals
        self.send_button.connect('clicked', self.on_send_message)
        self.message_entry.connect('activate', self.on_send_message)
        self.message_entry.connect('changed', self.on_message_entry_changed)
        self.emoji_button.connect('clicked', self.on_emoji_button_clicked)
        self.attachment_button.connect('clicked', self.on_attachment_button_clicked)
        
        # Set up message list
        self.messages_list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        
    def set_window(self, window):
        """Set reference to parent window."""
        self._window = window
        
    def setup_chat_info(self, jid):
        """Set up chat information in the header."""
        display_name = self.get_display_name(jid)
        self.chat_title.set_text(display_name)
        self.chat_subtitle.set_text("Online")  # TODO: Get actual status
        self.set_title(display_name)
        
        # Set up avatar
        self.chat_avatar.set_text(display_name)
        self.chat_avatar.set_show_initials(True)
        
    def get_display_name(self, jid):
        """Get display name for a JID."""
        if self._window:
            return self._window.get_display_name(jid)
        
        # Fallback: extract from phone number
        if '@' in jid:
            phone = jid.split('@')[0]
            if phone.startswith('55'):  # Brazilian number
                return f"+{phone[:2]} ({phone[2:4]}) {phone[4:9]}-{phone[9:]}"
            else:
                return f"+{phone}"
        return jid
        
    def set_contact_info(self, contact_name=None, avatar_base64=None):
        """Update contact information."""
        if contact_name:
            self.chat_title.set_text(contact_name)
            self.set_title(contact_name)
            self.chat_avatar.set_text(contact_name)
            
        if avatar_base64:
            self.set_avatar_base64(avatar_base64)
            
    def set_avatar_base64(self, avatar_base64):
        """Set avatar from base64 data."""
        try:
            # Decode base64 data
            image_data = base64.b64decode(avatar_base64)
            
            # Create pixbuf from image data
            loader = GdkPixbuf.PixbufLoader()
            loader.write(image_data)
            loader.close()
            pixbuf = loader.get_pixbuf()
            
            # Set avatar from pixbuf
            self.chat_avatar.set_custom_image(Gtk.Image.new_from_pixbuf(pixbuf))
        except Exception as e:
            print(f"Error setting avatar: {e}")
            # Keep initials as fallback
            
    def add_message(self, message_text, is_from_me=False, timestamp=None, status=None):
        """Add a message to the chat."""
        message_row = MessageRow(message_text, is_from_me, timestamp, status)
        self.messages_list_box.append(message_row)
        
        # Store in history
        self._message_history.append({
            'text': message_text,
            'is_from_me': is_from_me,
            'timestamp': timestamp,
            'status': status
        })
        
        # Scroll to bottom
        self.scroll_to_bottom()
        
    def clear_messages(self):
        """Clear all messages from the chat."""
        while True:
            row = self.messages_list_box.get_first_child()
            if row is None:
                break
            self.messages_list_box.remove(row)
        self._message_history.clear()
        
    def load_messages(self, messages):
        """Load multiple messages at once."""
        self.clear_messages()
        for msg in messages:
            self.add_message(
                msg.get('text', ''),
                msg.get('fromMe', False),
                msg.get('timestamp'),
                msg.get('status')
            )
            
    def scroll_to_bottom(self):
        """Scroll the message view to the bottom."""
        def do_scroll():
            vadj = self.messages_scrolled.get_vadjustment()
            vadj.set_value(vadj.get_upper() - vadj.get_page_size())
            return False

        # Use idle_add to ensure the UI is updated first
        from gi.repository import GLib
        GLib.idle_add(do_scroll)
        
    def on_send_message(self, widget):
        """Handle sending a message."""
        message_text = self.message_entry.get_text().strip()
        if not message_text:
            return

        # Clear the entry
        self.message_entry.set_text("")

        # Add message to UI immediately (optimistic update)
        self.add_message(message_text, is_from_me=True, status="sending")

        # Send message to backend through window
        if self._window:
            self._window.send_message_to_backend(self.jid, message_text)

        print(f"Sending message to {self.jid}: {message_text}")

    def on_message_entry_changed(self, entry):
        """Handle message entry text changes for typing indicators."""
        if not self._window:
            return

        from gi.repository import GLib

        # Cancel previous timeout
        if hasattr(self._window, '_typing_timeout') and self._window._typing_timeout:
            GLib.source_remove(self._window._typing_timeout)
            self._window._typing_timeout = None

        text = entry.get_text()
        if text and self.jid:
            # Send typing indicator to backend
            app = self._window.get_application()
            if app and app.ws_client:
                app.ws_client.send_command('typing_start', {
                    'to': self.jid
                })

            # Set timeout to stop typing indicator
            self._window._typing_timeout = GLib.timeout_add_seconds(3, self._window._stop_typing_timeout)
        else:
            # Send stop typing to backend immediately
            if hasattr(self._window, '_send_stop_typing'):
                self._window._send_stop_typing()

    def on_emoji_button_clicked(self, button):
        """Handle emoji button click."""
        if self._window:
            self._window.show_emoji_popover(button, self)

    def on_attachment_button_clicked(self, button):
        """Handle attachment button click."""
        print("Attachment button clicked")
        # TODO: Implement attachment functionality

    def update_message_status(self, message_text, new_status):
        """Update the status of a specific message."""
        # Find the message in history and update its status
        for message_data in self._message_history:
            if (message_data['text'] == message_text and
                message_data['is_from_me'] and
                message_data.get('status') == 'sending'):
                message_data['status'] = new_status
                # Reload messages to reflect the status change
                self.load_messages(self._message_history)
                break
