#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GObject, Gio
import os

# Dynamic app ID for Flatpak compatibility
APP_ID = os.environ.get('FLATPAK_ID', 'io.github.tobagin.Karere')


@Gtk.Template(resource_path=f'/{APP_ID.replace(".", "/")}/ui/dialogs/settings.ui')
class SettingsDialog(Adw.PreferencesDialog):
    """Settings dialog for configuring application preferences."""
    
    __gtype_name__ = 'SettingsDialog'
    
    # Template children
    dark_mode_switch = Gtk.Template.Child()
    theme_combo = Gtk.Template.Child()
    notifications_switch = Gtk.Template.Child()
    sound_switch = Gtk.Template.Child()
    read_receipts_switch = Gtk.Template.Child()
    typing_indicators_switch = Gtk.Template.Child()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Initialize settings
        self.settings = Gio.Settings.new(APP_ID)
        
        # Connect signals
        self.dark_mode_switch.connect('notify::active', self.on_dark_mode_changed)
        self.theme_combo.connect('notify::selected', self.on_theme_changed)
        self.notifications_switch.connect('notify::active', self.on_notifications_changed)
        self.sound_switch.connect('notify::active', self.on_sound_changed)
        self.read_receipts_switch.connect('notify::active', self.on_read_receipts_changed)
        self.typing_indicators_switch.connect('notify::active', self.on_typing_indicators_changed)
        
        # Load current settings
        self.load_settings()
        
    def load_settings(self):
        """Load settings from GSettings and update UI."""
        try:
            # Theme settings
            dark_mode = self.settings.get_boolean('dark-mode') if self.settings.get_user_value('dark-mode') else False
            self.dark_mode_switch.set_active(dark_mode)
            
            theme_index = self.settings.get_int('theme-preference') if self.settings.get_user_value('theme-preference') else 0
            self.theme_combo.set_selected(theme_index)
            
            # Notification settings
            notifications = self.settings.get_boolean('enable-notifications') if self.settings.get_user_value('enable-notifications') else True
            self.notifications_switch.set_active(notifications)
            
            sounds = self.settings.get_boolean('notification-sounds') if self.settings.get_user_value('notification-sounds') else True
            self.sound_switch.set_active(sounds)
            
            # Privacy settings
            read_receipts = self.settings.get_boolean('read-receipts') if self.settings.get_user_value('read-receipts') else True
            self.read_receipts_switch.set_active(read_receipts)
            
            typing_indicators = self.settings.get_boolean('typing-indicators') if self.settings.get_user_value('typing-indicators') else True
            self.typing_indicators_switch.set_active(typing_indicators)
            
        except Exception as e:
            print(f"Error loading settings: {e}")
            # Use default values if settings can't be loaded
            
    def on_dark_mode_changed(self, switch, param):
        """Handle dark mode toggle."""
        active = switch.get_active()
        self.settings.set_boolean('dark-mode', active)
        
        # Apply theme change immediately
        style_manager = Adw.StyleManager.get_default()
        if active:
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
            
    def on_theme_changed(self, combo, param):
        """Handle theme selection change."""
        selected = combo.get_selected()
        self.settings.set_int('theme-preference', selected)
        
        # Apply theme change immediately
        style_manager = Adw.StyleManager.get_default()
        if selected == 0:  # System
            style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)
        elif selected == 1:  # Light
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif selected == 2:  # Dark
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            
    def on_notifications_changed(self, switch, param):
        """Handle notifications toggle."""
        active = switch.get_active()
        self.settings.set_boolean('enable-notifications', active)
        
    def on_sound_changed(self, switch, param):
        """Handle notification sounds toggle."""
        active = switch.get_active()
        self.settings.set_boolean('notification-sounds', active)
        
    def on_read_receipts_changed(self, switch, param):
        """Handle read receipts toggle."""
        active = switch.get_active()
        self.settings.set_boolean('read-receipts', active)
        
        # Send setting to backend
        app = self.get_root().get_application()
        if app and app.ws_client:
            app.ws_client.send_command('update_setting', {
                'key': 'read_receipts',
                'value': active
            })
        
    def on_typing_indicators_changed(self, switch, param):
        """Handle typing indicators toggle."""
        active = switch.get_active()
        self.settings.set_boolean('typing-indicators', active)
        
        # Send setting to backend
        app = self.get_root().get_application()
        if app and app.ws_client:
            app.ws_client.send_command('update_setting', {
                'key': 'typing_indicators',
                'value': active
            })
