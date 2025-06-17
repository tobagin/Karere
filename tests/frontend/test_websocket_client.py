#!/usr/bin/env python3
"""
Unit tests for the WebSocket client module
"""

import unittest
import json
import threading
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the frontend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'frontend'))

# Mock GObject and Gtk before importing
sys.modules['gi'] = Mock()
sys.modules['gi.repository'] = Mock()
sys.modules['gi.repository.GObject'] = Mock()
sys.modules['gi.repository.GLib'] = Mock()
sys.modules['websocket'] = Mock()

# Mock GObject.Object
class MockGObject:
    def __init__(self):
        pass
    
    def emit(self, signal, *args):
        pass

# Set up the mock
gi_mock = Mock()
gi_mock.repository.GObject.Object = MockGObject
gi_mock.repository.GObject.SignalFlags = Mock()
gi_mock.repository.GObject.SignalFlags.RUN_FIRST = 1
gi_mock.repository.GObject.TYPE_PYOBJECT = object
gi_mock.repository.GLib.idle_add = Mock()
sys.modules['gi'] = gi_mock
sys.modules['gi.repository'] = gi_mock.repository


class TestWebSocketClient(unittest.TestCase):
    """Test cases for WebSocketClient class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Import after mocking
        from karere.websocket_client import WebSocketClient
        self.WebSocketClient = WebSocketClient
        
        # Create mock WebSocket app
        self.mock_ws_app = Mock()
        self.mock_ws_app.sock = Mock()
        self.mock_ws_app.sock.connected = True
        
        # Create client instance
        self.client = WebSocketClient("ws://localhost:8765")
        self.client.ws_app = self.mock_ws_app
    
    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self.client, 'thread') and self.client.thread:
            self.client.thread = None
    
    def test_initialization(self):
        """Test WebSocketClient initialization"""
        client = WebSocketClient("ws://test:1234")
        
        self.assertEqual(client.url, "ws://test:1234")
        self.assertIsNone(client.ws_app)
        self.assertIsNone(client.thread)
    
    def test_default_url(self):
        """Test default URL initialization"""
        client = WebSocketClient()
        
        self.assertEqual(client.url, "ws://localhost:8765")
    
    @patch('threading.Thread')
    def test_start(self, mock_thread):
        """Test starting the WebSocket client"""
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        self.client.start()
        
        mock_thread.assert_called_once_with(target=self.client._run, daemon=True)
        mock_thread_instance.start.assert_called_once()
        self.assertEqual(self.client.thread, mock_thread_instance)
    
    def test_send_command_connected(self):
        """Test sending command when connected"""
        command_type = "test_command"
        data = {"key": "value"}
        
        self.client.send_command(command_type, data)
        
        expected_message = json.dumps({
            "type": command_type,
            "data": data
        })
        self.mock_ws_app.send.assert_called_once_with(expected_message)
    
    def test_send_command_no_data(self):
        """Test sending command without data"""
        command_type = "test_command"
        
        self.client.send_command(command_type)
        
        expected_message = json.dumps({
            "type": command_type,
            "data": {}
        })
        self.mock_ws_app.send.assert_called_once_with(expected_message)
    
    def test_send_command_not_connected(self):
        """Test sending command when not connected"""
        self.client.ws_app = None
        
        # Should not raise an exception
        self.client.send_command("test_command", {"key": "value"})
    
    def test_send_command_disconnected_socket(self):
        """Test sending command when socket is disconnected"""
        self.mock_ws_app.sock.connected = False
        
        # Should not raise an exception
        self.client.send_command("test_command", {"key": "value"})
    
    def test_on_open(self):
        """Test WebSocket on_open callback"""
        with patch.object(self.client, 'emit') as mock_emit:
            self.client._on_open(self.mock_ws_app)
            
            # Should emit connection-opened signal
            gi_mock.repository.GLib.idle_add.assert_called()
    
    def test_on_close(self):
        """Test WebSocket on_close callback"""
        with patch.object(self.client, 'emit') as mock_emit:
            self.client._on_close(self.mock_ws_app, 1000, "Normal closure")
            
            # Should emit connection-closed signal
            gi_mock.repository.GLib.idle_add.assert_called()
    
    def test_on_error(self):
        """Test WebSocket on_error callback"""
        error = Exception("Test error")
        
        # Should not raise an exception
        self.client._on_error(self.mock_ws_app, error)
    
    def test_on_message_qr(self):
        """Test handling QR code message"""
        message_data = {
            "type": "qr",
            "data": {"url": "data:image/png;base64,test"}
        }
        message = json.dumps(message_data)
        
        with patch.object(self.client, 'emit') as mock_emit:
            self.client._on_message(self.mock_ws_app, message)
            
            # Should emit qr-received signal
            gi_mock.repository.GLib.idle_add.assert_called()
    
    def test_on_message_baileys_ready(self):
        """Test handling baileys_ready message"""
        message_data = {
            "type": "baileys_ready",
            "data": {}
        }
        message = json.dumps(message_data)
        
        with patch.object(self.client, 'emit') as mock_emit:
            self.client._on_message(self.mock_ws_app, message)
            
            # Should emit baileys-ready signal
            gi_mock.repository.GLib.idle_add.assert_called()
    
    def test_on_message_new_message(self):
        """Test handling new message"""
        message_data = {
            "type": "newMessage",
            "data": {
                "from": "5511999999999@s.whatsapp.net",
                "body": "Test message"
            }
        }
        message = json.dumps(message_data)
        
        with patch.object(self.client, 'emit') as mock_emit:
            self.client._on_message(self.mock_ws_app, message)
            
            # Should emit new-message signal
            gi_mock.repository.GLib.idle_add.assert_called()
    
    def test_on_message_initial_chats(self):
        """Test handling initial chats message"""
        message_data = {
            "type": "initial_chats",
            "data": {
                "chats": [
                    {"jid": "test1@s.whatsapp.net", "name": "Test 1"},
                    {"jid": "test2@s.whatsapp.net", "name": "Test 2"}
                ]
            }
        }
        message = json.dumps(message_data)
        
        with patch.object(self.client, 'emit') as mock_emit:
            self.client._on_message(self.mock_ws_app, message)
            
            # Should emit initial-chats signal
            gi_mock.repository.GLib.idle_add.assert_called()
    
    def test_on_message_message_sent(self):
        """Test handling message sent confirmation"""
        message_data = {
            "type": "message_sent",
            "data": {
                "to": "5511999999999@s.whatsapp.net",
                "message": "Test message"
            }
        }
        message = json.dumps(message_data)
        
        with patch.object(self.client, 'emit') as mock_emit:
            self.client._on_message(self.mock_ws_app, message)
            
            # Should emit message-sent signal
            gi_mock.repository.GLib.idle_add.assert_called()
    
    def test_on_message_message_error(self):
        """Test handling message error"""
        message_data = {
            "type": "message_error",
            "data": {"error": "Failed to send message"}
        }
        message = json.dumps(message_data)
        
        with patch.object(self.client, 'emit') as mock_emit:
            self.client._on_message(self.mock_ws_app, message)
            
            # Should emit message-error signal
            gi_mock.repository.GLib.idle_add.assert_called()
    
    def test_on_message_invalid_json(self):
        """Test handling invalid JSON message"""
        invalid_message = "invalid json"
        
        # Should not raise an exception
        self.client._on_message(self.mock_ws_app, invalid_message)
    
    def test_on_message_unknown_type(self):
        """Test handling unknown message type"""
        message_data = {
            "type": "unknown_type",
            "data": {}
        }
        message = json.dumps(message_data)
        
        # Should not raise an exception
        self.client._on_message(self.mock_ws_app, message)
    
    def test_signals_defined(self):
        """Test that all required signals are defined"""
        expected_signals = [
            'connection-opened',
            'connection-closed',
            'qr-received',
            'status-update',
            'new-message',
            'initial-chats',
            'baileys-ready',
            'message-sent',
            'message-error',
            'message-history',
        ]
        
        # Check that __gsignals__ is defined
        self.assertTrue(hasattr(self.WebSocketClient, '__gsignals__'))
        
        # Check that all expected signals are present
        defined_signals = list(self.WebSocketClient.__gsignals__.keys())
        for signal in expected_signals:
            self.assertIn(signal, defined_signals)


class TestWebSocketClientIntegration(unittest.TestCase):
    """Integration tests for WebSocketClient"""
    
    def setUp(self):
        """Set up test fixtures"""
        from karere.websocket_client import WebSocketClient
        self.WebSocketClient = WebSocketClient
    
    def test_signal_emission_flow(self):
        """Test the complete signal emission flow"""
        client = WebSocketClient()
        
        # Mock the emit method
        client.emit = Mock()
        
        # Test QR signal flow
        qr_message = json.dumps({
            "type": "qr",
            "data": {"url": "test_qr_data"}
        })
        
        client._on_message(None, qr_message)
        
        # Verify GLib.idle_add was called (signal emission)
        gi_mock.repository.GLib.idle_add.assert_called()
    
    def test_connection_lifecycle(self):
        """Test the complete connection lifecycle"""
        client = WebSocketClient()
        client.emit = Mock()
        
        # Test connection open
        client._on_open(None)
        
        # Test message handling
        test_message = json.dumps({
            "type": "baileys_ready",
            "data": {}
        })
        client._on_message(None, test_message)
        
        # Test connection close
        client._on_close(None, 1000, "Normal")
        
        # Verify all events were processed
        self.assertTrue(gi_mock.repository.GLib.idle_add.called)


if __name__ == '__main__':
    unittest.main()
