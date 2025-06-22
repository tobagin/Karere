#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GObject, Gdk, GdkPixbuf
import os
import time

# Dynamic app ID for Flatpak compatibility
APP_ID = os.environ.get('FLATPAK_ID', 'io.github.tobagin.Karere')


@Gtk.Template(resource_path=f'/{APP_ID.replace(".", "/")}/ui/chat_row.ui')
class ChatRow(Gtk.ListBoxRow):
    """Chat row widget for displaying individual chats in the chat list."""
    
    __gtype_name__ = 'KarereChatRow'
    
    # Template children
    avatar = Gtk.Template.Child()
    name_label = Gtk.Template.Child()
    time_label = Gtk.Template.Child()
    last_message_label = Gtk.Template.Child()
    status_icon = Gtk.Template.Child()
    muted_icon = Gtk.Template.Child()
    pinned_icon = Gtk.Template.Child()
    unread_badge = Gtk.Template.Child()
    
    def __init__(self, jid, last_message, timestamp=None, unread_count=0, **kwargs):
        super().__init__(**kwargs)

        # Store chat data
        self.jid = jid
        self.unread_count = unread_count
        self.is_muted = False
        self.is_pinned = False
        self._contact_name = None  # Cache for actual contact name
        self._avatar_base64 = None # Cache for profile picture base64 data

        # Reference to chat list page (will be set by chat list page)
        self.chat_list_page = None

        # Initialize UI
        self.update_contact_name(jid)
        self.update_last_message(last_message, timestamp)
        self.update_unread_count(unread_count)

        # Set up avatar
        self.setup_avatar(jid)
    
    def set_chat_list_page(self, chat_list_page):
        """Set reference to the chat list page."""
        self.chat_list_page = chat_list_page
    
    def setup_avatar(self, jid):
        """Set up the avatar for this chat."""
        # Extract name for initials
        display_name = self.get_display_name(jid)
        self.avatar.set_text(display_name)
        self.avatar.set_show_initials(True)

        # Use base64 avatar if available
        if self._avatar_base64:
            self.setup_avatar_from_base64(jid)

    def setup_avatar_from_base64(self, jid):
        """Set up the avatar from base64 data."""
        # Extract name for initials
        display_name = self.get_display_name(jid)
        self.avatar.set_text(display_name)
        self.avatar.set_show_initials(True)

        # Set actual profile picture if available
        if self._avatar_base64:
            try:
                import base64
                from io import BytesIO

                # Extract base64 data (remove data:image/...;base64, prefix)
                if ',' in self._avatar_base64:
                    base64_data = self._avatar_base64.split(',')[1]
                else:
                    base64_data = self._avatar_base64

                # Decode base64 to bytes
                image_data = base64.b64decode(base64_data)

                # Create pixbuf from bytes
                loader = GdkPixbuf.PixbufLoader()
                loader.write(image_data)
                loader.close()
                pixbuf = loader.get_pixbuf()

                # Scale to 48x48
                scaled_pixbuf = pixbuf.scale_simple(48, 48, GdkPixbuf.InterpType.BILINEAR)
                texture = Gdk.Texture.new_for_pixbuf(scaled_pixbuf)
                self.avatar.set_custom_image(texture)
                print(f"Successfully loaded base64 avatar for {jid}")
            except Exception as e:
                print(f"Failed to load base64 avatar: {e}")
                # Fall back to initials

    def get_display_name(self, jid):
        """Get display name for a JID."""
        # First priority: stored contact name
        if self._contact_name:
            return self._contact_name

        # Second priority: window's display name (may include contact lookup)
        if self.chat_list_page and self.chat_list_page.window:
            return self.chat_list_page.window.get_display_name(jid)

        # Fallback: extract from phone number
        if '@' in jid:
            phone = jid.split('@')[0]
            if phone.startswith('55'):  # Brazilian number
                return f"+{phone[:2]} ({phone[2:4]}) {phone[4:9]}-{phone[9:]}"
            else:
                return f"+{phone}"
        return jid
    
    def update_contact_name(self, jid):
        """Update the contact name display."""
        display_name = self.get_display_name(jid)
        self.name_label.set_text(display_name)
    
    def update_last_message(self, message, timestamp=None):
        """Update the last message and timestamp."""
        # Truncate long messages
        if len(message) > 50:
            message = message[:47] + "..."
        
        self.last_message_label.set_text(message)
        
        if timestamp:
            time_str = self.format_timestamp(timestamp)
            self.time_label.set_text(time_str)
        else:
            # Use current time if no timestamp provided
            current_time = time.time()
            time_str = self.format_timestamp(current_time)
            self.time_label.set_text(time_str)
    
    def format_timestamp(self, timestamp):
        """Format timestamp for display."""
        try:
            if isinstance(timestamp, str):
                # Try to parse string timestamp
                timestamp = float(timestamp)

            # Convert milliseconds to seconds if needed (WhatsApp timestamps are in milliseconds)
            if timestamp > 1e12:  # If timestamp is in milliseconds
                timestamp = timestamp / 1000

            current_time = time.time()
            diff = current_time - timestamp

            # If less than a day, show time
            if diff < 86400:  # 24 hours
                return time.strftime("%H:%M", time.localtime(timestamp))
            # If less than a week, show day
            elif diff < 604800:  # 7 days
                return time.strftime("%a", time.localtime(timestamp))
            # Otherwise show date
            else:
                return time.strftime("%d/%m", time.localtime(timestamp))
        except (ValueError, TypeError):
            return "now"
    
    def update_unread_count(self, count):
        """Update the unread message count."""
        self.unread_count = count
        
        if count > 0:
            self.unread_badge.set_text(str(count))
            self.unread_badge.set_visible(True)
        else:
            self.unread_badge.set_visible(False)
    
    def set_muted(self, muted):
        """Set muted status."""
        self.is_muted = muted
        self.muted_icon.set_visible(muted)
    
    def set_pinned(self, pinned):
        """Set pinned status."""
        self.is_pinned = pinned
        self.pinned_icon.set_visible(pinned)
    
    def set_message_status(self, status):
        """Set message status (sent, delivered, read)."""
        if status == "sent":
            self.status_icon.set_icon_name("emblem-ok-symbolic")
            self.status_icon.set_visible(True)
        elif status == "delivered":
            self.status_icon.set_icon_name("emblem-ok-symbolic")
            self.status_icon.set_visible(True)
        elif status == "read":
            self.status_icon.set_icon_name("emblem-ok-symbolic")
            self.status_icon.set_visible(True)
        else:
            self.status_icon.set_visible(False)
    
    def mark_as_read(self):
        """Mark this chat as read."""
        self.update_unread_count(0)
    
    def increment_unread(self):
        """Increment unread count."""
        self.update_unread_count(self.unread_count + 1)

    def set_contact_info(self, contact_name=None):
        """Set contact information (name)."""
        if contact_name:
            self._contact_name = contact_name
            self.name_label.set_text(contact_name)

    def get_contact_name(self):
        """Get the stored contact name."""
        return self._contact_name



    def set_avatar_base64(self, avatar_base64):
        """Set avatar base64 data and update the avatar display."""
        if avatar_base64:
            self._avatar_base64 = avatar_base64
            self.setup_avatar_from_base64(self.jid)
