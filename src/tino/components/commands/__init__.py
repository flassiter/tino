"""
Commands component package.

This package implements the command system for the tino editor, providing:
- Command pattern implementation for all user actions
- Keybinding management with customization
- Command registry for name-based lookup
- Command palette backend
- Quick file switching functionality
"""

from .categories import CommandCategory
from .command_base import BaseCommand
from .keybindings import KeybindingManager
from .registry import CommandRegistry

__all__ = [
    "BaseCommand",
    "CommandRegistry",
    "KeybindingManager",
    "CommandCategory",
]
