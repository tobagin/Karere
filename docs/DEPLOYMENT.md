# Karere Deployment Guide

This guide covers deployment strategies, packaging, and distribution for Karere across different platforms and environments.

## Table of Contents

1. [Deployment Overview](#deployment-overview)
2. [Flatpak Packaging](#flatpak-packaging)
3. [AppImage Creation](#appimage-creation)
4. [Distribution Packages](#distribution-packages)
5. [Container Deployment](#container-deployment)
6. [Release Process](#release-process)
7. [CI/CD Pipeline](#cicd-pipeline)

## Deployment Overview

Karere supports multiple deployment methods to reach different user bases:

### Deployment Targets

**Primary Targets:**
- **Flatpak**: Universal Linux packaging (recommended)
- **AppImage**: Portable application format
- **Distribution Packages**: Native .deb, .rpm, .pkg.tar.xz

**Secondary Targets:**
- **Snap**: Ubuntu/Canonical ecosystem
- **Container**: Docker/Podman for server deployments
- **Source**: Direct compilation for developers

### Architecture Support

- **x86_64**: Primary architecture (Intel/AMD 64-bit)
- **aarch64**: ARM 64-bit (Raspberry Pi 4, Apple Silicon via translation)
- **armv7**: ARM 32-bit (older Raspberry Pi models)

## Flatpak Packaging

Flatpak is the recommended distribution method for Karere, providing sandboxed execution and automatic updates.

### Build Environment Setup

```bash
# Install Flatpak development tools
sudo apt install flatpak flatpak-builder

# Add Flathub repository
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

# Install GNOME SDK
flatpak install flathub org.gnome.Platform//47 org.gnome.Sdk//47
```

### Building Flatpak

```bash
# Build development version
flatpak-builder build-dir frontend/data/io.github.tobagin.Karere.Devel.json --force-clean

# Install locally for testing
flatpak-builder --user --install build-dir frontend/data/io.github.tobagin.Karere.Devel.json --force-clean

# Run development build
flatpak run io.github.tobagin.Karere.Devel
```

### Production Flatpak Build

```bash
# Build production version
flatpak-builder build-dir frontend/data/io.github.tobagin.Karere.json --force-clean --repo=repo

# Create bundle for distribution
flatpak build-bundle repo karere.flatpak io.github.tobagin.Karere

# Export to repository
flatpak build-export repo build-dir
```

### Flatpak Manifest Configuration

Key sections in `io.github.tobagin.Karere.json`:

```json
{
    "app-id": "io.github.tobagin.Karere",
    "runtime": "org.gnome.Platform",
    "runtime-version": "47",
    "sdk": "org.gnome.Sdk",
    "command": "karere",
    "finish-args": [
        "--share=network",
        "--share=ipc",
        "--socket=fallback-x11",
        "--socket=wayland",
        "--device=dri",
        "--talk-name=org.freedesktop.secrets"
    ],
    "modules": [
        {
            "name": "nodejs",
            "buildsystem": "simple",
            "build-commands": [
                "wget https://nodejs.org/dist/v20.13.1/node-v20.13.1-linux-x64.tar.xz",
                "tar -xf node-v20.13.1-linux-x64.tar.xz",
                "cp -r node-v20.13.1-linux-x64/* /app/"
            ]
        },
        {
            "name": "karere",
            "buildsystem": "meson",
            "sources": [
                {
                    "type": "git",
                    "url": "https://github.com/tobagin/Karere.git",
                    "tag": "v1.0.0"
                }
            ]
        }
    ]
}
```

## AppImage Creation

AppImage provides a portable application format that runs on most Linux distributions.

### AppImage Build Script

Create `scripts/build-appimage.sh`:

```bash
#!/bin/bash
set -e

# Configuration
APP_NAME="Karere"
APP_VERSION="1.0.0"
ARCH="x86_64"
BUILD_DIR="appimage-build"

# Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Build application
meson setup builddir --prefix="/usr" --buildtype=release
meson compile -C builddir
DESTDIR="$PWD/$BUILD_DIR" meson install -C builddir

# Create AppDir structure
cd "$BUILD_DIR"
mkdir -p usr/bin usr/lib usr/share

# Copy backend
cp -r ../backend usr/share/karere-backend
cd usr/share/karere-backend && npm install --production && cd ../../..

# Download AppImage tools
wget -c "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
chmod +x appimagetool-x86_64.AppImage

# Create AppImage
./appimagetool-x86_64.AppImage "$BUILD_DIR" "$APP_NAME-$APP_VERSION-$ARCH.AppImage"
```

### AppImage Desktop Integration

Create `AppRun` script:

```bash
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
export PYTHONPATH="${HERE}/usr/share/karere:${PYTHONPATH}"

# Start backend in background
cd "${HERE}/usr/share/karere-backend"
node backend.js &
BACKEND_PID=$!

# Start frontend
cd "${HERE}"
python3 usr/share/karere/main.py

# Cleanup
kill $BACKEND_PID 2>/dev/null || true
```

## Distribution Packages

### Debian/Ubuntu Package

Create `scripts/build-deb.sh`:

```bash
#!/bin/bash
set -e

# Package information
PACKAGE_NAME="karere"
VERSION="1.0.0"
ARCH="amd64"
MAINTAINER="Karere Team <team@karere.app>"

# Create package structure
mkdir -p debian-build/DEBIAN
mkdir -p debian-build/usr/bin
mkdir -p debian-build/usr/share/applications
mkdir -p debian-build/usr/share/pixmaps

# Build and install
meson setup builddir --prefix="/usr" --buildtype=release
meson compile -C builddir
DESTDIR="$PWD/debian-build" meson install -C builddir

# Create control file
cat > debian-build/DEBIAN/control << EOF
Package: $PACKAGE_NAME
Version: $VERSION
Section: net
Priority: optional
Architecture: $ARCH
Depends: python3-gi, gir1.2-gtk-4.0, gir1.2-adw-1, nodejs (>= 18), npm
Maintainer: $MAINTAINER
Description: Modern native WhatsApp client for Linux
 Karere is a native Linux WhatsApp client built with GTK4 and Adwaita,
 providing a modern and integrated messaging experience.
EOF

# Create postinst script
cat > debian-build/DEBIAN/postinst << 'EOF'
#!/bin/bash
set -e

# Install backend dependencies
cd /usr/share/karere-backend
npm install --production

# Update desktop database
update-desktop-database
EOF

chmod +x debian-build/DEBIAN/postinst

# Build package
dpkg-deb --build debian-build "${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
```

### RPM Package (Fedora/RHEL)

Create `karere.spec`:

```spec
Name:           karere
Version:        1.0.0
Release:        1%{?dist}
Summary:        Modern native WhatsApp client for Linux

License:        GPL-3.0-or-later
URL:            https://github.com/tobagin/Karere
Source0:        %{name}-%{version}.tar.gz

BuildRequires:  meson
BuildRequires:  ninja-build
BuildRequires:  python3-gobject-devel
BuildRequires:  gtk4-devel
BuildRequires:  libadwaita-devel
BuildRequires:  nodejs
BuildRequires:  npm

Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       nodejs >= 18
Requires:       npm

%description
Karere is a native Linux WhatsApp client built with GTK4 and Adwaita,
providing a modern and integrated messaging experience.

%prep
%autosetup

%build
%meson
%meson_build

%install
%meson_install

# Install backend
mkdir -p %{buildroot}%{_datadir}/karere-backend
cp -r backend/* %{buildroot}%{_datadir}/karere-backend/

%post
cd %{_datadir}/karere-backend
npm install --production

%files
%license LICENSE
%doc README.md
%{_bindir}/karere
%{_datadir}/karere/
%{_datadir}/karere-backend/
%{_datadir}/applications/io.github.tobagin.Karere.desktop
%{_datadir}/metainfo/io.github.tobagin.Karere.appdata.xml

%changelog
* Mon Jan 01 2024 Karere Team <team@karere.app> - 1.0.0-1
- Initial release
```

## Container Deployment

### Docker Configuration

Create `Dockerfile`:

```dockerfile
FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-4.0 \
    gir1.2-adw-1 \
    nodejs \
    npm \
    meson \
    ninja-build \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -s /bin/bash karere

# Copy source
COPY . /app
WORKDIR /app

# Build application
RUN meson setup builddir --prefix=/usr
RUN meson compile -C builddir
RUN meson install -C builddir

# Install backend dependencies
WORKDIR /app/backend
RUN npm install --production

# Switch to app user
USER karere
WORKDIR /home/karere

# Expose WebSocket port
EXPOSE 8765

# Start application
CMD ["karere"]
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  karere:
    build: .
    ports:
      - "8765:8765"
    volumes:
      - karere-data:/home/karere/.local/share/karere
      - /tmp/.X11-unix:/tmp/.X11-unix:rw
    environment:
      - DISPLAY=${DISPLAY}
    network_mode: host

volumes:
  karere-data:
```

## Release Process

### Automated Release Workflow

Create `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build-packages:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: [flatpak, appimage, deb]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup build environment
      run: |
        sudo apt-get update
        sudo apt-get install -y flatpak flatpak-builder
    
    - name: Build ${{ matrix.package }}
      run: ./scripts/build-${{ matrix.package }}.sh
    
    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: ${{ matrix.package }}-package
        path: "*.{flatpak,AppImage,deb}"

  create-release:
    needs: build-packages
    runs-on: ubuntu-latest
    
    steps:
    - name: Download artifacts
      uses: actions/download-artifact@v3
    
    - name: Create Release
      uses: softprops/action-gh-release@v1
      with:
        files: |
          */*.flatpak
          */*.AppImage
          */*.deb
        generate_release_notes: true
```

### Version Management

Update version in multiple files:

```bash
# Update version script
#!/bin/bash
NEW_VERSION="$1"

if [ -z "$NEW_VERSION" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

# Update meson.build
sed -i "s/version: '[^']*'/version: '$NEW_VERSION'/" meson.build

# Update package.json
sed -i "s/\"version\": \"[^\"]*\"/\"version\": \"$NEW_VERSION\"/" backend/package.json

# Update AppData
sed -i "s/<release version=\"[^\"]*\"/<release version=\"$NEW_VERSION\"/" frontend/data/io.github.tobagin.Karere.appdata.xml.in

echo "Version updated to $NEW_VERSION"
```

## CI/CD Pipeline

### Build Matrix

The CI/CD pipeline tests multiple configurations:

- **Platforms**: Ubuntu 22.04, Fedora 38, Arch Linux
- **Python**: 3.8, 3.9, 3.10, 3.11
- **Node.js**: 18.x, 20.x
- **Build Types**: Debug, Release
- **Package Formats**: Flatpak, AppImage, DEB, RPM

### Quality Gates

Before release, all checks must pass:

1. **Unit Tests**: >95% coverage
2. **Integration Tests**: All scenarios pass
3. **Security Scan**: No high/critical vulnerabilities
4. **Performance Tests**: Memory usage < 200MB
5. **Package Tests**: All formats install and run correctly

### Deployment Stages

1. **Development**: Continuous integration on every commit
2. **Staging**: Nightly builds for testing
3. **Release Candidate**: Pre-release testing
4. **Production**: Stable release to all channels

---

For more information on building and packaging, see the [Developer Guide](DEVELOPER_GUIDE.md).
