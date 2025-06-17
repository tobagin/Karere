# Karere API Documentation

This document describes the internal APIs and communication protocols used in Karere.

## Table of Contents

1. [WebSocket Protocol](#websocket-protocol)
2. [Backend API](#backend-api)
3. [Database Schema](#database-schema)
4. [Frontend Components](#frontend-components)
5. [Error Handling](#error-handling)
6. [Events and Signals](#events-and-signals)

## WebSocket Protocol

Karere uses WebSocket for real-time communication between frontend and backend. All messages are JSON-formatted.

### Message Format

```javascript
{
    "type": "message_type",
    "data": {
        // Message-specific data
    }
}
```

### Client to Server Messages

#### `get_initial_chats`
Request the initial list of chats.

**Request:**
```javascript
{
    "type": "get_initial_chats",
    "data": {}
}
```

**Response:**
```javascript
{
    "type": "initial_chats",
    "data": {
        "chats": [
            {
                "jid": "5511999999999@s.whatsapp.net",
                "name": "Contact Name",
                "lastMessage": "Last message content",
                "timestamp": 1640995200000,
                "unreadCount": 3
            }
        ]
    }
}
```

#### `send_message`
Send a text message to a contact.

**Request:**
```javascript
{
    "type": "send_message",
    "data": {
        "to": "5511999999999@s.whatsapp.net",
        "message": "Hello, World!"
    }
}
```

**Response:**
```javascript
{
    "type": "message_sent",
    "data": {
        "to": "5511999999999@s.whatsapp.net",
        "message": "Hello, World!",
        "messageId": "msg_1640995200_123",
        "timestamp": 1640995200000
    }
}
```

#### `get_message_history`
Request message history for a specific chat.

**Request:**
```javascript
{
    "type": "get_message_history",
    "data": {
        "chatJid": "5511999999999@s.whatsapp.net",
        "limit": 50,
        "offset": 0
    }
}
```

**Response:**
```javascript
{
    "type": "message_history",
    "data": {
        "chatJid": "5511999999999@s.whatsapp.net",
        "messages": [
            {
                "id": "msg_123",
                "fromMe": true,
                "content": "Message content",
                "timestamp": 1640995200000,
                "status": "read"
            }
        ]
    }
}
```

#### `typing_start` / `typing_stop`
Send typing indicators.

**Request:**
```javascript
{
    "type": "typing_start",
    "data": {
        "chatJid": "5511999999999@s.whatsapp.net"
    }
}
```

#### `health_check`
Check backend service health.

**Request:**
```javascript
{
    "type": "health_check",
    "data": {}
}
```

**Response:**
```javascript
{
    "type": "health_status",
    "data": {
        "healthy": true,
        "backend": {
            "uptime": 3600,
            "services": ["websocket", "database", "baileys"],
            "performance": {
                "memory": {
                    "heapUsed": 50000000,
                    "heapTotal": 100000000
                },
                "cpu": {
                    "user": 1000,
                    "system": 500
                }
            }
        },
        "baileys": {
            "status": "open",
            "connected": true
        }
    }
}
```

### Server to Client Messages

#### `qr`
QR code for WhatsApp authentication.

```javascript
{
    "type": "qr",
    "data": {
        "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
    }
}
```

#### `status`
Connection status updates.

```javascript
{
    "type": "status",
    "data": {
        "message": "Connected to WhatsApp",
        "level": "info"
    }
}
```

#### `baileys_ready`
WhatsApp connection established.

```javascript
{
    "type": "baileys_ready",
    "data": {}
}
```

#### `newMessage`
Incoming message from WhatsApp.

```javascript
{
    "type": "newMessage",
    "data": {
        "from": "5511999999999@s.whatsapp.net",
        "body": "Incoming message content",
        "timestamp": 1640995200000,
        "messageId": "msg_incoming_123"
    }
}
```

#### `error`
Error notifications.

```javascript
{
    "type": "error",
    "data": {
        "type": "websocket_error",
        "message": "Connection failed",
        "details": "Detailed error information"
    }
}
```

## Backend API

### Logger Module

#### `log` Object
Structured logging with different levels and components.

```javascript
import { log } from './logger.js';

// General logging
log.info('Application started', { version: '1.0.0' });
log.warn('High memory usage', { usage: '85%' });
log.error('Database connection failed', error, { context: 'startup' });

// Component-specific logging
log.websocket('Client connected', { clientId: 'ws_123' });
log.baileys('QR code generated', { attempt: 1 });
log.auth('Authentication successful', { user: 'user_123' });
log.message('Message sent', { to: 'contact_123', messageId: 'msg_456' });
log.performance('Database query', 150, { query: 'SELECT * FROM messages' });
```

#### `errorHandler` Object
Standardized error handling with context.

```javascript
import { errorHandler } from './logger.js';

// Error handling
const wsError = errorHandler.websocket(error, 'connection');
const baileysError = errorHandler.baileys(error, 'authentication');
const dbError = errorHandler.database(error, 'message_save');
const genericError = errorHandler.generic(error, 'unknown_operation');
```

### Database Module

#### Core Methods

```javascript
import database from './database.js';

// Initialize database
await database.initialize();

// Chat operations
await database.saveChat(jid, name, lastMessageId, timestamp);
const chats = await database.getChats(limit);

// Message operations
await database.saveMessage(id, chatJid, fromMe, content, timestamp, messageType, status);
const messages = await database.getMessages(chatJid, limit, offset);
await database.updateMessageStatus(messageId, status);

// Contact operations
await database.saveContact(jid, name, phoneNumber);
const contact = await database.getContact(jid);

// Settings operations
await database.setSetting(key, value);
const value = await database.getSetting(key, defaultValue);

// Maintenance
await database.cleanup();
await database.close();
```

### Service Manager Module

#### Service Registration

```javascript
import serviceManager from './service-manager.js';

// Register services
serviceManager.registerService('websocket', wsServer);
serviceManager.registerService('database', database);

// Health checks
serviceManager.addHealthCheck('memory', () => {
    const usage = process.memoryUsage();
    return {
        healthy: usage.heapUsed < 500 * 1024 * 1024,
        details: { heapUsed: usage.heapUsed }
    };
});

// Cron jobs
serviceManager.addCronJob('cleanup', '0 2 * * *', async () => {
    await database.cleanup();
});

// Status and metrics
const status = serviceManager.getStatus();
const metrics = serviceManager.getPerformanceMetrics();
const healthResult = await serviceManager.runHealthChecks();
```

## Database Schema

### Tables

#### `chats`
```sql
CREATE TABLE chats (
    jid TEXT PRIMARY KEY,
    name TEXT,
    last_message_id TEXT,
    last_message_timestamp INTEGER,
    unread_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### `messages`
```sql
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    chat_jid TEXT NOT NULL,
    from_me BOOLEAN NOT NULL,
    message_type TEXT NOT NULL DEFAULT 'text',
    content TEXT,
    timestamp INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chat_jid) REFERENCES chats(jid)
);
```

#### `contacts`
```sql
CREATE TABLE contacts (
    jid TEXT PRIMARY KEY,
    name TEXT,
    phone_number TEXT,
    avatar_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### `media`
```sql
CREATE TABLE media (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL,
    media_type TEXT NOT NULL,
    file_path TEXT,
    file_size INTEGER,
    mime_type TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(id)
);
```

#### `settings`
```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Frontend Components

### WebSocketClient

#### Signals
```python
__gsignals__ = {
    'connection-opened': (GObject.SignalFlags.RUN_FIRST, None, ()),
    'connection-closed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    'qr-received': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    'status-update': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    'new-message': (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
    'initial-chats': (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT,)),
    'baileys-ready': (GObject.SignalFlags.RUN_FIRST, None, ()),
    'message-sent': (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
    'message-error': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    'message-history': (GObject.SignalFlags.RUN_FIRST, None, (str, GObject.TYPE_PYOBJECT)),
}
```

#### Methods
```python
# Connection management
client.start()  # Start WebSocket connection
client.send_command(command_type, data)  # Send command to backend

# Usage example
client = WebSocketClient("ws://localhost:8765")
client.connect('new-message', self.on_new_message)
client.start()
client.send_command('send_message', {'to': jid, 'message': text})
```

### KarereWindow

#### Key Methods
```python
# Chat management
window.add_or_update_chat(jid, last_message, timestamp, unread_count)
window.on_chat_selected(listbox, row)

# Message handling
window.add_message_to_chat(jid, message, from_me, timestamp, status)
window.on_send_message(button)

# UI updates
window.show_qr_view()
window.show_chat_view()
window.scroll_to_bottom()
```

## Error Handling

### Error Types

#### Backend Errors
- `websocket_error`: WebSocket connection issues
- `baileys_error`: WhatsApp/Baileys related errors
- `messaging_error`: Message processing failures
- `database_error`: Database operation failures
- `generic_error`: Unspecified errors

#### Frontend Errors
- Connection errors are handled by automatic reconnection
- UI errors are logged and displayed to user
- Invalid data is sanitized and logged

### Error Response Format
```javascript
{
    "type": "error",
    "data": {
        "type": "error_category",
        "message": "User-friendly error message",
        "details": "Technical error details",
        "context": "Operation context",
        "timestamp": 1640995200000
    }
}
```

## Events and Signals

### Backend Events

#### WebSocket Events
- `connection`: New client connected
- `message`: Message received from client
- `close`: Client disconnected
- `error`: WebSocket error occurred

#### Baileys Events
- `connection.update`: Connection status changed
- `messages.upsert`: New messages received
- `creds.update`: Authentication credentials updated

### Frontend Signals

#### WebSocket Signals
- `connection-opened`: Connected to backend
- `connection-closed`: Disconnected from backend
- `qr-received`: QR code received for authentication
- `new-message`: New message received
- `message-sent`: Message sent successfully

#### UI Signals
- `row-selected`: Chat selected in list
- `clicked`: Button clicked
- `activate`: Text entry activated (Enter pressed)

---

For implementation examples, see the [Developer Guide](DEVELOPER_GUIDE.md).
