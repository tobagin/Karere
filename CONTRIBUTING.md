# Contributing to Karere

Thank you for your interest in contributing to Karere! This document provides guidelines for contributing to the project.

## 🚀 Getting Started

### Prerequisites

- Linux system with GTK4 support
- Python 3.8+ with PyGObject
- Node.js 18+ and npm
- Meson build system
- Git

### Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Karere.git
   cd Karere
   ```

2. **Install dependencies**:
   ```bash
   # System dependencies (Ubuntu/Debian)
   sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 \
                    nodejs npm meson ninja-build python3-websocket

   # Backend dependencies
   cd backend && npm install && cd ..
   ```

3. **Build the project**:
   ```bash
   meson setup builddir --buildtype=debug
   meson compile -C builddir
   ```

4. **Run in development mode**:
   ```bash
   # Terminal 1: Start backend
   cd backend && npm start

   # Terminal 2: Start frontend
   cd builddir && ./karere
   ```

## 📝 Development Guidelines

### Code Style

#### Python (Frontend)
- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Document functions and classes with docstrings
- Use meaningful variable and function names

#### JavaScript (Backend)
- Use ES6+ features and modules
- Follow consistent indentation (2 spaces)
- Use meaningful variable and function names
- Add comments for complex logic

### Commit Messages

Use conventional commit format:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `style:` for formatting changes
- `refactor:` for code refactoring
- `test:` for adding tests
- `chore:` for maintenance tasks

Example: `feat: add message search functionality`

### Branch Naming

- `feature/description` for new features
- `fix/description` for bug fixes
- `docs/description` for documentation
- `refactor/description` for refactoring

## 🧪 Testing

### Running Tests

```bash
# Backend tests (when available)
cd backend && npm test

# Frontend tests (when available)
python -m pytest tests/

# Integration tests
./scripts/run-integration-tests.sh
```

### Writing Tests

- Write unit tests for new functionality
- Include integration tests for complex features
- Test both success and error cases
- Ensure tests are deterministic and isolated

## 🐛 Reporting Issues

### Bug Reports

When reporting bugs, please include:

1. **Environment information**:
   - OS and version
   - Python version
   - Node.js version
   - GTK4 version

2. **Steps to reproduce**:
   - Clear, numbered steps
   - Expected vs actual behavior
   - Screenshots if applicable

3. **Logs**:
   - Backend logs from terminal
   - Frontend logs from terminal
   - Any error messages

### Feature Requests

For feature requests, please:

1. Check if the feature already exists or is planned
2. Describe the use case and benefits
3. Provide mockups or examples if applicable
4. Consider implementation complexity

## 🔄 Pull Request Process

1. **Create a feature branch** from `main`
2. **Make your changes** following the guidelines above
3. **Test thoroughly** on your local system
4. **Update documentation** if needed
5. **Submit a pull request** with:
   - Clear description of changes
   - Reference to related issues
   - Screenshots for UI changes
   - Test results

### Pull Request Review

- All PRs require at least one review
- Address reviewer feedback promptly
- Keep PRs focused and reasonably sized
- Ensure CI checks pass

## 📚 Documentation

### Code Documentation

- Document all public APIs
- Include usage examples
- Keep documentation up to date with code changes

### User Documentation

- Update README.md for user-facing changes
- Add troubleshooting entries for common issues
- Include screenshots for UI changes

## 🤝 Community Guidelines

- Be respectful and inclusive
- Help newcomers get started
- Share knowledge and best practices
- Focus on constructive feedback

## 📞 Getting Help

- **GitHub Discussions**: For questions and general discussion
- **GitHub Issues**: For bug reports and feature requests
- **Code Review**: For implementation feedback

## 🏆 Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes for significant contributions
- GitHub contributor graphs

Thank you for contributing to Karere! 🎉
