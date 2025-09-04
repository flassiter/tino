"""
Simple markdown editor application.

Provides a clean markdown editor with:
- Text editor with syntax highlighting
- File operations (Ctrl+O, Ctrl+S)
- Single-pane focused editing
"""

import asyncio
from pathlib import Path
from typing import Optional

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DirectoryTree, Footer, Header, Input, TextArea
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen

from tino.components.file_manager.file_manager import FileManager
from tino.core.events.bus import EventBus


class FileDialogScreen(ModalScreen):
    """Modal screen for file selection."""

    CSS = """
    FileDialogScreen {
        align: center middle;
    }
    
    #file_dialog {
        width: 80;
        height: 30;
        border: solid $primary;
        background: $surface;
    }
    
    #file_tree {
        height: 25;
        overflow-y: auto;
    }
    
    #button_bar {
        height: 3;
        dock: bottom;
        align: center middle;
    }
    """

    def __init__(self, initial_path: Path = None) -> None:
        super().__init__()
        self.selected_file: Optional[Path] = None
        self.initial_path = initial_path or Path.cwd()

    def compose(self) -> ComposeResult:
        """Create the file dialog layout."""
        with Container(id="file_dialog"):
            yield DirectoryTree(str(self.initial_path), id="file_tree")
            with Horizontal(id="button_bar"):
                yield Button("Open", variant="primary", id="open_button")
                yield Button("Cancel", variant="default", id="cancel_button")

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
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


class SaveFileDialogScreen(ModalScreen):
    """Modal screen for save file dialog."""

    CSS = """
    SaveFileDialogScreen {
        align: center middle;
    }
    
    #save_dialog {
        width: 80;
        height: 32;
        border: solid $primary;
        background: $surface;
    }
    
    #filename_input {
        dock: top;
        height: 3;
        margin: 1;
    }
    
    #save_tree {
        height: 23;
        overflow-y: auto;
    }
    
    #save_button_bar {
        height: 3;
        dock: bottom;
        align: center middle;
    }
    """

    def __init__(self, initial_path: Path = None, default_name: str = "untitled.md") -> None:
        super().__init__()
        self.selected_directory: Path = initial_path or Path.cwd()
        self.default_name = default_name

    def compose(self) -> ComposeResult:
        """Create the save dialog layout."""
        with Container(id="save_dialog"):
            yield Input(
                placeholder="Enter filename...",
                value=self.default_name,
                id="filename_input"
            )
            yield DirectoryTree(str(self.selected_directory), id="save_tree")
            with Horizontal(id="save_button_bar"):
                yield Button("Save", variant="primary", id="save_button")
                yield Button("Cancel", variant="default", id="cancel_button")

    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        """Handle directory selection in the tree."""
        self.selected_directory = event.path

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save_button":
            filename_input = self.query_one("#filename_input", Input)
            filename = filename_input.value.strip()
            
            if not filename:
                self.app.notify("Please enter a filename", severity="warning")
                return
            
            # Combine directory and filename
            full_path = self.selected_directory / filename
            
            # Add .md extension if no extension provided
            if not full_path.suffix:
                full_path = full_path.with_suffix(".md")
            
            self.dismiss(full_path)
            
        elif event.button.id == "cancel_button":
            self.dismiss(None)


class EditorPane(Vertical):
    """Editor pane containing the text editor."""
    
    DEFAULT_CSS = """
    EditorPane {
        border-right: solid $primary;
    }
    
    EditorPane TextArea {
        height: 1fr;
    }
    """
    
    content = reactive("", init=False)
    
    def __init__(self, name: str | None = None, id: str | None = None) -> None:
        """Initialize the editor pane."""
        super().__init__(name=name, id=id)
        self._editor: TextArea | None = None
        self._file_path: Optional[Path] = None
        self._modified = False
    
    def compose(self) -> ComposeResult:
        """Compose the editor pane."""
        self._editor = TextArea("", language="markdown")
        self._editor.show_line_numbers = True
        yield self._editor
    
    def watch_content(self, content: str) -> None:
        """Update editor content when reactive changes."""
        if self._editor and self._editor.text != content:
            self._editor.text = content
    
    @on(TextArea.Changed)
    def on_editor_changed(self, event: TextArea.Changed) -> None:
        """Handle editor content changes."""
        self.content = event.text_area.text
        self._modified = True
        self.post_message(EditorContentChanged(self.content))
    
    
    
    
    def set_file_path(self, path: Path | None) -> None:
        """Set the current file path."""
        self._file_path = path
        self._modified = False
    
    def get_file_path(self) -> Path | None:
        """Get the current file path."""
        return self._file_path
    
    def is_modified(self) -> bool:
        """Check if content has been modified."""
        return self._modified
    
    def mark_saved(self) -> None:
        """Mark content as saved."""
        self._modified = False
    
    def jump_to_line(self, line_number: int) -> None:
        """Jump to a specific line in the editor."""
        if self._editor:
            # Convert to 0-based indexing
            line_index = max(0, line_number - 1)
            try:
                self._editor.cursor_location = (line_index, 0)
                self._editor.scroll_to_line(line_index)
            except Exception:
                pass  # Line might be out of range


class EditorContentChanged(Message):
    """Message sent when editor content changes."""
    
    def __init__(self, content: str) -> None:
        """Initialize the message."""
        super().__init__()
        self.content = content






class PreviewApp(App[None]):
    """Main Tino markdown editor application."""
    
    TITLE = "Tino - Markdown Editor"
    
    CSS = """
    Screen {
        layout: vertical;
    }
    
    .main-container {
        height: 1fr;
    }
    
    Footer {
        dock: bottom;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+o", "open_file", "Open"),
        Binding("ctrl+shift+o", "open_file", "Open File Dialog"),
        Binding("ctrl+s", "save_file", "Save"),
        Binding("f12", "save_file_as", "Save As"),  # Using F12 instead of ctrl+shift+s
        Binding("ctrl+q", "quit", "Quit"),
    ]
    
    
    def __init__(self) -> None:
        """Initialize the preview app."""
        super().__init__()
        
        # Initialize components
        self._event_bus = EventBus()
        self._file_manager = FileManager(self._event_bus)
        
        # UI components
        self._editor_pane: EditorPane | None = None
        
        # State
        self._current_file: Optional[Path] = None
        
    def compose(self) -> ComposeResult:
        """Compose the application."""
        yield Header()
        
        # Single editor pane taking full space
        self._editor_pane = EditorPane()
        self._editor_pane.add_class("main-container")
        yield self._editor_pane
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Handle application mounting."""
        self.title = self.TITLE
    
    
    @on(EditorContentChanged)
    def on_editor_content_changed(self, event: EditorContentChanged) -> None:
        """Handle editor content changes."""
        # Update title to show modified state
        if self._editor_pane and self._editor_pane.is_modified():
            self.title = f"{self.TITLE} - {self._get_filename()}*"
        else:
            self.title = f"{self.TITLE} - {self._get_filename()}"
    
    
    
    async def action_open_file(self) -> None:
        """Open a file dialog and load the selected file."""
        def handle_file_selected(selected_file: Optional[Path]) -> None:
            """Handle the result of file dialog."""
            if selected_file:
                # Load the selected file asynchronously
                asyncio.create_task(self._load_file(selected_file))
            
        # Show the file dialog modal
        self.push_screen(FileDialogScreen(), handle_file_selected)
    
    async def action_save_file(self) -> None:
        """Save the current file."""
        if not self._editor_pane:
            return
            
        if self._current_file:
            # Save to existing file
            try:
                success = await self._save_to_file(self._current_file)
                if success:
                    self._editor_pane.mark_saved()
                    self.title = f"{self.TITLE} - {self._get_filename()}"
                    self.notify("File saved successfully")
                else:
                    self.notify("Failed to save file", severity="error")
            except Exception as e:
                self.notify(f"Error saving file: {e}", severity="error")
        else:
            # Save as new file - for demo, use a default name
            await self.action_save_file_as()
    
    
    async def action_save_file_as(self) -> None:
        """Save the current file with a new name."""
        if not self._editor_pane:
            return
        
        def handle_save_file_selected(save_path: Optional[Path]) -> None:
            """Handle the result of save file dialog."""
            if save_path:
                # Save the file asynchronously
                asyncio.create_task(self._save_as_new_file(save_path))
        
        # Determine default filename
        default_name = self._current_file.name if self._current_file else "untitled.md"
        initial_dir = self._current_file.parent if self._current_file else Path.cwd()
        
        # Show the save dialog modal
        self.push_screen(
            SaveFileDialogScreen(initial_path=initial_dir, default_name=default_name),
            handle_save_file_selected
        )
    
    async def _save_as_new_file(self, save_path: Path) -> None:
        """Save content to a new file path."""
        if not self._editor_pane:
            return
        
        try:
            success = await self._save_to_file(save_path)
            if success:
                self._current_file = save_path
                self._editor_pane.set_file_path(save_path)
                self._editor_pane.mark_saved()
                self.title = f"{self.TITLE} - {save_path.name}"
                self.notify(f"File saved as {save_path.name}")
            else:
                self.notify("Failed to save file", severity="error")
        except Exception as e:
            self.notify(f"Error saving file: {e}", severity="error")
    
    async def _load_file(self, file_path: Path) -> None:
        """Load content from a file."""
        try:
            content = await asyncio.get_event_loop().run_in_executor(
                None, self._file_manager.open_file, str(file_path)
            )
            
            if self._editor_pane:
                self._editor_pane.content = content
                self._editor_pane.set_file_path(file_path)
                self._current_file = file_path
                self.title = f"{self.TITLE} - {file_path.name}"
                
        except Exception as e:
            self.notify(f"Error loading file: {e}", severity="error")
    
    async def _save_to_file(self, file_path: Path) -> bool:
        """Save content to a file."""
        if not self._editor_pane:
            return False
            
        try:
            success = await asyncio.get_event_loop().run_in_executor(
                None, 
                self._file_manager.save_file, 
                str(file_path), 
                self._editor_pane.content
            )
            return success
        except Exception:
            return False
    
    
    def _get_filename(self) -> str:
        """Get current filename for display."""
        if self._current_file:
            return self._current_file.name
        return "New File"


def main():
    """Run the preview app."""
    app = PreviewApp()
    app.run()


if __name__ == "__main__":
    main()