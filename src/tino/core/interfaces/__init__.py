"""
Core interfaces for the tino editor components.

These abstract base classes define the contracts that components must implement,
enabling loose coupling and testability through dependency injection.
"""

from .command import ICommand
from .editor import IEditor
from .file_manager import IFileManager
from .renderer import IRenderer

__all__ = [
    "ICommand",
    "IEditor",
    "IFileManager",
    "IRenderer",
]
