# Karere Documentation

Welcome to the comprehensive documentation for Karere, a modern native WhatsApp client for Linux.

## 📚 Documentation Overview

This documentation is organized into several sections to help different types of users:

### 👥 For Users

- **[User Guide](USER_GUIDE.md)** - Complete guide for installing, setting up, and using Karere
  - Installation methods (Flatpak, AppImage, packages)
  - First-time setup and QR code authentication
  - Basic usage and features
  - Troubleshooting common issues
  - FAQ and support information

### 🔧 For Developers

- **[Developer Guide](DEVELOPER_GUIDE.md)** - Comprehensive development documentation
  - Architecture overview and design decisions
  - Development environment setup
  - Project structure and code organization
  - Backend and frontend development guides
  - Testing framework and quality assurance
  - Building and packaging instructions

- **[API Documentation](API.md)** - Technical API reference
  - WebSocket protocol specification
  - Backend API reference
  - Database schema documentation
  - Frontend component APIs
  - Error handling and event systems

### 🚀 For Distributors

- **[Deployment Guide](DEPLOYMENT.md)** - Packaging and distribution
  - Flatpak packaging and distribution
  - AppImage creation and deployment
  - Distribution-specific packages (DEB, RPM, Snap)
  - Container deployment with Docker
  - Release process and automation
  - CI/CD pipeline configuration

### 📋 Project Information

- **[Contributing Guidelines](../CONTRIBUTING.md)** - How to contribute to Karere
  - Development setup and workflow
  - Code style and conventions
  - Testing requirements
  - Pull request process
  - Community guidelines

- **[Changelog](../CHANGELOG.md)** - Version history and release notes
  - Feature additions and improvements
  - Bug fixes and security updates
  - Breaking changes and migration guides
  - Release schedule and versioning

## 🎯 Quick Start

### For Users
1. **Install**: Choose your preferred [installation method](USER_GUIDE.md#installation)
2. **Setup**: Follow the [first-time setup guide](USER_GUIDE.md#first-time-setup)
3. **Use**: Learn about [basic usage](USER_GUIDE.md#basic-usage) and [features](USER_GUIDE.md#features)

### For Developers
1. **Setup**: Follow the [development setup](DEVELOPER_GUIDE.md#development-setup)
2. **Understand**: Read the [architecture overview](DEVELOPER_GUIDE.md#architecture-overview)
3. **Develop**: Use the [development guides](DEVELOPER_GUIDE.md#backend-development) for your area of interest

### For Distributors
1. **Prepare**: Set up the [build environment](DEPLOYMENT.md#deployment-overview)
2. **Package**: Choose your [packaging method](DEPLOYMENT.md#flatpak-packaging)
3. **Deploy**: Follow the [release process](DEPLOYMENT.md#release-process)

## 🏗️ Architecture Overview

Karere uses a modern client-server architecture:

```
┌─────────────────┐    WebSocket    ┌─────────────────┐    WhatsApp Web    ┌─────────────────┐
│  GTK4 Frontend  │ ◄──────────────► │ Node.js Backend │ ◄─────────────────► │ WhatsApp Servers│
│    (Python)     │                 │  (JavaScript)   │                     │                 │
└─────────────────┘                 └─────────────────┘                     └─────────────────┘
        │                                     │
        ▼                                     ▼
┌─────────────────┐                 ┌─────────────────┐
│   UI Components │                 │   SQLite DB     │
│   • Chat List   │                 │   • Messages    │
│   • Messages    │                 │   • Chats       │
│   • Search      │                 │   • Contacts    │
└─────────────────┘                 └─────────────────┘
```

**Key Components:**
- **Frontend**: Python GTK4 application with Adwaita design
- **Backend**: Node.js service using Baileys for WhatsApp integration
- **Communication**: Real-time WebSocket protocol
- **Storage**: SQLite database for message persistence

## 🔧 Technology Stack

### Frontend
- **Language**: Python 3.8+
- **UI Framework**: GTK4 with Adwaita
- **Bindings**: PyGObject (python3-gi)
- **Communication**: WebSocket client
- **Build System**: Meson

### Backend
- **Language**: JavaScript (Node.js 18+)
- **WhatsApp Integration**: Baileys library
- **Communication**: WebSocket server (ws)
- **Database**: SQLite3
- **Logging**: Winston
- **Testing**: Jest

### Development Tools
- **Build System**: Meson with Ninja
- **Version Control**: Git with conventional commits
- **CI/CD**: GitHub Actions
- **Testing**: Jest (backend), unittest (frontend)
- **Code Quality**: ESLint, coverage reporting
- **Documentation**: Markdown with GitHub Pages

## 📊 Project Status

### Current Version: 1.0.0

**Stable Features:**
- ✅ Real-time text messaging
- ✅ QR code authentication
- ✅ Message history and search
- ✅ Typing indicators
- ✅ Contact management
- ✅ Dark mode support
- ✅ Native Linux integration

**In Development:**
- 🚧 Media message support (images, videos, documents)
- 🚧 Voice message recording and playback
- 🚧 Group chat management
- 🚧 Status/Story viewing

**Planned Features:**
- 📋 Message backup and restore
- 📋 Multi-account support
- 📋 Advanced search and filtering
- 📋 Custom themes and styling

## 🤝 Community

### Getting Help
- **User Support**: [GitHub Discussions](https://github.com/tobagin/Karere/discussions)
- **Bug Reports**: [GitHub Issues](https://github.com/tobagin/Karere/issues)
- **Feature Requests**: [GitHub Discussions](https://github.com/tobagin/Karere/discussions)

### Contributing
- **Code Contributions**: See [Contributing Guidelines](../CONTRIBUTING.md)
- **Documentation**: Help improve these docs
- **Testing**: Report bugs and test new features
- **Translation**: Help translate Karere (coming soon)

### Development Community
- **Discussions**: Technical discussions and questions
- **Code Reviews**: Collaborative code improvement
- **Feature Planning**: Community input on new features

## 📝 Documentation Standards

### Writing Guidelines
- **Clear and Concise**: Use simple, direct language
- **User-Focused**: Write from the user's perspective
- **Examples**: Include practical examples and code snippets
- **Screenshots**: Use screenshots for UI-related documentation
- **Links**: Cross-reference related documentation

### Structure
- **Logical Organization**: Group related information together
- **Progressive Disclosure**: Start simple, add complexity gradually
- **Searchable**: Use clear headings and keywords
- **Maintainable**: Keep documentation up-to-date with code changes

### Contributing to Documentation
1. **Identify Gaps**: Find areas that need better documentation
2. **Write Clearly**: Follow the writing guidelines above
3. **Test Instructions**: Verify that instructions actually work
4. **Submit Changes**: Create pull requests for documentation improvements

## 🔗 External Resources

### WhatsApp Integration
- [Baileys Documentation](https://github.com/WhiskeySockets/Baileys)
- [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp)

### GTK4 Development
- [GTK4 Documentation](https://docs.gtk.org/gtk4/)
- [Adwaita Documentation](https://gnome.pages.gitlab.gnome.org/libadwaita/)
- [PyGObject Documentation](https://pygobject.readthedocs.io/)

### Linux Packaging
- [Flatpak Documentation](https://docs.flatpak.org/)
- [AppImage Documentation](https://appimage.org/)
- [Meson Build System](https://mesonbuild.com/)

---

**Need help?** Check the [User Guide](USER_GUIDE.md) for common questions, or [open a discussion](https://github.com/tobagin/Karere/discussions) for community support.
