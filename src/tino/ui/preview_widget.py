"""
Preview widget for markdown rendering in TUI.

Provides a Textual widget that displays rendered markdown with synchronized
scrolling, theme support, and outline navigation.
"""

from typing import Any, Dict, List, Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Markdown
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Tree
from textual.scroll_view import ScrollView
from textual.message import Message
from textual.geometry import Offset

from tino.core.interfaces.renderer import IRenderer, Heading


# Removed SyncScrollView - using standard Markdown widget scrolling now


class OutlinePanel(Widget):
    """Panel showing document outline with clickable headings."""
    
    def __init__(self, name: str | None = None, id: str | None = None) -> None:
        """Initialize the outline panel."""
        super().__init__(name=name, id=id)
        self._headings: List[Heading] = []
        self._tree: Tree[Heading] | None = None
    
    def compose(self) -> ComposeResult:
        """Compose the outline panel widgets."""
        with Vertical():
            self._tree = Tree("Document Outline", id="outline-tree")
            yield self._tree
    
    def update_outline(self, headings: List[Heading]) -> None:
        """
        Update the outline with new headings.
        
        Args:
            headings: List of headings to display
        """
        self._headings = headings
        if self._tree is None:
            return
        
        self._tree.clear()
        
        if not headings:
            return
        
        # Build hierarchical tree structure
        stack = [self._tree.root]
        
        for heading in headings:
            # Determine where to place this heading in the hierarchy
            while len(stack) > heading.level:
                stack.pop()
            
            # Ensure we have a parent at the right level
            while len(stack) < heading.level:
                # Create intermediate nodes if needed
                parent = stack[-1]
                intermediate = parent.add(f"Level {len(stack)}", expand=True)
                stack.append(intermediate)
            
            # Add the heading
            parent = stack[-1]
            node = parent.add(heading.text, data=heading)
            stack.append(node)
    
    @on(Tree.NodeSelected)
    def on_heading_selected(self, event: Tree.NodeSelected[Heading]) -> None:
        """Handle heading selection in outline."""
        if event.node.data:
            # Post message that heading was selected
            self.post_message(HeadingSelected(event.node.data))


class HeadingSelected(Message):
    """Message sent when a heading is selected in outline."""
    
    def __init__(self, heading: Heading) -> None:
        """Initialize the message."""
        super().__init__()
        self.heading = heading


class MarkdownPreview(Widget):
    """Widget for displaying rendered markdown with outline."""
    
    DEFAULT_CSS = """
    MarkdownPreview {
        layout: horizontal;
    }
    
    .preview-content {
        dock: left;
        width: 75%;
        overflow-y: auto;
    }
    
    .outline-panel {
        dock: right;
        width: 25%;
        border-left: solid $primary;
        padding: 1;
    }
    
    .outline-hidden .preview-content {
        width: 100%;
    }
    
    .outline-hidden .outline-panel {
        display: none;
    }
    """
    
    content = reactive("")
    show_outline = reactive(True)
    current_theme = reactive("dark")
    
    def __init__(
        self,
        renderer: IRenderer,
        name: str | None = None,
        id: str | None = None
    ) -> None:
        """
        Initialize the markdown preview widget.
        
        Args:
            renderer: Renderer instance for markdown processing
            name: Widget name
            id: Widget ID
        """
        super().__init__(name=name, id=id)
        self._renderer = renderer
        self._markdown_widget: Markdown | None = None
        self._outline_panel: OutlinePanel | None = None
        self._current_headings: List[Heading] = []
        # Note: Debouncing removed for MVP simplicity
        self._last_content = ""
    
    def compose(self) -> ComposeResult:
        """Compose the preview widget."""
        with Horizontal():
            # Main preview area with standard scrollbars
            with ScrollView(classes="preview-content"):
                self._markdown_widget = Markdown("", id="markdown-content")
                yield self._markdown_widget
            
            # Outline panel  
            self._outline_panel = OutlinePanel()
            self._outline_panel.add_class("outline-panel")
            yield self._outline_panel
    
    def on_mount(self) -> None:
        """Handle widget mounting."""
        self._update_preview()
    
    def watch_content(self, content: str) -> None:
        """Handle content changes with immediate updates."""
        if content == self._last_content:
            return
        
        self._last_content = content
        
        # Update preview immediately for MVP
        # TODO: Add proper debouncing in future version
        self._update_preview()
    
    def watch_show_outline(self, show_outline: bool) -> None:
        """Handle outline visibility changes."""
        if show_outline:
            self.remove_class("outline-hidden")
        else:
            self.add_class("outline-hidden")
    
    def watch_current_theme(self, theme: str) -> None:
        """Handle theme changes."""
        self._renderer.set_theme(theme)
        self._update_preview()
    
    def toggle_outline(self) -> None:
        """Toggle outline panel visibility."""
        self.show_outline = not self.show_outline
    
    def jump_to_heading(self, heading: Heading) -> None:
        """
        Jump to a specific heading in the preview.
        
        Args:
            heading: Heading to jump to
        """
        # This would require coordination with the editor
        # For now, just post a message that can be handled by parent
        self.post_message(JumpToLine(heading.line_number))
    
    def get_current_headings(self) -> List[Heading]:
        """Get the current document headings."""
        return self._current_headings.copy()
    
    
    @on(HeadingSelected)
    def on_heading_selected(self, event: HeadingSelected) -> None:
        """Handle heading selection from outline panel."""
        self.jump_to_heading(event.heading)
    
    def _update_preview(self) -> None:
        """Update the preview content."""
        if not self._markdown_widget or not self.content:
            return
        
        try:
            # Render markdown to get headings and validation
            render_result = self._renderer.render_html(self.content)
            self._current_headings = render_result.outline
            
            # Update markdown widget
            self._markdown_widget.update(self.content)
            
            # Update outline panel
            if self._outline_panel:
                self._outline_panel.update_outline(self._current_headings)
            
            # Post message with render statistics
            self.post_message(PreviewUpdated(
                render_time=render_result.render_time_ms,
                cached=render_result.cached,
                issues=render_result.issues
            ))
            
        except Exception as e:
            # Handle rendering errors gracefully
            error_content = f"**Rendering Error**: {str(e)}"
            self._markdown_widget.update(error_content)
            
            self.post_message(PreviewError(str(e)))


class JumpToLine(Message):
    """Message to request jumping to a specific line."""
    
    def __init__(self, line_number: int) -> None:
        """Initialize the message."""
        super().__init__()
        self.line_number = line_number


class PreviewUpdated(Message):
    """Message sent when preview is updated."""
    
    def __init__(
        self, 
        render_time: float, 
        cached: bool,
        issues: List[Any]
    ) -> None:
        """Initialize the message."""
        super().__init__()
        self.render_time = render_time
        self.cached = cached
        self.issues = issues


class PreviewError(Message):
    """Message sent when preview rendering fails."""
    
    def __init__(self, error: str) -> None:
        """Initialize the message."""
        super().__init__()
        self.error = error


class SplitPane(Widget):
    """Split pane container for editor and preview."""
    
    DEFAULT_CSS = """
    SplitPane {
        layout: horizontal;
    }
    
    .editor-pane {
        width: 50%;
        dock: left;
        border-right: solid $primary;
    }
    
    .preview-pane {
        width: 50%;
        dock: right;
    }
    
    .preview-hidden .editor-pane {
        width: 100%;
        border-right: none;
    }
    
    .preview-hidden .preview-pane {
        display: none;
    }
    """
    
    show_preview = reactive(True)
    
    def __init__(
        self,
        editor_widget: Widget,
        preview_widget: MarkdownPreview,
        name: str | None = None,
        id: str | None = None
    ) -> None:
        """
        Initialize the split pane.
        
        Args:
            editor_widget: Editor widget for the left pane
            preview_widget: Preview widget for the right pane
            name: Widget name
            id: Widget ID
        """
        super().__init__(name=name, id=id)
        self._editor_widget = editor_widget
        self._preview_widget = preview_widget
    
    def compose(self) -> ComposeResult:
        """Compose the split pane."""
        with Horizontal():
            # Editor pane
            with Vertical(classes="editor-pane"):
                yield self._editor_widget
            
            # Preview pane
            with Vertical(classes="preview-pane"):
                yield self._preview_widget
    
    def watch_show_preview(self, show_preview: bool) -> None:
        """Handle preview visibility changes."""
        if show_preview:
            self.remove_class("preview-hidden")
        else:
            self.add_class("preview-hidden")
    
    def toggle_preview(self) -> None:
        """Toggle preview pane visibility."""
        self.show_preview = not self.show_preview
    
    def resize_panes(self, editor_percent: float) -> None:
        """
        Resize the panes to new proportions.
        
        Args:
            editor_percent: Percentage of width for editor (0.0-1.0)
        """
        preview_percent = 1.0 - editor_percent
        
        # Update CSS dynamically (simplified - real implementation would be more complex)
        self.styles.css = f"""
        .editor-pane {{ width: {editor_percent * 100}%; }}
        .preview-pane {{ width: {preview_percent * 100}%; }}
        """