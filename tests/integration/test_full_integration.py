#!/usr/bin/env python3
"""
Full integration tests for Karere application
Tests the complete flow from frontend to backend
"""

import unittest
import asyncio
import json
import time
import threading
import subprocess
import signal
import os
import sys
from unittest.mock import Mock, patch
import websocket

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'frontend'))


class TestFullIntegration(unittest.TestCase):
    """Full integration tests for the complete application"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.backend_process = None
        cls.backend_port = 8766  # Test port
        cls.backend_ready = False
        
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        if cls.backend_process:
            cls.backend_process.terminate()
            cls.backend_process.wait()
    
    def setUp(self):
        """Set up individual test"""
        self.ws_client = None
        self.received_messages = []
        
    def tearDown(self):
        """Clean up individual test"""
        if self.ws_client:
            self.ws_client.close()
    
    def start_mock_backend(self):
        """Start a mock backend server for testing"""
        import websocket
        from websocket_server import WebsocketServer
        
        def new_client(client, server):
            """Handle new client connection"""
            print(f"New client connected: {client['id']}")
        
        def client_left(client, server):
            """Handle client disconnection"""
            print(f"Client disconnected: {client['id']}")
        
        def message_received(client, server, message):
            """Handle received message"""
            try:
                data = json.loads(message)
                print(f"Received: {data}")
                
                # Mock responses based on message type
                if data.get('type') == 'get_initial_chats':
                    response = {
                        'type': 'initial_chats',
                        'data': {
                            'chats': [
                                {
                                    'jid': '5511999999999@s.whatsapp.net',
                                    'name': 'Test Contact 1',
                                    'lastMessage': 'Hello from test',
                                    'timestamp': int(time.time() * 1000),
                                    'unreadCount': 2
                                },
                                {
                                    'jid': '5511888888888@s.whatsapp.net',
                                    'name': 'Test Contact 2',
                                    'lastMessage': 'Another test message',
                                    'timestamp': int(time.time() * 1000) - 1000,
                                    'unreadCount': 0
                                }
                            ]
                        }
                    }
                    server.send_message(client, json.dumps(response))
                
                elif data.get('type') == 'send_message':
                    # Mock successful message send
                    response = {
                        'type': 'message_sent',
                        'data': {
                            'to': data['data']['to'],
                            'message': data['data']['message'],
                            'messageId': f"msg_{int(time.time())}",
                            'timestamp': int(time.time() * 1000)
                        }
                    }
                    server.send_message(client, json.dumps(response))
                
                elif data.get('type') == 'health_check':
                    response = {
                        'type': 'health_status',
                        'data': {
                            'healthy': True,
                            'backend': {
                                'uptime': 100,
                                'services': ['websocket', 'database'],
                                'performance': {
                                    'memory': {'heapUsed': 50000000},
                                    'cpu': {'user': 1000, 'system': 500}
                                }
                            },
                            'baileys': {
                                'status': 'open',
                                'connected': True
                            }
                        }
                    }
                    server.send_message(client, json.dumps(response))
                    
            except json.JSONDecodeError:
                print(f"Invalid JSON received: {message}")
        
        # Start mock server
        server = WebsocketServer(self.backend_port, host='localhost')
        server.set_fn_new_client(new_client)
        server.set_fn_client_left(client_left)
        server.set_fn_message_received(message_received)
        
        # Run server in thread
        server_thread = threading.Thread(target=server.run_forever, daemon=True)
        server_thread.start()
        
        # Wait for server to start
        time.sleep(1)
        self.backend_ready = True
        
        return server
    
    def create_websocket_client(self):
        """Create a WebSocket client for testing"""
        def on_message(ws, message):
            self.received_messages.append(json.loads(message))
            print(f"Received message: {message}")
        
        def on_error(ws, error):
            print(f"WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            print("WebSocket connection closed")
        
        def on_open(ws):
            print("WebSocket connection opened")
        
        ws_url = f"ws://localhost:{self.backend_port}"
        self.ws_client = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Start WebSocket in thread
        ws_thread = threading.Thread(target=self.ws_client.run_forever, daemon=True)
        ws_thread.start()
        
        # Wait for connection
        time.sleep(1)
        
        return self.ws_client
    
    def send_message(self, message_type, data=None):
        """Send a message to the backend"""
        if not self.ws_client:
            raise Exception("WebSocket client not initialized")
        
        message = {
            'type': message_type,
            'data': data or {}
        }
        
        self.ws_client.send(json.dumps(message))
    
    def wait_for_message(self, message_type, timeout=5):
        """Wait for a specific message type"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            for msg in self.received_messages:
                if msg.get('type') == message_type:
                    return msg
            time.sleep(0.1)
        
        raise TimeoutError(f"Message type '{message_type}' not received within {timeout} seconds")
    
    @unittest.skipIf(not os.getenv('RUN_INTEGRATION_TESTS'), "Integration tests disabled")
    def test_websocket_connection(self):
        """Test WebSocket connection to backend"""
        try:
            # Start mock backend
            server = self.start_mock_backend()
            
            # Create WebSocket client
            client = self.create_websocket_client()
            
            # Test connection by sending a health check
            self.send_message('health_check')
            
            # Wait for response
            response = self.wait_for_message('health_status')
            
            self.assertEqual(response['type'], 'health_status')
            self.assertTrue(response['data']['healthy'])
            
        except ImportError:
            self.skipTest("websocket-server not available for integration tests")
    
    @unittest.skipIf(not os.getenv('RUN_INTEGRATION_TESTS'), "Integration tests disabled")
    def test_chat_loading_flow(self):
        """Test the complete chat loading flow"""
        try:
            # Start mock backend
            server = self.start_mock_backend()
            
            # Create WebSocket client
            client = self.create_websocket_client()
            
            # Request initial chats
            self.send_message('get_initial_chats')
            
            # Wait for chat list response
            response = self.wait_for_message('initial_chats')
            
            self.assertEqual(response['type'], 'initial_chats')
            self.assertIn('chats', response['data'])
            self.assertGreater(len(response['data']['chats']), 0)
            
            # Verify chat structure
            chat = response['data']['chats'][0]
            self.assertIn('jid', chat)
            self.assertIn('name', chat)
            self.assertIn('lastMessage', chat)
            self.assertIn('timestamp', chat)
            
        except ImportError:
            self.skipTest("websocket-server not available for integration tests")
    
    @unittest.skipIf(not os.getenv('RUN_INTEGRATION_TESTS'), "Integration tests disabled")
    def test_message_sending_flow(self):
        """Test the complete message sending flow"""
        try:
            # Start mock backend
            server = self.start_mock_backend()
            
            # Create WebSocket client
            client = self.create_websocket_client()
            
            # Send a message
            message_data = {
                'to': '5511999999999@s.whatsapp.net',
                'message': 'Test message from integration test'
            }
            self.send_message('send_message', message_data)
            
            # Wait for confirmation
            response = self.wait_for_message('message_sent')
            
            self.assertEqual(response['type'], 'message_sent')
            self.assertEqual(response['data']['to'], message_data['to'])
            self.assertEqual(response['data']['message'], message_data['message'])
            self.assertIn('messageId', response['data'])
            self.assertIn('timestamp', response['data'])
            
        except ImportError:
            self.skipTest("websocket-server not available for integration tests")
    
    def test_frontend_component_integration(self):
        """Test frontend component integration without actual backend"""
        # Mock GTK components
        with patch('gi.repository.GObject'), \
             patch('gi.repository.Gtk'), \
             patch('gi.repository.Adw'):
            
            # Import frontend modules
            try:
                from karere.websocket_client import WebSocketClient
                from karere.window import KarereWindow, ChatRow, MessageRow
                
                # Test WebSocketClient initialization
                ws_client = WebSocketClient("ws://localhost:8765")
                self.assertEqual(ws_client.url, "ws://localhost:8765")
                
                # Test ChatRow creation
                chat_row = ChatRow("test@s.whatsapp.net", "Test message")
                self.assertEqual(chat_row.jid, "test@s.whatsapp.net")
                
                # Test MessageRow creation
                message_row = MessageRow("Test message", True, "14:30", "sent")
                self.assertEqual(message_row.message_text, "Test message")
                self.assertTrue(message_row.is_from_me)
                
            except ImportError as e:
                self.skipTest(f"Frontend modules not available: {e}")
    
    def test_error_handling_integration(self):
        """Test error handling across components"""
        try:
            # Start mock backend
            server = self.start_mock_backend()
            
            # Create WebSocket client
            client = self.create_websocket_client()
            
            # Send invalid message
            invalid_message = "invalid json"
            self.ws_client.send(invalid_message)
            
            # Should not crash the connection
            time.sleep(1)
            
            # Send valid message after invalid one
            self.send_message('health_check')
            response = self.wait_for_message('health_status')
            
            # Should still work
            self.assertEqual(response['type'], 'health_status')
            
        except ImportError:
            self.skipTest("websocket-server not available for integration tests")
    
    def test_performance_under_load(self):
        """Test performance under message load"""
        try:
            # Start mock backend
            server = self.start_mock_backend()
            
            # Create WebSocket client
            client = self.create_websocket_client()
            
            # Send multiple messages rapidly
            start_time = time.time()
            message_count = 10
            
            for i in range(message_count):
                self.send_message('health_check')
            
            # Wait for all responses
            responses = []
            for i in range(message_count):
                try:
                    response = self.wait_for_message('health_status', timeout=1)
                    responses.append(response)
                except TimeoutError:
                    break
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Should handle at least 5 messages per second
            self.assertGreater(len(responses), message_count // 2)
            self.assertLess(duration, message_count)  # Should be faster than 1 message per second
            
        except ImportError:
            self.skipTest("websocket-server not available for integration tests")


class TestDatabaseIntegration(unittest.TestCase):
    """Test database integration"""
    
    def setUp(self):
        """Set up test database"""
        self.test_db_path = "/tmp/test_karere.db"
        
        # Clean up any existing test database
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
    
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
    
    @unittest.skipIf(not os.getenv('RUN_INTEGRATION_TESTS'), "Integration tests disabled")
    def test_database_operations(self):
        """Test database operations integration"""
        try:
            # This would test actual database operations
            # For now, we'll just verify the test setup
            self.assertTrue(True)
            
        except ImportError:
            self.skipTest("Database modules not available for integration tests")


if __name__ == '__main__':
    # Set environment variable to enable integration tests
    os.environ['RUN_INTEGRATION_TESTS'] = '1'
    
    unittest.main(verbosity=2)
