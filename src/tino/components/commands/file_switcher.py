"""
Quick file switching functionality for the tino editor.

Implements Ctrl+Tab (last file) and Ctrl+R (recent files list) functionality
with efficient file switching and history management.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque

from ...core.interfaces.file_manager import IFileManager
from ...core.interfaces.command import CommandError
from .command_base import FileCommand, CommandContext


@dataclass
class FileInfo:
    """Information about a file in the switcher."""
    
    path: Path
    name: str
    modified_time: float
    size: int
    is_current: bool = False
    cursor_position: Optional[Tuple[int, int]] = None


class FileSwitcher:
    """
    Manages quick file switching functionality.
    
    Tracks file history and provides fast switching between recently used files.
    """
    
    def __init__(self, file_manager: IFileManager, max_recent: int = 30):
        """
        Initialize file switcher.
        
        Args:
            file_manager: File manager for file operations
            max_recent: Maximum number of recent files to track
        """
        self._file_manager = file_manager
        self._max_recent = max_recent
        
        # File switching state
        self._current_file: Optional[Path] = None
        self._last_file: Optional[Path] = None
        self._file_history: deque = deque(maxlen=max_recent)
        
        # Tab switching state (for Ctrl+Tab cycling)
        self._tab_cycle_active = False
        self._tab_cycle_index = 0
        self._tab_cycle_files: List[Path] = []
    
    def set_current_file(self, file_path: Optional[Path]) -> None:
        """
        Set the current active file.
        
        Args:
            file_path: Path to the current file (None for new file)
        """
        if file_path == self._current_file:
            return
        
        # Update file history
        if self._current_file is not None:
            self._last_file = self._current_file
            self._add_to_history(self._current_file)
        
        self._current_file = file_path
        
        # Add new file to recent files if it exists
        if file_path and self._file_manager.file_exists(file_path):
            self._file_manager.add_recent_file(file_path)
    
    def get_last_file(self) -> Optional[Path]:
        """
        Get the last opened file (for Ctrl+Tab quick switch).
        
        Returns:
            Path to the last file or None
        """
        # First try the explicitly tracked last file
        if self._last_file and self._last_file != self._current_file:
            return self._last_file
        
        # Fall back to file manager's last file
        return self._file_manager.get_last_file()
    
    def get_recent_files(self, limit: Optional[int] = None) -> List[FileInfo]:
        """
        Get list of recent files with metadata.
        
        Args:
            limit: Maximum number of files to return
            
        Returns:
            List of FileInfo objects
        """
        limit = limit or self._max_recent
        recent_paths = self._file_manager.get_recent_files(limit)
        
        file_infos = []
        for path in recent_paths:
            try:
                if self._file_manager.file_exists(path):
                    size, modified_time, encoding = self._file_manager.get_file_info(path)
                    cursor_pos = self._file_manager.get_cursor_position(path)
                    
                    file_info = FileInfo(
                        path=path,
                        name=path.name,
                        modified_time=modified_time,
                        size=size,
                        is_current=(path == self._current_file),
                        cursor_position=cursor_pos
                    )
                    file_infos.append(file_info)
            except Exception:
                # Skip files that can't be accessed
                continue
        
        return file_infos
    
    def start_tab_cycle(self) -> Optional[Path]:
        """
        Start tab cycling mode (for Ctrl+Tab).
        
        Returns:
            Path to switch to or None if no files available
        """
        recent_files = [info.path for info in self.get_recent_files()]
        
        # Filter out current file
        available_files = [f for f in recent_files if f != self._current_file]
        
        if not available_files:
            return None
        
        self._tab_cycle_active = True
        self._tab_cycle_files = available_files
        self._tab_cycle_index = 0
        
        return self._tab_cycle_files[0]
    
    def continue_tab_cycle(self) -> Optional[Path]:
        """
        Continue tab cycling to next file.
        
        Returns:
            Path to switch to or None if not in cycle mode
        """
        if not self._tab_cycle_active or not self._tab_cycle_files:
            return None
        
        self._tab_cycle_index = (self._tab_cycle_index + 1) % len(self._tab_cycle_files)
        return self._tab_cycle_files[self._tab_cycle_index]
    
    def end_tab_cycle(self) -> Optional[Path]:
        """
        End tab cycling and return selected file.
        
        Returns:
            Path of selected file or None
        """
        if not self._tab_cycle_active:
            return None
        
        selected_file = None
        if self._tab_cycle_files and 0 <= self._tab_cycle_index < len(self._tab_cycle_files):
            selected_file = self._tab_cycle_files[self._tab_cycle_index]
        
        # Reset cycle state
        self._tab_cycle_active = False
        self._tab_cycle_files = []
        self._tab_cycle_index = 0
        
        return selected_file
    
    def cancel_tab_cycle(self) -> None:
        """Cancel tab cycling without switching."""
        self._tab_cycle_active = False
        self._tab_cycle_files = []
        self._tab_cycle_index = 0
    
    def is_tab_cycling(self) -> bool:
        """Check if currently in tab cycle mode."""
        return self._tab_cycle_active
    
    def get_tab_cycle_files(self) -> List[FileInfo]:
        """Get files available in current tab cycle."""
        if not self._tab_cycle_active:
            return []
        
        file_infos = []
        for i, path in enumerate(self._tab_cycle_files):
            try:
                if self._file_manager.file_exists(path):
                    size, modified_time, encoding = self._file_manager.get_file_info(path)
                    cursor_pos = self._file_manager.get_cursor_position(path)
                    
                    file_info = FileInfo(
                        path=path,
                        name=path.name,
                        modified_time=modified_time,
                        size=size,
                        is_current=(i == self._tab_cycle_index),
                        cursor_position=cursor_pos
                    )
                    file_infos.append(file_info)
            except Exception:
                continue
        
        return file_infos
    
    def search_recent_files(self, query: str) -> List[FileInfo]:
        """
        Search recent files by name.
        
        Args:
            query: Search query
            
        Returns:
            List of matching FileInfo objects
        """
        if not query.strip():
            return self.get_recent_files()
        
        query_lower = query.lower()
        all_files = self.get_recent_files()
        
        matching_files = []
        for file_info in all_files:
            if query_lower in file_info.name.lower():
                matching_files.append(file_info)
        
        return matching_files
    
    def _add_to_history(self, file_path: Path) -> None:
        """Add file to internal history (different from file manager's recent files)."""
        # Remove if already exists
        try:
            self._file_history.remove(file_path)
        except ValueError:
            pass
        
        # Add to front
        self._file_history.append(file_path)


class QuickSwitchCommand(FileCommand):
    """Base class for quick file switching commands."""
    
    def __init__(self, context: Optional[CommandContext] = None):
        super().__init__(context)
        self._file_switcher: Optional[FileSwitcher] = None
    
    @property
    def file_switcher(self) -> FileSwitcher:
        """Get or create file switcher instance."""
        if self._file_switcher is None:
            self._file_switcher = FileSwitcher(self.file_manager)
        return self._file_switcher
    
    def _switch_to_file(self, file_path: Path) -> bool:
        """Switch to a specific file."""
        try:
            if not self.file_manager.file_exists(file_path):
                return False
            
            # Store current state for undo
            old_file = self.context.current_file_path
            old_content = ""
            if self.context.editor:
                old_content = self.context.editor.get_content()
            
            self._store_execution_data("old_file", old_file)
            self._store_execution_data("old_content", old_content)
            
            # Read new file
            content = self.file_manager.open_file(file_path)
            
            # Update editor
            if self.context.editor:
                self.context.editor.set_content(content)
                self.context.editor.set_modified(False)
                
                # Restore cursor position
                cursor_pos = self.file_manager.get_cursor_position(file_path)
                if cursor_pos:
                    self.context.editor.set_cursor_position(cursor_pos[0], cursor_pos[1])
            
            # Update application state
            self.context.current_file_path = str(file_path)
            self.context.application_state["current_file"] = str(file_path)
            
            # Update file switcher
            self.file_switcher.set_current_file(file_path)
            
            return True
            
        except Exception:
            return False


class LastFileQuickSwitchCommand(QuickSwitchCommand):
    """Ctrl+Tab - Switch to the last opened file instantly."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute last file switch command."""
        try:
            last_file = self.file_switcher.get_last_file()
            
            if not last_file:
                # No last file available, start tab cycle instead
                cycle_file = self.file_switcher.start_tab_cycle()
                if cycle_file:
                    # Store tab cycle state in application state for UI
                    self.context.application_state['tab_cycle_active'] = True
                    self.context.application_state['tab_cycle_files'] = [
                        str(f.path) for f in self.file_switcher.get_tab_cycle_files()
                    ]
                    return True
                return False
            
            # Switch to last file directly
            success = self._switch_to_file(last_file)
            
            if success:
                self._mark_executed(can_undo=True)
            
            return success
            
        except Exception as e:
            raise CommandError(f"Failed to switch to last file: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Restore previous file."""
        if not self.can_undo():
            return False
        
        try:
            old_file = self._get_execution_data("old_file")
            old_content = self._get_execution_data("old_content", "")
            
            if self.context.editor:
                self.context.editor.set_content(old_content)
                self.context.editor.set_modified(False)
            
            self.context.current_file_path = old_file
            self.context.application_state["current_file"] = old_file
            
            if old_file:
                self.file_switcher.set_current_file(Path(old_file))
            
            return True
            
        except Exception:
            return False
    
    def get_name(self) -> str:
        return "Switch to Last File"
    
    def get_description(self) -> str:
        return "Switch to the last opened file (Ctrl+Tab)"
    
    def get_category(self) -> str:
        return "File"
    
    def get_shortcut(self) -> Optional[str]:
        return "ctrl+tab"


class RecentFilesDialogCommand(FileCommand):
    """Ctrl+R - Show recent files dialog for selection."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute recent files dialog command."""
        try:
            # Get file switcher (creates one if needed)
            if not hasattr(self, '_file_switcher'):
                self._file_switcher = FileSwitcher(self.file_manager)
            
            # Get recent files
            recent_files = self._file_switcher.get_recent_files()
            
            if not recent_files:
                return False
            
            # Store recent files data for UI
            files_data = []
            for file_info in recent_files:
                files_data.append({
                    'path': str(file_info.path),
                    'name': file_info.name,
                    'modified_time': file_info.modified_time,
                    'size': file_info.size,
                    'is_current': file_info.is_current,
                    'cursor_position': file_info.cursor_position
                })
            
            self.context.application_state.update({
                'show_recent_files_dialog': True,
                'recent_files_data': files_data,
                'recent_files_query': ''
            })
            
            self._mark_executed(can_undo=False)  # UI action, no undo needed
            
            return True
            
        except Exception as e:
            raise CommandError(f"Failed to show recent files: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Recent files dialog cannot be undone."""
        return False
    
    def get_name(self) -> str:
        return "Recent Files"
    
    def get_description(self) -> str:
        return "Show recent files dialog (Ctrl+R)"
    
    def get_category(self) -> str:
        return "File"
    
    def get_shortcut(self) -> Optional[str]:
        return "ctrl+r"


class SwitchToFileCommand(QuickSwitchCommand):
    """Switch to a specific file by path."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute switch to file command."""
        try:
            file_path = kwargs.get('file_path') or (args[0] if args else None)
            
            if not file_path:
                raise CommandError("No file path provided", self.get_name())
            
            file_path = Path(file_path)
            success = self._switch_to_file(file_path)
            
            if success:
                self._mark_executed(can_undo=True)
            
            return success
            
        except Exception as e:
            raise CommandError(f"Failed to switch to file: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Restore previous file."""
        if not self.can_undo():
            return False
        
        try:
            old_file = self._get_execution_data("old_file")
            old_content = self._get_execution_data("old_content", "")
            
            if self.context.editor:
                self.context.editor.set_content(old_content)
                self.context.editor.set_modified(False)
            
            self.context.current_file_path = old_file
            self.context.application_state["current_file"] = old_file
            
            if old_file:
                self.file_switcher.set_current_file(Path(old_file))
            
            return True
            
        except Exception:
            return False
    
    def get_name(self) -> str:
        return "Switch to File"
    
    def get_description(self) -> str:
        return "Switch to a specific file"
    
    def get_category(self) -> str:
        return "File"
    
    def validate_parameters(self, *args: Any, **kwargs: Any) -> Optional[str]:
        """Validate file path parameter."""
        file_path = kwargs.get('file_path') or (args[0] if args else None)
        
        if not file_path:
            return "File path is required"
        
        try:
            path_obj = Path(file_path)
            if not path_obj.exists():
                return f"File does not exist: {file_path}"
        except Exception:
            return "Invalid file path format"
        
        return None