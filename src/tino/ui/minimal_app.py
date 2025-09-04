"""
Minimal Textual application for testing the EditorComponent.

Provides a simple TUI with just the editor, file operations, and status display
for testing all keyboard shortcuts and editor functionality.
"""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Footer, Header, Static, TextArea

from ..components.editor.editor_component import EditorComponent
from ..components.file_manager import FileManager
from ..core.events.bus import EventBus
from ..core.events.types import CursorMovedEvent, TextChangedEvent


class StatusBar(Static):
    """Status bar showing file info and cursor position."""

    def __init__(self) -> None:
        super().__init__()
        self.update_status()

    def update_status(
        self,
        file_path: Path | None = None,
        line: int = 1,
        column: int = 1,
        modified: bool = False,
        word_count: int = 0,
    ) -> None:
        """Update status bar content."""
        file_name = file_path.name if file_path else "untitled"
        mod_indicator = "*" if modified else ""

        status_text = (
            f" {file_name}{mod_indicator} | "
            f"Ln {line}, Col {column} | "
            f"{word_count} words"
        )

        self.update(status_text)


class FileDialogScreen(ModalScreen):
    """Modal screen for file selection."""

    CSS = """
    FileDialogScreen {
        align: center middle;
    }

    #file_dialog {
        width: 60;
        height: 20;
        border: solid $primary;
        background: $surface;
    }

    #file_tree {
        height: 15;
    }

    #button_bar {
        height: 3;
        dock: bottom;
        align: center middle;
    }
    """

    def __init__(self, initial_path: Path = None) -> None:
        super().__init__()
        self.selected_file: Path | None = None
        self.initial_path = initial_path or Path.cwd()

    def compose(self) -> ComposeResult:
        """Create the file dialog layout."""
        with Container(id="file_dialog"):
            yield DirectoryTree(str(self.initial_path), id="file_tree")
            with Horizontal(id="button_bar"):
                yield Button("Open", variant="primary", id="open_button")
                yield Button("Cancel", variant="default", id="cancel_button")

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """Handle file selection in the directory tree."""
        self.selected_file = event.path
        # Auto-open on double-click/enter
        if self.selected_file and self.selected_file.is_file():
            self.dismiss(self.selected_file)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "open_button":
            if self.selected_file and self.selected_file.is_file():
                self.dismiss(self.selected_file)
            else:
                self.app.notify("Please select a file to open", severity="warning")
        elif event.button.id == "cancel_button":
            self.dismiss(None)


class MinimalEditorApp(App):
    """
    Minimal text editor application for testing.

    Features:
    - Text editing with TextArea
    - File open/save operations
    - Status bar with cursor position
    - All keyboard shortcuts
    """

    CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text;
        content-align: left middle;
    }

    #editor {
        border: solid $primary;
    }
    """

    BINDINGS = [
        # File operations
        Binding("ctrl+n", "new_file", "New File"),
        Binding("ctrl+o", "open_file", "Open File"),
        Binding("ctrl+s", "save_file", "Save"),
        Binding("ctrl+shift+s", "save_as", "Save As"),
        Binding("ctrl+q", "quit", "Quit"),
        # Edit operations
        Binding("ctrl+z", "undo", "Undo"),
        Binding("ctrl+y", "redo", "Redo"),
        Binding("ctrl+x", "cut", "Cut"),
        Binding("ctrl+c", "copy", "Copy"),
        Binding("ctrl+v", "paste", "Paste"),
        Binding("ctrl+a", "select_all", "Select All"),
        Binding("ctrl+d", "duplicate_line", "Duplicate Line"),
        # Navigation
        Binding("ctrl+f", "find", "Find"),
        Binding("ctrl+h", "replace", "Replace"),
        Binding("ctrl+g", "goto_line", "Go to Line"),
        # View operations
        Binding("f2", "toggle_preview", "Toggle Preview"),
        Binding("ctrl+shift+o", "open_file_dialog", "Open File Dialog"),
        # Testing shortcuts
        Binding("f1", "show_help", "Help"),
        Binding("f9", "toggle_debug", "Debug"),
    ]

    # Reactive attributes
    current_file: reactive[Path | None] = reactive(None)
    modified: reactive[bool] = reactive(False)
    show_preview: reactive[bool] = reactive(True)

    def __init__(self) -> None:
        super().__init__()

        # Initialize components
        self.event_bus = EventBus()
        self.file_manager = FileManager(self.event_bus)

        # Clear any pre-existing recent files to prevent cycling
        self.file_manager.recent_files._files.clear()
        self.file_manager.recent_files._last_file = None

        # UI components
        self.text_area: TextArea | None = None
        self.editor: EditorComponent | None = None
        self.status_bar: StatusBar | None = None

        # State
        self._clipboard_content = ""
        self.debug_mode = False

        # Subscribe to events
        self.event_bus.subscribe(TextChangedEvent, self.on_text_changed)
        self.event_bus.subscribe(CursorMovedEvent, self.on_cursor_moved)

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header(show_clock=False)

        with Container():
            self.text_area = TextArea(text="", id="editor", show_line_numbers=True)
            yield self.text_area

        self.status_bar = StatusBar()
        yield self.status_bar

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the editor component after mounting."""
        if self.text_area:
            # Create editor component and link it to TextArea
            self.editor = EditorComponent(self.event_bus)
            self.editor.set_text_area(self.text_area)

            # Initial status update
            self.update_status()

            self.text_area.focus()

    # Event handlers

    def on_text_changed(self, event: TextChangedEvent) -> None:
        """Handle text changed events."""
        self.modified = True
        self.update_status()

        if self.debug_mode:
            self.notify(f"Text changed: {event.change_type} at {event.position}")

    def on_cursor_moved(self, event: CursorMovedEvent) -> None:
        """Handle cursor moved events."""
        self.update_status()

        if self.debug_mode:
            self.notify(f"Cursor: Ln {event.line + 1}, Col {event.column + 1}")

    def watch_current_file(self, new_file: Path | None) -> None:
        """React to current file changes."""
        self.update_status()

        if new_file:
            self.title = f"Tino - {new_file.name}"
        else:
            self.title = "Tino - Untitled"

    def watch_modified(self, is_modified: bool) -> None:
        """React to modification state changes."""
        self.update_status()

    # Action handlers

    async def action_new_file(self) -> None:
        """Create a new file."""
        if self.modified:
            # In a real app, you'd show a save dialog
            pass

        if self.text_area and self.editor:
            self.editor.set_content("")
            self.current_file = None
            self.modified = False

        self.notify("New file created")

    async def action_open_file(self) -> None:
        """Open a file - redirects to file dialog."""
        await self.action_open_file_dialog()

    async def action_save_file(self) -> None:
        """Save the current file."""
        if not self.editor:
            return

        if self.current_file:
            try:
                content = self.editor.get_content()
                self.file_manager.save_file(self.current_file, content)
                self.modified = False
                self.notify(f"Saved {self.current_file.name}")
            except Exception as e:
                self.notify(f"Error saving: {e}", severity="error")
        else:
            await self.action_save_as()

    async def action_save_as(self) -> None:
        """Save file with new name."""
        # For testing, save to a test file
        test_file = Path("test_output.md")

        if self.editor:
            try:
                content = self.editor.get_content()
                self.file_manager.save_file(test_file, content)
                self.current_file = test_file
                self.modified = False
                self.notify(f"Saved as {test_file.name}")
            except Exception as e:
                self.notify(f"Error saving: {e}", severity="error")

    async def action_undo(self) -> None:
        """Undo last operation."""
        if self.editor and self.editor.can_undo():
            self.editor.undo()
            self.notify("Undo")
        else:
            self.notify("Nothing to undo")

    async def action_redo(self) -> None:
        """Redo last undone operation."""
        if self.editor and self.editor.can_redo():
            self.editor.redo()
            self.notify("Redo")
        else:
            self.notify("Nothing to redo")

    async def action_cut(self) -> None:
        """Cut selected text."""
        if self.editor:
            self._clipboard_content = self.editor.get_selected_text()
            if self._clipboard_content:
                start, end = self.editor.get_selection()
                self.editor.delete_range(start, end)
                self.notify("Cut to clipboard")
            else:
                self.notify("No selection to cut")

    async def action_copy(self) -> None:
        """Copy selected text."""
        if self.editor:
            self._clipboard_content = self.editor.get_selected_text()
            if self._clipboard_content:
                self.notify("Copied to clipboard")
            else:
                self.notify("No selection to copy")

    async def action_paste(self) -> None:
        """Paste from clipboard."""
        if self.editor and self._clipboard_content:
            self.editor.replace_selection(self._clipboard_content)
            self.notify("Pasted from clipboard")
        else:
            self.notify("Clipboard is empty")

    async def action_select_all(self) -> None:
        """Select all text."""
        if self.editor:
            content_length = len(self.editor.get_content())
            self.editor.set_selection(0, content_length)
            self.notify("Selected all")

    async def action_duplicate_line(self) -> None:
        """Duplicate current line."""
        if self.editor:
            line, column, pos = self.editor.get_cursor_position()
            line_text = self.editor.get_line_text(line)

            # Insert duplicate line below current line
            line_end = pos + (len(line_text) - column)
            self.editor.insert_text(line_end, f"\n{line_text}")
            self.notify("Line duplicated")

    async def action_find(self) -> None:
        """Show find dialog (simplified)."""
        self.notify("Find: Feature not implemented in minimal app")

    async def action_replace(self) -> None:
        """Show replace dialog (simplified)."""
        self.notify("Replace: Feature not implemented in minimal app")

    async def action_goto_line(self) -> None:
        """Go to specific line (simplified)."""
        self.notify("Go to line: Feature not implemented in minimal app")

    async def action_show_help(self) -> None:
        """Show help information."""
        help_text = """
Tino Editor - Minimal Test App

Keyboard Shortcuts:
- Ctrl+N: New file
- Ctrl+O: Open file
- Ctrl+S: Save
- Ctrl+Z/Y: Undo/Redo
- Ctrl+X/C/V: Cut/Copy/Paste
- Ctrl+A: Select All
- Ctrl+D: Duplicate Line
- F2: Toggle Preview (limited)
- Ctrl+Shift+O: Open File Dialog
- F9: Toggle Debug Mode
- Ctrl+Q: Quit

This is a minimal test application for the EditorComponent.
For full functionality, use the preview app instead.
"""
        self.notify(help_text.strip())

    async def action_toggle_debug(self) -> None:
        """Toggle debug mode."""
        self.debug_mode = not self.debug_mode
        mode = "ON" if self.debug_mode else "OFF"
        self.notify(f"Debug mode {mode}")

    async def action_toggle_preview(self) -> None:
        """Toggle markdown preview pane."""
        self.show_preview = not self.show_preview
        status = "shown" if self.show_preview else "hidden"
        self.notify(f"Preview {status}")

    async def action_open_file_dialog(self) -> None:
        """Open file dialog."""

        def handle_file_selected(selected_file: Path | None) -> None:
            """Handle the result of file dialog."""
            if selected_file:
                try:
                    # Load file content using the file manager
                    content = self.file_manager.load_file(selected_file)

                    # Update editor with new content
                    if self.editor:
                        self.editor.set_content(content)

                    # Update app state
                    self.current_file = selected_file
                    self.modified = False

                    self.notify(f"Opened {selected_file.name}")

                except Exception as e:
                    self.notify(f"Error opening file: {e}", severity="error")

        # Show the file dialog modal
        self.push_screen(FileDialogScreen(), handle_file_selected)

    # Helper methods

    def update_status(self) -> None:
        """Update the status bar."""
        if not self.status_bar or not self.editor:
            return

        line, column, _ = self.editor.get_cursor_position()
        word_count = len(self.editor.get_content().split())

        self.status_bar.update_status(
            file_path=self.current_file,
            line=line + 1,  # Display as 1-based
            column=column + 1,  # Display as 1-based
            modified=self.modified,
            word_count=word_count,
        )


def run_minimal_app():
    """Run the minimal editor application."""
    app = MinimalEditorApp()
    app.run()
    return 0


if __name__ == "__main__":
    run_minimal_app()
