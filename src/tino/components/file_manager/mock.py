"""
Mock FileManager implementation for testing.

Provides a mock implementation of IFileManager that simulates file operations
without actually touching the filesystem, useful for unit testing.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import time

from tino.core.interfaces.file_manager import IFileManager
from tino.core.events.bus import EventBus
from tino.core.events.types import FileOpenedEvent, FileSavedEvent, FileClosedEvent

logger = logging.getLogger(__name__)


class MockFileManager(IFileManager):
    """
    Mock file manager for testing.
    
    Simulates file operations in memory without touching the filesystem.
    Maintains operation history for verification in tests.
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        """
        Initialize the mock file manager.
        
        Args:
            event_bus: Event bus for component communication
        """
        self.event_bus = event_bus
        
        # Mock file system
        self._files: Dict[Path, str] = {}  # file_path -> content
        self._file_encodings: Dict[Path, str] = {}  # file_path -> encoding
        self._file_modified_times: Dict[Path, float] = {}  # file_path -> timestamp
        self._binary_files: set[Path] = set()
        
        # Recent files and cursor memory
        self._recent_files: List[Path] = []
        self._last_file: Optional[Path] = None
        self._cursor_positions: Dict[Path, Tuple[int, int]] = {}
        
        # Backup tracking
        self._backup_files: Dict[Path, Path] = {}  # original -> backup path
        self._backed_up_this_session: set[Path] = set()
        
        # Operation history for testing
        self.operation_history: List[Tuple[str, Path, dict]] = []
        
        # Configuration
        self.max_recent_files = 30
        self.large_file_threshold = 50 * 1024 * 1024
        
        # Error simulation
        self._simulate_errors: Dict[str, Exception] = {}
    
    def add_mock_file(self, file_path: Path, content: str, encoding: str = 'utf-8', 
                      is_binary: bool = False) -> None:
        """
        Add a mock file to the simulated filesystem.
        
        Args:
            file_path: Path to the mock file
            content: File content
            encoding: File encoding
            is_binary: Whether file should be treated as binary
        """
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        self._files[file_path] = content
        self._file_encodings[file_path] = encoding
        self._file_modified_times[file_path] = time.time()
        
        if is_binary:
            self._binary_files.add(file_path)
        else:
            self._binary_files.discard(file_path)
        
        logger.debug(f"Added mock file: {file_path}")
    
    def remove_mock_file(self, file_path: Path) -> None:
        """Remove a mock file from the simulated filesystem."""
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        self._files.pop(file_path, None)
        self._file_encodings.pop(file_path, None)
        self._file_modified_times.pop(file_path, None)
        self._binary_files.discard(file_path)
        
        # Clean up related data
        if file_path in self._recent_files:
            self._recent_files.remove(file_path)
        if self._last_file == file_path:
            self._last_file = None
        self._cursor_positions.pop(file_path, None)
        self._backup_files.pop(file_path, None)
        self._backed_up_this_session.discard(file_path)
        
        logger.debug(f"Removed mock file: {file_path}")
    
    def simulate_error(self, operation: str, error: Exception) -> None:
        """
        Configure the mock to simulate an error for a specific operation.
        
        Args:
            operation: Operation name (e.g., 'open_file', 'save_file')
            error: Exception to raise
        """
        self._simulate_errors[operation] = error
    
    def clear_error_simulation(self, operation: Optional[str] = None) -> None:
        """
        Clear error simulation.
        
        Args:
            operation: Specific operation to clear, or None for all
        """
        if operation:
            self._simulate_errors.pop(operation, None)
        else:
            self._simulate_errors.clear()
    
    def _check_for_simulated_error(self, operation: str) -> None:
        """Check if we should simulate an error for this operation."""
        if operation in self._simulate_errors:
            raise self._simulate_errors[operation]
    
    def _record_operation(self, operation: str, file_path: Path, **kwargs) -> None:
        """Record operation in history for testing verification."""
        self.operation_history.append((operation, file_path, kwargs))
    
    def open_file(self, file_path: Path) -> str:
        """Open a mock file and return its content."""
        self._check_for_simulated_error('open_file')
        
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        if file_path not in self._files:
            raise FileNotFoundError(f"Mock file not found: {file_path}")
        
        if file_path in self._binary_files:
            raise ValueError(f"Cannot open binary file: {file_path}")
        
        content = self._files[file_path]
        encoding = self._file_encodings.get(file_path, 'utf-8')
        
        # Add to recent files
        self.add_recent_file(file_path)
        
        # Emit event
        if self.event_bus:
            event = FileOpenedEvent(
                file_path=file_path,
                encoding=encoding,
                size=len(content),
                source="MockFileManager.open_file"
            )
            self.event_bus.emit(event)
        
        self._record_operation('open_file', file_path, encoding=encoding, size=len(content))
        logger.debug(f"Mock opened file: {file_path}")
        return content
    
    def save_file(self, file_path: Path, content: str, encoding: Optional[str] = None) -> bool:
        """Save content to a mock file."""
        self._check_for_simulated_error('save_file')
        
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        if encoding is None:
            encoding = self._file_encodings.get(file_path, 'utf-8')
        
        # Create backup if needed
        backup_created = False
        if (file_path in self._files and 
            file_path not in self._backed_up_this_session):
            
            backup_path = self.create_backup(file_path)
            backup_created = backup_path is not None
        
        # Save file
        self._files[file_path] = content
        self._file_encodings[file_path] = encoding
        self._file_modified_times[file_path] = time.time()
        self._binary_files.discard(file_path)  # Saved text files aren't binary
        
        # Add to recent files
        self.add_recent_file(file_path)
        
        # Emit event
        if self.event_bus:
            event = FileSavedEvent(
                file_path=file_path,
                size=len(content),
                encoding=encoding,
                backup_created=backup_created,
                source="MockFileManager.save_file"
            )
            self.event_bus.emit(event)
        
        self._record_operation('save_file', file_path, 
                              encoding=encoding, size=len(content), 
                              backup_created=backup_created)
        logger.debug(f"Mock saved file: {file_path}")
        return True
    
    def create_backup(self, file_path: Path) -> Optional[Path]:
        """Create a mock backup file."""
        self._check_for_simulated_error('create_backup')
        
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        if file_path not in self._files:
            return None
        
        if file_path in self._backed_up_this_session:
            return None
        
        # Create backup
        backup_path = file_path.with_suffix(file_path.suffix + '.tino.bak')
        self._files[backup_path] = self._files[file_path]
        self._file_encodings[backup_path] = self._file_encodings.get(file_path, 'utf-8')
        self._file_modified_times[backup_path] = time.time()
        
        self._backup_files[file_path] = backup_path
        self._backed_up_this_session.add(file_path)
        
        self._record_operation('create_backup', file_path, backup_path=backup_path)
        logger.debug(f"Mock created backup: {backup_path}")
        return backup_path
    
    def get_encoding(self, file_path: Path) -> str:
        """Get encoding of a mock file."""
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        if file_path not in self._files:
            raise FileNotFoundError(f"Mock file not found: {file_path}")
        
        return self._file_encodings.get(file_path, 'utf-8')
    
    def watch_file(self, file_path: Path) -> bool:
        """Mock file watching (always returns False for MVP)."""
        return False
    
    def unwatch_file(self, file_path: Path) -> bool:
        """Mock file unwatching (always returns False for MVP)."""
        return False
    
    def file_exists(self, file_path: Path) -> bool:
        """Check if a mock file exists."""
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        return file_path in self._files
    
    def get_file_info(self, file_path: Path) -> Tuple[int, float, str]:
        """Get mock file information."""
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        if file_path not in self._files:
            raise FileNotFoundError(f"Mock file not found: {file_path}")
        
        content = self._files[file_path]
        modified_time = self._file_modified_times.get(file_path, time.time())
        encoding = self._file_encodings.get(file_path, 'utf-8')
        
        return (len(content.encode(encoding)), modified_time, encoding)
    
    def is_binary_file(self, file_path: Path) -> bool:
        """Check if a mock file is binary."""
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        return file_path in self._binary_files
    
    def add_recent_file(self, file_path: Path) -> None:
        """Add a file to the mock recent files list."""
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        # Store current first file as last file
        if self._recent_files and file_path not in self._recent_files:
            self._last_file = self._recent_files[0]
        
        # Remove if already exists
        if file_path in self._recent_files:
            self._recent_files.remove(file_path)
        
        # Add to front
        self._recent_files.insert(0, file_path)
        
        # Trim if too many
        while len(self._recent_files) > self.max_recent_files:
            self._recent_files.pop()
    
    def get_recent_files(self, limit: Optional[int] = None) -> List[Path]:
        """Get the mock recent files list."""
        files = self._recent_files[:]
        if limit is not None and limit > 0:
            files = files[:limit]
        return files
    
    def get_last_file(self) -> Optional[Path]:
        """Get the last opened file."""
        if self._last_file and self._last_file in self._recent_files:
            return self._last_file
        
        if len(self._recent_files) >= 2:
            return self._recent_files[1]
        
        return None
    
    def clear_recent_files(self) -> None:
        """Clear the mock recent files list."""
        self._recent_files.clear()
        self._last_file = None
    
    def set_cursor_position(self, file_path: Path, line: int, column: int) -> None:
        """Set cursor position for a mock file."""
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        self._cursor_positions[file_path] = (max(0, line), max(0, column))
    
    def get_cursor_position(self, file_path: Path) -> Optional[Tuple[int, int]]:
        """Get cursor position for a mock file."""
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        return self._cursor_positions.get(file_path)
    
    def validate_file_path(self, file_path: Path) -> Tuple[bool, str]:
        """Validate a mock file path (always valid unless configured otherwise)."""
        return True, ""
    
    def get_temp_file_path(self, original_path: Path) -> Path:
        """Get a mock temporary file path."""
        if not isinstance(original_path, Path):
            original_path = Path(original_path)
        
        return original_path.with_suffix(original_path.suffix + '.tmp')
    
    def cleanup_temp_files(self) -> int:
        """Mock cleanup of temporary files."""
        # Remove any .tmp files from mock filesystem
        temp_files = [p for p in self._files.keys() if p.suffix == '.tmp']
        for temp_file in temp_files:
            self.remove_mock_file(temp_file)
        return len(temp_files)
    
    # Additional methods for testing
    def get_mock_files(self) -> Dict[Path, str]:
        """Get all mock files (for testing)."""
        return self._files.copy()
    
    def get_operation_history(self) -> List[Tuple[str, Path, dict]]:
        """Get operation history (for testing)."""
        return self.operation_history.copy()
    
    def clear_operation_history(self) -> None:
        """Clear operation history."""
        self.operation_history.clear()
    
    def get_backup_files(self) -> Dict[Path, Path]:
        """Get backup files mapping (for testing)."""
        return self._backup_files.copy()
    
    def reset_mock(self) -> None:
        """Reset the mock to initial state."""
        self._files.clear()
        self._file_encodings.clear()
        self._file_modified_times.clear()
        self._binary_files.clear()
        self._recent_files.clear()
        self._last_file = None
        self._cursor_positions.clear()
        self._backup_files.clear()
        self._backed_up_this_session.clear()
        self.operation_history.clear()
        self._simulate_errors.clear()
        logger.debug("Mock file manager reset")