"""
Editor component package.

Provides text editing functionality with undo/redo support, selection management,
and event emission through a wrapper around Textual's TextArea widget.
"""

from .editor_component import EditorComponent
from .mock import MockEditor
from .undo_stack import UndoStack, UndoOperation
from .selection_manager import SelectionManager
from .cursor_tracker import CursorTracker
from .text_metrics import TextMetrics

__all__ = [
    "EditorComponent",
    "MockEditor",
    "UndoStack",
    "UndoOperation", 
    "SelectionManager",
    "CursorTracker",
    "TextMetrics"
]