"""
Event system for component communication.

This package provides the event bus and event type definitions that allow
components to communicate without direct dependencies.
"""

from .bus import EventBus
from .types import (
    CommandExecutedEvent,
    ComponentLoadedEvent,
    ComponentUnloadedEvent,
    CursorMovedEvent,
    Event,
    FileClosedEvent,
    FileOpenedEvent,
    FileSavedEvent,
    ReplaceEvent,
    SearchEvent,
    SelectionChangedEvent,
    TextChangedEvent,
)

__all__ = [
    "EventBus",
    "Event",
    "TextChangedEvent",
    "FileOpenedEvent",
    "FileSavedEvent",
    "FileClosedEvent",
    "SelectionChangedEvent",
    "CursorMovedEvent",
    "ComponentLoadedEvent",
    "ComponentUnloadedEvent",
    "SearchEvent",
    "ReplaceEvent",
    "CommandExecutedEvent",
]
