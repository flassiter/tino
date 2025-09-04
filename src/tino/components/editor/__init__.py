"""
Editor component package.

Provides text editing functionality with undo/redo support, selection management,
and event emission through a wrapper around Textual's TextArea widget.
"""

from .cursor_tracker import CursorTracker
from .editor_component import EditorComponent
from .mock import MockEditor
from .selection_manager import SelectionManager
from .text_metrics import TextMetrics
from .undo_stack import UndoOperation, UndoStack

__all__ = [
    "EditorComponent",
    "MockEditor",
    "UndoStack",
    "UndoOperation",
    "SelectionManager",
    "CursorTracker",
    "TextMetrics",
]
