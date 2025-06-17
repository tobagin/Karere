#!/usr/bin/env python3
"""
Unit tests for the main window module
"""

import unittest
import base64
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the frontend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'frontend'))

# Mock all GTK and GObject modules
class MockGObject:
    def __init__(self):
        pass
    
    def emit(self, signal, *args):
        pass

class MockWidget:
    def __init__(self):
        self.visible = True
        self.text = ""
        self.active = False
    
    def set_visible(self, visible):
        self.visible = visible
    
    def get_visible(self):
        return self.visible
    
    def set_text(self, text):
        self.text = text
    
    def get_text(self):
        return self.text
    
    def set_active(self, active):
        self.active = active
    
    def get_active(self):
        return self.active
    
    def connect(self, signal, callback):
        pass
    
    def grab_focus(self):
        pass

# Set up comprehensive mocks
gi_mock = Mock()
gi_mock.repository.GObject.Object = MockGObject
gi_mock.repository.GObject.SignalFlags = Mock()
gi_mock.repository.GObject.SignalFlags.RUN_FIRST = 1
gi_mock.repository.GObject.TYPE_PYOBJECT = object
gi_mock.repository.GLib.idle_add = Mock()
gi_mock.repository.Gtk = Mock()
gi_mock.repository.Gtk.Template = Mock()
gi_mock.repository.Gtk.Template.Child = Mock()
gi_mock.repository.Gtk.ListBoxRow = MockWidget
gi_mock.repository.Gtk.Label = MockWidget
gi_mock.repository.Gtk.Box = MockWidget
gi_mock.repository.Gtk.Align = Mock()
gi_mock.repository.Gtk.Align.START = 0
gi_mock.repository.Gtk.Align.END = 1
gi_mock.repository.Adw = Mock()
gi_mock.repository.Adw.ApplicationWindow = MockWidget
gi_mock.repository.GdkPixbuf = Mock()

sys.modules['gi'] = gi_mock
sys.modules['gi.repository'] = gi_mock.repository
sys.modules['gi.repository.GObject'] = gi_mock.repository.GObject
sys.modules['gi.repository.GLib'] = gi_mock.repository.GLib
sys.modules['gi.repository.Gtk'] = gi_mock.repository.Gtk
sys.modules['gi.repository.Adw'] = gi_mock.repository.Adw
sys.modules['gi.repository.GdkPixbuf'] = gi_mock.repository.GdkPixbuf


class TestChatRow(unittest.TestCase):
    """Test cases for ChatRow class"""
    
    def setUp(self):
        """Set up test fixtures"""
        from karere.window import ChatRow
        self.ChatRow = ChatRow
    
    def test_chat_row_initialization(self):
        """Test ChatRow initialization"""
        jid = "5511999999999@s.whatsapp.net"
        last_message = "Hello, world!"
        timestamp = 1234567890
        unread_count = 5
        
        chat_row = ChatRow(jid, last_message, timestamp, unread_count)
        
        self.assertEqual(chat_row.jid, jid)
        self.assertEqual(chat_row.unread_count, unread_count)
    
    def test_chat_row_default_values(self):
        """Test ChatRow with default values"""
        jid = "5511999999999@s.whatsapp.net"
        last_message = "Hello, world!"
        
        chat_row = ChatRow(jid, last_message)
        
        self.assertEqual(chat_row.jid, jid)
        self.assertEqual(chat_row.unread_count, 0)
    
    def test_update_last_message(self):
        """Test updating last message"""
        chat_row = ChatRow("test@s.whatsapp.net", "Old message")
        new_message = "New message"
        timestamp = 1234567890
        
        chat_row.update_last_message(new_message, timestamp)
        
        # Should not raise an exception
        self.assertTrue(True)
    
    def test_update_unread_count(self):
        """Test updating unread count"""
        chat_row = ChatRow("test@s.whatsapp.net", "Message")
        
        # Test with count > 0
        chat_row.update_unread_count(5)
        self.assertEqual(chat_row.unread_count, 5)
        
        # Test with count = 0
        chat_row.update_unread_count(0)
        self.assertEqual(chat_row.unread_count, 0)
        
        # Test with count > 99
        chat_row.update_unread_count(150)
        self.assertEqual(chat_row.unread_count, 150)
    
    def test_get_display_name(self):
        """Test display name formatting"""
        chat_row = ChatRow("test@s.whatsapp.net", "Message")
        
        # Test Brazilian number
        brazilian_jid = "5511999999999@s.whatsapp.net"
        display_name = chat_row.get_display_name(brazilian_jid)
        self.assertIn("+55", display_name)
        self.assertIn("(11)", display_name)
        
        # Test non-Brazilian number
        other_jid = "1234567890@s.whatsapp.net"
        display_name = chat_row.get_display_name(other_jid)
        self.assertIn("+1234567890", display_name)
        
        # Test JID without @
        simple_jid = "test"
        display_name = chat_row.get_display_name(simple_jid)
        self.assertEqual(display_name, simple_jid)


class TestMessageRow(unittest.TestCase):
    """Test cases for MessageRow class"""
    
    def setUp(self):
        """Set up test fixtures"""
        from karere.window import MessageRow
        self.MessageRow = MessageRow
    
    def test_message_row_initialization(self):
        """Test MessageRow initialization"""
        message_text = "Test message"
        is_from_me = True
        timestamp = "14:30"
        status = "sent"
        
        message_row = MessageRow(message_text, is_from_me, timestamp, status)
        
        self.assertEqual(message_row.message_text, message_text)
        self.assertEqual(message_row.is_from_me, is_from_me)
        self.assertEqual(message_row.status, status)
    
    def test_message_row_default_values(self):
        """Test MessageRow with default values"""
        message_text = "Test message"
        
        message_row = MessageRow(message_text)
        
        self.assertEqual(message_row.message_text, message_text)
        self.assertEqual(message_row.is_from_me, False)
        self.assertIsNone(message_row.status)
    
    def test_format_timestamp_string(self):
        """Test timestamp formatting with string input"""
        message_row = MessageRow("Test")
        
        # Test with already formatted string
        formatted = message_row.format_timestamp("14:30")
        self.assertEqual(formatted, "14:30")
    
    def test_format_timestamp_unix(self):
        """Test timestamp formatting with Unix timestamp"""
        message_row = MessageRow("Test")
        
        # Test with Unix timestamp (should not raise exception)
        import time
        current_time = int(time.time())
        formatted = message_row.format_timestamp(current_time)
        
        # Should return some formatted string
        self.assertIsInstance(formatted, str)
    
    def test_format_timestamp_invalid(self):
        """Test timestamp formatting with invalid input"""
        message_row = MessageRow("Test")
        
        # Test with invalid timestamp
        formatted = message_row.format_timestamp("invalid")
        
        # Should return the input as string
        self.assertEqual(formatted, "invalid")


class TestKarereWindow(unittest.TestCase):
    """Test cases for KarereWindow class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock template decorator
        def mock_template(resource_path):
            def decorator(cls):
                return cls
            return decorator
        
        gi_mock.repository.Gtk.Template = mock_template
        
        from karere.window import KarereWindow
        self.KarereWindow = KarereWindow
        
        # Create mock template children
        self.mock_children = {
            'main_stack': MockWidget(),
            'chat_list_box': MockWidget(),
            'qr_image': MockWidget(),
            'qr_spinner': MockWidget(),
            'message_stack': MockWidget(),
            'messages_list_box': MockWidget(),
            'chat_title_label': MockWidget(),
            'message_entry': MockWidget(),
            'send_button': MockWidget(),
            'messages_scrolled': MockWidget(),
            'search_bar': MockWidget(),
            'search_entry': MockWidget(),
            'search_button': MockWidget(),
            'typing_revealer': MockWidget(),
            'typing_label': MockWidget(),
            'emoji_button': MockWidget(),
        }
    
    def create_window_instance(self):
        """Create a KarereWindow instance with mocked children"""
        window = self.KarereWindow()
        
        # Set mock children
        for name, widget in self.mock_children.items():
            setattr(window, name, widget)
        
        return window
    
    def test_window_initialization(self):
        """Test KarereWindow initialization"""
        window = self.create_window_instance()
        
        self.assertIsInstance(window._chat_rows, dict)
        self.assertIsNone(window._current_chat_jid)
        self.assertIsInstance(window._message_history, dict)
    
    def test_add_or_update_chat_new(self):
        """Test adding a new chat"""
        window = self.create_window_instance()
        
        jid = "5511999999999@s.whatsapp.net"
        last_message = "Hello, world!"
        timestamp = 1234567890
        unread_count = 2
        
        window.add_or_update_chat(jid, last_message, timestamp, unread_count)
        
        # Should not raise an exception
        self.assertTrue(True)
    
    def test_add_or_update_chat_existing(self):
        """Test updating an existing chat"""
        window = self.create_window_instance()
        
        jid = "5511999999999@s.whatsapp.net"
        
        # Add chat first
        window.add_or_update_chat(jid, "First message")
        
        # Update chat
        window.add_or_update_chat(jid, "Second message", 1234567890, 1)
        
        # Should not raise an exception
        self.assertTrue(True)
    
    def test_on_chat_selected(self):
        """Test chat selection"""
        window = self.create_window_instance()
        
        # Create mock chat row
        mock_row = Mock()
        mock_row.jid = "5511999999999@s.whatsapp.net"
        
        window.on_chat_selected(None, mock_row)
        
        self.assertEqual(window._current_chat_jid, mock_row.jid)
    
    def test_on_chat_selected_none(self):
        """Test chat selection with None row"""
        window = self.create_window_instance()
        
        # Should not raise an exception
        window.on_chat_selected(None, None)
        
        self.assertIsNone(window._current_chat_jid)
    
    def test_on_send_message_no_chat(self):
        """Test sending message with no chat selected"""
        window = self.create_window_instance()
        
        # Should not raise an exception
        window.on_send_message(None)
        
        self.assertIsNone(window._current_chat_jid)
    
    def test_on_send_message_empty_text(self):
        """Test sending empty message"""
        window = self.create_window_instance()
        window._current_chat_jid = "test@s.whatsapp.net"
        window.message_entry.get_text = Mock(return_value="   ")
        
        # Should not raise an exception
        window.on_send_message(None)
    
    def test_on_send_message_valid(self):
        """Test sending valid message"""
        window = self.create_window_instance()
        window._current_chat_jid = "test@s.whatsapp.net"
        window.message_entry.get_text = Mock(return_value="Test message")
        window.message_entry.set_text = Mock()
        window.add_message_to_chat = Mock()
        window.send_message_to_backend = Mock()
        
        window.on_send_message(None)
        
        window.message_entry.set_text.assert_called_with("")
        window.add_message_to_chat.assert_called()
        window.send_message_to_backend.assert_called()
    
    def test_get_display_name(self):
        """Test display name formatting"""
        window = self.create_window_instance()
        
        # Test Brazilian number
        brazilian_jid = "5511999999999@s.whatsapp.net"
        display_name = window.get_display_name(brazilian_jid)
        self.assertIn("+55", display_name)
        
        # Test other number
        other_jid = "1234567890@s.whatsapp.net"
        display_name = window.get_display_name(other_jid)
        self.assertIn("+1234567890", display_name)
        
        # Test simple JID
        simple_jid = "test"
        display_name = window.get_display_name(simple_jid)
        self.assertEqual(display_name, simple_jid)
    
    def test_show_qr_code_valid(self):
        """Test showing valid QR code"""
        window = self.create_window_instance()
        
        # Create valid base64 QR data
        test_data = base64.b64encode(b"test").decode()
        qr_data_url = f"data:image/png;base64,{test_data}"
        
        # Mock pixbuf loader
        mock_loader = Mock()
        mock_pixbuf = Mock()
        mock_loader.get_pixbuf.return_value = mock_pixbuf
        
        with patch('gi.repository.GdkPixbuf.PixbufLoader.new_with_type', return_value=mock_loader):
            window.show_qr_code(qr_data_url)
            
            mock_loader.write.assert_called()
            mock_loader.close.assert_called()
    
    def test_show_qr_code_invalid(self):
        """Test showing invalid QR code"""
        window = self.create_window_instance()
        
        # Should not raise an exception
        window.show_qr_code("invalid_data")
        window.show_qr_code("")
        window.show_qr_code(None)
    
    def test_search_functionality(self):
        """Test search functionality"""
        window = self.create_window_instance()
        
        # Test search toggle
        window.search_button.get_active = Mock(return_value=True)
        window.search_bar.set_search_mode = Mock()
        window.search_entry.grab_focus = Mock()
        
        window.on_search_toggled(window.search_button)
        
        window.search_bar.set_search_mode.assert_called_with(True)
        window.search_entry.grab_focus.assert_called()
    
    def test_filter_chat_row(self):
        """Test chat row filtering"""
        window = self.create_window_instance()
        window.search_entry.get_text = Mock(return_value="test")
        
        # Create mock chat row
        mock_row = Mock()
        mock_row.jid = "test@s.whatsapp.net"
        mock_row.last_message_label.get_text = Mock(return_value="test message")
        
        result = window.filter_chat_row(mock_row)
        
        # Should return True for matching text
        self.assertTrue(result)
    
    def test_filter_chat_row_no_search(self):
        """Test chat row filtering with no search text"""
        window = self.create_window_instance()
        window.search_entry.get_text = Mock(return_value="")
        
        mock_row = Mock()
        
        result = window.filter_chat_row(mock_row)
        
        # Should return True when no search text
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
