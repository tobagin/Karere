#!/bin/bash
# run-dev.sh
# Convenient script to launch Karere in development mode

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build"

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

Launch Karere in development mode.

OPTIONS:
    -h, --help              Show this help message
    -c, --clean             Clean build before running
    -v, --verbose           Verbose output
    --build-only            Only build, don't run
    --no-build              Skip build step

EXAMPLES:
    $0                      # Build and run Karere
    $0 --clean              # Clean build and run
    $0 --build-only         # Only build, don't run
    $0 --no-build           # Skip build, just run

EOF
}

# Default options
CLEAN_BUILD=false
VERBOSE=false
BUILD_ONLY=false
NO_BUILD=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -c|--clean)
            CLEAN_BUILD=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --build-only)
            BUILD_ONLY=true
            shift
            ;;
        --no-build)
            NO_BUILD=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Function to check dependencies
check_dependencies() {
    print_status "Checking dependencies..."
    
    local missing_deps=()
    
    # Check Python and GTK
    if ! command -v python3 >/dev/null 2>&1; then
        missing_deps+=("python3")
    fi
    
    # Check Node.js
    if ! command -v node >/dev/null 2>&1; then
        missing_deps+=("node")
    fi
    
    # Check npm
    if ! command -v npm >/dev/null 2>&1; then
        missing_deps+=("npm")
    fi
    
    # Check meson
    if ! command -v meson >/dev/null 2>&1; then
        missing_deps+=("meson")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        print_status "Please install missing dependencies and try again."
        exit 1
    fi
    
    print_success "All dependencies found"
}

# Function to setup build environment
setup_build() {
    if [[ "$NO_BUILD" == true ]]; then
        print_status "Skipping build step (--no-build)"
        return
    fi
    
    print_status "Setting up build environment..."
    
    cd "$PROJECT_ROOT"
    
    # Clean build if requested
    if [[ "$CLEAN_BUILD" == true ]]; then
        print_status "Cleaning build directory..."
        rm -rf "$BUILD_DIR"
    fi
    
    # Setup build directory
    if [[ ! -d "$BUILD_DIR" ]]; then
        print_status "Creating build directory..."
        meson setup "$BUILD_DIR" --buildtype=debug
    fi
    
    # Build project
    print_status "Building Karere..."
    if [[ "$VERBOSE" == true ]]; then
        meson compile -C "$BUILD_DIR" -v
    else
        meson compile -C "$BUILD_DIR"
    fi
    
    print_success "Build completed successfully"
}

# Function to check backend dependencies
check_backend_deps() {
    print_status "Checking backend dependencies..."
    
    cd "$PROJECT_ROOT/backend"
    
    if [[ ! -d "node_modules" ]]; then
        print_status "Installing backend dependencies..."
        npm install
    else
        print_status "Backend dependencies already installed"
    fi
    
    print_success "Backend dependencies ready"
}

# Function to run Karere
run_karere() {
    if [[ "$BUILD_ONLY" == true ]]; then
        print_status "Build-only mode, not running application"
        return
    fi
    
    print_status "Starting Karere in development mode..."
    print_status "Project root: $PROJECT_ROOT"
    print_status "Build directory: $BUILD_DIR"
    
    cd "$BUILD_DIR"
    
    print_success "Launching Karere..."
    print_status "The application will:"
    print_status "  1. Load GTK4 resources"
    print_status "  2. Start the backend Node.js process automatically"
    print_status "  3. Connect to WhatsApp and show QR code"
    print_status "  4. Display the main interface"
    echo
    print_warning "To stop the application, close the window or press Ctrl+C"
    echo
    
    # Launch Karere
    python3 ../src/karere/main.py
}

# Function to show post-run information
show_info() {
    if [[ "$BUILD_ONLY" == true ]]; then
        print_success "Build completed! You can now run Karere with:"
        echo "  cd $BUILD_DIR"
        echo "  python3 ../src/karere/main.py"
        return
    fi
    
    print_success "Karere development session ended"
    print_status "Logs and data are stored in:"
    print_status "  Backend logs: $PROJECT_ROOT/backend/logs/"
    print_status "  Database: $PROJECT_ROOT/backend/data/karere.db"
    print_status "  WhatsApp auth: $PROJECT_ROOT/backend/auth_info_baileys/"
}

# Main execution
main() {
    print_success "🚀 Karere Development Launcher"
    echo
    
    # Check dependencies
    check_dependencies
    
    # Setup build environment
    setup_build
    
    # Check backend dependencies
    check_backend_deps
    
    # Run Karere
    run_karere
    
    # Show information
    show_info
}

# Handle Ctrl+C gracefully
trap 'echo; print_warning "Development session interrupted"; show_info; exit 0' INT

# Run main function
main "$@"
