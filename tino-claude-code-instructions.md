# Tino Editor - Claude Code Development Instructions

## Overview
This document provides phase-by-phase instructions for building the Tino TUI editor using Claude Code. Each phase includes specific prompts, expected deliverables, and testing requirements.

**IMPORTANT**: Always refer to the accompanying `tino-requirements.md` document for detailed architectural decisions and component specifications.

## MVP Simplifications
To reduce complexity while maintaining a strong foundation, the MVP excludes:
- File watching for external changes
- Macro recording/playback
- Multi-file search
- Regex search (initially)
- Advanced markdown features (Mermaid, LaTeX, YAML frontmatter)
- Multiple export formats (only HTML for now)
- Menu bar and file tree
- Extended file type support (just Markdown, Python, JSON, YAML)

These can be added later without architectural changes due to the component-based design.

---

## Initial Setup Prompt

```
Create a new Python project called 'tino' with the following structure:
- Use Python 3.12+ with type hints throughout
- Set up a proper package structure with src/tino/ directory
- Initialize with pyproject.toml using modern Python packaging
- Add pytest for testing with coverage configuration
- Create a Makefile with common commands (test, run, lint, format)
- Use black for formatting and ruff for linting
- Add a comprehensive .gitignore for Python projects
- Create README.md with project description and setup instructions
- Add MIT LICENSE file

The project should follow these architectural principles:
1. Component-based architecture with clear interfaces
2. Event-driven communication between components
3. Dependency injection for testability
4. Abstract interfaces for swappable implementations

Create the initial directory structure but don't implement any functionality yet.
```

---

## Phase 0: Core Infrastructure (Week 1)

### Prompt for Phase 0

```
Implement the core infrastructure for the tino editor with these components:

1. Create an event bus system in src/tino/core/events/:
   - EventBus class with subscribe/unsubscribe/emit methods
   - Event base class with timestamp and source
   - Type-safe event definitions (TextChangedEvent, FileOpenedEvent, etc.)
   - Async event support for non-blocking operations

2. Create base interfaces in src/tino/core/interfaces/:
   - IEditor interface with methods: get_content, set_content, insert_text, delete_range, get_selection, set_selection, undo, redo
   - IFileManager interface with methods: open_file, save_file, create_backup, get_encoding, watch_file
   - IRenderer interface with methods: render_html, render_preview, get_outline, validate
   - ICommand interface with methods: execute, undo, can_execute

3. Create a component registry in src/tino/core/registry.py:
   - ComponentRegistry class to manage component lifecycle
   - Dependency injection container
   - Component initialization order resolution

4. Set up logging in src/tino/core/logging.py:
   - Structured logging with proper levels
   - Rotating file handler
   - Platform-specific log directories using platformdirs

5. Create comprehensive tests for each component:
   - Event bus message delivery and filtering
   - Registry component management
   - Interface contract tests
   - Logging configuration

Deliverables:
- All core infrastructure components
- 100% test coverage for core components
- Type hints on all methods
- Documentation strings for all public APIs
```

### Expected Deliverables (Phase 0)
- [ ] `src/tino/core/events/bus.py` - Event bus implementation
- [ ] `src/tino/core/events/types.py` - Event type definitions
- [ ] `src/tino/core/interfaces/*.py` - All interface definitions
- [ ] `src/tino/core/registry.py` - Component registry
- [ ] `src/tino/core/logging.py` - Logging setup
- [ ] `tests/unit/core/test_event_bus.py` - Event bus tests
- [ ] `tests/unit/core/test_registry.py` - Registry tests
- [ ] `tests/unit/core/test_interfaces.py` - Interface contract tests

### Manual Test Checklist (Phase 0)
- [ ] Run `make test` - all tests pass
- [ ] Run `make coverage` - 100% coverage for core/
- [ ] Run `python -m tino.core.registry` - demonstrates component registration
- [ ] Check logs are created in correct platform directory

---

## Phase 1: File Manager Component (Week 2)

### Prompt for Phase 1

```
Implement the FileManager component with these features:

1. Create FileManager class implementing IFileManager in src/tino/components/file_manager/:
   - Atomic file saves (write to temp file, then rename)
   - Automatic backup creation (.tino.bak) on first modification
   - Encoding detection using chardet library
   - Cross-platform path handling
   - Recent files tracking (last 30 files)
   - Cursor position memory per file (in session only)

2. Create supporting classes:
   - BackupManager for backup file handling (single backup per file)
   - EncodingDetector for robust encoding detection
   - RecentFilesManager for managing recent file history
   - CursorMemory for tracking last cursor position per file

3. Handle edge cases:
   - Large files (>50MB) with warnings
   - Binary file detection and rejection
   - Permission errors with helpful messages
   - Network drive handling

4. Create comprehensive tests:
   - Mock filesystem for unit tests
   - Real filesystem integration tests
   - Cross-platform path handling tests
   - Backup creation and recovery tests
   - Recent files list management tests

5. Create a CLI tool for testing:
   - Simple script to test file operations
   - Demonstrate backup functionality
   - Show recent files list

Deliverables:
- Complete FileManager implementation
- Mock FileManager for testing other components
- Recent files with Ctrl+Tab (last file) support
- 95% test coverage
- CLI demonstration script
```

### Expected Deliverables (Phase 1)
- [ ] `src/tino/components/file_manager/file_manager.py` - Main implementation
- [ ] `src/tino/components/file_manager/backup_manager.py` - Backup handling
- [ ] `src/tino/components/file_manager/encoding_detector.py` - Encoding detection
- [ ] `src/tino/components/file_manager/recent_files.py` - Recent files tracking
- [ ] `src/tino/components/file_manager/cursor_memory.py` - Cursor position tracking
- [ ] `src/tino/components/file_manager/mock.py` - Mock implementation
- [ ] `tests/unit/components/test_file_manager.py` - Unit tests
- [ ] `tests/integration/test_file_operations.py` - Integration tests
- [ ] `scripts/test_file_manager.py` - CLI test script

### Manual Test Checklist (Phase 1)
- [ ] Create and save a new file
- [ ] Open and modify an existing file
- [ ] Verify backup file creation (only one .tino.bak)
- [ ] Test with UTF-8, UTF-16, and ASCII files
- [ ] Test recent files list maintains order
- [ ] Verify cursor position is remembered when reopening

---

## Phase 2: Editor Component (Week 3)

### Prompt for Phase 2

```
Implement the EditorComponent with Textual TextArea widget:

1. Create EditorComponent implementing IEditor in src/tino/components/editor/:
   - Wrapper around Textual's TextArea widget
   - Full implementation of IEditor interface
   - Undo/redo stack with 100-operation history
   - Selection management and cursor tracking
   - Emit events on text changes via event bus

2. Create supporting functionality:
   - UndoStack class for managing history
   - SelectionManager for selection operations
   - CursorTracker for position management
   - TextMetrics for line/column/word count

3. Create MockEditor for testing:
   - Implements same IEditor interface
   - Simulates all editor operations
   - Maintains operation history for verification
   - No UI dependencies

4. Build a minimal Textual app for testing:
   - Simple TUI with just the editor
   - File open/save functionality
   - Display cursor position and file status
   - Test all keyboard shortcuts

5. Comprehensive testing:
   - Unit tests with MockEditor
   - Integration tests with FileManager
   - Undo/redo edge cases
   - Selection operations
   - Event emission verification

Deliverables:
- Complete EditorComponent implementation
- MockEditor for testing
- Minimal working text editor app
- Keyboard shortcut verification
- 90% test coverage
```

### Expected Deliverables (Phase 2)
- [ ] `src/tino/components/editor/editor_component.py` - Main implementation
- [ ] `src/tino/components/editor/undo_stack.py` - Undo/redo management
- [ ] `src/tino/components/editor/selection_manager.py` - Selection handling
- [ ] `src/tino/components/editor/mock.py` - Mock implementation
- [ ] `src/tino/ui/minimal_app.py` - Minimal Textual application
- [ ] `tests/unit/components/test_editor.py` - Unit tests
- [ ] `tests/integration/test_editor_file_integration.py` - Integration tests

### Manual Test Checklist (Phase 2)
- [ ] Type and edit text in the minimal app
- [ ] Undo/redo operations (Ctrl+Z/Y)
- [ ] Select text with keyboard (Shift+arrows)
- [ ] Save file (Ctrl+S)
- [ ] Open existing file
- [ ] Verify status bar shows correct line/column

---

## Phase 3: Markdown Renderer Component (Week 4)

### Prompt for Phase 3

```
Implement the MarkdownRenderer component using mistune:

1. Create MarkdownRenderer implementing IRenderer in src/tino/components/renderer/:
   - Use mistune 3.x for parsing
   - Support CommonMark + GitHub Flavored Markdown tables
   - Generate HTML for preview
   - Extract document outline from headings
   - Basic link validation (check if local files exist)
   - Cache rendered content for performance

2. Create preview widget integration:
   - Textual Markdown widget wrapper
   - Synchronized scrolling support
   - Theme-aware rendering
   - Outline/TOC panel

3. Implement core features:
   - Table of contents generator
   - Heading hierarchy analyzer
   - Local file link validator
   - HTML export for copy/paste

4. Performance optimizations:
   - Render caching with invalidation
   - Debounced preview updates (50ms)
   - Efficient diff rendering

5. Build preview integration:
   - Split-pane editor with live preview
   - Synchronized scrolling
   - Resizable panes
   - HTML export functionality

Deliverables:
- Complete MarkdownRenderer implementation
- Working split-pane preview
- Link validation for local files
- HTML export functionality
- Performance under 50ms update time
```

### Expected Deliverables (Phase 3)
- [ ] `src/tino/components/renderer/markdown_renderer.py` - Main implementation
- [ ] `src/tino/components/renderer/link_validator.py` - Local file link checking
- [ ] `src/tino/components/renderer/outline_extractor.py` - TOC generation
- [ ] `src/tino/components/renderer/cache.py` - Render caching
- [ ] `src/tino/ui/preview_app.py` - Editor with preview
- [ ] `tests/unit/components/test_renderer.py` - Unit tests
- [ ] `benchmarks/render_performance.py` - Performance tests

### Manual Test Checklist (Phase 3)
- [ ] Preview updates as you type
- [ ] Scrolling syncs between panes
- [ ] CommonMark elements render correctly
- [ ] Tables render properly
- [ ] Local file links are validated
- [ ] Export produces valid HTML
- [ ] Large document (>1000 lines) performs well

---

## Phase 4: Command System Component (Week 5)

### Prompt for Phase 4

```
Implement the Command System for all user actions:

1. Create Command System in src/tino/components/commands/:
   - Command pattern implementation
   - Command registry with name-based lookup
   - Keybinding manager with customization
   - Command palette backend
   - Quick file switching (Ctrl+Tab for last file, Ctrl+R for recent files)

2. Implement core commands:
   - File commands (New, Open, Save, SaveAs, Recent, LastFile)
   - Edit commands (Cut, Copy, Paste, Undo, Redo, DuplicateLine)
   - Format commands (Bold, Italic, Link, Code)
   - Navigation commands (Find, Replace, GoToLine)
   - View commands (TogglePreview, ToggleLineNumbers)

3. Keybinding system:
   - Default Windows-standard bindings
   - User customization via config
   - Conflict detection and resolution
   - Ctrl+Tab for quick last-file switching
   - Ctrl+R for recent files list

4. Command palette:
   - Simple search for commands
   - Recent commands tracking
   - Command categories
   - Keyboard-only navigation

5. Testing framework:
   - Command execution verification
   - Undo/redo for all commands
   - Keybinding trigger tests
   - Recent files navigation tests
   - Command palette interaction tests

Deliverables:
- Complete command system
- All editor commands implemented
- Working command palette
- Quick file switching (Ctrl+Tab, Ctrl+R)
- Keybinding customization
```

### Expected Deliverables (Phase 4)
- [ ] `src/tino/components/commands/command_base.py` - Base classes
- [ ] `src/tino/components/commands/registry.py` - Command registry
- [ ] `src/tino/components/commands/keybindings.py` - Keybinding manager
- [ ] `src/tino/components/commands/file_commands.py` - File operations
- [ ] `src/tino/components/commands/edit_commands.py` - Edit operations
- [ ] `src/tino/components/commands/format_commands.py` - Markdown formatting
- [ ] `src/tino/ui/command_palette.py` - Command palette UI
- [ ] `src/tino/ui/recent_files_dialog.py` - Recent files list UI
- [ ] `tests/unit/components/test_commands.py` - Unit tests

### Manual Test Checklist (Phase 4)
- [ ] All keyboard shortcuts work (Ctrl+S, Ctrl+B, etc.)
- [ ] Ctrl+Tab switches to last file instantly
- [ ] Ctrl+R opens recent files list
- [ ] Command palette opens with Ctrl+Shift+P
- [ ] Custom keybindings override defaults
- [ ] Undo works for all commands

---

## Phase 5: Search Component (Week 6)

### Prompt for Phase 5

```
Implement the Search Engine component for current file only:

1. Create SearchEngine in src/tino/components/search/:
   - Text search with literal strings (no regex initially)
   - Case sensitive/insensitive options
   - Whole word matching option
   - Find next/previous navigation
   - Replace with preview and confirmation
   - Search history (last 10 searches)

2. Core search features:
   - Find all occurrences with highlighting
   - Incremental search (search as you type)
   - Wrap around at document end
   - Match counter in status bar
   - Search in selection only option

3. UI Integration:
   - Search bar widget (bottom of screen, like nano)
   - Replace bar with preview
   - Highlight all matches in editor
   - Current match indicator
   - Match counter (e.g., "3 of 15 matches")

4. Performance optimizations:
   - Efficient string searching algorithm
   - Cached search results
   - Debounced incremental search
   - Fast highlighting updates

5. Testing:
   - Search accuracy tests
   - Case sensitivity tests
   - Whole word boundary detection
   - Replace operation verification
   - Search history persistence

Deliverables:
- Complete search implementation for current file
- Search and replace UI
- Search highlighting
- Search history
- Performance benchmarks
```

### Expected Deliverables (Phase 5)
- [ ] `src/tino/components/search/search_engine.py` - Main implementation
- [ ] `src/tino/components/search/text_finder.py` - String search algorithms
- [ ] `src/tino/components/search/search_history.py` - History management
- [ ] `src/tino/ui/search_bar.py` - Search UI widget
- [ ] `tests/unit/components/test_search.py` - Unit tests
- [ ] `benchmarks/search_performance.py` - Performance tests

### Manual Test Checklist (Phase 5)
- [ ] Find text with Ctrl+F
- [ ] Navigate results with F3/Shift+F3
- [ ] Replace single and all occurrences
- [ ] Case sensitive toggle works
- [ ] Whole word search works
- [ ] Search wraps at document end
- [ ] Search history persists

---

## Phase 6: UI Layout Manager (Week 7)

### Prompt for Phase 6

```
Implement the UI Layout Manager for a minimal but complete interface:

1. Create LayoutManager in src/tino/ui/:
   - Split-pane management (editor and preview)
   - Pane resizing with keyboard (Ctrl+< and Ctrl+>)
   - Layout persistence between sessions
   - Preview pane toggle (F2)
   - Responsive to terminal resize

2. Essential UI Components:
   - Status bar with file info, cursor position, match counter
   - Markdown outline panel (collapsible)
   - Recent files dialog (Ctrl+R)
   - Simple notification system (save confirmations, errors)
   - Search bar at bottom (nano-style)

3. Theme System:
   - Dark theme (default)
   - Light theme
   - Apply to editor, preview, and UI components
   - Persist theme selection

4. Mouse Support:
   - Click to position cursor
   - Drag to select text
   - Scroll wheel support
   - Pane splitter dragging (if terminal supports)

5. Responsive Design:
   - Minimum terminal size detection (80x24)
   - Graceful degradation for small terminals
   - Hide preview if terminal too narrow
   - Adjust layout for terminal resize

Deliverables:
- Complete layout system
- Status bar and outline panel
- Recent files dialog
- Theme switching (dark/light)
- Basic mouse support
```

### Expected Deliverables (Phase 6)
- [ ] `src/tino/ui/layout_manager.py` - Layout orchestration
- [ ] `src/tino/ui/status_bar.py` - Status bar widget
- [ ] `src/tino/ui/outline_panel.py` - Markdown outline
- [ ] `src/tino/ui/recent_files_dialog.py` - Recent files UI
- [ ] `src/tino/ui/themes.py` - Dark and light themes
- [ ] `src/tino/ui/notifications.py` - Toast notifications
- [ ] `tests/integration/test_ui_layout.py` - UI tests

### Manual Test Checklist (Phase 6)
- [ ] F2 toggles preview pane
- [ ] Ctrl+< and Ctrl+> resize panes
- [ ] Status bar shows correct info
- [ ] Outline panel shows document structure
- [ ] Ctrl+R opens recent files dialog
- [ ] Theme switch persists after restart
- [ ] Layout adjusts to terminal resize

---

## Phase 7: Integration & Polish (Week 8)

### Prompt for Phase 7

```
Complete the integration and add essential file type support:

1. Full Integration:
   - Wire all components through event bus
   - Implement configuration system (TOML)
   - Add settings UI (Ctrl+,)
   - Add simple help screen (F1)
   - Ensure all components work together

2. Configuration System:
   - Load/save user preferences
   - Custom keybindings in config.toml
   - Theme preference
   - Editor settings (tab size, word wrap)
   - Markdown preview settings

3. Essential File Type Support:
   - Markdown (.md) - full support with preview
   - Python (.py) - syntax highlighting only
   - JSON (.json) - syntax highlighting and basic validation
   - YAML (.yaml) - syntax highlighting and basic validation
   - Plain text (.txt) - basic editing

4. Performance Optimization:
   - Profile and optimize startup time (<200ms)
   - Ensure smooth typing (no lag)
   - Optimize preview updates (<50ms)
   - Memory usage under 75MB

5. Distribution:
   - PyInstaller executable for Windows
   - Simple install script for Linux
   - PyPI package preparation
   - Basic user documentation (README)
   - Keyboard shortcut reference card

6. Final Testing:
   - Complete editing workflow test
   - All keyboard shortcuts work
   - Cross-platform testing (Windows Terminal, Ubuntu)
   - No memory leaks
   - Stress test with 10MB markdown file

Deliverables:
- Complete, integrated application
- Configuration system working
- 4 file types supported
- Distributable packages
- Basic documentation
```

### Expected Deliverables (Phase 7)
- [ ] `src/tino/app.py` - Main application
- [ ] `src/tino/config/settings.py` - Configuration management
- [ ] `src/tino/config/defaults.toml` - Default settings
- [ ] `src/tino/syntax/` - Syntax highlighting for 4 file types
- [ ] `src/tino/ui/settings_dialog.py` - Settings UI
- [ ] `src/tino/ui/help_screen.py` - Help screen
- [ ] `dist/` - Distribution packages
- [ ] `README.md` - User documentation
- [ ] `SHORTCUTS.md` - Keyboard reference
- [ ] `tests/system/` - System tests

### Manual Test Checklist (Phase 7)
- [ ] Create, edit, save markdown document
- [ ] Preview updates live while typing
- [ ] All shortcuts work as documented
- [ ] Settings persist between sessions
- [ ] Python files highlight correctly
- [ ] JSON validation catches errors
- [ ] Application starts in <200ms
- [ ] No lag while typing
- [ ] Works on both Windows and Linux

---

## Testing Strategy for Each Phase

### Unit Testing Requirements
- Minimum 90% code coverage per component
- All public methods have tests
- Edge cases are covered
- Mock implementations are tested against interfaces

### Integration Testing Requirements
- Component pairs work together
- Event bus communication is verified
- No circular dependencies
- Performance meets requirements

### Manual Testing Requirements
- Core functionality works as expected
- Keyboard shortcuts are responsive
- UI updates correctly
- No data loss scenarios

### Test File Naming Convention
```
tests/
├── unit/
│   ├── components/
│   │   └── test_{component_name}.py
│   └── core/
│       └── test_{module_name}.py
├── integration/
│   └── test_{feature}_integration.py
└── system/
    └── test_{workflow}.py
```

---

## Common Development Commands

Add these to your Makefile:

```makefile
.PHONY: test coverage run lint format clean

test:
	pytest tests/ -v

coverage:
	pytest tests/ --cov=src/tino --cov-report=html --cov-report=term

run:
	python -m tino

lint:
	ruff check src/ tests/

format:
	black src/ tests/
	ruff check src/ tests/ --fix

clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
```

---

## Progress Tracking

Create a `PROGRESS.md` file to track completion:

```markdown
# Tino Development Progress

## Phase 0: Core Infrastructure ⬜
- [ ] Event Bus System
- [ ] Base Interfaces
- [ ] Component Registry
- [ ] Logging System
- [ ] Tests (0% coverage)

## Phase 1: File Manager ⬜
- [ ] FileManager Implementation
- [ ] Backup System
- [ ] Encoding Detection
- [ ] Tests (0% coverage)

[Continue for all phases...]
```

---

## Troubleshooting Guide

### Common Issues and Solutions

1. **Import Errors**
   - Ensure `src/` is in PYTHONPATH
   - Use absolute imports: `from tino.core.events import EventBus`

2. **Textual Widget Issues**
   - Check Textual version compatibility
   - Test in different terminals
   - Use Textual's debug mode

3. **Performance Problems**
   - Profile with cProfile
   - Check event bus for excessive messages
   - Verify caching is working

4. **Test Failures**
   - Check mock/real implementation parity
   - Verify event subscriptions
   - Check for race conditions

---

## Code Review Checklist

Before completing each phase:

- [ ] All tests pass
- [ ] Coverage meets requirements (90%+)
- [ ] Type hints on all functions
- [ ] Docstrings on public APIs
- [ ] No circular dependencies
- [ ] Interfaces are properly implemented
- [ ] Mock and real implementations match
- [ ] Performance benchmarks pass
- [ ] Manual testing completed
- [ ] Code is formatted (black/ruff)

---

## Notes for Claude Code

When implementing each phase:

1. **Start with tests** - Write the test first, then implement
2. **Use type hints** - Every function should have type annotations
3. **Follow interfaces strictly** - Don't add methods not in the interface
4. **Event-driven** - Components communicate via events, not direct calls
5. **Keep components isolated** - Each should work independently
6. **Document edge cases** - Note any limitations or assumptions
7. **Performance matters** - Profile if something feels slow
8. **Cross-platform** - Test path handling on both Windows and Linux styles

Remember: The goal is a fast, reliable markdown editor that's better than nano for documentation work!