"""
Editor component implementation using Textual's TextArea widget.

Provides a complete implementation of the IEditor interface wrapped around
Textual's TextArea widget with undo/redo, selection management, and event emission.
"""

from typing import Optional, Tuple
from textual.widgets import TextArea
from textual.events import Key

from ...core.interfaces.editor import IEditor
from ...core.events.bus import EventBus
from ...core.events.types import TextChangedEvent, SelectionChangedEvent, CursorMovedEvent
from .undo_stack import UndoStack, UndoOperation
from .selection_manager import SelectionManager
from .cursor_tracker import CursorTracker
from .text_metrics import TextMetrics


class EditorComponent(IEditor):
    """
    TextArea-based editor implementation.
    
    Wraps Textual's TextArea widget to provide a complete IEditor interface
    with undo/redo support, selection management, and event emission.
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        Initialize editor component.
        
        Args:
            event_bus: Event bus for component communication
        """
        self._event_bus = event_bus
        self._text_area: Optional[TextArea] = None
        
        # Internal state management
        self._undo_stack = UndoStack(max_size=100)
        self._selection_manager = SelectionManager()
        self._cursor_tracker = CursorTracker()
        self._text_metrics = TextMetrics()
        
        # State tracking
        self._content = ""
        self._modified = False
        self._last_cursor_line = 0
        self._last_cursor_column = 0
        self._last_selection_start = 0
        self._last_selection_end = 0
        
        # Performance optimization
        self._suppress_events = False
    
    def set_text_area(self, text_area: TextArea) -> None:
        """
        Set the underlying TextArea widget.
        
        Args:
            text_area: Textual TextArea widget to wrap
        """
        self._text_area = text_area
        
        # Initialize state from text area
        self._content = str(text_area.text)
        self._update_internal_state()
        
        # Set up event handlers if possible
        # Note: This would need to be integrated with Textual's event system
        # when used in an actual application
    
    def get_content(self) -> str:
        """Get the current text content of the editor."""
        if self._text_area:
            return str(self._text_area.text)
        return self._content
    
    def set_content(self, text: str) -> None:
        """Set the entire text content of the editor."""
        old_content = self.get_content()
        old_cursor = self.get_cursor_position()
        
        # Create undo operation
        operation = UndoOperation(
            operation_type="replace",
            position=0,
            old_text=old_content,
            new_text=text,
            old_cursor=(old_cursor[0], old_cursor[1]),
            new_cursor=(0, 0)  # Reset cursor to start
        )
        
        if self._text_area:
            self._text_area.text = text
        
        self._content = text
        self._update_internal_state()
        self.set_modified(True)
        
        # Add to undo stack
        self._undo_stack.push_operation(operation)
        
        # Emit text changed event
        self._emit_text_changed(text, old_content, "replace", 0, len(old_content))
    
    def insert_text(self, position: int, text: str) -> None:
        """Insert text at the specified position."""
        if position < 0 or position > len(self._content):
            raise IndexError(f"Position {position} out of range")
        
        old_content = self._content
        old_cursor = self.get_cursor_position()
        
        # Create undo operation
        operation = UndoOperation(
            operation_type="insert",
            position=position,
            old_text="",
            new_text=text,
            old_cursor=(old_cursor[0], old_cursor[1]),
            new_cursor=(old_cursor[0], old_cursor[1])  # Will be updated
        )
        
        # Perform insertion
        new_content = old_content[:position] + text + old_content[position:]
        
        if self._text_area:
            self._text_area.text = new_content
            
        self._content = new_content
        self._update_internal_state()
        self.set_modified(True)
        
        # Update cursor position
        new_cursor = self._calculate_cursor_after_insert(position, text, old_cursor)
        operation.new_cursor = (new_cursor[0], new_cursor[1])
        
        # Add to undo stack
        self._undo_stack.push_operation(operation)
        
        # Emit events
        self._emit_text_changed(new_content, old_content, "insert", position, len(text))
    
    def delete_range(self, start: int, end: int) -> str:
        """Delete text within the specified range."""
        if start < 0 or end > len(self._content) or start > end:
            raise IndexError(f"Invalid range [{start}, {end})")
        
        old_content = self._content
        old_cursor = self.get_cursor_position()
        deleted_text = old_content[start:end]
        
        # Create undo operation
        operation = UndoOperation(
            operation_type="delete",
            position=start,
            old_text=deleted_text,
            new_text="",
            old_cursor=(old_cursor[0], old_cursor[1]),
            new_cursor=(old_cursor[0], old_cursor[1])  # Will be updated
        )
        
        # Perform deletion
        new_content = old_content[:start] + old_content[end:]
        
        if self._text_area:
            self._text_area.text = new_content
            
        self._content = new_content
        self._update_internal_state()
        self.set_modified(True)
        
        # Update cursor position
        new_cursor = self._calculate_cursor_after_delete(start, end, old_cursor)
        operation.new_cursor = (new_cursor[0], new_cursor[1])
        
        # Add to undo stack
        self._undo_stack.push_operation(operation)
        
        # Emit events
        self._emit_text_changed(new_content, old_content, "delete", start, end - start)
        
        return deleted_text
    
    def get_selection(self) -> Tuple[int, int]:
        """Get the current selection range."""
        if self._text_area and hasattr(self._text_area, 'selection'):
            # Get from TextArea if available
            selection = self._text_area.selection
            return (selection.start, selection.end)
        return self._selection_manager.get_selection()
    
    def set_selection(self, start: int, end: int) -> None:
        """Set the selection range."""
        content_len = len(self._content)
        start = max(0, min(start, content_len))
        end = max(start, min(end, content_len))
        
        if self._text_area and hasattr(self._text_area, 'selection'):
            # Set on TextArea if available
            pass  # TextArea selection API would go here
            
        self._selection_manager.set_selection(start, end)
        
        # Emit selection changed event
        selected_text = self._content[start:end] if start != end else ""
        self._emit_selection_changed(start, end, selected_text)
    
    def get_cursor_position(self) -> Tuple[int, int, int]:
        """Get the current cursor position."""
        if self._text_area and hasattr(self._text_area, 'cursor_position'):
            # Get from TextArea if available
            pass  # TextArea cursor API would go here
            
        return self._cursor_tracker.get_line_column_position()
    
    def set_cursor_position(self, line: int, column: int) -> None:
        """Set the cursor position."""
        old_position = self.get_cursor_position()
        
        if self._text_area and hasattr(self._text_area, 'cursor_position'):
            # Set on TextArea if available
            pass  # TextArea cursor API would go here
            
        self._cursor_tracker.set_line_column(line, column)
        
        # Emit cursor moved event
        new_position = self._cursor_tracker.get_line_column_position()
        self._emit_cursor_moved(
            new_position[0], new_position[1], new_position[2],
            old_position[0], old_position[1], old_position[2]
        )
    
    def undo(self) -> bool:
        """Undo the last operation."""
        operation = self._undo_stack.undo()
        if not operation:
            return False
            
        self._apply_undo_operation(operation)
        return True
    
    def redo(self) -> bool:
        """Redo the last undone operation."""
        operation = self._undo_stack.redo()
        if not operation:
            return False
            
        self._apply_redo_operation(operation)
        return True
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return self._undo_stack.can_undo()
    
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return self._undo_stack.can_redo()
    
    def get_selected_text(self) -> str:
        """Get the currently selected text."""
        return self._selection_manager.get_selected_text(self._content)
    
    def replace_selection(self, text: str) -> None:
        """Replace the current selection with new text."""
        start, end = self.get_selection()
        
        if start == end:
            # No selection, just insert
            self.insert_text(start, text)
        else:
            # Replace selection
            old_content = self._content
            old_cursor = self.get_cursor_position()
            selected_text = self._content[start:end]
            
            # Create undo operation
            operation = UndoOperation(
                operation_type="replace",
                position=start,
                old_text=selected_text,
                new_text=text,
                old_cursor=(old_cursor[0], old_cursor[1]),
                new_cursor=(old_cursor[0], old_cursor[1])  # Will be updated
            )
            
            # Perform replacement
            new_content, new_cursor_pos = self._selection_manager.replace_selection(
                self._content, text
            )
            
            if self._text_area:
                self._text_area.text = new_content
                
            self._content = new_content
            self._update_internal_state()
            self.set_modified(True)
            
            # Update cursor position after replacement
            self._cursor_tracker.set_position(new_cursor_pos)
            new_cursor = self._cursor_tracker.get_line_column_position()
            operation.new_cursor = (new_cursor[0], new_cursor[1])
            
            # Add to undo stack
            self._undo_stack.push_operation(operation)
            
            # Emit events
            self._emit_text_changed(new_content, old_content, "replace", start, len(selected_text))
    
    def get_line_count(self) -> int:
        """Get the number of lines in the document."""
        return self._text_metrics.get_line_count()
    
    def get_line_text(self, line_number: int) -> str:
        """Get the text of a specific line."""
        if line_number < 0 or line_number >= self.get_line_count():
            raise IndexError(f"Line {line_number} out of range")
            
        return self._cursor_tracker.get_line_text(line_number)
    
    def find_text(self, pattern: str, start: int = 0, case_sensitive: bool = True) -> Optional[Tuple[int, int]]:
        """Find the next occurrence of text."""
        content = self._content
        search_content = content if case_sensitive else content.lower()
        search_pattern = pattern if case_sensitive else pattern.lower()
        
        pos = search_content.find(search_pattern, start)
        if pos == -1:
            return None
            
        return (pos, pos + len(pattern))
    
    def is_modified(self) -> bool:
        """Check if the content has been modified since last save."""
        return self._modified
    
    def set_modified(self, modified: bool) -> None:
        """Set the modified state."""
        self._modified = modified
    
    def clear_undo_history(self) -> None:
        """Clear the undo/redo history."""
        self._undo_stack.clear()
    
    # Helper methods
    
    def _update_internal_state(self) -> None:
        """Update internal state after content changes."""
        self._selection_manager.set_content_length(len(self._content))
        self._cursor_tracker.set_content(self._content)
        self._text_metrics.set_content(self._content)
    
    def _apply_undo_operation(self, operation: UndoOperation) -> None:
        """Apply an undo operation."""
        if operation.operation_type == "insert":
            # Undo insert = delete
            self._content = (
                self._content[:operation.position] + 
                self._content[operation.position + len(operation.new_text):]
            )
        elif operation.operation_type == "delete":
            # Undo delete = insert
            self._content = (
                self._content[:operation.position] + 
                operation.old_text + 
                self._content[operation.position:]
            )
        elif operation.operation_type == "replace":
            # Undo replace = replace back
            end_pos = operation.position + len(operation.new_text)
            self._content = (
                self._content[:operation.position] + 
                operation.old_text + 
                self._content[end_pos:]
            )
        
        if self._text_area:
            self._text_area.text = self._content
            
        self._update_internal_state()
        self._cursor_tracker.set_line_column(
            operation.old_cursor[0], operation.old_cursor[1]
        )
        self.set_modified(True)
    
    def _apply_redo_operation(self, operation: UndoOperation) -> None:
        """Apply a redo operation."""
        if operation.operation_type == "insert":
            self._content = (
                self._content[:operation.position] + 
                operation.new_text + 
                self._content[operation.position:]
            )
        elif operation.operation_type == "delete":
            end_pos = operation.position + len(operation.old_text)
            self._content = (
                self._content[:operation.position] + 
                self._content[end_pos:]
            )
        elif operation.operation_type == "replace":
            end_pos = operation.position + len(operation.old_text)
            self._content = (
                self._content[:operation.position] + 
                operation.new_text + 
                self._content[end_pos:]
            )
        
        if self._text_area:
            self._text_area.text = self._content
            
        self._update_internal_state()
        self._cursor_tracker.set_line_column(
            operation.new_cursor[0], operation.new_cursor[1]
        )
        self.set_modified(True)
    
    def _calculate_cursor_after_insert(
        self, position: int, text: str, old_cursor: Tuple[int, int, int]
    ) -> Tuple[int, int, int]:
        """Calculate cursor position after text insertion."""
        # If insertion is before cursor, move cursor by length of inserted text
        if position <= old_cursor[2]:
            new_pos = old_cursor[2] + len(text)
            self._cursor_tracker.set_position(new_pos)
        
        return self._cursor_tracker.get_line_column_position()
    
    def _calculate_cursor_after_delete(
        self, start: int, end: int, old_cursor: Tuple[int, int, int]
    ) -> Tuple[int, int, int]:
        """Calculate cursor position after text deletion."""
        deleted_length = end - start
        
        if old_cursor[2] >= end:
            # Cursor after deleted range
            new_pos = old_cursor[2] - deleted_length
            self._cursor_tracker.set_position(new_pos)
        elif old_cursor[2] > start:
            # Cursor within deleted range
            self._cursor_tracker.set_position(start)
        
        return self._cursor_tracker.get_line_column_position()
    
    def _emit_text_changed(
        self, content: str, old_content: str, change_type: str, 
        position: int, length: int
    ) -> None:
        """Emit text changed event."""
        if self._event_bus and not self._suppress_events:
            event = TextChangedEvent(
                content=content,
                old_content=old_content,
                change_type=change_type,
                position=position,
                length=length,
                source="EditorComponent"
            )
            self._event_bus.emit(event)
    
    def _emit_selection_changed(self, start: int, end: int, selected_text: str) -> None:
        """Emit selection changed event."""
        if (self._event_bus and not self._suppress_events and 
            (start != self._last_selection_start or end != self._last_selection_end)):
            
            event = SelectionChangedEvent(
                start=start,
                end=end,
                selected_text=selected_text,
                source="EditorComponent"
            )
            self._event_bus.emit(event)
            
            self._last_selection_start = start
            self._last_selection_end = end
    
    def _emit_cursor_moved(
        self, line: int, column: int, position: int,
        old_line: int, old_column: int, old_position: int
    ) -> None:
        """Emit cursor moved event."""
        if (self._event_bus and not self._suppress_events and 
            (line != self._last_cursor_line or column != self._last_cursor_column)):
            
            event = CursorMovedEvent(
                line=line,
                column=column,
                position=position,
                old_line=old_line,
                old_column=old_column,
                old_position=old_position,
                source="EditorComponent"
            )
            self._event_bus.emit(event)
            
            self._last_cursor_line = line
            self._last_cursor_column = column