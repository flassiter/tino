"""
File manager interface for file operations.

Defines the contract for file management components that handle reading, writing,
backup creation, encoding detection, and file watching operations.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class IFileManager(ABC):
    """
    Interface for file management components.

    Handles all file I/O operations including reading, writing, backup management,
    encoding detection, and recent files tracking.
    """

    @abstractmethod
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
        pass

    @abstractmethod
    def save_file(
        self, file_path: Path, content: str, encoding: str | None = None
    ) -> bool:
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
        pass

    @abstractmethod
    def create_backup(self, file_path: Path) -> Path | None:
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def watch_file(self, file_path: Path) -> bool:
        """
        Start watching a file for external changes.

        Args:
            file_path: Path to the file to watch

        Returns:
            True if watching started successfully
        """
        pass

    @abstractmethod
    def unwatch_file(self, file_path: Path) -> bool:
        """
        Stop watching a file for changes.

        Args:
            file_path: Path to the file to stop watching

        Returns:
            True if watching stopped successfully
        """
        pass

    @abstractmethod
    def file_exists(self, file_path: Path) -> bool:
        """
        Check if a file exists.

        Args:
            file_path: Path to check

        Returns:
            True if file exists
        """
        pass

    @abstractmethod
    def get_file_info(self, file_path: Path) -> tuple[int, float, str]:
        """
        Get file information.

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (size_bytes, modified_timestamp, encoding)

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        pass

    @abstractmethod
    def is_binary_file(self, file_path: Path) -> bool:
        """
        Check if a file is binary.

        Args:
            file_path: Path to check

        Returns:
            True if file appears to be binary
        """
        pass

    @abstractmethod
    def add_recent_file(self, file_path: Path) -> None:
        """
        Add a file to the recent files list.

        Args:
            file_path: Path to add to recent files
        """
        pass

    @abstractmethod
    def get_recent_files(self, limit: int | None = None) -> list[Path]:
        """
        Get the list of recently opened files.

        Args:
            limit: Maximum number of files to return

        Returns:
            List of recent file paths, most recent first
        """
        pass

    @abstractmethod
    def get_last_file(self) -> Path | None:
        """
        Get the last opened file (for quick switching).

        Returns:
            Path to the last file, or None if no previous file
        """
        pass

    @abstractmethod
    def clear_recent_files(self) -> None:
        """Clear the recent files list."""
        pass

    @abstractmethod
    def set_cursor_position(self, file_path: Path, line: int, column: int) -> None:
        """
        Remember cursor position for a file.

        Args:
            file_path: Path to the file
            line: Line number (0-based)
            column: Column number (0-based)
        """
        pass

    @abstractmethod
    def get_cursor_position(self, file_path: Path) -> tuple[int, int] | None:
        """
        Get remembered cursor position for a file.

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (line, column) if remembered, None otherwise
        """
        pass

    @abstractmethod
    def validate_file_path(self, file_path: Path) -> tuple[bool, str]:
        """
        Validate if a file path can be used.

        Args:
            file_path: Path to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass

    @abstractmethod
    def get_temp_file_path(self, original_path: Path) -> Path:
        """
        Get a temporary file path for atomic saves.

        Args:
            original_path: The original file path

        Returns:
            Path to use for temporary file
        """
        pass

    @abstractmethod
    def cleanup_temp_files(self) -> int:
        """
        Clean up any leftover temporary files.

        Returns:
            Number of files cleaned up
        """
        pass
