"""
Cursor Memory for tracking cursor positions in files.

Maintains session-only cursor position memory for each file to restore
cursor position when reopening files during the same session.
"""

import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


class CursorMemory:
    """
    Manages cursor position memory for files.

    Tracks cursor positions (line, column) for each file during the current
    session only. Positions are not persisted between application sessions.
    """

    def __init__(self) -> None:
        """Initialize the cursor memory manager."""
        self._positions: dict[Path, tuple[int, int]] = {}
        self._lock = threading.RLock()

    def set_cursor_position(self, file_path: Path, line: int, column: int) -> None:
        """
        Store cursor position for a file.

        Args:
            file_path: Path to the file
            line: Line number (0-based)
            column: Column number (0-based)
        """
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        # Resolve to absolute path for consistency
        try:
            file_path = file_path.resolve()
        except OSError:
            # If we can't resolve, use as-is
            pass

        # Validate line and column
        line = max(0, int(line))
        column = max(0, int(column))

        with self._lock:
            old_position = self._positions.get(file_path)
            self._positions[file_path] = (line, column)

            if old_position != (line, column):
                logger.debug(
                    f"Updated cursor position for {file_path}: {line}:{column}"
                )

    def get_cursor_position(self, file_path: Path) -> tuple[int, int] | None:
        """
        Get stored cursor position for a file.

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (line, column) if remembered, None otherwise
        """
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        try:
            file_path = file_path.resolve()
        except OSError:
            pass

        with self._lock:
            position = self._positions.get(file_path)
            if position:
                logger.debug(
                    f"Retrieved cursor position for {file_path}: {position[0]}:{position[1]}"
                )
            return position

    def has_cursor_position(self, file_path: Path) -> bool:
        """
        Check if cursor position is stored for a file.

        Args:
            file_path: Path to check

        Returns:
            True if cursor position is remembered
        """
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        try:
            file_path = file_path.resolve()
        except OSError:
            pass

        with self._lock:
            return file_path in self._positions

    def remove_cursor_position(self, file_path: Path) -> bool:
        """
        Remove stored cursor position for a file.

        Args:
            file_path: Path to remove position for

        Returns:
            True if position was removed, False if not found
        """
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        try:
            file_path = file_path.resolve()
        except OSError:
            pass

        with self._lock:
            if file_path in self._positions:
                del self._positions[file_path]
                logger.debug(f"Removed cursor position for {file_path}")
                return True
            return False

    def clear_all_positions(self) -> None:
        """Clear all stored cursor positions."""
        with self._lock:
            count = len(self._positions)
            self._positions.clear()
            if count > 0:
                logger.debug(f"Cleared {count} cursor positions")

    def get_all_positions(self) -> dict[Path, tuple[int, int]]:
        """
        Get all stored cursor positions.

        Returns:
            Dictionary mapping file paths to (line, column) tuples
        """
        with self._lock:
            return dict(self._positions)

    def update_cursor_position(
        self, file_path: Path, delta_line: int = 0, delta_column: int = 0
    ) -> tuple[int, int] | None:
        """
        Update cursor position by delta values.

        Args:
            file_path: Path to the file
            delta_line: Change in line number (can be negative)
            delta_column: Change in column number (can be negative)

        Returns:
            New cursor position if file was found, None otherwise
        """
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        try:
            file_path = file_path.resolve()
        except OSError:
            pass

        with self._lock:
            current_position = self._positions.get(file_path)
            if current_position is None:
                return None

            line, column = current_position
            new_line = max(0, line + delta_line)
            new_column = max(0, column + delta_column)

            self._positions[file_path] = (new_line, new_column)
            logger.debug(
                f"Updated cursor position for {file_path} by delta ({delta_line}, {delta_column}): {new_line}:{new_column}"
            )

            return (new_line, new_column)

    def cleanup_missing_files(self) -> int:
        """
        Remove cursor positions for files that no longer exist.

        Returns:
            Number of positions removed
        """
        removed_count = 0

        with self._lock:
            missing_files = []

            for file_path in self._positions:
                if not file_path.exists():
                    missing_files.append(file_path)

            for file_path in missing_files:
                del self._positions[file_path]
                removed_count += 1

        if removed_count > 0:
            logger.info(
                f"Cleaned up cursor positions for {removed_count} missing files"
            )

        return removed_count

    def get_stats(self) -> dict:
        """
        Get statistics about cursor memory.

        Returns:
            Dictionary with statistics
        """
        with self._lock:
            positions = list(self._positions.values())
            return {
                "total_files": len(self._positions),
                "max_line": max(pos[0] for pos in positions) if positions else None,
                "max_column": max(pos[1] for pos in positions) if positions else None,
                "avg_line": (
                    sum(pos[0] for pos in positions) / len(positions)
                    if positions
                    else None
                ),
                "avg_column": (
                    sum(pos[1] for pos in positions) / len(positions)
                    if positions
                    else None
                ),
            }

    def validate_position(
        self, file_path: Path, max_lines: int | None = None
    ) -> tuple[int, int] | None:
        """
        Validate and potentially adjust cursor position for a file.

        Args:
            file_path: Path to the file
            max_lines: Maximum number of lines in file (None to skip validation)

        Returns:
            Valid cursor position, adjusted if necessary
        """
        position = self.get_cursor_position(file_path)
        if position is None:
            return None

        line, column = position
        adjusted = False

        # Validate line number
        if max_lines is not None and line >= max_lines:
            line = max(0, max_lines - 1)
            adjusted = True

        # Column validation would need content, so we skip it here
        # The editor component can handle column validation when it has the text

        if adjusted:
            self.set_cursor_position(file_path, line, column)
            logger.debug(f"Adjusted cursor position for {file_path} to {line}:{column}")

        return (line, column)

    def import_positions(self, positions: dict[Path, tuple[int, int]]) -> int:
        """
        Import cursor positions from another source.

        Args:
            positions: Dictionary of positions to import

        Returns:
            Number of positions imported
        """
        imported_count = 0

        with self._lock:
            for file_path, position in positions.items():
                if isinstance(position, list | tuple) and len(position) >= 2:
                    line, column = int(position[0]), int(position[1])
                    self.set_cursor_position(file_path, line, column)
                    imported_count += 1

        if imported_count > 0:
            logger.info(f"Imported {imported_count} cursor positions")

        return imported_count

    def __len__(self) -> int:
        """Return the number of stored cursor positions."""
        with self._lock:
            return len(self._positions)

    def __contains__(self, file_path: Path) -> bool:
        """Check if cursor position is stored for a file."""
        return self.has_cursor_position(file_path)
