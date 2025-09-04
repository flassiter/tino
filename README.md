# Tino - Terminal Interactive Nano-like Organizer

A modern TUI (Terminal User Interface) editor optimized for markdown documentation with secondary support for configuration files and scripts. Tino is designed as a better alternative to nano for developers who write documentation in markdown and need quick, efficient editing of Python scripts and config files.

## Features

### Phase 0 (Core Infrastructure) - ✅ Complete
- **Event-Driven Architecture**: Robust event bus system for component communication
- **Component Registry**: Dependency injection and lifecycle management
- **Comprehensive Logging**: Structured logging with file rotation and platform-specific directories
- **Abstract Interfaces**: Well-defined contracts for swappable implementations
- **Type Safety**: Full type hints throughout the codebase

### Planned Features (Future Phases)
- **Markdown-First Editing**: Live preview with synchronized scrolling
- **Fast File Switching**: Quick recent files access (Ctrl+Tab, Ctrl+R)
- **Syntax Highlighting**: Support for Markdown, Python, JSON, YAML
- **Command System**: Extensible command pattern with keybinding customization
- **Search & Replace**: Fast text search with highlighting
- **Cross-Platform**: Consistent experience on Windows Terminal and Linux

## Core Principles

- **Single-File Focus**: One file at a time, done well
- **Markdown-First**: Optimized for markdown authoring with live preview
- **Windows-Friendly**: Familiar keyboard shortcuts (Ctrl+C, Ctrl+V, Ctrl+S)
- **Simple but Powerful**: More capable than nano, simpler than an IDE
- **Component-Based**: Modular architecture for maintainability and testing

## Requirements

- Python 3.12+
- Dependencies:
  - textual>=0.70.0
  - mistune>=3.0.0
  - platformdirs>=4.0.0
  - chardet>=5.0.0
  - pygments>=2.17.0

## Installation

### From Source (Development)

```bash
git clone https://github.com/your-org/tino.git
cd tino
pip install -e .[dev]
```

### PyPI (Future)

```bash
pip install tino
```

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -e .[dev]

# Run tests
make test

# Run tests with coverage
make coverage

# Format code
make format

# Lint code
make lint

# Clean build artifacts
make clean
```

### Testing

The project uses pytest with comprehensive test coverage:

```bash
# Run all tests
pytest

# Run specific test module
pytest tests/unit/core/test_event_bus.py

# Run with coverage report
pytest --cov=src/tino --cov-report=html
```

## Architecture

Tino is built using a component-based architecture with the following key patterns:

- **Event Bus**: Components communicate through events, avoiding direct dependencies
- **Dependency Injection**: Components receive their dependencies through constructors
- **Command Pattern**: All user actions are implemented as commands with undo/redo support
- **Abstract Interfaces**: Clear contracts allow for component swapping and testing

### Core Components

1. **Event Bus System**: Centralized communication hub with async support
2. **Component Registry**: Manages component lifecycle and dependency resolution
3. **File Manager**: Handles file I/O with atomic saves and backup management
4. **Editor Component**: Text editing with undo/redo and selection management
5. **Markdown Renderer**: CommonMark + GFM table support with live preview
6. **Command System**: Extensible commands with keybinding support
7. **Search Engine**: Fast text search with replace functionality

## Project Status

### Phase 0: Core Infrastructure ✅
- Event bus system with 17 tests
- Component registry with 23 tests  
- Abstract interfaces with 11 tests
- Logging system with 25 tests
- **Total: 76 tests, all passing**

### Next Phases
- Phase 1: File Manager Component
- Phase 2: Editor Component  
- Phase 3: Markdown Renderer
- Phase 4: Command System
- Phase 5: Search Component
- Phase 6: UI Layout Manager
- Phase 7: Integration & Polish

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite and ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Built with [Textual](https://github.com/Textualize/textual) for the TUI framework
- Inspired by nano's simplicity and vim's power
- Component architecture influenced by modern software design patterns