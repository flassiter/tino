"""
Mock editor implementation for testing.

Provides a test-friendly implementation of the IEditor interface that
simulates all editor operations without UI dependencies, maintaining
operation history for verification in tests.
"""

from typing import Any

from ...core.events.bus import EventBus
from ...core.events.types import (
    CursorMovedEvent,
    SelectionChangedEvent,
    TextChangedEvent,
)
from ...core.interfaces.editor import IEditor


class MockEditor(IEditor):
    """
    Mock editor implementation for testing.

    Simulates all editor operations without UI dependencies and maintains
    detailed operation history for test verification.
    """

    def __init__(self, event_bus: EventBus | None = None):
        """
        Initialize mock editor.

        Args:
            event_bus: Optional event bus for testing event emission
        """
        self._event_bus = event_bus
        self._content = ""
        self._cursor_line = 0
        self._cursor_column = 0
        self._selection_start = 0
        self._selection_end = 0
        self._modified = False

        # Undo/redo stacks
        self._undo_stack: list[dict[str, Any]] = []
        self._redo_stack: list[dict[str, Any]] = []
        self._max_undo = 100

        # Operation history for testing
        self._operation_history: list[dict[str, Any]] = []
        self._event_history: list[Any] = []

        # Testing configuration
        self._simulate_find_failures = False
        self._simulate_undo_failures = False

    def get_content(self) -> str:
        """Get the current text content of the editor."""
        self._record_operation("get_content", result=self._content)
        return self._content

    def set_content(self, text: str) -> None:
        """Set the entire text content of the editor."""
        old_content = self._content

        # Record undo operation
        self._push_undo(
            {
                "operation": "set_content",
                "old_content": old_content,
                "new_content": text,
                "old_cursor": (self._cursor_line, self._cursor_column),
                "old_selection": (self._selection_start, self._selection_end),
            }
        )

        self._content = text
        self._update_cursor_after_content_change()
        self.set_modified(True)

        self._record_operation("set_content", text=text, old_content=old_content)
        self._emit_text_changed(text, old_content, "replace", 0, len(old_content))

    def insert_text(self, position: int, text: str) -> None:
        """Insert text at the specified position."""
        if position < 0 or position > len(self._content):
            raise IndexError(f"Position {position} out of range")

        old_content = self._content

        # Record undo operation
        self._push_undo(
            {
                "operation": "delete_range",
                "start": position,
                "end": position + len(text),
                "old_cursor": (self._cursor_line, self._cursor_column),
            }
        )

        self._content = self._content[:position] + text + self._content[position:]
        self._update_cursor_after_insert(position, text)
        self.set_modified(True)

        self._record_operation("insert_text", position=position, text=text)
        self._emit_text_changed(
            self._content, old_content, "insert", position, len(text)
        )

    def delete_range(self, start: int, end: int) -> str:
        """Delete text within the specified range."""
        if start < 0 or end > len(self._content) or start > end:
            raise IndexError(f"Invalid range [{start}, {end})")

        old_content = self._content
        deleted_text = self._content[start:end]

        # Record undo operation
        self._push_undo(
            {
                "operation": "insert_text",
                "position": start,
                "text": deleted_text,
                "old_cursor": (self._cursor_line, self._cursor_column),
            }
        )

        self._content = self._content[:start] + self._content[end:]
        self._update_cursor_after_delete(start, end)
        self.set_modified(True)

        self._record_operation(
            "delete_range", start=start, end=end, deleted_text=deleted_text
        )
        self._emit_text_changed(
            self._content, old_content, "delete", start, end - start
        )

        return deleted_text

    def get_selection(self) -> tuple[int, int]:
        """Get the current selection range."""
        result = (self._selection_start, self._selection_end)
        self._record_operation("get_selection", result=result)
        return result

    def set_selection(self, start: int, end: int) -> None:
        """Set the selection range."""
        content_len = len(self._content)
        start = max(0, min(start, content_len))
        end = max(start, min(end, content_len))

        old_selection = (self._selection_start, self._selection_end)
        self._selection_start = start
        self._selection_end = end

        selected_text = self._content[start:end] if start != end else ""

        self._record_operation(
            "set_selection", start=start, end=end, old_selection=old_selection
        )

        if old_selection != (start, end):
            self._emit_selection_changed(start, end, selected_text)

    def get_cursor_position(self) -> tuple[int, int, int]:
        """Get the current cursor position."""
        absolute_pos = self._calculate_absolute_position(
            self._cursor_line, self._cursor_column
        )
        result = (self._cursor_line, self._cursor_column, absolute_pos)
        self._record_operation("get_cursor_position", result=result)
        return result

    def set_cursor_position(self, line: int, column: int) -> None:
        """Set the cursor position."""
        old_position = (self._cursor_line, self._cursor_column)

        # Validate and clamp values
        lines = self._content.split("\n")
        line = max(0, min(line, len(lines) - 1))

        if line < len(lines):
            column = max(0, min(column, len(lines[line])))
        else:
            column = 0

        self._cursor_line = line
        self._cursor_column = column

        old_abs = self._calculate_absolute_position(old_position[0], old_position[1])
        new_abs = self._calculate_absolute_position(line, column)

        self._record_operation(
            "set_cursor_position", line=line, column=column, old_position=old_position
        )

        if old_position != (line, column):
            self._emit_cursor_moved(
                line, column, new_abs, old_position[0], old_position[1], old_abs
            )

    def undo(self) -> bool:
        """Undo the last operation."""
        if self._simulate_undo_failures or not self._undo_stack:
            self._record_operation("undo", result=False)
            return False

        operation = self._undo_stack.pop()
        self._redo_stack.append(self._create_redo_operation())

        self._apply_undo_operation(operation)

        self._record_operation("undo", result=True, undo_operation=operation)
        return True

    def redo(self) -> bool:
        """Redo the last undone operation."""
        if not self._redo_stack:
            self._record_operation("redo", result=False)
            return False

        operation = self._redo_stack.pop()
        self._undo_stack.append(self._create_undo_operation())

        self._apply_redo_operation(operation)

        self._record_operation("redo", result=True, redo_operation=operation)
        return True

    def can_undo(self) -> bool:
        """Check if undo is available."""
        result = len(self._undo_stack) > 0 and not self._simulate_undo_failures
        self._record_operation("can_undo", result=result)
        return result

    def can_redo(self) -> bool:
        """Check if redo is available."""
        result = len(self._redo_stack) > 0
        self._record_operation("can_redo", result=result)
        return result

    def get_selected_text(self) -> str:
        """Get the currently selected text."""
        if self._selection_start == self._selection_end:
            result = ""
        else:
            result = self._content[self._selection_start : self._selection_end]

        self._record_operation("get_selected_text", result=result)
        return result

    def replace_selection(self, text: str) -> None:
        """Replace the current selection with new text."""
        start = self._selection_start
        end = self._selection_end

        if start == end:
            # No selection, just insert
            self.insert_text(start, text)
        else:
            # Replace selection
            old_content = self._content
            selected_text = self._content[start:end]

            # Record undo operation
            self._push_undo(
                {
                    "operation": "replace_selection",
                    "start": start,
                    "old_text": selected_text,
                    "new_text": text,
                    "old_cursor": (self._cursor_line, self._cursor_column),
                }
            )

            self._content = self._content[:start] + text + self._content[end:]

            # Update cursor to end of replacement
            new_pos = start + len(text)
            self._update_cursor_from_absolute_position(new_pos)

            # Clear selection
            self._selection_start = new_pos
            self._selection_end = new_pos

            self.set_modified(True)

            self._record_operation(
                "replace_selection",
                text=text,
                start=start,
                end=end,
                selected_text=selected_text,
            )
            self._emit_text_changed(
                self._content, old_content, "replace", start, len(selected_text)
            )

    def get_line_count(self) -> int:
        """Get the number of lines in the document."""
        result = max(1, self._content.count("\n") + 1)
        self._record_operation("get_line_count", result=result)
        return result

    def get_line_text(self, line_number: int) -> str:
        """Get the text of a specific line."""
        lines = self._content.split("\n")

        if line_number < 0 or line_number >= len(lines):
            raise IndexError(f"Line {line_number} out of range")

        result = lines[line_number]
        self._record_operation("get_line_text", line_number=line_number, result=result)
        return result

    def find_text(
        self, pattern: str, start: int = 0, case_sensitive: bool = True
    ) -> tuple[int, int] | None:
        """Find the next occurrence of text."""
        if self._simulate_find_failures:
            self._record_operation(
                "find_text",
                pattern=pattern,
                start=start,
                case_sensitive=case_sensitive,
                result=None,
            )
            return None

        content = self._content
        search_content = content if case_sensitive else content.lower()
        search_pattern = pattern if case_sensitive else pattern.lower()

        pos = search_content.find(search_pattern, start)
        result = None if pos == -1 else (pos, pos + len(pattern))

        self._record_operation(
            "find_text",
            pattern=pattern,
            start=start,
            case_sensitive=case_sensitive,
            result=result,
        )
        return result

    def is_modified(self) -> bool:
        """Check if the content has been modified since last save."""
        self._record_operation("is_modified", result=self._modified)
        return self._modified

    def set_modified(self, modified: bool) -> None:
        """Set the modified state."""
        old_modified = self._modified
        self._modified = modified
        self._record_operation(
            "set_modified", modified=modified, old_modified=old_modified
        )

    def clear_undo_history(self) -> None:
        """Clear the undo/redo history."""
        old_undo_count = len(self._undo_stack)
        old_redo_count = len(self._redo_stack)

        self._undo_stack.clear()
        self._redo_stack.clear()

        self._record_operation(
            "clear_undo_history",
            old_undo_count=old_undo_count,
            old_redo_count=old_redo_count,
        )

    # Testing utilities

    def get_operation_history(self) -> list[dict[str, Any]]:
        """Get the history of operations for testing."""
        return self._operation_history.copy()

    def get_event_history(self) -> list[Any]:
        """Get the history of emitted events for testing."""
        return self._event_history.copy()

    def clear_history(self) -> None:
        """Clear operation and event history."""
        self._operation_history.clear()
        self._event_history.clear()

    def set_simulate_failures(
        self, find_failures: bool = False, undo_failures: bool = False
    ) -> None:
        """Configure failure simulation for testing."""
        self._simulate_find_failures = find_failures
        self._simulate_undo_failures = undo_failures

    def get_undo_stack_size(self) -> int:
        """Get the size of the undo stack."""
        return len(self._undo_stack)

    def get_redo_stack_size(self) -> int:
        """Get the size of the redo stack."""
        return len(self._redo_stack)

    # Internal helper methods

    def _record_operation(self, operation: str, **kwargs) -> None:
        """Record an operation for testing verification."""
        self._operation_history.append(
            {
                "operation": operation,
                "timestamp": len(self._operation_history),
                **kwargs,
            }
        )

    def _push_undo(self, operation: dict[str, Any]) -> None:
        """Push an operation onto the undo stack."""
        self._undo_stack.append(operation)
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack = self._undo_stack[-self._max_undo :]

        # Clear redo stack when new operation is added
        self._redo_stack.clear()

    def _create_redo_operation(self) -> dict[str, Any]:
        """Create a redo operation from current state."""
        return {
            "content": self._content,
            "cursor": (self._cursor_line, self._cursor_column),
            "selection": (self._selection_start, self._selection_end),
            "modified": self._modified,
        }

    def _create_undo_operation(self) -> dict[str, Any]:
        """Create an undo operation from current state."""
        return self._create_redo_operation()

    def _apply_undo_operation(self, operation: dict[str, Any]) -> None:
        """Apply an undo operation by reversing the original operation."""
        op_type = operation["operation"]

        if op_type == "set_content":
            # Restore old content
            self._content = operation["old_content"]
            self._cursor_line, self._cursor_column = operation["old_cursor"]
            if "old_selection" in operation:
                self._selection_start, self._selection_end = operation["old_selection"]

        elif op_type == "insert_text":
            # Remove the inserted text (this reverses delete_range)
            start = operation["position"]
            text = operation["text"]
            end = start + len(text)
            self._content = self._content[:start] + text + self._content[start:]
            self._cursor_line, self._cursor_column = operation["old_cursor"]

        elif op_type == "delete_range":
            # Insert back the deleted text (this reverses insert_text)
            start = operation["start"]
            end = operation["end"]
            self._content = self._content[:start] + self._content[end:]
            self._cursor_line, self._cursor_column = operation["old_cursor"]

        elif op_type == "replace_selection":
            # Restore old text
            start = operation["start"]
            old_text = operation["old_text"]
            new_text = operation["new_text"]
            # Find where new_text is and replace with old_text
            current_end = start + len(new_text)
            self._content = (
                self._content[:start] + old_text + self._content[current_end:]
            )
            self._cursor_line, self._cursor_column = operation["old_cursor"]

    def _apply_redo_operation(self, operation: dict[str, Any]) -> None:
        """Apply a redo operation."""
        self._content = operation["content"]
        self._cursor_line, self._cursor_column = operation["cursor"]
        self._selection_start, self._selection_end = operation["selection"]
        self._modified = operation["modified"]

    def _calculate_absolute_position(self, line: int, column: int) -> int:
        """Calculate absolute position from line/column."""
        lines = self._content.split("\n")
        position = 0

        for i in range(min(line, len(lines))):
            if i < len(lines):
                position += len(lines[i])
                if i < len(lines) - 1:  # Add newline except for last line
                    position += 1

        position += min(column, len(lines[line]) if line < len(lines) else 0)
        return position

    def _update_cursor_from_absolute_position(self, position: int) -> None:
        """Update cursor position from absolute position."""
        lines = self._content.split("\n")
        current_pos = 0

        for line_num, line in enumerate(lines):
            if current_pos + len(line) >= position:
                self._cursor_line = line_num
                self._cursor_column = position - current_pos
                return
            current_pos += len(line) + 1  # +1 for newline

        # Position is at end
        self._cursor_line = max(0, len(lines) - 1)
        self._cursor_column = len(lines[-1]) if lines else 0

    def _update_cursor_after_content_change(self) -> None:
        """Update cursor position after content changes."""
        lines = self._content.split("\n")
        if self._cursor_line >= len(lines):
            self._cursor_line = max(0, len(lines) - 1)

        if self._cursor_line < len(lines):
            line_length = len(lines[self._cursor_line])
            if self._cursor_column > line_length:
                self._cursor_column = line_length

    def _update_cursor_after_insert(self, position: int, text: str) -> None:
        """Update cursor position after text insertion."""
        abs_cursor = self._calculate_absolute_position(
            self._cursor_line, self._cursor_column
        )

        if position <= abs_cursor:
            # Insertion before cursor, move cursor
            new_abs = abs_cursor + len(text)
            self._update_cursor_from_absolute_position(new_abs)

    def _update_cursor_after_delete(self, start: int, end: int) -> None:
        """Update cursor position after text deletion."""
        abs_cursor = self._calculate_absolute_position(
            self._cursor_line, self._cursor_column
        )

        if abs_cursor >= end:
            # Cursor after deleted range
            new_abs = abs_cursor - (end - start)
            self._update_cursor_from_absolute_position(new_abs)
        elif abs_cursor > start:
            # Cursor within deleted range
            self._update_cursor_from_absolute_position(start)

    def _emit_text_changed(
        self,
        content: str,
        old_content: str,
        change_type: str,
        position: int,
        length: int,
    ) -> None:
        """Emit text changed event."""
        if self._event_bus:
            event = TextChangedEvent(
                content=content,
                old_content=old_content,
                change_type=change_type,
                position=position,
                length=length,
                source="MockEditor",
            )
            self._event_bus.emit(event)
            self._event_history.append(event)

    def _emit_selection_changed(self, start: int, end: int, selected_text: str) -> None:
        """Emit selection changed event."""
        if self._event_bus:
            event = SelectionChangedEvent(
                start=start, end=end, selected_text=selected_text, source="MockEditor"
            )
            self._event_bus.emit(event)
            self._event_history.append(event)

    def _emit_cursor_moved(
        self,
        line: int,
        column: int,
        position: int,
        old_line: int,
        old_column: int,
        old_position: int,
    ) -> None:
        """Emit cursor moved event."""
        if self._event_bus:
            event = CursorMovedEvent(
                line=line,
                column=column,
                position=position,
                old_line=old_line,
                old_column=old_column,
                old_position=old_position,
                source="MockEditor",
            )
            self._event_bus.emit(event)
            self._event_history.append(event)
