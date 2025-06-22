#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GObject
import os

# Dynamic app ID for Flatpak compatibility
APP_ID = os.environ.get('FLATPAK_ID', 'io.github.tobagin.Karere')


@Gtk.Template(resource_path=f'/{APP_ID.replace(".", "/")}/ui/pages/chat_list_page.ui')
class ChatListPage(Adw.NavigationPage):
    """Chat list page that displays all chats in the sidebar."""
    
    __gtype_name__ = 'KarereChatListPage'
    
    # Template children
    chats_listbox = Gtk.Template.Child()
    search_bar = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    new_chat = Gtk.Template.Child()
    contacts = Gtk.Template.Child()
    search = Gtk.Template.Child()
    chats_menu = Gtk.Template.Child()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Store chat rows
        self._chat_rows = {}
        
        # Connect signals
        self.chats_listbox.connect('row-selected', self.on_chat_selected)
        self.new_chat.connect('clicked', self.on_new_chat_clicked)
        self.contacts.connect('clicked', self.on_contacts_clicked)
        self.search.connect('clicked', self.on_search_clicked)
        
        # Set up search functionality
        self.search_entry.connect('search-changed', self.on_search_changed)
        self.search_bar.connect_entry(self.search_entry)
        self.chats_listbox.set_filter_func(self.filter_chat_row)
        
        # Reference to parent window (will be set by window)
        self.window = None
    
    def set_window(self, window):
        """Set reference to parent window."""
        self.window = window
    
    def add_or_update_chat(self, jid, last_message, timestamp=None, unread_count=0, contact_name=None, avatar_base64=None):
        """Add or update a chat in the list."""
        from chat_row import ChatRow

        if jid in self._chat_rows:
            # Update existing chat row
            chat_row = self._chat_rows[jid]
            chat_row.update_last_message(last_message, timestamp)
            if unread_count > 0:
                chat_row.update_unread_count(unread_count)
            # Update contact info if provided
            if contact_name:
                chat_row.set_contact_info(contact_name=contact_name)
            if avatar_base64:
                chat_row.set_avatar_base64(avatar_base64)

            # Move chat to top of list (remove and prepend)
            self.chats_listbox.remove(chat_row)
            self.chats_listbox.prepend(chat_row)
        else:
            # Create new chat row
            new_row = ChatRow(jid, last_message, timestamp, unread_count)
            new_row.set_chat_list_page(self)  # Set reference to this page
            # Set contact info if provided
            if contact_name:
                new_row.set_contact_info(contact_name=contact_name)
            if avatar_base64:
                new_row.set_avatar_base64(avatar_base64)
            self._chat_rows[jid] = new_row
            self.chats_listbox.prepend(new_row)
            new_row.set_visible(True)
    
    def remove_chat(self, jid):
        """Remove a chat from the list."""
        if jid in self._chat_rows:
            chat_row = self._chat_rows[jid]
            self.chats_listbox.remove(chat_row)
            del self._chat_rows[jid]
    
    def get_chat_row(self, jid):
        """Get chat row by JID."""
        return self._chat_rows.get(jid)
    
    def on_chat_selected(self, listbox, row):
        """Handle chat selection."""
        if row is None or self.window is None:
            return
        
        # Delegate to window's chat selection handler
        self.window.on_chat_selected_from_list(row)
    
    def on_new_chat_clicked(self, button):
        """Handle new chat button click."""
        print("New chat clicked")
        # TODO: Implement new chat functionality
    
    def on_contacts_clicked(self, button):
        """Handle contacts button click."""
        print("Contacts clicked")
        # TODO: Implement contacts functionality
    
    def on_search_clicked(self, button):
        """Handle search button click."""
        self.search_bar.set_search_mode(not self.search_bar.get_search_mode())
    
    def on_search_changed(self, search_entry):
        """Handle search text change."""
        self.chats_listbox.invalidate_filter()
    
    def filter_chat_row(self, row):
        """Filter chat rows based on search text."""
        if not self.search_bar.get_search_mode():
            return True
        
        search_text = self.search_entry.get_text().lower()
        if not search_text:
            return True
        
        # Filter by contact name or JID
        if hasattr(row, 'jid'):
            jid = row.jid.lower()
            # Get display name from window if available
            if self.window:
                display_name = self.window.get_display_name(row.jid).lower()
                return search_text in display_name or search_text in jid
            else:
                return search_text in jid
        
        return True
    
    def clear_chats(self):
        """Clear all chats from the list."""
        for jid in list(self._chat_rows.keys()):
            self.remove_chat(jid)
