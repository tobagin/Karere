#!/bin/bash
# release.sh
# Automated release script for Karere

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELEASE_DIR="$PROJECT_ROOT/release"

# Default options
DRY_RUN=false
SKIP_TESTS=false
SKIP_BUILD=false
FORCE=false
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
Usage: $0 <version> [OPTIONS]

Create a new release of Karere.

ARGUMENTS:
    version                 Version number (e.g., 1.0.0, 2.1.0-beta.1)

OPTIONS:
    -h, --help              Show this help message
    -d, --dry-run           Show what would be done without making changes
    -t, --skip-tests        Skip running tests
    -b, --skip-build        Skip building packages
    -f, --force             Force release even if checks fail
    -v, --verbose           Verbose output

EXAMPLES:
    $0 1.0.0                # Create release 1.0.0
    $0 2.0.0-beta.1 --dry-run  # Preview beta release
    $0 1.1.0 --skip-tests   # Release without running tests

EOF
}

# Parse command line arguments
if [[ $# -eq 0 ]]; then
    print_error "Version number required"
    show_usage
    exit 1
fi

VERSION="$1"
shift

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -t|--skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        -b|--skip-build)
            SKIP_BUILD=true
            shift
            ;;
        -f|--force)
            FORCE=true
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

# Validate version format
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.-]+)?$ ]]; then
    print_error "Invalid version format: $VERSION"
    print_status "Expected format: X.Y.Z or X.Y.Z-suffix (e.g., 1.0.0, 2.1.0-beta.1)"
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
    
    if ! command_exists git; then
        missing_deps+=("git")
    fi
    
    if ! command_exists gh; then
        missing_deps+=("gh (GitHub CLI)")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        exit 1
    fi
    
    print_success "All dependencies found"
}

# Function to check git status
check_git_status() {
    print_status "Checking git status..."
    
    cd "$PROJECT_ROOT"
    
    # Check if we're on main branch
    local current_branch=$(git branch --show-current)
    if [[ "$current_branch" != "main" ]] && [[ "$FORCE" != true ]]; then
        print_error "Not on main branch (currently on: $current_branch)"
        print_status "Use --force to release from current branch"
        exit 1
    fi
    
    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD --; then
        if [[ "$FORCE" != true ]]; then
            print_error "Uncommitted changes detected"
            print_status "Commit or stash changes before releasing, or use --force"
            exit 1
        else
            print_warning "Uncommitted changes detected (forced)"
        fi
    fi
    
    # Check if tag already exists
    if git tag -l | grep -q "^v$VERSION$"; then
        if [[ "$FORCE" != true ]]; then
            print_error "Tag v$VERSION already exists"
            print_status "Use --force to overwrite existing tag"
            exit 1
        else
            print_warning "Tag v$VERSION already exists (will be overwritten)"
        fi
    fi
    
    print_success "Git status check passed"
}

# Function to update version in files
update_version() {
    print_status "Updating version to $VERSION..."
    
    if [[ "$DRY_RUN" == true ]]; then
        print_status "[DRY RUN] Would update version in:"
        print_status "  - meson.build"
        print_status "  - backend/package.json"
        print_status "  - frontend/data/io.github.tobagin.Karere.appdata.xml.in"
        return
    fi
    
    cd "$PROJECT_ROOT"
    
    # Update meson.build
    sed -i "s/version: '[^']*'/version: '$VERSION'/" meson.build
    
    # Update package.json
    sed -i "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/" backend/package.json
    
    # Update AppData
    local release_date=$(date +%Y-%m-%d)
    sed -i "s/<release version=\"[^\"]*\" date=\"[^\"]*\"/<release version=\"$VERSION\" date=\"$release_date\"/" frontend/data/io.github.tobagin.Karere.appdata.xml.in
    
    print_success "Version updated to $VERSION"
}

# Function to run tests
run_tests() {
    if [[ "$SKIP_TESTS" == true ]]; then
        print_warning "Skipping tests (--skip-tests)"
        return
    fi
    
    print_status "Running test suite..."
    
    if [[ "$DRY_RUN" == true ]]; then
        print_status "[DRY RUN] Would run: ./scripts/run-tests.sh --all"
        return
    fi
    
    cd "$PROJECT_ROOT"
    
    if [[ "$VERBOSE" == true ]]; then
        ./scripts/run-tests.sh --all --verbose
    else
        ./scripts/run-tests.sh --all
    fi
    
    print_success "All tests passed"
}

# Function to build packages
build_packages() {
    if [[ "$SKIP_BUILD" == true ]]; then
        print_warning "Skipping package build (--skip-build)"
        return
    fi
    
    print_status "Building release packages..."
    
    if [[ "$DRY_RUN" == true ]]; then
        print_status "[DRY RUN] Would run: ./scripts/build-packages.sh --all"
        return
    fi
    
    cd "$PROJECT_ROOT"
    
    if [[ "$VERBOSE" == true ]]; then
        ./scripts/build-packages.sh --all --verbose
    else
        ./scripts/build-packages.sh --all
    fi
    
    print_success "All packages built successfully"
}

# Function to create git tag
create_git_tag() {
    print_status "Creating git tag v$VERSION..."
    
    if [[ "$DRY_RUN" == true ]]; then
        print_status "[DRY RUN] Would create tag: v$VERSION"
        return
    fi
    
    cd "$PROJECT_ROOT"
    
    # Commit version changes
    git add meson.build backend/package.json frontend/data/io.github.tobagin.Karere.appdata.xml.in
    git commit -m "chore: bump version to $VERSION" || true  # May fail if no changes
    
    # Create tag
    if [[ "$FORCE" == true ]] && git tag -l | grep -q "^v$VERSION$"; then
        git tag -d "v$VERSION"
    fi
    
    git tag -a "v$VERSION" -m "Release version $VERSION"
    
    print_success "Git tag v$VERSION created"
}

# Function to generate changelog
generate_changelog() {
    print_status "Generating changelog..."
    
    cd "$PROJECT_ROOT"
    
    # Get previous tag
    local prev_tag=$(git describe --tags --abbrev=0 HEAD^ 2>/dev/null || echo "")
    
    if [[ -z "$prev_tag" ]]; then
        print_warning "No previous tag found, generating full changelog"
        local commit_range="HEAD"
    else
        local commit_range="$prev_tag..HEAD"
    fi
    
    # Generate changelog
    local changelog_file="$RELEASE_DIR/CHANGELOG-$VERSION.md"
    mkdir -p "$RELEASE_DIR"
    
    cat > "$changelog_file" << EOF
# Changelog for Karere $VERSION

## Changes since ${prev_tag:-"initial commit"}

### Features
$(git log $commit_range --oneline --grep="^feat" --pretty="- %s" || echo "- No new features")

### Bug Fixes
$(git log $commit_range --oneline --grep="^fix" --pretty="- %s" || echo "- No bug fixes")

### Documentation
$(git log $commit_range --oneline --grep="^docs" --pretty="- %s" || echo "- No documentation changes")

### Other Changes
$(git log $commit_range --oneline --grep="^chore\|^refactor\|^test" --pretty="- %s" || echo "- No other changes")

## Full Commit History
$(git log $commit_range --oneline --pretty="- %h %s")

---
Released on $(date +"%Y-%m-%d")
EOF
    
    print_success "Changelog generated: $changelog_file"
}

# Function to create GitHub release
create_github_release() {
    print_status "Creating GitHub release..."
    
    if [[ "$DRY_RUN" == true ]]; then
        print_status "[DRY RUN] Would create GitHub release for v$VERSION"
        return
    fi
    
    cd "$PROJECT_ROOT"
    
    # Push tag to remote
    git push origin "v$VERSION"
    
    # Create release with GitHub CLI
    local changelog_file="$RELEASE_DIR/CHANGELOG-$VERSION.md"
    local release_notes=""
    
    if [[ -f "$changelog_file" ]]; then
        release_notes="--notes-file $changelog_file"
    else
        release_notes="--generate-notes"
    fi
    
    # Determine if this is a prerelease
    local prerelease_flag=""
    if [[ "$VERSION" =~ -[a-zA-Z] ]]; then
        prerelease_flag="--prerelease"
    fi
    
    gh release create "v$VERSION" \
        --title "Karere $VERSION" \
        $release_notes \
        $prerelease_flag \
        dist/* || true  # May fail if no dist files
    
    print_success "GitHub release created: https://github.com/tobagin/Karere/releases/tag/v$VERSION"
}

# Function to cleanup
cleanup() {
    print_status "Cleaning up temporary files..."
    
    if [[ "$DRY_RUN" == true ]]; then
        print_status "[DRY RUN] Would clean up temporary files"
        return
    fi
    
    # Clean up build artifacts if desired
    # rm -rf build-packages dist
    
    print_success "Cleanup completed"
}

# Main execution
main() {
    print_status "Starting release process for Karere v$VERSION"
    
    if [[ "$DRY_RUN" == true ]]; then
        print_warning "DRY RUN MODE - No changes will be made"
    fi
    
    # Check dependencies
    check_dependencies
    
    # Check git status
    check_git_status
    
    # Update version
    update_version
    
    # Run tests
    run_tests
    
    # Build packages
    build_packages
    
    # Create git tag
    create_git_tag
    
    # Generate changelog
    generate_changelog
    
    # Create GitHub release
    create_github_release
    
    # Cleanup
    cleanup
    
    # Final status
    if [[ "$DRY_RUN" == true ]]; then
        print_success "Dry run completed successfully!"
        print_status "Run without --dry-run to perform the actual release"
    else
        print_success "Release v$VERSION completed successfully!"
        print_status "Release available at: https://github.com/tobagin/Karere/releases/tag/v$VERSION"
    fi
}

# Run main function
main "$@"
