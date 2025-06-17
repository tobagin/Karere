# Karere Developer Guide

This guide provides comprehensive information for developers who want to contribute to Karere or understand its architecture.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Development Setup](#development-setup)
3. [Project Structure](#project-structure)
4. [Backend Development](#backend-development)
5. [Frontend Development](#frontend-development)
6. [Testing](#testing)
7. [Building and Packaging](#building-and-packaging)
8. [Contributing](#contributing)

## Architecture Overview

Karere follows a client-server architecture with clear separation between frontend and backend:

```
┌─────────────────┐    WebSocket    ┌─────────────────┐    WhatsApp Web    ┌─────────────────┐
│                 │ ◄──────────────► │                 │ ◄─────────────────► │                 │
│  GTK4 Frontend  │                 │  Node.js Backend│                     │  WhatsApp Servers│
│   (Python)      │                 │   (JavaScript)  │                     │                 │
└─────────────────┘                 └─────────────────┘                     └─────────────────┘
        │                                     │
        │                                     │
        ▼                                     ▼
┌─────────────────┐                 ┌─────────────────┐
│   UI Components │                 │   SQLite DB     │
│   • Chat List   │                 │   • Messages    │
│   • Messages    │                 │   • Chats       │
│   • Search      │                 │   • Contacts    │
└─────────────────┘                 └─────────────────┘
```

### Core Components

**Frontend (Python + GTK4):**
- **UI Layer**: GTK4 widgets with Adwaita design
- **WebSocket Client**: Real-time communication with backend
- **State Management**: Local UI state and message caching
- **Event Handling**: User interactions and system events

**Backend (Node.js):**
- **WhatsApp Integration**: Baileys library for WhatsApp Web API
- **WebSocket Server**: Real-time communication with frontend
- **Database Layer**: SQLite for message persistence
- **Service Management**: Health monitoring and graceful shutdown

**Communication:**
- **Protocol**: WebSocket with JSON messages
- **Authentication**: QR code flow through WhatsApp Web
- **Data Flow**: Bidirectional real-time messaging

## Development Setup

### Prerequisites

**System Requirements:**
- Linux with GTK4 support (Ubuntu 22.04+, Fedora 36+)
- Python 3.8+ with PyGObject
- Node.js 18+ with npm
- Git for version control

**Development Tools:**
- Code editor (VS Code, PyCharm, etc.)
- Terminal with bash support
- Browser for testing WebSocket connections

### Quick Setup

```bash
# Clone repository
git clone https://github.com/tobagin/Karere.git
cd Karere

# Install system dependencies (Ubuntu/Debian)
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 \
                 nodejs npm meson ninja-build python3-websocket

# Install backend dependencies
cd backend && npm install && cd ..

# Setup build environment
meson setup builddir --buildtype=debug

# Build project
meson compile -C builddir

# Run tests
./scripts/run-tests.sh --all
```

### Development Workflow

```bash
# Terminal 1: Backend development server
cd backend
npm run start

# Terminal 2: Frontend development
cd builddir
./karere

# Terminal 3: Testing and development
./scripts/run-tests.sh --watch
```

## Project Structure

```
Karere/
├── backend/                    # Node.js backend service
│   ├── backend.js             # Main server entry point
│   ├── logger.js              # Logging and error handling
│   ├── database.js            # SQLite database operations
│   ├── service-manager.js     # Service lifecycle management
│   ├── package.json           # Dependencies and scripts
│   └── tests/                 # Backend test suite
│       ├── unit/              # Unit tests
│       ├── integration/       # Integration tests
│       └── setup.js           # Test configuration
├── frontend/                  # Python GTK4 frontend
│   ├── karere/               # Python package
│   │   ├── main.py           # Application entry point
│   │   ├── window.py         # Main window and UI logic
│   │   └── websocket_client.py # Backend communication
│   ├── data/                 # UI resources and metadata
│   │   ├── karere.ui         # GTK4 interface definition
│   │   ├── style.css         # Custom styling
│   │   └── *.xml             # Desktop integration files
│   └── meson.build           # Frontend build configuration
├── docs/                     # Documentation
│   ├── USER_GUIDE.md         # User documentation
│   ├── DEVELOPER_GUIDE.md    # This file
│   └── API.md                # API documentation
├── scripts/                  # Build and utility scripts
│   ├── run-tests.sh          # Test runner
│   ├── build-packages.sh     # Package building
│   └── deploy.sh             # Deployment automation
├── tests/                    # Cross-component tests
│   ├── frontend/             # Frontend unit tests
│   └── integration/          # Full integration tests
├── .github/                  # GitHub Actions CI/CD
│   └── workflows/            # Automated testing and deployment
├── meson.build               # Root build configuration
├── README.md                 # Project overview
└── CONTRIBUTING.md           # Contribution guidelines
```

## Backend Development

### Core Modules

**backend.js** - Main server entry point:
```javascript
// WebSocket server setup
const wss = new WebSocketServer({ port: 8765 });

// Baileys WhatsApp client
const sock = makeWASocket({
    auth: state,
    printQRInTerminal: false
});

// Message handling
sock.ev.on('messages.upsert', handleIncomingMessages);
```

**logger.js** - Comprehensive logging system:
```javascript
// Structured logging with Winston
export const log = {
    info: (message, meta) => logger.info(message, meta),
    error: (message, error, meta) => logger.error(message, { error, ...meta }),
    websocket: (message, meta) => logger.info(message, { component: 'websocket', ...meta })
};

// Error handling with context
export const errorHandler = {
    websocket: (error, context) => ({ type: 'websocket_error', message: 'WebSocket error', details: error.message }),
    baileys: (error, context) => ({ type: 'baileys_error', message: 'WhatsApp error', details: error.message })
};
```

**database.js** - SQLite operations:
```javascript
// Database schema and operations
class Database {
    async saveMessage(id, chatJid, fromMe, content, timestamp, messageType, status) {
        const sql = `INSERT OR REPLACE INTO messages 
                     (id, chat_jid, from_me, message_type, content, timestamp, status) 
                     VALUES (?, ?, ?, ?, ?, ?, ?)`;
        return this.run(sql, [id, chatJid, fromMe, messageType, content, timestamp, status]);
    }
}
```

### WebSocket Protocol

**Message Format:**
```javascript
// Client to Server
{
    "type": "send_message",
    "data": {
        "to": "5511999999999@s.whatsapp.net",
        "message": "Hello, World!"
    }
}

// Server to Client
{
    "type": "message_sent",
    "data": {
        "messageId": "msg_123456789",
        "to": "5511999999999@s.whatsapp.net",
        "timestamp": 1640995200000
    }
}
```

**Message Types:**
- `get_initial_chats` - Request chat list
- `send_message` - Send text message
- `get_message_history` - Request chat history
- `typing_start/stop` - Typing indicators
- `health_check` - Service health status

### Adding New Features

**1. Backend Message Handler:**
```javascript
// Add to handleFrontendCommand()
case 'new_feature':
    await handleNewFeature(data);
    break;

async function handleNewFeature(data) {
    try {
        // Implement feature logic
        const result = await processFeature(data);
        
        // Send response to frontend
        sendToFrontend('feature_response', result);
        
        // Log operation
        log.info('New feature executed', { data, result });
    } catch (error) {
        const errorResponse = errorHandler.generic(error, 'new_feature');
        sendToFrontend('error', errorResponse);
    }
}
```

**2. Database Schema Updates:**
```javascript
// Add to database.js initialization
const createNewTable = `
    CREATE TABLE IF NOT EXISTS new_feature (
        id TEXT PRIMARY KEY,
        data TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
`;
```

## Frontend Development

### GTK4 Architecture

**Main Components:**
- **KarereWindow**: Main application window
- **ChatRow**: Individual chat list items
- **MessageRow**: Individual message display
- **WebSocketClient**: Backend communication

**UI Definition (karere.ui):**
```xml
<object class="AdwApplicationWindow" id="main_window">
    <child>
        <object class="AdwLeaflet" id="main_leaflet">
            <child>
                <object class="GtkBox" id="sidebar">
                    <child>
                        <object class="GtkListBox" id="chat_list_box"/>
                    </child>
                </object>
            </child>
        </object>
    </child>
</object>
```

### WebSocket Integration

**Signal-based Communication:**
```python
class WebSocketClient(GObject.Object):
    __gsignals__ = {
        'new-message': (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
        'message-sent': (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
        'connection-opened': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }
    
    def _on_message(self, ws, message):
        data = json.loads(message)
        if data['type'] == 'newMessage':
            GLib.idle_add(self.emit, 'new-message', data['data']['from'], data['data']['body'])
```

**Event Handling:**
```python
# Connect WebSocket signals to UI updates
self.ws_client.connect('new-message', self.on_new_message)
self.ws_client.connect('message-sent', self.on_message_sent)

def on_new_message(self, client, sender, message):
    # Update UI with new message
    self.add_message_to_chat(sender, message, False)
    self.scroll_to_bottom()
```

### Adding UI Features

**1. New UI Component:**
```python
@Gtk.Template(resource_path='/io/github/tobagin/Karere/new_component.ui')
class NewComponent(Gtk.Box):
    __gtype_name__ = 'NewComponent'
    
    def __init__(self):
        super().__init__()
        self.setup_signals()
    
    def setup_signals(self):
        # Connect UI events
        pass
```

**2. WebSocket Command:**
```python
def send_new_command(self, data):
    if self.ws_client:
        self.ws_client.send_command('new_command', data)
```

## Testing

### Test Structure

**Backend Tests (Jest):**
```javascript
// Unit test example
describe('Database Module', () => {
    test('should save message successfully', async () => {
        const messageData = { /* test data */ };
        await database.saveMessage(...messageData);
        expect(mockDb.run).toHaveBeenCalledWith(/* expected SQL */);
    });
});
```

**Frontend Tests (unittest):**
```python
# Unit test example
class TestWebSocketClient(unittest.TestCase):
    def test_send_command(self):
        client = WebSocketClient()
        client.ws_app = Mock()
        client.send_command('test', {'data': 'value'})
        client.ws_app.send.assert_called_once()
```

### Running Tests

```bash
# All tests
./scripts/run-tests.sh --all

# Backend only
cd backend && npm test

# Frontend only
cd tests/frontend && python -m pytest

# Integration tests
./scripts/run-tests.sh --integration

# With coverage
./scripts/run-tests.sh --coverage
```

## Building and Packaging

### Local Development Build

```bash
# Debug build
meson setup builddir --buildtype=debug
meson compile -C builddir

# Release build
meson setup builddir --buildtype=release
meson compile -C builddir
```

### Package Creation

**Flatpak:**
```bash
# Build Flatpak
flatpak-builder build-dir frontend/data/io.github.tobagin.Karere.Devel.json

# Install locally
flatpak-builder --user --install build-dir frontend/data/io.github.tobagin.Karere.Devel.json
```

**AppImage:**
```bash
# Create AppImage
./scripts/build-appimage.sh
```

**Debian Package:**
```bash
# Build .deb package
./scripts/build-deb.sh
```

## Contributing

### Code Style

**Python (Frontend):**
- Follow PEP 8
- Use type hints
- Document with docstrings
- 4-space indentation

**JavaScript (Backend):**
- ES6+ modules
- 2-space indentation
- JSDoc comments
- Consistent naming

### Pull Request Process

1. **Fork and Branch**: Create feature branch from main
2. **Develop**: Implement changes with tests
3. **Test**: Run full test suite
4. **Document**: Update relevant documentation
5. **Submit**: Create PR with clear description

### Development Guidelines

- **Atomic Commits**: One logical change per commit
- **Test Coverage**: Maintain >90% coverage for new code
- **Documentation**: Update docs for user-facing changes
- **Performance**: Consider memory and CPU impact
- **Accessibility**: Follow GNOME accessibility guidelines

---

For more information, see [CONTRIBUTING.md](../CONTRIBUTING.md) and [API.md](API.md).
