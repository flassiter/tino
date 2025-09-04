"""
File Manager implementation for file I/O operations.

Provides atomic file saves, backup management, encoding detection,
recent files tracking, and cursor position memory.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from tino.core.interfaces.file_manager import IFileManager
from tino.core.events.bus import EventBus
from tino.core.events.types import FileOpenedEvent, FileSavedEvent, FileClosedEvent

from .backup_manager import BackupManager
from .encoding_detector import EncodingDetector
from .recent_files import RecentFilesManager
from .cursor_memory import CursorMemory

logger = logging.getLogger(__name__)


class FileManager(IFileManager):
    """
    File manager implementation providing all file I/O operations.
    
    Combines backup management, encoding detection, recent files tracking,
    and cursor position memory into a cohesive file management system.
    """
    
    # File size warning threshold (50MB)
    LARGE_FILE_THRESHOLD = 50 * 1024 * 1024
    
    # Binary file detection sample size
    BINARY_SAMPLE_SIZE = 8192
    
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        """
        Initialize the file manager.
        
        Args:
            event_bus: Event bus for component communication
        """
        self.event_bus = event_bus
        self.backup_manager = BackupManager()
        self.encoding_detector = EncodingDetector()
        self.recent_files = RecentFilesManager()
        self.cursor_memory = CursorMemory()
    
    def open_file(self, file_path: Path) -> str:
        """
        Open a file and return its content.
        
        Args:
            file_path: Path to the file to open
            
        Returns:
            File content as string
            
        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file cannot be read
            UnicodeDecodeError: If file encoding cannot be determined
        """
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Check if file is binary
        if self.is_binary_file(file_path):
            raise ValueError(f"Cannot open binary file: {file_path}")
        
        # Check file size and warn if large
        try:
            file_size = file_path.stat().st_size
            if file_size > self.LARGE_FILE_THRESHOLD:
                logger.warning(f"Opening large file ({file_size / 1024 / 1024:.1f}MB): {file_path}")
        except OSError as e:
            logger.warning(f"Could not get file size for {file_path}: {e}")
        
        # Detect encoding
        encoding = self.get_encoding(file_path)
        
        # Read file content
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
                
            # Add to recent files
            self.recent_files.add_file(file_path)
            
            # Emit file opened event
            if self.event_bus:
                event = FileOpenedEvent(
                    file_path=file_path,
                    encoding=encoding,
                    size=len(content),
                    source="FileManager.open_file"
                )
                self.event_bus.emit(event)
            
            logger.info(f"Opened file: {file_path} ({encoding}, {len(content)} chars)")
            return content
            
        except PermissionError as e:
            logger.error(f"Permission denied reading {file_path}: {e}")
            raise
        except UnicodeDecodeError as e:
            logger.error(f"Encoding error reading {file_path}: {e}")
            raise
        except OSError as e:
            logger.error(f"I/O error reading {file_path}: {e}")
            raise
    
    def save_file(self, file_path: Path, content: str, encoding: Optional[str] = None) -> bool:
        """
        Save content to a file atomically.
        
        Args:
            file_path: Path where to save the file
            content: Content to save
            encoding: File encoding (auto-detected if None)
            
        Returns:
            True if save was successful
            
        Raises:
            PermissionError: If file cannot be written
            OSError: If disk space insufficient or other I/O error
        """
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        # Determine encoding
        if encoding is None:
            if file_path.exists():
                encoding = self.get_encoding(file_path)
            else:
                encoding = 'utf-8'
        
        # Create backup if file exists and we haven't backed it up yet
        backup_created = False
        if file_path.exists():
            try:
                backup_path = self.backup_manager.create_backup(file_path)
                backup_created = backup_path is not None
            except (PermissionError, OSError) as e:
                logger.warning(f"Could not create backup for {file_path}: {e}")
        
        # Save file atomically
        try:
            # Create temporary file in same directory for atomic operation
            temp_path = self.get_temp_file_path(file_path)
            
            # Write content to temp file
            with open(temp_path, 'w', encoding=encoding) as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
            
            # Atomically replace original file
            temp_path.replace(file_path)
            
            # Add to recent files
            self.recent_files.add_file(file_path)
            
            # Emit file saved event
            if self.event_bus:
                event = FileSavedEvent(
                    file_path=file_path,
                    size=len(content),
                    encoding=encoding,
                    backup_created=backup_created,
                    source="FileManager.save_file"
                )
                self.event_bus.emit(event)
            
            logger.info(f"Saved file: {file_path} ({encoding}, {len(content)} chars, backup: {backup_created})")
            return True
            
        except PermissionError as e:
            logger.error(f"Permission denied saving {file_path}: {e}")
            # Clean up temp file if it exists
            if 'temp_path' in locals() and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise
        except OSError as e:
            logger.error(f"I/O error saving {file_path}: {e}")
            # Clean up temp file if it exists
            if 'temp_path' in locals() and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise
    
    def create_backup(self, file_path: Path) -> Optional[Path]:
        """
        Create a backup of the specified file.
        
        Args:
            file_path: Path to the file to backup
            
        Returns:
            Path to the backup file if created, None if backup not needed
            
        Raises:
            PermissionError: If backup cannot be created
            OSError: If disk space insufficient
        """
        return self.backup_manager.create_backup(file_path)
    
    def get_encoding(self, file_path: Path) -> str:
        """
        Detect the encoding of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Detected encoding name (e.g., 'utf-8', 'latin-1')
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        return self.encoding_detector.detect_file_encoding(file_path)
    
    def watch_file(self, file_path: Path) -> bool:
        """
        Start watching a file for external changes.
        
        Args:
            file_path: Path to the file to watch
            
        Returns:
            True if watching started successfully
        """
        # File watching is deferred for MVP
        logger.debug(f"File watching not implemented for MVP: {file_path}")
        return False
    
    def unwatch_file(self, file_path: Path) -> bool:
        """
        Stop watching a file for changes.
        
        Args:
            file_path: Path to the file to stop watching
            
        Returns:
            True if watching stopped successfully
        """
        # File watching is deferred for MVP
        logger.debug(f"File watching not implemented for MVP: {file_path}")
        return False
    
    def file_exists(self, file_path: Path) -> bool:
        """
        Check if a file exists.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file exists
        """
        return file_path.exists() if isinstance(file_path, Path) else Path(file_path).exists()
    
    def get_file_info(self, file_path: Path) -> Tuple[int, float, str]:
        """
        Get file information.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (size_bytes, modified_timestamp, encoding)
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            stat_info = file_path.stat()
            encoding = self.get_encoding(file_path)
            return (stat_info.st_size, stat_info.st_mtime, encoding)
        except OSError as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            raise
    
    def is_binary_file(self, file_path: Path) -> bool:
        """
        Check if a file is binary.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file appears to be binary
        """
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        if not file_path.exists():
            return False
        
        try:
            with open(file_path, 'rb') as f:
                sample = f.read(self.BINARY_SAMPLE_SIZE)
            
            return self.encoding_detector.is_binary_data(sample)
            
        except OSError:
            return True  # Assume binary if we can't read it
    
    def add_recent_file(self, file_path: Path) -> None:
        """
        Add a file to the recent files list.
        
        Args:
            file_path: Path to add to recent files
        """
        self.recent_files.add_file(file_path)
    
    def get_recent_files(self, limit: Optional[int] = None) -> List[Path]:
        """
        Get the list of recently opened files.
        
        Args:
            limit: Maximum number of files to return
            
        Returns:
            List of recent file paths, most recent first
        """
        return self.recent_files.get_recent_files(limit)
    
    def get_last_file(self) -> Optional[Path]:
        """
        Get the last opened file (for quick switching).
        
        Returns:
            Path to the last file, or None if no previous file
        """
        return self.recent_files.get_last_file()
    
    def clear_recent_files(self) -> None:
        """Clear the recent files list."""
        self.recent_files.clear()
    
    def set_cursor_position(self, file_path: Path, line: int, column: int) -> None:
        """
        Remember cursor position for a file.
        
        Args:
            file_path: Path to the file
            line: Line number (0-based)
            column: Column number (0-based)
        """
        self.cursor_memory.set_cursor_position(file_path, line, column)
    
    def remember_cursor_position(self, file_path: Path, line: int, column: int) -> None:
        """
        Alias for set_cursor_position for backward compatibility.
        
        Args:
            file_path: Path to the file
            line: Line number (0-based)
            column: Column number (0-based)
        """
        self.set_cursor_position(file_path, line, column)
    
    def get_cursor_position(self, file_path: Path) -> Optional[Tuple[int, int]]:
        """
        Get remembered cursor position for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (line, column) if remembered, None otherwise
        """
        return self.cursor_memory.get_cursor_position(file_path)
    
    def validate_file_path(self, file_path: Path) -> Tuple[bool, str]:
        """
        Validate if a file path can be used.
        
        Args:
            file_path: Path to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        # Check if path is absolute or can be made absolute
        try:
            file_path = file_path.resolve()
        except (OSError, ValueError) as e:
            return False, f"Invalid path: {e}"
        
        # Check parent directory
        parent = file_path.parent
        if not parent.exists():
            return False, f"Parent directory does not exist: {parent}"
        
        if not parent.is_dir():
            return False, f"Parent is not a directory: {parent}"
        
        # Check permissions on parent directory
        if not os.access(parent, os.W_OK):
            return False, f"Cannot write to parent directory: {parent}"
        
        # If file exists, check if we can read/write it
        if file_path.exists():
            if not file_path.is_file():
                return False, f"Path is not a file: {file_path}"
            
            if not os.access(file_path, os.R_OK):
                return False, f"Cannot read file: {file_path}"
            
            if not os.access(file_path, os.W_OK):
                return False, f"Cannot write file: {file_path}"
        
        return True, ""
    
    def get_temp_file_path(self, original_path: Path) -> Path:
        """
        Get a temporary file path for atomic saves.
        
        Args:
            original_path: The original file path
            
        Returns:
            Path to use for temporary file
        """
        if not isinstance(original_path, Path):
            original_path = Path(original_path)
        
        # Create temp file in same directory
        parent = original_path.parent
        prefix = f".tino_temp_{original_path.name}_"
        suffix = ".tmp"
        
        # Use tempfile to get unique name
        with tempfile.NamedTemporaryFile(
            dir=parent,
            prefix=prefix,
            suffix=suffix,
            delete=False
        ) as f:
            return Path(f.name)
    
    def cleanup_temp_files(self) -> int:
        """
        Clean up any leftover temporary files.
        
        Returns:
            Number of files cleaned up
        """
        cleaned = 0
        
        # Clean up temp files in recent directories
        recent_dirs = set()
        for file_path in self.recent_files.get_recent_files():
            recent_dirs.add(file_path.parent)
        
        for directory in recent_dirs:
            try:
                for temp_file in directory.glob(".tino_temp_*"):
                    try:
                        temp_file.unlink()
                        cleaned += 1
                        logger.debug(f"Cleaned up temp file: {temp_file}")
                    except OSError as e:
                        logger.warning(f"Could not clean up temp file {temp_file}: {e}")
            except OSError:
                continue
        
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} temporary files")
        
        return cleaned
    
    def close_file(self, file_path: Path, was_modified: bool = False, saved: bool = False) -> None:
        """
        Handle file closing operations.
        
        Args:
            file_path: Path to the file being closed
            was_modified: Whether the file was modified
            saved: Whether the file was saved before closing
        """
        # Emit file closed event
        if self.event_bus:
            event = FileClosedEvent(
                file_path=file_path,
                was_modified=was_modified,
                saved=saved,
                source="FileManager.close_file"
            )
            self.event_bus.emit(event)
        
        logger.debug(f"Closed file: {file_path} (modified: {was_modified}, saved: {saved})")
    
    def get_manager_stats(self) -> dict:
        """
        Get statistics about the file manager.
        
        Returns:
            Dictionary with manager statistics
        """
        return {
            'recent_files': self.recent_files.get_stats(),
            'cursor_memory': self.cursor_memory.get_stats(),
            'backup_info': {
                'backed_up_files': len(self.backup_manager._backed_up_files)
            }
        }