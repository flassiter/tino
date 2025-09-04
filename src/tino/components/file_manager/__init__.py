"""
File Manager Component Package.

Provides file I/O operations including atomic saves, backup management,
encoding detection, recent files tracking, and cursor position memory.
"""

from .file_manager import FileManager
from .backup_manager import BackupManager
from .encoding_detector import EncodingDetector
from .recent_files import RecentFilesManager
from .cursor_memory import CursorMemory
from .mock import MockFileManager

__all__ = [
    "FileManager",
    "BackupManager", 
    "EncodingDetector",
    "RecentFilesManager",
    "CursorMemory",
    "MockFileManager",
]