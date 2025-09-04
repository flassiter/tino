"""
Recent Files Manager for tracking recently opened files.

Maintains an ordered list of recently opened files with a maximum limit
and provides quick access to the last opened file for Ctrl+Tab functionality.
"""

import logging
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Iterator, List, Optional

logger = logging.getLogger(__name__)


class RecentFilesManager:
    """
    Manages a list of recently opened files.
    
    Maintains an ordered list of recently opened files with thread-safety
    and provides quick access to the most recently opened file.
    """
    
    DEFAULT_MAX_FILES = 30
    
    def __init__(self, max_files: int = DEFAULT_MAX_FILES) -> None:
        """
        Initialize the recent files manager.
        
        Args:
            max_files: Maximum number of recent files to track
        """
        self.max_files = max(1, max_files)  # At least 1 file
        self._files: OrderedDict[Path, float] = OrderedDict()
        self._lock = threading.RLock()
        self._last_file: Optional[Path] = None
    
    def add_file(self, file_path: Path) -> None:
        """
        Add a file to the recent files list.
        
        If the file is already in the list, it's moved to the front.
        If the list exceeds max_files, the oldest entry is removed.
        
        Args:
            file_path: Path to add to recent files
        """
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        # Resolve to absolute path for consistency
        try:
            file_path = file_path.resolve()
        except OSError:
            # If we can't resolve, use as-is
            pass
        
        with self._lock:
            import time
            current_time = time.time()
            
            # Store the current first file as the last file (for Ctrl+Tab)
            if self._files and file_path not in self._files:
                # Only update last_file if we're adding a new file
                self._last_file = next(iter(self._files), None)
            
            # Remove if already exists (will be re-added at front)
            if file_path in self._files:
                del self._files[file_path]
            
            # Add to front
            self._files[file_path] = current_time
            self._files.move_to_end(file_path, last=False)
            
            # Trim if too many files
            while len(self._files) > self.max_files:
                oldest_file, _ = self._files.popitem(last=True)
                logger.debug(f"Removed old recent file: {oldest_file}")
            
            logger.debug(f"Added recent file: {file_path} (total: {len(self._files)})")
    
    def get_recent_files(self, limit: Optional[int] = None) -> List[Path]:
        """
        Get the list of recent files, most recent first.
        
        Args:
            limit: Maximum number of files to return (None for all)
            
        Returns:
            List of recent file paths, most recent first
        """
        with self._lock:
            files = list(self._files.keys())
            
            if limit is not None and limit > 0:
                files = files[:limit]
            
            return files
    
    def get_last_file(self) -> Optional[Path]:
        """
        Get the most recently opened file.
        
        Returns:
            Path to the most recent file, or None if no files
        """
        with self._lock:
            # Return the most recent file (first in the ordered dict)
            files = list(self._files.keys())
            if files:
                return files[0]
            
            return None
    
    def remove_file(self, file_path: Path) -> bool:
        """
        Remove a file from the recent files list.
        
        Args:
            file_path: Path to remove
            
        Returns:
            True if file was removed, False if it wasn't in the list
        """
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        try:
            file_path = file_path.resolve()
        except OSError:
            pass
        
        with self._lock:
            if file_path in self._files:
                del self._files[file_path]
                
                # Update last_file if it was the removed file
                if self._last_file == file_path:
                    self._last_file = next(iter(self._files), None)
                
                logger.debug(f"Removed recent file: {file_path}")
                return True
            
            return False
    
    def clear(self) -> None:
        """Clear all recent files."""
        with self._lock:
            self._files.clear()
            self._last_file = None
            logger.debug("Cleared all recent files")
    
    def contains(self, file_path: Path) -> bool:
        """
        Check if a file is in the recent files list.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file is in the recent files list
        """
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        try:
            file_path = file_path.resolve()
        except OSError:
            pass
        
        with self._lock:
            return file_path in self._files
    
    def get_file_info(self, file_path: Path) -> Optional[dict]:
        """
        Get information about a recent file.
        
        Args:
            file_path: Path to get info for
            
        Returns:
            Dictionary with file info, None if not in recent files
        """
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        
        try:
            file_path = file_path.resolve()
        except OSError:
            pass
        
        with self._lock:
            if file_path not in self._files:
                return None
            
            access_time = self._files[file_path]
            files_list = list(self._files.keys())
            position = files_list.index(file_path)
            
            return {
                'path': file_path,
                'access_time': access_time,
                'position': position,
                'is_last_file': file_path == self._last_file
            }
    
    def cleanup_missing_files(self) -> int:
        """
        Remove files that no longer exist from the recent files list.
        
        Returns:
            Number of files removed
        """
        removed_count = 0
        
        with self._lock:
            missing_files = []
            
            for file_path in self._files:
                if not file_path.exists():
                    missing_files.append(file_path)
            
            for file_path in missing_files:
                del self._files[file_path]
                if self._last_file == file_path:
                    self._last_file = next(iter(self._files), None)
                removed_count += 1
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} missing recent files")
        
        return removed_count
    
    def set_max_files(self, max_files: int) -> None:
        """
        Set the maximum number of recent files to track.
        
        Args:
            max_files: New maximum number of files
        """
        max_files = max(1, max_files)
        
        with self._lock:
            self.max_files = max_files
            
            # Trim if current list is too long
            while len(self._files) > max_files:
                oldest_file, _ = self._files.popitem(last=True)
                logger.debug(f"Removed old recent file due to limit change: {oldest_file}")
    
    def get_stats(self) -> dict:
        """
        Get statistics about the recent files manager.
        
        Returns:
            Dictionary with statistics
        """
        with self._lock:
            return {
                'total_files': len(self._files),
                'max_files': self.max_files,
                'has_last_file': self._last_file is not None,
                'last_file': str(self._last_file) if self._last_file else None,
                'oldest_access_time': min(self._files.values()) if self._files else None,
                'newest_access_time': max(self._files.values()) if self._files else None,
            }
    
    def __len__(self) -> int:
        """Return the number of recent files."""
        with self._lock:
            return len(self._files)
    
    def __contains__(self, file_path: Path) -> bool:
        """Check if a file is in the recent files list."""
        return self.contains(file_path)
    
    def __iter__(self) -> Iterator[Path]:
        """Iterate over recent files, most recent first."""
        with self._lock:
            return iter(list(self._files.keys()))