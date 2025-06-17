#!/bin/bash
# build-packages.sh
# Comprehensive package building script for Karere

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build-packages"
DIST_DIR="$PROJECT_ROOT/dist"

# Package information
APP_NAME="Karere"
APP_ID="io.github.tobagin.Karere"
VERSION="1.0.0"
MAINTAINER="Karere Team <team@karere.app>"

# Default options
BUILD_FLATPAK=false
BUILD_APPIMAGE=false
BUILD_DEB=false
BUILD_RPM=false
BUILD_SNAP=false
BUILD_ALL=false
CLEAN_BUILD=false
VERBOSE=false

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Build packages for Karere distribution.

OPTIONS:
    -h, --help              Show this help message
    -f, --flatpak           Build Flatpak package
    -a, --appimage          Build AppImage package
    -d, --deb               Build Debian package
    -r, --rpm               Build RPM package
    -s, --snap              Build Snap package
    --all                   Build all package types
    -c, --clean             Clean build directories before building
    -v, --verbose           Verbose output

EXAMPLES:
    $0 --flatpak            # Build only Flatpak
    $0 --all                # Build all packages
    $0 --deb --rpm          # Build DEB and RPM packages
    $0 --clean --all        # Clean build and build all packages

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -f|--flatpak)
            BUILD_FLATPAK=true
            shift
            ;;
        -a|--appimage)
            BUILD_APPIMAGE=true
            shift
            ;;
        -d|--deb)
            BUILD_DEB=true
            shift
            ;;
        -r|--rpm)
            BUILD_RPM=true
            shift
            ;;
        -s|--snap)
            BUILD_SNAP=true
            shift
            ;;
        --all)
            BUILD_ALL=true
            shift
            ;;
        -c|--clean)
            CLEAN_BUILD=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Set all packages if --all is specified
if [[ "$BUILD_ALL" == true ]]; then
    BUILD_FLATPAK=true
    BUILD_APPIMAGE=true
    BUILD_DEB=true
    BUILD_RPM=true
    BUILD_SNAP=true
fi

# Check if at least one package type is selected
if [[ "$BUILD_FLATPAK" == false && "$BUILD_APPIMAGE" == false && "$BUILD_DEB" == false && "$BUILD_RPM" == false && "$BUILD_SNAP" == false ]]; then
    print_error "No package type selected. Use --help for usage information."
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check dependencies
check_dependencies() {
    print_status "Checking dependencies..."
    
    local missing_deps=()
    
    # Common dependencies
    if ! command_exists meson; then
        missing_deps+=("meson")
    fi
    
    if ! command_exists ninja; then
        missing_deps+=("ninja-build")
    fi
    
    # Flatpak dependencies
    if [[ "$BUILD_FLATPAK" == true ]]; then
        if ! command_exists flatpak-builder; then
            missing_deps+=("flatpak-builder")
        fi
    fi
    
    # AppImage dependencies
    if [[ "$BUILD_APPIMAGE" == true ]]; then
        if ! command_exists wget; then
            missing_deps+=("wget")
        fi
    fi
    
    # DEB dependencies
    if [[ "$BUILD_DEB" == true ]]; then
        if ! command_exists dpkg-deb; then
            missing_deps+=("dpkg-dev")
        fi
    fi
    
    # RPM dependencies
    if [[ "$BUILD_RPM" == true ]]; then
        if ! command_exists rpmbuild; then
            missing_deps+=("rpm-build")
        fi
    fi
    
    # Snap dependencies
    if [[ "$BUILD_SNAP" == true ]]; then
        if ! command_exists snapcraft; then
            missing_deps+=("snapcraft")
        fi
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        print_status "Install missing dependencies and try again."
        exit 1
    fi
    
    print_success "All dependencies found"
}

# Function to setup build environment
setup_build_env() {
    print_status "Setting up build environment..."
    
    # Clean build directories if requested
    if [[ "$CLEAN_BUILD" == true ]]; then
        print_status "Cleaning build directories..."
        rm -rf "$BUILD_DIR" "$DIST_DIR"
    fi
    
    # Create directories
    mkdir -p "$BUILD_DIR" "$DIST_DIR"
    
    # Build the application first
    print_status "Building Karere..."
    cd "$PROJECT_ROOT"
    
    if [[ ! -d "builddir" ]] || [[ "$CLEAN_BUILD" == true ]]; then
        meson setup builddir --buildtype=release
    fi
    
    meson compile -C builddir
    
    print_success "Build environment ready"
}

# Function to build Flatpak
build_flatpak() {
    print_status "Building Flatpak package..."
    
    local flatpak_dir="$BUILD_DIR/flatpak"
    mkdir -p "$flatpak_dir"
    
    cd "$flatpak_dir"
    
    # Copy manifest
    cp "$PROJECT_ROOT/frontend/data/io.github.tobagin.Karere.json" .
    
    # Build Flatpak
    if [[ "$VERBOSE" == true ]]; then
        flatpak-builder build-dir io.github.tobagin.Karere.json --force-clean --repo=repo
    else
        flatpak-builder build-dir io.github.tobagin.Karere.json --force-clean --repo=repo > /dev/null 2>&1
    fi
    
    # Create bundle
    flatpak build-bundle repo "$DIST_DIR/${APP_NAME}-${VERSION}.flatpak" "$APP_ID"
    
    print_success "Flatpak package created: ${APP_NAME}-${VERSION}.flatpak"
}

# Function to build AppImage
build_appimage() {
    print_status "Building AppImage package..."
    
    local appimage_dir="$BUILD_DIR/appimage"
    local appdir="$appimage_dir/AppDir"
    
    mkdir -p "$appdir"
    cd "$appimage_dir"
    
    # Install to AppDir
    DESTDIR="$appdir" meson install -C "$PROJECT_ROOT/builddir"
    
    # Copy backend
    mkdir -p "$appdir/usr/share/karere-backend"
    cp -r "$PROJECT_ROOT/backend"/* "$appdir/usr/share/karere-backend/"
    
    # Install backend dependencies
    cd "$appdir/usr/share/karere-backend"
    npm install --production --silent
    cd "$appimage_dir"
    
    # Create AppRun script
    cat > "$appdir/AppRun" << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
export PYTHONPATH="${HERE}/usr/share/karere:${PYTHONPATH}"

# Start backend in background
cd "${HERE}/usr/share/karere-backend"
node backend.js &
BACKEND_PID=$!

# Cleanup function
cleanup() {
    kill $BACKEND_PID 2>/dev/null || true
}
trap cleanup EXIT

# Start frontend
cd "${HERE}"
python3 usr/share/karere/main.py
EOF
    
    chmod +x "$appdir/AppRun"
    
    # Copy desktop file and icon
    cp "$appdir/usr/share/applications/${APP_ID}.desktop" "$appdir/"
    mkdir -p "$appdir/usr/share/pixmaps"
    # Note: Add icon copying here when icon is available
    
    # Download appimagetool
    if [[ ! -f "appimagetool-x86_64.AppImage" ]]; then
        wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
        chmod +x appimagetool-x86_64.AppImage
    fi
    
    # Create AppImage
    if [[ "$VERBOSE" == true ]]; then
        ./appimagetool-x86_64.AppImage "$appdir" "$DIST_DIR/${APP_NAME}-${VERSION}-x86_64.AppImage"
    else
        ./appimagetool-x86_64.AppImage "$appdir" "$DIST_DIR/${APP_NAME}-${VERSION}-x86_64.AppImage" > /dev/null 2>&1
    fi
    
    print_success "AppImage package created: ${APP_NAME}-${VERSION}-x86_64.AppImage"
}

# Function to build DEB package
build_deb() {
    print_status "Building DEB package..."
    
    local deb_dir="$BUILD_DIR/deb"
    local package_dir="$deb_dir/package"
    
    mkdir -p "$package_dir/DEBIAN"
    
    # Install to package directory
    DESTDIR="$package_dir" meson install -C "$PROJECT_ROOT/builddir"
    
    # Copy backend
    mkdir -p "$package_dir/usr/share/karere-backend"
    cp -r "$PROJECT_ROOT/backend"/* "$package_dir/usr/share/karere-backend/"
    
    # Create control file
    cat > "$package_dir/DEBIAN/control" << EOF
Package: karere
Version: $VERSION
Section: net
Priority: optional
Architecture: amd64
Depends: python3-gi, gir1.2-gtk-4.0, gir1.2-adw-1, nodejs (>= 18), npm
Maintainer: $MAINTAINER
Description: Modern native WhatsApp client for Linux
 Karere is a native Linux WhatsApp client built with GTK4 and Adwaita,
 providing a modern and integrated messaging experience.
EOF
    
    # Create postinst script
    cat > "$package_dir/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

# Install backend dependencies
cd /usr/share/karere-backend
npm install --production --silent

# Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database
fi
EOF
    
    chmod +x "$package_dir/DEBIAN/postinst"
    
    # Build package
    cd "$deb_dir"
    dpkg-deb --build package "$DIST_DIR/karere_${VERSION}_amd64.deb"
    
    print_success "DEB package created: karere_${VERSION}_amd64.deb"
}

# Function to build RPM package
build_rpm() {
    print_status "Building RPM package..."
    
    local rpm_dir="$BUILD_DIR/rpm"
    mkdir -p "$rpm_dir"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
    
    # Create source tarball
    cd "$PROJECT_ROOT"
    tar --exclude='.git' --exclude='builddir' --exclude='build-packages' --exclude='dist' \
        -czf "$rpm_dir/SOURCES/karere-${VERSION}.tar.gz" .
    
    # Create spec file
    cat > "$rpm_dir/SPECS/karere.spec" << EOF
Name:           karere
Version:        $VERSION
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
npm install --production --silent

%files
%license LICENSE
%doc README.md
%{_bindir}/karere
%{_datadir}/karere/
%{_datadir}/karere-backend/
%{_datadir}/applications/io.github.tobagin.Karere.desktop
%{_datadir}/metainfo/io.github.tobagin.Karere.appdata.xml

%changelog
* $(date '+%a %b %d %Y') $MAINTAINER - $VERSION-1
- Version $VERSION release
EOF
    
    # Build RPM
    cd "$rpm_dir"
    if [[ "$VERBOSE" == true ]]; then
        rpmbuild --define "_topdir $rpm_dir" -ba SPECS/karere.spec
    else
        rpmbuild --define "_topdir $rpm_dir" -ba SPECS/karere.spec > /dev/null 2>&1
    fi
    
    # Copy to dist directory
    cp RPMS/*/karere-*.rpm "$DIST_DIR/"
    
    print_success "RPM package created: $(basename RPMS/*/karere-*.rpm)"
}

# Function to build Snap package
build_snap() {
    print_status "Building Snap package..."
    
    local snap_dir="$BUILD_DIR/snap"
    mkdir -p "$snap_dir"
    
    cd "$snap_dir"
    
    # Create snapcraft.yaml
    cat > snapcraft.yaml << EOF
name: karere
version: '$VERSION'
summary: Modern native WhatsApp client for Linux
description: |
  Karere is a native Linux WhatsApp client built with GTK4 and Adwaita,
  providing a modern and integrated messaging experience.

grade: stable
confinement: strict
base: core22

apps:
  karere:
    command: usr/bin/karere
    desktop: usr/share/applications/io.github.tobagin.Karere.desktop
    plugs:
      - network
      - desktop
      - desktop-legacy
      - wayland
      - x11

parts:
  karere:
    source: $PROJECT_ROOT
    plugin: meson
    meson-parameters:
      - --prefix=/usr
    build-packages:
      - python3-gi-dev
      - libgtk-4-dev
      - libadwaita-1-dev
      - nodejs
      - npm
    stage-packages:
      - python3-gi
      - gir1.2-gtk-4.0
      - gir1.2-adw-1
      - nodejs
      - npm
    override-build: |
      craftctl default
      # Install backend dependencies
      cd \$CRAFT_PART_INSTALL/usr/share/karere-backend
      npm install --production
EOF
    
    # Build snap
    if [[ "$VERBOSE" == true ]]; then
        snapcraft
    else
        snapcraft > /dev/null 2>&1
    fi
    
    # Copy to dist directory
    cp karere_*.snap "$DIST_DIR/"
    
    print_success "Snap package created: $(basename karere_*.snap)"
}

# Main execution
main() {
    print_status "Starting Karere package building..."
    print_status "Project root: $PROJECT_ROOT"
    
    # Check dependencies
    check_dependencies
    
    # Setup build environment
    setup_build_env
    
    local exit_code=0
    
    # Build packages
    if [[ "$BUILD_FLATPAK" == true ]]; then
        if ! build_flatpak; then
            exit_code=1
        fi
    fi
    
    if [[ "$BUILD_APPIMAGE" == true ]]; then
        if ! build_appimage; then
            exit_code=1
        fi
    fi
    
    if [[ "$BUILD_DEB" == true ]]; then
        if ! build_deb; then
            exit_code=1
        fi
    fi
    
    if [[ "$BUILD_RPM" == true ]]; then
        if ! build_rpm; then
            exit_code=1
        fi
    fi
    
    if [[ "$BUILD_SNAP" == true ]]; then
        if ! build_snap; then
            exit_code=1
        fi
    fi
    
    # Final status
    if [[ $exit_code -eq 0 ]]; then
        print_success "All packages built successfully!"
        print_status "Packages available in: $DIST_DIR"
        ls -la "$DIST_DIR"
    else
        print_error "Some packages failed to build!"
    fi
    
    return $exit_code
}

# Run main function
main "$@"
