# Karere

<div align="center">

![Karere Logo](frontend/data/icons/io.github.tobagin.karere.png)

**A modern, native WhatsApp client for Linux**

[![GitHub release](https://img.shields.io/github/release/tobagin/Karere.svg)](https://github.com/tobagin/Karere/releases)
[![CI Status](https://github.com/tobagin/Karere/workflows/CI/badge.svg)](https://github.com/tobagin/Karere/actions)
[![Coverage](https://codecov.io/gh/tobagin/Karere/branch/main/graph/badge.svg)](https://codecov.io/gh/tobagin/Karere)
[![License](https://img.shields.io/github/license/tobagin/Karere.svg)](LICENSE)

Built with Python GTK4 and Node.js for a seamless GNOME experience

[📥 Download](#-installation) • [📖 User Guide](docs/USER_GUIDE.md) • [🔧 Developer Guide](docs/DEVELOPER_GUIDE.md) • [🐛 Report Bug](https://github.com/tobagin/Karere/issues) • [💡 Request Feature](https://github.com/tobagin/Karere/discussions)

</div>

## ✨ Features

### 🎯 Core Messaging
- **Real-time Messaging**: Send and receive WhatsApp messages instantly with full compatibility
- **Message Status**: Visual delivery and read receipts (✓ sent, ✓✓ delivered, blue ✓✓ read)
- **Typing Indicators**: See when contacts are typing and show your typing status
- **Message History**: Access complete chat history with fast loading and search
- **Contact Management**: Automatic contact name resolution and phone number formatting

### 🎨 Modern Interface
- **Native Linux Integration**: Built with GTK4 and Adwaita for seamless GNOME integration
- **Responsive Design**: Adaptive interface that works on different screen sizes
- **Dark Mode Support**: Automatic theme switching based on system preferences
- **Search Functionality**: Find messages and contacts quickly with real-time filtering
- **Emoji Support**: Full emoji picker with categories and search

### 🔒 Security & Privacy
- **QR Code Authentication**: Secure login using WhatsApp's official QR code system
- **End-to-End Encryption**: All messages use WhatsApp's encryption (handled by WhatsApp servers)
- **Local Storage**: Messages stored locally with SQLite database for privacy
- **No Data Collection**: Karere doesn't collect, store, or transmit user data to third parties

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

### Method 1: Flatpak (Recommended)

```bash
# Add Flathub repository (if not already added)
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

# Install Karere
flatpak install flathub io.github.tobagin.Karere

# Run Karere
flatpak run io.github.tobagin.Karere
```

### Method 2: AppImage

Download the latest AppImage from [GitHub Releases](https://github.com/tobagin/Karere/releases):

```bash
# Download AppImage
wget https://github.com/tobagin/Karere/releases/latest/download/Karere-x86_64.AppImage

# Make executable and run
chmod +x Karere-x86_64.AppImage
./Karere-x86_64.AppImage
```

### Method 3: Distribution Packages

**Ubuntu/Debian:**
```bash
# Add Karere repository
curl -fsSL https://packages.karere.app/gpg | sudo gpg --dearmor -o /usr/share/keyrings/karere.gpg
echo "deb [signed-by=/usr/share/keyrings/karere.gpg] https://packages.karere.app/deb stable main" | sudo tee /etc/apt/sources.list.d/karere.list

# Install
sudo apt update && sudo apt install karere
```

**Fedora:**
```bash
# Add repository and install
sudo dnf config-manager --add-repo https://packages.karere.app/rpm/karere.repo
sudo dnf install karere
```

**Arch Linux (AUR):**
```bash
# Using yay or paru
yay -S karere
# or
paru -S karere
```

### Method 4: From Source

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

## 📚 Documentation

- **[User Guide](docs/USER_GUIDE.md)**: Complete user documentation with screenshots and tutorials
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)**: Architecture overview and development setup
- **[API Documentation](docs/API.md)**: WebSocket protocol and internal APIs
- **[Deployment Guide](docs/DEPLOYMENT.md)**: Packaging and distribution instructions
- **[Contributing Guidelines](CONTRIBUTING.md)**: How to contribute to the project

## 🚀 Roadmap

### Current Features (v1.0)
- ✅ Real-time text messaging
- ✅ QR code authentication
- ✅ Message history and search
- ✅ Typing indicators
- ✅ Contact management
- ✅ Dark mode support

### Planned Features (v1.1+)
- 🚧 Media messages (images, videos, documents)
- 🚧 Voice messages (record and playback)
- 🚧 Group chat management
- 🚧 Status/Story viewing
- 🚧 Message backup and restore
- 🚧 Multi-account support

## 🤝 Contributing

We welcome contributions! Here's how you can help:

- **🐛 Report Bugs**: [Create an issue](https://github.com/tobagin/Karere/issues) with detailed information
- **💡 Suggest Features**: [Start a discussion](https://github.com/tobagin/Karere/discussions) about new ideas
- **🔧 Submit Code**: Fork the repo, make changes, and create a pull request
- **📖 Improve Docs**: Help improve documentation and guides
- **🌍 Translate**: Help translate Karere to other languages

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 🔗 Links

- **[GitHub Repository](https://github.com/tobagin/Karere)**: Source code and development
- **[Releases](https://github.com/tobagin/Karere/releases)**: Download latest versions
- **[Issues](https://github.com/tobagin/Karere/issues)**: Bug reports and feature requests
- **[Discussions](https://github.com/tobagin/Karere/discussions)**: Community support and questions
- **[Flathub](https://flathub.org/apps/details/io.github.tobagin.Karere)**: Flatpak distribution

## ⭐ Support the Project

If you find Karere useful, please consider:
- ⭐ **Starring the repository** on GitHub
- 🐛 **Reporting bugs** and suggesting improvements
- 🔧 **Contributing code** or documentation
- 💬 **Spreading the word** about Karere

---

**Note**: Karere is an unofficial WhatsApp client. It is not affiliated with, endorsed by, or sponsored by WhatsApp Inc.
