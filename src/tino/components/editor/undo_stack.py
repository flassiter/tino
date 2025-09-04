"""
Undo/redo stack for managing text editing operations.

Maintains a history of operations with configurable maximum size,
allowing for efficient undo and redo functionality.
"""

from collections import deque
from dataclasses import dataclass


@dataclass
class UndoOperation:
    """Represents a single undoable operation."""

    operation_type: str  # "insert", "delete", "replace"
    position: int  # Position in text where operation occurred
    old_text: str  # Text before the operation
    new_text: str  # Text after the operation
    old_cursor: tuple[int, int]  # (line, column) before operation
    new_cursor: tuple[int, int]  # (line, column) after operation

    def reverse(self) -> "UndoOperation":
        """Create the reverse operation for undo."""
        reverse_type = {"insert": "delete", "delete": "insert", "replace": "replace"}

        return UndoOperation(
            operation_type=reverse_type[self.operation_type],
            position=self.position,
            old_text=self.new_text,
            new_text=self.old_text,
            old_cursor=self.new_cursor,
            new_cursor=self.old_cursor,
        )


class UndoStack:
    """
    Manages undo/redo operations with a maximum history size.

    Provides efficient undo and redo functionality while managing
    memory usage by limiting the number of stored operations.
    """

    def __init__(self, max_size: int = 100):
        """
        Initialize undo stack.

        Args:
            max_size: Maximum number of operations to store
        """
        self.max_size = max_size
        self._undo_stack: deque[UndoOperation] = deque(maxlen=max_size)
        self._redo_stack: deque[UndoOperation] = deque(maxlen=max_size)
        self._group_id: str | None = None
        self._group_operations: list[UndoOperation] = []

    def push_operation(self, operation: UndoOperation) -> None:
        """
        Add a new operation to the undo stack.

        Args:
            operation: The operation to add
        """
        if self._group_id:
            # We're in a group, collect operations
            self._group_operations.append(operation)
            return

        # Clear redo stack when new operation is added
        self._redo_stack.clear()

        # Add to undo stack
        self._undo_stack.append(operation)

    def start_group(self, group_id: str) -> None:
        """
        Start grouping operations together.

        Args:
            group_id: Identifier for the group
        """
        self._group_id = group_id
        self._group_operations.clear()

    def end_group(self) -> None:
        """End the current operation group."""
        if self._group_id and self._group_operations:
            # Create a compound operation
            group_op = UndoOperation(
                operation_type="group",
                position=self._group_operations[0].position,
                old_text="",  # Will be handled specially
                new_text="",  # Will be handled specially
                old_cursor=self._group_operations[0].old_cursor,
                new_cursor=self._group_operations[-1].new_cursor,
            )
            # Store the group operations in the operation
            group_op.group_operations = self._group_operations.copy()

            # Clear redo stack and add group
            self._redo_stack.clear()
            self._undo_stack.append(group_op)

        self._group_id = None
        self._group_operations.clear()

    def can_undo(self) -> bool:
        """
        Check if undo is available.

        Returns:
            True if operations can be undone
        """
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """
        Check if redo is available.

        Returns:
            True if operations can be redone
        """
        return len(self._redo_stack) > 0

    def undo(self) -> UndoOperation | None:
        """
        Get the next operation to undo.

        Returns:
            The operation to undo, or None if no operations available
        """
        if not self._undo_stack:
            return None

        operation = self._undo_stack.pop()
        self._redo_stack.append(operation)

        return operation

    def redo(self) -> UndoOperation | None:
        """
        Get the next operation to redo.

        Returns:
            The operation to redo, or None if no operations available
        """
        if not self._redo_stack:
            return None

        operation = self._redo_stack.pop()
        self._undo_stack.append(operation)

        return operation

    def clear(self) -> None:
        """Clear all undo and redo history."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._group_id = None
        self._group_operations.clear()

    def get_undo_count(self) -> int:
        """Get the number of available undo operations."""
        return len(self._undo_stack)

    def get_redo_count(self) -> int:
        """Get the number of available redo operations."""
        return len(self._redo_stack)
