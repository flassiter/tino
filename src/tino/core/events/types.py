"""
Event type definitions for the tino editor.

All events inherit from the base Event class and include timestamp and source
information for debugging and tracing.
"""

import asyncio
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Tuple


@dataclass
class Event(ABC):
    """Base class for all events in the system."""
    
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = field(default="unknown")
    event_id: str = field(default_factory=lambda: f"evt_{id(object())}")
    
    def __post_init__(self) -> None:
        """Ensure event is properly initialized."""
        if not self.source or self.source == "unknown":
            # Try to determine source from call stack
            import inspect
            frame = inspect.currentframe()
            if frame and frame.f_back and frame.f_back.f_back:
                caller = frame.f_back.f_back
                self.source = f"{caller.f_globals.get('__name__', 'unknown')}.{caller.f_code.co_name}"


@dataclass
class TextChangedEvent(Event):
    """Fired when text content changes in the editor."""
    
    content: str = ""
    old_content: str = ""
    change_type: str = "unknown"  # "insert", "delete", "replace"
    position: int = 0
    length: int = 0


@dataclass
class FileOpenedEvent(Event):
    """Fired when a file is opened."""
    
    file_path: Optional[Path] = None
    encoding: str = "utf-8"
    size: int = 0
    modified: bool = False


@dataclass
class FileSavedEvent(Event):
    """Fired when a file is saved."""
    
    file_path: Optional[Path] = None
    size: int = 0
    encoding: str = "utf-8"
    backup_created: bool = False


@dataclass
class FileClosedEvent(Event):
    """Fired when a file is closed."""
    
    file_path: Optional[Path] = None
    was_modified: bool = False
    saved: bool = False


@dataclass
class SelectionChangedEvent(Event):
    """Fired when text selection changes."""
    
    start: int = 0
    end: int = 0
    selected_text: str = ""


@dataclass
class CursorMovedEvent(Event):
    """Fired when cursor position changes."""
    
    line: int = 0
    column: int = 0
    position: int = 0
    old_line: int = 0
    old_column: int = 0
    old_position: int = 0


@dataclass
class ComponentLoadedEvent(Event):
    """Fired when a component is loaded."""
    
    component_name: str = ""
    component_type: str = ""
    load_time_ms: float = 0.0


@dataclass
class ComponentUnloadedEvent(Event):
    """Fired when a component is unloaded."""
    
    component_name: str = ""
    component_type: str = ""
    unload_time_ms: float = 0.0


@dataclass
class SearchEvent(Event):
    """Fired when a search operation is performed."""
    
    pattern: str = ""
    case_sensitive: bool = False
    whole_word: bool = False
    matches_found: int = 0
    current_match: int = 0


@dataclass
class ReplaceEvent(Event):
    """Fired when a replace operation is performed."""
    
    pattern: str = ""
    replacement: str = ""
    replacements_made: int = 0
    case_sensitive: bool = False
    whole_word: bool = False


@dataclass
class CommandExecutedEvent(Event):
    """Fired when a command is executed successfully."""
    
    command_name: str = ""
    args: tuple = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0  # in milliseconds


@dataclass
class CommandFailedEvent(Event):
    """Fired when a command execution fails."""
    
    command_name: str = ""
    error_message: str = ""
    args: tuple = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)