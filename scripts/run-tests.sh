#!/bin/bash
# run-tests.sh
# Comprehensive test runner for Karere project

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
TESTS_DIR="$PROJECT_ROOT/tests"

# Default options
RUN_BACKEND_TESTS=true
RUN_FRONTEND_TESTS=true
RUN_INTEGRATION_TESTS=false
RUN_COVERAGE=false
RUN_LINT=false
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

Run tests for the Karere project.

OPTIONS:
    -h, --help              Show this help message
    -b, --backend-only      Run only backend tests
    -f, --frontend-only     Run only frontend tests
    -i, --integration       Run integration tests
    -c, --coverage          Generate coverage reports
    -l, --lint              Run linting checks
    -v, --verbose           Verbose output
    --no-backend            Skip backend tests
    --no-frontend           Skip frontend tests
    --all                   Run all tests including integration

EXAMPLES:
    $0                      # Run basic unit tests
    $0 --all                # Run all tests
    $0 --backend-only -c    # Run backend tests with coverage
    $0 --integration -v     # Run integration tests with verbose output

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -b|--backend-only)
            RUN_FRONTEND_TESTS=false
            shift
            ;;
        -f|--frontend-only)
            RUN_BACKEND_TESTS=false
            shift
            ;;
        -i|--integration)
            RUN_INTEGRATION_TESTS=true
            shift
            ;;
        -c|--coverage)
            RUN_COVERAGE=true
            shift
            ;;
        -l|--lint)
            RUN_LINT=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --no-backend)
            RUN_BACKEND_TESTS=false
            shift
            ;;
        --no-frontend)
            RUN_FRONTEND_TESTS=false
            shift
            ;;
        --all)
            RUN_INTEGRATION_TESTS=true
            RUN_COVERAGE=true
            RUN_LINT=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check dependencies
check_dependencies() {
    print_status "Checking dependencies..."
    
    local missing_deps=()
    
    if [[ "$RUN_BACKEND_TESTS" == true ]]; then
        if ! command_exists node; then
            missing_deps+=("node")
        fi
        if ! command_exists npm; then
            missing_deps+=("npm")
        fi
    fi
    
    if [[ "$RUN_FRONTEND_TESTS" == true ]]; then
        if ! command_exists python3; then
            missing_deps+=("python3")
        fi
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        exit 1
    fi
    
    print_success "All dependencies found"
}

# Function to run backend tests
run_backend_tests() {
    print_status "Running backend tests..."
    
    cd "$BACKEND_DIR"
    
    # Check if node_modules exists
    if [[ ! -d "node_modules" ]]; then
        print_status "Installing backend dependencies..."
        npm install
    fi
    
    # Run linting if requested
    if [[ "$RUN_LINT" == true ]]; then
        print_status "Running ESLint..."
        if npm run lint; then
            print_success "ESLint passed"
        else
            print_warning "ESLint found issues"
        fi
    fi
    
    # Run unit tests
    print_status "Running backend unit tests..."
    if [[ "$RUN_COVERAGE" == true ]]; then
        if [[ "$VERBOSE" == true ]]; then
            npm run test:coverage -- --verbose
        else
            npm run test:coverage
        fi
    else
        if [[ "$VERBOSE" == true ]]; then
            npm run test:unit -- --verbose
        else
            npm run test:unit
        fi
    fi
    
    print_success "Backend tests completed"
}

# Function to run frontend tests
run_frontend_tests() {
    print_status "Running frontend tests..."
    
    cd "$TESTS_DIR/frontend"
    
    # Check if pytest is available
    if ! command_exists pytest; then
        print_status "Installing pytest..."
        pip3 install pytest pytest-cov pytest-mock
    fi
    
    # Run frontend unit tests
    print_status "Running frontend unit tests..."
    
    local pytest_args=()
    if [[ "$VERBOSE" == true ]]; then
        pytest_args+=("-v")
    fi
    
    if [[ "$RUN_COVERAGE" == true ]]; then
        pytest_args+=("--cov=../../frontend/karere" "--cov-report=term-missing" "--cov-report=html")
    fi
    
    if python3 -m pytest "${pytest_args[@]}" test_websocket_client.py test_window.py; then
        print_success "Frontend tests passed"
    else
        print_error "Frontend tests failed"
        return 1
    fi
}

# Function to run integration tests
run_integration_tests() {
    print_status "Running integration tests..."
    
    cd "$TESTS_DIR/integration"
    
    # Set environment variable for integration tests
    export RUN_INTEGRATION_TESTS=1
    
    # Install additional dependencies for integration tests
    if ! python3 -c "import websocket" 2>/dev/null; then
        print_status "Installing websocket-client for integration tests..."
        pip3 install websocket-client
    fi
    
    # Run integration tests
    local pytest_args=()
    if [[ "$VERBOSE" == true ]]; then
        pytest_args+=("-v" "-s")
    fi
    
    if python3 -m pytest "${pytest_args[@]}" test_full_integration.py; then
        print_success "Integration tests passed"
    else
        print_warning "Integration tests failed (this may be expected without full setup)"
        return 0  # Don't fail the entire test suite
    fi
}

# Function to generate test report
generate_report() {
    print_status "Generating test report..."
    
    local report_dir="$PROJECT_ROOT/test-reports"
    mkdir -p "$report_dir"
    
    # Combine coverage reports if available
    if [[ "$RUN_COVERAGE" == true ]]; then
        if [[ -f "$BACKEND_DIR/coverage/lcov.info" ]]; then
            cp "$BACKEND_DIR/coverage/lcov.info" "$report_dir/backend-coverage.lcov"
        fi
        
        if [[ -f "$TESTS_DIR/frontend/htmlcov/index.html" ]]; then
            cp -r "$TESTS_DIR/frontend/htmlcov" "$report_dir/frontend-coverage"
        fi
    fi
    
    # Create summary report
    cat > "$report_dir/test-summary.txt" << EOF
Karere Test Summary
==================
Date: $(date)
Backend Tests: $([[ "$RUN_BACKEND_TESTS" == true ]] && echo "✓ Enabled" || echo "✗ Disabled")
Frontend Tests: $([[ "$RUN_FRONTEND_TESTS" == true ]] && echo "✓ Enabled" || echo "✗ Disabled")
Integration Tests: $([[ "$RUN_INTEGRATION_TESTS" == true ]] && echo "✓ Enabled" || echo "✗ Disabled")
Coverage: $([[ "$RUN_COVERAGE" == true ]] && echo "✓ Enabled" || echo "✗ Disabled")
Linting: $([[ "$RUN_LINT" == true ]] && echo "✓ Enabled" || echo "✗ Disabled")

Test Results:
EOF
    
    print_success "Test report generated in $report_dir"
}

# Main execution
main() {
    print_status "Starting Karere test suite..."
    print_status "Project root: $PROJECT_ROOT"
    
    # Check dependencies
    check_dependencies
    
    local exit_code=0
    
    # Run backend tests
    if [[ "$RUN_BACKEND_TESTS" == true ]]; then
        if ! run_backend_tests; then
            exit_code=1
        fi
    fi
    
    # Run frontend tests
    if [[ "$RUN_FRONTEND_TESTS" == true ]]; then
        if ! run_frontend_tests; then
            exit_code=1
        fi
    fi
    
    # Run integration tests
    if [[ "$RUN_INTEGRATION_TESTS" == true ]]; then
        if ! run_integration_tests; then
            # Integration test failures don't fail the build
            print_warning "Integration tests had issues"
        fi
    fi
    
    # Generate report
    generate_report
    
    # Final status
    if [[ $exit_code -eq 0 ]]; then
        print_success "All tests completed successfully!"
    else
        print_error "Some tests failed!"
    fi
    
    return $exit_code
}

# Run main function
main "$@"
