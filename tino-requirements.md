# Tino TUI Editor - Requirements & Implementation Plan
**Version:** 3.0  
**Last Updated:** August 28, 2025  
**Project Name:** tino (Terminal Interactive Nano-like Organizer)

## 1. Executive Summary & Vision

Tino is a modern, single-file TUI editor optimized for markdown documentation with secondary support for configuration files and scripts. It's designed as a better alternative to nano for developers who write documentation in markdown and need quick, efficient editing of Python scripts and config files.

### Primary Use Case
**Markdown Documentation** - Creating, editing, and previewing markdown files with live preview and essential formatting tools.

### Secondary Use Case  
**Configuration & Scripts** - Quick edits to Python scripts, JSON/YAML configuration files with syntax highlighting.

### Core Principles
- **Single-File Focus**: One file at a time, done well
- **Markdown-First**: Optimized for markdown authoring with live preview
- **Fast File Switching**: Quick recent files access (Ctrl+Tab, Ctrl+R)
- **Edit From Start**: Full editing capability from Phase 1
- **Cross-Platform**: Consistent experience on Windows Terminal and Linux
- **Windows-Friendly**: Familiar keyboard shortcuts (Ctrl+C, Ctrl+V, Ctrl+S)
- **Simple but Powerful**: More capable than nano, simpler than an IDE

### MVP Scope
The MVP focuses on essential features while maintaining a strong architectural foundation for future enhancements. Complex features like file watching, macros, regex search, and advanced markdown are deferred to keep initial complexity manageable.

---

## 2. Technical Architecture

### 2.1 Component-Based Architecture

The application is built using loosely coupled, independently testable components with clear interfaces. Each component can be developed, tested, and potentially replaced independently.

```python
# Example component structure
tino/
├── core/
│   ├── interfaces/          # Abstract base classes
│   │   ├── editor.py        # IEditor interface
│   │   ├── renderer.py      # IRenderer interface
│   │   ├── file_manager.py  # IFileManager interface
│   │   └── command.py       # ICommand interface
│   ├── events/              # Event system
│   │   ├── bus.py          # Event bus for component communication
│   │   └── types.py        # Event type definitions
│   └── registry.py         # Component registry
├── components/
│   ├── editor/             # Editor component
│   │   ├── text_editor.py  # TextArea implementation
│   │   └── mock_editor.py  # Mock for testing
│   ├── preview/            # Preview component
│   │   ├── markdown_preview.py
│   │   └── html_exporter.py
│   ├── file_manager/       # File operations
│   │   ├── file_handler.py
│   │   └── backup_manager.py
│   ├── syntax/             # Syntax highlighting
│   │   ├── highlighter.py
│   │   └── language_detector.py
│   ├── search/             # Search & navigation
│   │   ├── text_search.py
│   │   └── outline_builder.py
│   ├── commands/           # Command system
│   │   ├── command_registry.py
│   │   └── keybinding_manager.py
│   └── config/             # Configuration
│       ├── settings_manager.py
│       └── theme_manager.py
├── ui/
│   ├── layout_manager.py   # UI layout orchestration
│   ├── status_bar.py       # Status bar widget
│   └── dialogs/            # Dialog components
└── app.py                  # Main application orchestrator
```

### 2.2 Core Components & Interfaces

| Component | Interface | Default Implementation | Abstraction Benefit |
|-----------|-----------|----------------------|-------------------|
| **Editor** | `IEditor` | TextArea wrapper | Can swap to different editor widget |
| **Markdown Renderer** | `IRenderer` | mistune 3.x | Can change parser without affecting app |
| **File Manager** | `IFileManager` | PathLib-based | Can add cloud storage, version control |
| **Syntax Highlighter** | `IHighlighter` | Pygments wrapper | Can swap highlighting engine |
| **Search Engine** | `ISearchEngine` | Regex-based | Can upgrade to fuzzy search, indexing |
| **Command System** | `ICommand` | Command pattern | Supports undo/redo, macros |
| **Config Manager** | `IConfigManager` | TOML-based | Can change config format |
| **Export System** | `IExporter` | Format-specific | Pluggable export formats |

### 2.3 Component Communication

Components communicate through an event bus, avoiding direct dependencies:

```python
# Example: Editor notifies preview of changes
class EditorComponent:
    def on_text_change(self):
        self.event_bus.emit(TextChangedEvent(self.get_content()))

class PreviewComponent:
    def __init__(self):
        self.event_bus.subscribe(TextChangedEvent, self.update_preview)
```

### 2.4 Technology Stack

| Layer | Technology | Abstracted Via |
|-------|------------|----------------|
| **UI Framework** | Textual 0.70+ | Layout Manager interface |
| **Editor Widget** | textual.widgets.TextArea | IEditor interface |
| **Markdown Parser** | mistune 3.x | IRenderer interface |
| **Syntax Highlighting** | Pygments 2.x | IHighlighter interface |
| **Configuration** | TOML + platformdirs | IConfigManager interface |
| **Testing** | pytest + unittest.mock | Component mocks |
| **Packaging** | PyInstaller | Build scripts |

### 2.5 Performance Requirements

- **Startup Time**: < 200ms (lazy load components)
- **Preview Update**: < 50ms (debounced rendering)
- **Component Init**: < 10ms per component
- **Memory per Component**: < 10MB
- **File Operations**: Async where possible

---

## 3. Implementation Phases (Component-Based)

### Phase 0: Core Infrastructure (Week 1)
**Goal**: Foundation with event system and component registry

#### Components to Build:
- [ ] **Event Bus System** - Central communication hub
- [ ] **Component Registry** - Component lifecycle management
- [ ] **Base Interfaces** - IEditor, IFileManager, IRenderer
- [ ] **Logging System** - Structured logging with levels
- [ ] **Test Infrastructure** - pytest, mocks, fixtures

#### Integration Tests:
1. **T0.1**: Event bus delivers messages between components
2. **T0.2**: Component registry loads/unloads components
3. **T0.3**: Mock components work with real interfaces
4. **T0.4**: Logging captures component interactions

### Phase 1: File Manager Component (Week 2)
**Goal**: File operations with backup and recent files tracking

#### Component: FileManager
```python
class IFileManager(ABC):
    def open_file(path: Path) -> str
    def save_file(path: Path, content: str) -> bool
    def create_backup(path: Path) -> bool
    def get_encoding(path: Path) -> str
    def add_recent_file(path: Path) -> None
    def get_recent_files() -> List[Path]
    def get_last_file() -> Optional[Path]
```

#### Deliverables:
- [ ] **FM-101**: Atomic file saves (write temp, rename)
- [ ] **FM-102**: Auto-backup manager (.tino.bak on first edit)
- [ ] **FM-103**: Encoding detection (UTF-8, UTF-16, ASCII)
- [ ] **FM-104**: Path normalization (Windows/Linux)
- [ ] **FM-105**: Recent files tracker (30 files max)
- [ ] **FM-106**: Cursor position memory per file (in session)

#### Unit Tests:
1. **T1.1**: Atomic save prevents corruption on interrupt
2. **T1.2**: Backup created only on first change
3. **T1.3**: Correct encoding detection and preservation
4. **T1.4**: Path handling works cross-platform
5. **T1.5**: Recent files list maintains order and max size

---

### Phase 2: Editor Component (Week 3)
**Goal**: Abstracted editor with full editing capabilities

#### Component: EditorComponent
```python
class IEditor(ABC):
    def get_content() -> str
    def set_content(text: str)
    def insert_text(position: int, text: str)
    def delete_range(start: int, end: int)
    def get_selection() -> Tuple[int, int]
    def set_selection(start: int, end: int)
    def undo() / redo()
```

#### Deliverables:
- [ ] **ED-201**: TextArea wrapper implementing IEditor
- [ ] **ED-202**: Undo/redo stack (100 operations)
- [ ] **ED-203**: Selection management
- [ ] **ED-204**: Cursor position tracking
- [ ] **ED-205**: Text change events
- [ ] **ED-206**: Mock editor for testing

#### Unit Tests:
1. **T2.1**: All IEditor methods work correctly
2. **T2.2**: Undo/redo maintains correct state
3. **T2.3**: Events fire on text changes
4. **T2.4**: Mock editor matches real behavior
5. **T2.5**: Component integrates with event bus

---

### Phase 3: Markdown Renderer Component (Week 4)
**Goal**: Basic markdown rendering with preview

#### Component: MarkdownRenderer
```python
class IRenderer(ABC):
    def render_html(markdown: str) -> str
    def render_preview(markdown: str) -> Widget
    def get_outline(markdown: str) -> List[Heading]
    def validate_links(markdown: str) -> List[Issue]
```

#### Deliverables:
- [ ] **MR-301**: Mistune wrapper for CommonMark + tables
- [ ] **MR-302**: Preview widget generator
- [ ] **MR-303**: Outline/TOC extractor
- [ ] **MR-304**: Basic link validation (file existence)
- [ ] **MR-305**: HTML export for copy/paste
- [ ] **MR-306**: Render caching for performance

#### Unit Tests:
1. **T3.1**: Renders CommonMark elements correctly
2. **T3.2**: Tables render properly
3. **T3.3**: Outline extraction handles nested headings
4. **T3.4**: Caching improves performance
5. **T3.5**: HTML export is valid

---

### Phase 4: Command System Component (Week 5)
**Goal**: Command pattern for all user actions

#### Component: CommandSystem
```python
class ICommand(ABC):
    def execute() -> bool
    def undo() -> bool
    def can_execute() -> bool

class CommandRegistry:
    def register(name: str, command: ICommand)
    def execute(name: str) -> bool
    def bind_key(key: str, command: str)
```

#### Deliverables:
- [ ] **CS-401**: Command pattern implementation
- [ ] **CS-402**: Keybinding manager
- [ ] **CS-403**: Command palette backend
- [ ] **CS-404**: Command history for undo/redo
- [ ] **CS-405**: Customizable keybindings
- [ ] **CS-406**: Quick file switching (Ctrl+Tab, Ctrl+R)

#### Unit Tests:
1. **T4.1**: Commands execute and undo correctly
2. **T4.2**: Keybindings trigger correct commands
3. **T4.3**: Command palette finds all commands
4. **T4.4**: Recent files quick switch works
5. **T4.5**: Custom bindings override defaults

---

### Phase 5: Search Component (Week 6)
**Goal**: Find and replace in current file

#### Component: SearchEngine
```python
class ISearchEngine(ABC):
    def find_all(text: str, pattern: str, case_sensitive: bool) -> List[Match]
    def replace_all(text: str, pattern: str, replacement: str) -> str
    def find_next(text: str, pattern: str, start_pos: int) -> Optional[Match]
```

#### Deliverables:
- [ ] **SE-501**: Text search (literal strings only)
- [ ] **SE-502**: Case sensitive/insensitive search
- [ ] **SE-503**: Replace with preview
- [ ] **SE-504**: Search highlighting
- [ ] **SE-505**: Whole word matching option
- [ ] **SE-506**: Search history (last 10 searches)

#### Unit Tests:
1. **T5.1**: Find all occurrences correctly
2. **T5.2**: Case sensitivity works
3. **T5.3**: Replace preserves undo history
4. **T5.4**: Whole word boundary detection
5. **T5.5**: Search wraps around document

---

### Phase 6: UI Layout Manager (Week 7)
**Goal**: Minimal but complete UI

#### Component: LayoutManager
```python
class LayoutManager:
    def add_pane(name: str, widget: Widget, position: str)
    def toggle_pane(name: str)
    def resize_pane(name: str, size: int)
    def save_layout() / restore_layout()
```

#### Deliverables:
- [ ] **UI-601**: Split pane management (editor/preview)
- [ ] **UI-602**: Status bar component
- [ ] **UI-603**: Markdown outline panel
- [ ] **UI-604**: Recent files dialog (Ctrl+R)
- [ ] **UI-605**: Theme application (dark/light)
- [ ] **UI-606**: Responsive layout

#### Integration Tests:
1. **T6.1**: Panes resize correctly
2. **T6.2**: Layout persists between sessions
3. **T6.3**: Themes apply to all components
4. **T6.4**: Recent files dialog works
5. **T6.5**: Responsive to terminal resize

---

### Phase 7: Integration & Polish (Week 8)
**Goal**: Complete integration with essential file types

#### Full Integration:
- [ ] **IN-701**: Wire all components through event bus
- [ ] **IN-702**: Command palette UI
- [ ] **IN-703**: Settings UI (Ctrl+,)
- [ ] **IN-704**: Recent files list (Ctrl+R)
- [ ] **IN-705**: Help system (F1)
- [ ] **IN-706**: Performance optimization
- [ ] **IN-707**: Package and distribute

#### File Type Support:
- [ ] **FT-701**: Markdown (.md) - full support
- [ ] **FT-702**: Python (.py) - syntax highlighting
- [ ] **FT-703**: JSON (.json) - highlighting & validation
- [ ] **FT-704**: YAML (.yaml) - highlighting & validation

#### System Tests:
1. **T7.1**: Full editing workflow works
2. **T7.2**: All keybindings function
3. **T7.3**: No memory leaks
4. **T7.4**: Cross-platform compatibility
5. **T7.5**: Stress test with large files

---

## 4. Architectural Patterns & Decisions

### 4.1 Key Design Patterns

#### Dependency Injection
```python
# Components receive dependencies through constructor
class EditorComponent:
    def __init__(self, file_manager: IFileManager, event_bus: EventBus):
        self.file_manager = file_manager
        self.event_bus = event_bus
```

#### Repository Pattern for Data Access
```python
# Abstract file operations behind repository
class FileRepository:
    def __init__(self, backend: IFileManager):
        self.backend = backend
    
    def get_recent_files(self) -> List[Path]:
        # Business logic here, storage details in backend
```

#### Command Pattern for Actions
```python
# All user actions as commands
class BoldCommand(ICommand):
    def execute(self, editor: IEditor):
        selection = editor.get_selection()
        editor.wrap_selection("**", "**")
        return True
    
    def undo(self, editor: IEditor):
        # Undo logic
        return True
```

### 4.2 Testing Strategy

#### Component Testing Levels
1. **Unit Tests**: Each component in isolation with mocks
2. **Integration Tests**: Component pairs (e.g., Editor + FileManager)
3. **System Tests**: Full application workflows
4. **Contract Tests**: Verify interfaces between components

#### Test Structure
```python
tests/
├── unit/
│   ├── test_editor_component.py
│   ├── test_file_manager.py
│   └── test_markdown_renderer.py
├── integration/
│   ├── test_editor_file_integration.py
│   └── test_preview_sync.py
├── system/
│   ├── test_full_workflow.py
│   └── test_keybindings.py
└── fixtures/
    ├── sample_files/
    └── mock_components.py
```

#### Mock Components
Every interface has a corresponding mock for testing:
```python
class MockEditor(IEditor):
    def __init__(self):
        self.content = ""
        self.history = []
    
    def set_content(self, text: str):
        self.history.append(self.content)
        self.content = text
```

### 4.3 Component Upgrade Paths

#### Example: Upgrading from TextArea to CodeMirror
1. New implementation implements same IEditor interface
2. Update component registry configuration
3. No changes needed in dependent components
4. Run contract tests to verify compatibility

#### Example: Adding Cloud Storage
1. Create CloudFileManager implementing IFileManager
2. Add configuration for storage backend
3. File selection in UI to choose local vs cloud
4. Existing code continues working unchanged

### 4.1 Editing Enhancements
- **Smart Formatting**: Apply formatting to selected text or at cursor
- **Table Editor**: Visual table editing with Tab navigation
- **Link Assistant**: Ctrl+K opens link dialog with URL validation
- **Image Insertion**: Drag & drop or paste images (create relative links)
- **Code Block Templates**: Quick insert with language selection

### 4.2 Preview Enhancements  
- **Mermaid Diagram Support**: Render diagrams in preview
- **Math Expression Support**: LaTeX math rendering
- **Custom CSS**: User-definable preview styles
- **Print Preview**: See how document will look when printed
- **Export Preview**: Preview export format before saving

### 4.3 Markdown Variants Support
- CommonMark (default)
- GitHub Flavored Markdown
- MultiMarkdown
- Markdown Extra

---

## 5. Implementation Recommendations

### 5.1 MVP Scope (What We're Building)

#### Core Features to Include:
- ✅ Component architecture with interfaces
- ✅ Event bus for decoupling
- ✅ Atomic saves with simple backup
- ✅ Basic markdown (CommonMark + tables)
- ✅ Live preview with sync scroll
- ✅ Simple find/replace (no regex initially)
- ✅ Recent files with quick switching (Ctrl+Tab, Ctrl+R)
- ✅ Dark/light themes
- ✅ 4 file types (Markdown, Python, JSON, YAML)

#### Features to Defer (Add Post-MVP):
- ❌ File watching for external changes
- ❌ Macro recording
- ❌ Multi-file/project search
- ❌ Regex search patterns
- ❌ Advanced markdown (Mermaid, LaTeX, frontmatter)
- ❌ PDF/DOCX export
- ❌ Menu bar
- ❌ File tree sidebar
- ❌ Multi-cursor editing
- ❌ Extended language support

### 5.2 Progressive Enhancement Strategy

Each component starts minimal and grows:

1. **FileManager Evolution**:
   - v1: Read/write files + atomic saves
   - v2: Add backup system
   - v3: Add recent files tracking
   - v4: Add cursor position memory
   - Future: Add file watching, cloud sync

2. **Editor Evolution**:
   - v1: Basic text editing
   - v2: Add undo/redo
   - v3: Add selection management  
   - Future: Add multi-cursor, snippets

3. **Search Evolution**:
   - v1: Simple string search
   - v2: Add case sensitivity, whole word
   - v3: Add search history
   - Future: Add regex, fuzzy search, indexing

### 5.3 Critical Abstractions to Maintain

**Must Abstract** (likely to change):
- Editor widget (TextArea → future alternatives)
- Markdown parser (mistune → future alternatives)
- Search implementation (simple → advanced)

**Can Be Concrete** (unlikely to change):
- Event bus (simple pub/sub is sufficient)
- Command registry (standard pattern)
- Configuration format (TOML is stable)

### 5.4 Development Workflow

1. **Build Component in Isolation**
2. **Test with Mocks**
3. **Integration Test**
4. **Add to Main App**

### 5.5 Early Decisions to Avoid Later Pain

1. **Use Type Hints Everywhere**
2. **Separate Business Logic from UI**
3. **Configuration Schema from Day 1**
4. **Version Your Interfaces**

This simplified scope reduces initial complexity by ~40% while maintaining the architectural foundation for future enhancements.

```
┌─────────────────────────────────────────────────────────┐
│ Tino - document.md*                              [_][□][X]│
├─────────────────────────────────────────────────────────┤
│ File  Edit  View  Format  Tools  Help                    │
├──────────────────────────┬───────────────────────────────┤
│ EDITOR                   │ PREVIEW                       │
│ 1 │ # My Document        │ My Document                   │
│ 2 │                       │ ═══════════                   │
│ 3 │ This is **bold** and  │ This is bold and this is      │
│ 4 │ this is *italic*.     │ italic.                       │
│ 5 │                       │                               │
│ 6 │ ## Section One        │ Section One                   │
│ 7 │                       │ ────────────                  │
│   │                       │                               │
├──────────────────────────┴───────────────────────────────┤
│ Ln 3, Col 18  │  Markdown  │  UTF-8  │  2.3k words       │
└─────────────────────────────────────────────────────────┘
```

---

## 8. Keyboard Shortcuts (Complete List)

### File Operations
- `Ctrl+N` - New file
- `Ctrl+O` - Open file  
- `Ctrl+S` - Save
- `Ctrl+Shift+S` - Save As
- `Ctrl+R` - Recent files list
- `Ctrl+Tab` - Switch to last file
- `Ctrl+Q` - Quit

### Editing
- `Ctrl+Z` - Undo
- `Ctrl+Y` - Redo
- `Ctrl+X` - Cut
- `Ctrl+C` - Copy
- `Ctrl+V` - Paste
- `Ctrl+A` - Select all
- `Ctrl+D` - Duplicate line

### Markdown Formatting
- `Ctrl+B` - Bold
- `Ctrl+I` - Italic
- `Ctrl+K` - Insert link
- `Ctrl+Shift+C` - Inline code

### Navigation
- `Ctrl+F` - Find
- `Ctrl+H` - Replace
- `Ctrl+G` - Go to line
- `Ctrl+Shift+O` - Jump to heading
- `F2` - Toggle preview
- `F11` - Preview only mode

### View
- `Ctrl+,` - Settings
- `Ctrl+Shift+P` - Command palette
- `F1` - Help
- `Alt+Z` - Toggle word wrap

---

## 9. Configuration File Structure (Simplified)

```toml
# ~/.config/tino/config.toml (Linux)
# %APPDATA%/tino/config.toml (Windows)

[editor]
theme = "dark"  # dark or light
font_size = 14
tab_size = 4
use_tabs = false
word_wrap = true
show_line_numbers = true

[markdown]
auto_preview = true  # auto-show preview for .md files
sync_scroll = true
default_split = 50  # percentage

[files]
max_recent = 30
remember_cursor = true
auto_backup = true

[shortcuts]
# Override defaults if needed
save = "ctrl+s"
bold = "ctrl+b"
recent_files = "ctrl+r"
last_file = "ctrl+tab"
```

---

## 10. Success Criteria

### MVP Success (Phases 0-5)
- Editor opens and saves files reliably
- Markdown preview works with <50ms updates
- Basic search and replace functions
- Recent files with Ctrl+Tab quick switching
- No data loss during normal operation
- Startup time <200ms

### Full Product Success (Phases 6-7)
- All keyboard shortcuts work as expected
- Supports Markdown, Python, JSON, YAML files
- Settings persist between sessions
- Cross-platform compatibility verified
- Memory usage under 75MB
- Better than nano for markdown editing

---

## 11. Testing Priority

### Critical Tests (Must Pass for MVP)
1. Atomic file saves work correctly
2. Markdown preview accuracy
3. Recent files and quick switching
4. Basic search functionality
5. All core keyboard shortcuts

### Important Tests
1. Large file performance (10MB+)
2. HTML export quality
3. Cursor position memory
4. Theme switching
5. Cross-platform paths

---

## 12. Distribution & Documentation

### Installation Methods
```bash
# PyPI
pip install tino

# Windows
download tino-setup.exe

# Linux
snap install tino
# or
curl -L https://github.com/xxx/releases/latest/tino-linux -o tino
chmod +x tino
```

### Documentation Priority
1. **Quick Start**: 5-minute markdown editing guide
2. **Keyboard Reference**: Printable cheat sheet
3. **Markdown Guide**: Feature showcase
4. **Configuration Guide**: Customization options
5. **Migration Guide**: From other editors

---

## Appendix A: Why Markdown First?

Based on the refined use case, markdown functionality takes precedence because:

1. **Documentation is Daily Work**: Teams write documentation constantly
2. **Preview is Essential**: Seeing formatted output while writing is crucial
3. **Formatting Tools Save Time**: Bold, italic, links, tables are used frequently
4. **Export is Required**: Documentation needs to be shared in various formats
5. **Config Files are Occasional**: Script/config editing is less frequent

This priority ensures tino becomes the go-to tool for documentation, with config editing as a valuable bonus rather than the reverse.