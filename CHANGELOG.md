# Changelog

All notable changes to Karere will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive documentation system with user and developer guides
- Automated package building for Flatpak, AppImage, DEB, RPM, and Snap
- Release automation with GitHub Actions
- API documentation for WebSocket protocol and internal APIs
- Deployment guides for multiple distribution methods

### Changed
- Enhanced README with better structure and comprehensive information
- Improved project documentation organization

### Fixed
- Documentation links and references

## [1.0.0] - 2024-01-15

### Added
- **Core Messaging Features**
  - Real-time text messaging with WhatsApp compatibility
  - Message status indicators (sent, delivered, read)
  - Typing indicators for both sending and receiving
  - Message history loading and persistence
  - Contact name resolution and management

- **Modern GTK4 Interface**
  - Native Linux integration with GTK4 and Adwaita
  - Responsive design that adapts to different screen sizes
  - Dark mode support with automatic theme switching
  - Search functionality for messages and contacts
  - Emoji picker with categories and search

- **Backend Infrastructure**
  - Node.js backend using Baileys for WhatsApp Web API
  - WebSocket communication between frontend and backend
  - SQLite database for local message persistence
  - Comprehensive logging system with Winston
  - Service management with health monitoring
  - Graceful shutdown and error handling

- **Security & Authentication**
  - QR code authentication using WhatsApp's official system
  - End-to-end encryption maintained through WhatsApp protocol
  - Local message storage with SQLite
  - No data collection or transmission to third parties

- **Testing & Quality Assurance**
  - Comprehensive test suite with Jest (backend) and unittest (frontend)
  - Unit tests for all major components
  - Integration tests for WebSocket communication
  - GitHub Actions CI/CD pipeline
  - Code coverage reporting with Codecov
  - ESLint for code quality enforcement

- **Build System & Packaging**
  - Meson build system for native Linux packaging
  - Flatpak manifest for universal Linux distribution
  - Desktop integration with .desktop and AppData files
  - GTK4 resource compilation and installation

### Technical Details
- **Frontend**: Python 3.8+ with PyGObject, GTK4, and Adwaita
- **Backend**: Node.js 18+ with Baileys, WebSocket, and SQLite
- **Communication**: Real-time WebSocket protocol with JSON messages
- **Database**: SQLite with tables for chats, messages, contacts, and settings
- **Build**: Meson build system with ninja backend

### System Requirements
- Linux distribution with GTK4 support (Ubuntu 22.04+, Fedora 36+)
- Python 3.8+ with PyGObject bindings
- Node.js 18+ with npm package manager
- 4GB RAM minimum, 8GB recommended
- 1GB free disk space

### Known Limitations
- Single WhatsApp account support (multi-account planned for v1.1)
- Text messages only (media support planned for v1.1)
- Requires phone to be online and connected to internet
- Linux only (Windows/macOS support not planned)

## [0.9.0] - 2024-01-01 (Beta Release)

### Added
- Initial beta release with core messaging functionality
- Basic GTK4 interface with chat list and message view
- WhatsApp Web integration using Baileys
- QR code authentication flow
- Real-time message sending and receiving

### Known Issues
- Limited error handling and recovery
- No message persistence between sessions
- Basic UI without advanced features
- No comprehensive testing

## [0.1.0] - 2023-12-01 (Alpha Release)

### Added
- Initial project setup and architecture
- Basic frontend structure with GTK4
- Backend foundation with Node.js and Baileys
- WebSocket communication proof of concept
- Meson build system configuration

---

## Release Notes Template

### Version X.Y.Z - YYYY-MM-DD

#### 🎉 Highlights
- Major feature or improvement summary

#### ✨ New Features
- **Feature Name**: Description of the new feature
- **Another Feature**: What it does and why it's useful

#### 🔧 Improvements
- **Performance**: Specific performance improvements
- **UI/UX**: User interface and experience enhancements
- **Developer Experience**: Tools and workflow improvements

#### 🐛 Bug Fixes
- **Issue Description**: What was fixed and how
- **Another Fix**: Resolution details

#### 🔒 Security
- **Security Enhancement**: Description of security improvements
- **Vulnerability Fix**: Details of security fixes

#### 📚 Documentation
- **New Documentation**: What documentation was added
- **Updated Guides**: Which guides were improved

#### 🏗️ Technical Changes
- **Architecture**: Structural changes to the codebase
- **Dependencies**: Updated libraries and dependencies
- **Build System**: Changes to build and packaging

#### ⚠️ Breaking Changes
- **API Changes**: Changes that might affect existing users
- **Configuration**: Changes to configuration files or setup

#### 🚀 Migration Guide
- **From Previous Version**: Steps to upgrade from previous version
- **Configuration Changes**: Required configuration updates

#### 📦 Downloads
- **Flatpak**: `flatpak install flathub io.github.tobagin.Karere`
- **AppImage**: [Download from GitHub Releases](https://github.com/tobagin/Karere/releases)
- **Source**: Available on [GitHub](https://github.com/tobagin/Karere)

#### 🙏 Contributors
- Thanks to all contributors who made this release possible

#### 🔗 Links
- [Full Changelog](https://github.com/tobagin/Karere/compare/vX.Y.Z-1...vX.Y.Z)
- [GitHub Release](https://github.com/tobagin/Karere/releases/tag/vX.Y.Z)
- [Documentation](https://github.com/tobagin/Karere/tree/vX.Y.Z/docs)

---

## Versioning Strategy

Karere follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version (X.0.0): Incompatible API changes or major architectural changes
- **MINOR** version (X.Y.0): New features in a backwards compatible manner
- **PATCH** version (X.Y.Z): Backwards compatible bug fixes

### Pre-release Versions
- **Alpha** (X.Y.Z-alpha.N): Early development versions with incomplete features
- **Beta** (X.Y.Z-beta.N): Feature-complete versions undergoing testing
- **Release Candidate** (X.Y.Z-rc.N): Final testing before stable release

### Release Schedule
- **Major releases**: Every 6-12 months
- **Minor releases**: Every 2-3 months
- **Patch releases**: As needed for critical bug fixes
- **Security releases**: Immediate for critical security issues

### Support Policy
- **Current major version**: Full support with new features and bug fixes
- **Previous major version**: Security fixes and critical bug fixes for 6 months
- **Older versions**: No official support (community support available)

---

For more information about releases and versioning, see the [Release Process](docs/DEPLOYMENT.md#release-process) documentation.
