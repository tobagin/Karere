# Karere 📱

A modern, native WhatsApp client for Linux built with Python GTK4 and Node.js.

![Karere Logo](frontend/data/icons/io.github.tobagin.karere.png)

## ✨ Features

- **Native Linux Integration**: Built with GTK4 and Adwaita for seamless GNOME integration
- **Real-time Messaging**: Send and receive WhatsApp messages in real-time
- **QR Code Authentication**: Secure login using WhatsApp's QR code system
- **Modern UI**: Clean, responsive interface following GNOME design guidelines
- **Cross-platform Backend**: Node.js backend using the reliable Baileys library
- **Secure**: End-to-end encryption maintained through WhatsApp's protocol

## 🏗️ Architecture

Karere uses a hybrid architecture:

- **Frontend**: Python application using GTK4/Adwaita for the user interface
- **Backend**: Node.js service using Baileys for WhatsApp Web API integration
- **Communication**: WebSocket connection between frontend and backend
- **Build System**: Meson for native Linux packaging and installation

## 📋 Requirements

### System Requirements
- Linux distribution with GTK4 support
- Python 3.8+ with PyGObject
- Node.js 18+ and npm
- Meson build system

### Dependencies

#### Frontend (Python)
- `python3-gi` - Python GObject bindings
- `gir1.2-gtk-4.0` - GTK4 bindings
- `gir1.2-adw-1` - Adwaita bindings
- `python3-websocket` - WebSocket client

#### Backend (Node.js)
- `@whiskeysockets/baileys` - WhatsApp Web API
- `ws` - WebSocket server
- `qrcode` - QR code generation

## 🚀 Installation

### From Source

1. **Clone the repository**:
   ```bash
   git clone https://github.com/tobagin/Karere.git
   cd Karere
   ```

2. **Install system dependencies** (Ubuntu/Debian):
   ```bash
   sudo apt update
   sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 \
                    nodejs npm meson ninja-build python3-websocket
   ```

3. **Install backend dependencies**:
   ```bash
   cd backend
   npm install
   cd ..
   ```

4. **Build the application**:
   ```bash
   meson setup builddir
   meson compile -C builddir
   ```

5. **Install (optional)**:
   ```bash
   sudo meson install -C builddir
   ```

### Using Flatpak (Coming Soon)

```bash
flatpak install flathub io.github.tobagin.Karere
```

## 🎮 Usage

### Running from Source

1. **Start the backend service**:
   ```bash
   cd backend
   npm start
   ```

2. **In a new terminal, start the frontend**:
   ```bash
   cd builddir
   ./karere
   ```

   Or if installed system-wide:
   ```bash
   karere
   ```

### First Time Setup

1. Launch Karere
2. The application will display a QR code
3. Open WhatsApp on your phone
4. Go to Settings → Linked Devices → Link a Device
5. Scan the QR code displayed in Karere
6. Your chats will load automatically

## 🔧 Development

### Project Structure

```
Karere/
├── backend/                 # Node.js backend service
│   ├── backend.js          # Main backend server
│   ├── package.json        # Node.js dependencies
│   └── baileys_auth_info/  # WhatsApp session data
├── frontend/               # Python GTK4 frontend
│   ├── karere/            # Python package
│   │   ├── main.py        # Application entry point
│   │   ├── window.py      # Main window implementation
│   │   └── websocket_client.py # Backend communication
│   ├── data/              # UI files and resources
│   │   ├── karere.ui      # GTK4 interface definition
│   │   └── *.xml          # Desktop integration files
│   └── meson.build        # Frontend build configuration
├── builddir/              # Build output directory
└── meson.build           # Main build configuration
```

### Development Setup

1. **Set up development environment**:
   ```bash
   meson setup builddir --buildtype=debug
   meson devenv -C builddir
   ```

2. **Run in development mode**:
   ```bash
   # Terminal 1: Backend
   cd backend && npm start

   # Terminal 2: Frontend
   cd builddir && ./karere
   ```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Commit with conventional commit messages
5. Push to your fork and create a pull request

## 🐛 Troubleshooting

### Common Issues

**Backend won't start**:
- Ensure Node.js 18+ is installed
- Run `npm install` in the backend directory
- Check if port 8765 is available

**Frontend crashes on startup**:
- Verify GTK4 and Adwaita are installed
- Check Python dependencies: `python3 -c "import gi; gi.require_version('Gtk', '4.0')"`
- Ensure resources are built: `meson compile -C builddir`

**QR code not displaying**:
- Check backend logs for connection issues
- Verify WebSocket connection on port 8765
- Restart both frontend and backend

**Authentication fails**:
- Delete `backend/baileys_auth_info/` directory
- Restart the backend to generate a new QR code
- Ensure your phone has internet connectivity

### Logs and Debugging

- Backend logs: Check terminal output where `npm start` was run
- Frontend logs: Check terminal output where `karere` was run
- Enable debug mode: Set `G_MESSAGES_DEBUG=all` environment variable

## 📄 License

This project is licensed under the GPL-3.0-or-later License. See the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Baileys](https://github.com/WhiskeySockets/Baileys) - WhatsApp Web API implementation
- [GTK](https://gtk.org/) - Cross-platform GUI toolkit
- [Adwaita](https://gnome.pages.gitlab.gnome.org/libadwaita/) - GNOME's design system
- [Meson](https://mesonbuild.com/) - Build system

## 🔗 Links

- [Report Issues](https://github.com/tobagin/Karere/issues)
- [Feature Requests](https://github.com/tobagin/Karere/discussions)
- [Documentation](https://github.com/tobagin/Karere/wiki)

---

**Note**: Karere is an unofficial WhatsApp client. It is not affiliated with, endorsed by, or sponsored by WhatsApp Inc.
