"""
Commands component package.

This package implements the command system for the tino editor, providing:
- Command pattern implementation for all user actions
- Keybinding management with customization
- Command registry for name-based lookup
- Command palette backend
- Quick file switching functionality
"""

from .command_base import BaseCommand
from .registry import CommandRegistry
from .keybindings import KeybindingManager
from .categories import CommandCategory

__all__ = [
    'BaseCommand',
    'CommandRegistry', 
    'KeybindingManager',
    'CommandCategory',
]