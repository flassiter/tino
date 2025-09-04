"""
File Manager Component Package.

Provides file I/O operations including atomic saves, backup management,
encoding detection, recent files tracking, and cursor position memory.
"""

from .backup_manager import BackupManager
from .cursor_memory import CursorMemory
from .encoding_detector import EncodingDetector
from .file_manager import FileManager
from .mock import MockFileManager
from .recent_files import RecentFilesManager

__all__ = [
    "FileManager",
    "BackupManager",
    "EncodingDetector",
    "RecentFilesManager",
    "CursorMemory",
    "MockFileManager",
]
