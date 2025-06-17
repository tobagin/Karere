# Karere User Guide

Welcome to Karere, a modern native WhatsApp client for Linux! This comprehensive guide will help you get started and make the most of Karere's features.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Installation](#installation)
3. [First Time Setup](#first-time-setup)
4. [Basic Usage](#basic-usage)
5. [Features](#features)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)
8. [Support](#support)

## Getting Started

### What is Karere?

Karere is a native Linux WhatsApp client built with modern technologies:
- **GTK4/Adwaita** for a beautiful, native Linux interface
- **Real-time messaging** with full WhatsApp compatibility
- **Secure authentication** using WhatsApp's official QR code system
- **Modern features** like search, emoji picker, and typing indicators

### System Requirements

**Minimum Requirements:**
- Linux distribution with GTK4 support (Ubuntu 22.04+, Fedora 36+, etc.)
- 4GB RAM
- 1GB free disk space
- Internet connection

**Recommended:**
- 8GB RAM for optimal performance
- SSD storage for faster message loading
- Modern CPU (2015 or newer)

## Installation

### Method 1: Flatpak (Recommended)

Flatpak provides the easiest installation with automatic updates:

```bash
# Add Flathub repository (if not already added)
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

# Install Karere
flatpak install flathub io.github.tobagin.Karere

# Run Karere
flatpak run io.github.tobagin.Karere
```

### Method 2: Package Manager

**Ubuntu/Debian:**
```bash
# Add Karere repository
curl -fsSL https://packages.karere.app/gpg | sudo gpg --dearmor -o /usr/share/keyrings/karere.gpg
echo "deb [signed-by=/usr/share/keyrings/karere.gpg] https://packages.karere.app/deb stable main" | sudo tee /etc/apt/sources.list.d/karere.list

# Install
sudo apt update
sudo apt install karere
```

**Fedora:**
```bash
# Add Karere repository
sudo dnf config-manager --add-repo https://packages.karere.app/rpm/karere.repo

# Install
sudo dnf install karere
```

**Arch Linux (AUR):**
```bash
# Using yay
yay -S karere

# Using paru
paru -S karere
```

### Method 3: AppImage

Download the latest AppImage from [GitHub Releases](https://github.com/tobagin/Karere/releases):

```bash
# Download AppImage
wget https://github.com/tobagin/Karere/releases/latest/download/Karere-x86_64.AppImage

# Make executable
chmod +x Karere-x86_64.AppImage

# Run
./Karere-x86_64.AppImage
```

### Method 4: From Source

For developers or advanced users:

```bash
# Install dependencies
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 nodejs npm meson ninja-build

# Clone and build
git clone https://github.com/tobagin/Karere.git
cd Karere
meson setup builddir
meson compile -C builddir
sudo meson install -C builddir
```

## First Time Setup

### 1. Launch Karere

After installation, launch Karere from your application menu or run `karere` in terminal.

### 2. QR Code Authentication

1. **QR Code Display**: Karere will show a QR code on the welcome screen
2. **Open WhatsApp**: On your phone, open WhatsApp
3. **Navigate to Settings**: Go to Settings → Linked Devices
4. **Link Device**: Tap "Link a Device"
5. **Scan QR Code**: Point your phone camera at the QR code in Karere
6. **Wait for Connection**: Karere will automatically connect and load your chats

### 3. Initial Sync

- **Chat Loading**: Your chats will appear in the sidebar
- **Message History**: Recent messages will be downloaded automatically
- **Contacts**: Contact names will be resolved and displayed

## Basic Usage

### Chat Management

**Selecting Chats:**
- Click any chat in the sidebar to open it
- Use the search bar to find specific chats
- Recent chats appear at the top

**Sending Messages:**
- Type your message in the text field at the bottom
- Press Enter or click the send button
- Messages appear immediately with delivery status

**Message Features:**
- **Timestamps**: Hover over messages to see exact time
- **Status Indicators**: ✓ sent, ✓✓ delivered, blue ✓✓ read
- **Message Selection**: Click and drag to select text

### Search and Navigation

**Chat Search:**
- Click the search icon in the chat sidebar
- Type contact names, phone numbers, or message content
- Results filter in real-time

**Message Navigation:**
- Scroll up to load older messages
- Use Ctrl+F to search within the current chat
- Click timestamps to jump to specific dates

### Emoji and Expressions

**Emoji Picker:**
- Click the emoji button (😊) next to the message field
- Browse categories or search for specific emojis
- Click any emoji to insert it

**Typing Indicators:**
- See when contacts are typing (appears below chat)
- Your typing status is sent to contacts automatically

## Features

### Core Messaging

✅ **Send and receive text messages**
✅ **Real-time message delivery**
✅ **Message status indicators**
✅ **Typing indicators**
✅ **Chat search and filtering**
✅ **Emoji picker with categories**
✅ **Contact name resolution**
✅ **Message timestamps**

### Interface Features

✅ **Dark mode support** (follows system theme)
✅ **Responsive design** (adapts to window size)
✅ **Keyboard shortcuts** (Enter to send, Ctrl+F to search)
✅ **Native notifications** (desktop integration)
✅ **System tray integration** (minimize to tray)

### Advanced Features

🚧 **Media messages** (images, videos, documents) - Coming Soon
🚧 **Voice messages** (record and playback) - Coming Soon
🚧 **Group chat management** - Coming Soon
🚧 **Status/Story viewing** - Coming Soon
🚧 **Message backup and restore** - Coming Soon

## Troubleshooting

### Common Issues

**Problem: QR Code Not Displaying**
- **Solution**: Restart Karere and ensure internet connection
- **Check**: Backend service is running (should start automatically)
- **Verify**: Port 8765 is not blocked by firewall

**Problem: Messages Not Sending**
- **Solution**: Check internet connection and WhatsApp account status
- **Verify**: Phone is connected to internet and WhatsApp is active
- **Try**: Restart Karere and re-scan QR code if needed

**Problem: Application Won't Start**
- **Solution**: Check system dependencies are installed
- **Verify**: GTK4 and Adwaita libraries are available
- **Check**: Run `karere` in terminal to see error messages

**Problem: High Memory Usage**
- **Solution**: Restart Karere periodically for long sessions
- **Check**: Close unused chats to reduce memory usage
- **Monitor**: Use system monitor to track resource usage

### Getting Help

**Log Files:**
- Application logs: `~/.local/share/karere/logs/`
- Backend logs: `~/.local/share/karere/backend/logs/`

**Debug Mode:**
```bash
# Run with debug output
G_MESSAGES_DEBUG=all karere

# Backend debug mode
cd ~/.local/share/karere/backend
DEBUG=* npm start
```

**System Information:**
```bash
# Check GTK version
pkg-config --modversion gtk4

# Check Python version
python3 --version

# Check Node.js version
node --version
```

## FAQ

**Q: Is Karere official WhatsApp software?**
A: No, Karere is an unofficial client that uses WhatsApp's web interface. It's not affiliated with WhatsApp Inc.

**Q: Is my data secure?**
A: Yes, Karere uses WhatsApp's end-to-end encryption. Messages are encrypted between your phone and contacts.

**Q: Can I use Karere without my phone?**
A: No, your phone must be connected to internet and have WhatsApp active for Karere to work.

**Q: Does Karere support multiple accounts?**
A: Currently, Karere supports one WhatsApp account at a time.

**Q: Can I backup my chat history?**
A: Chat history is stored locally. Backup features are planned for future releases.

**Q: Why does Karere need my phone to be online?**
A: Karere connects through WhatsApp Web, which requires your phone to relay messages.

## Support

### Getting Help

- **GitHub Issues**: [Report bugs and request features](https://github.com/tobagin/Karere/issues)
- **Discussions**: [Community support and questions](https://github.com/tobagin/Karere/discussions)
- **Documentation**: [Technical documentation](https://github.com/tobagin/Karere/wiki)

### Contributing

Karere is open source! Contributions are welcome:
- **Code**: Submit pull requests for bug fixes and features
- **Documentation**: Help improve guides and documentation
- **Testing**: Report bugs and test new features
- **Translation**: Help translate Karere to other languages

### License

Karere is licensed under GPL-3.0-or-later. See [LICENSE](../LICENSE) for details.

---

**Happy messaging with Karere! 🎉**
