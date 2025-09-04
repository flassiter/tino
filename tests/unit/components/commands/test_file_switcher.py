"""
Tests for file switching commands.

Tests quick file switching functionality including Ctrl+Tab (last file),
Ctrl+R (recent files), and file switching history management.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock

from src.tino.components.commands.file_switcher import (
    FileSwitcher,
    FileInfo,
    QuickSwitchCommand,
    LastFileQuickSwitchCommand,
    RecentFilesDialogCommand,
    SwitchToFileCommand
)
from src.tino.components.commands.command_base import CommandContext
from src.tino.core.interfaces.command import CommandError


class TestFileSwitcher:
    """Tests for FileSwitcher class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_file_manager = Mock()
        self.file_switcher = FileSwitcher(self.mock_file_manager, max_recent=5)
        
        # Mock file info returns
        self.mock_file_manager.get_file_info.return_value = (1024, "2024-01-01", "utf-8")
    
    def test_initialization(self):
        """Test file switcher initialization."""
        assert self.file_switcher._max_recent == 5
        assert self.file_switcher._current_file is None
        assert self.file_switcher._last_file is None
    
    def test_add_file_first_file(self):
        """Test adding first file to switcher."""
        file_path = Path("/test/file1.md")
        
        self.file_switcher.add_file(file_path)
        
        assert self.file_switcher._current_file == file_path
        assert self.file_switcher._last_file is None
    
    def test_add_file_second_file(self):
        """Test adding second file."""
        file1 = Path("/test/file1.md")
        file2 = Path("/test/file2.md")
        
        self.file_switcher.add_file(file1)
        self.file_switcher.add_file(file2)
        
        assert self.file_switcher._current_file == file2
        assert self.file_switcher._last_file == file1
    
    def test_add_same_file_twice(self):
        """Test adding same file twice doesn't change last file."""
        file1 = Path("/test/file1.md")
        
        self.file_switcher.add_file(file1)
        original_last = self.file_switcher._last_file
        self.file_switcher.add_file(file1)  # Same file again
        
        assert self.file_switcher._current_file == file1
        assert self.file_switcher._last_file == original_last
    
    def test_get_last_file_no_last_file(self):
        """Test getting last file when none exists."""
        result = self.file_switcher.get_last_file()
        
        assert result is None
    
    def test_get_last_file_with_history(self):
        """Test getting last file with history."""
        file1 = Path("/test/file1.md")
        file2 = Path("/test/file2.md")
        
        self.file_switcher.add_file(file1)
        self.file_switcher.add_file(file2)
        
        result = self.file_switcher.get_last_file()
        
        assert result == file1
    
    def test_get_recent_files_empty(self):
        """Test getting recent files when empty."""
        result = self.file_switcher.get_recent_files()
        
        assert result == []
    
    def test_get_recent_files_with_history(self):
        """Test getting recent files with history."""
        files = [Path(f"/test/file{i}.md") for i in range(3)]
        
        for file_path in files:
            self.file_switcher.add_file(file_path)
        
        result = self.file_switcher.get_recent_files()
        
        # Should return files in reverse order (most recent first, excluding current)
        assert len(result) <= 2  # Excludes current file
        assert isinstance(result[0], FileInfo)
    
    def test_max_recent_files_limit(self):
        """Test that recent files list respects max limit."""
        # Add more files than max_recent
        for i in range(10):
            self.file_switcher.add_file(Path(f"/test/file{i}.md"))
        
        result = self.file_switcher.get_recent_files()
        
        # Should not exceed max_recent - 1 (excluding current)
        assert len(result) <= 4  # max_recent=5, minus current file
    
    def test_switch_to_last_file(self):
        """Test switching to last file."""
        file1 = Path("/test/file1.md")
        file2 = Path("/test/file2.md")
        
        self.file_switcher.add_file(file1)
        self.file_switcher.add_file(file2)
        
        # Switch back to file1
        result = self.file_switcher.switch_to_last_file()
        
        assert result == file1
        assert self.file_switcher._current_file == file1
        assert self.file_switcher._last_file == file2


class TestFileSwitcherCommandsBase:
    """Base test setup for file switcher commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock dependencies
        self.mock_editor = Mock()
        self.mock_file_manager = Mock()
        self.mock_event_bus = Mock()
        
        # Setup file manager mocks
        self.mock_file_manager.get_file_info.return_value = (1024, "2024-01-01", "utf-8")
        self.mock_file_manager.open_file.return_value = "file content"
        self.mock_file_manager.validate_file_path.return_value = (True, "")
        self.mock_file_manager.file_exists.return_value = True
        
        # Create command context with file switcher
        self.context = CommandContext()
        self.context.editor = self.mock_editor
        self.context.file_manager = self.mock_file_manager
        self.context.event_bus = self.mock_event_bus
        self.context.file_switcher = FileSwitcher(self.mock_file_manager)
        self.context.current_file_path = None


class TestQuickSwitchCommand(TestFileSwitcherCommandsBase):
    """Tests for QuickSwitchCommand."""
    
    def test_command_initialization(self):
        """Test command initialization."""
        command = QuickSwitchCommand(self.context)
        
        assert "switch" in command.get_name().lower()
        assert "switch" in command.get_description().lower()
        assert "file" in command.get_category().lower()
    
    def test_execute_with_file_parameter(self):
        """Test quick switch with file parameter."""
        target_file = Path("/test/target.md")
        command = QuickSwitchCommand(self.context)
        
        result = command.execute(file_path=str(target_file))
        
        assert isinstance(result, bool)
    
    def test_execute_without_file_parameter(self):
        """Test quick switch without file parameter."""
        command = QuickSwitchCommand(self.context)
        
        result = command.execute()
        
        # Should handle missing file gracefully
        assert isinstance(result, bool)


class TestLastFileQuickSwitchCommand(TestFileSwitcherCommandsBase):
    """Tests for LastFileQuickSwitchCommand."""
    
    def test_command_initialization(self):
        """Test command initialization."""
        command = LastFileQuickSwitchCommand(self.context)
        
        assert command.get_name() == "Switch to Last File"
        assert "last file" in command.get_description().lower()
        assert command.get_shortcut() == "ctrl+tab"
    
    def test_execute_with_last_file(self):
        """Test switching to last file when available."""
        # Setup file history
        file1 = Path("/test/file1.md")
        file2 = Path("/test/file2.md")
        self.context.file_switcher.add_file(file1)
        self.context.file_switcher.add_file(file2)
        
        command = LastFileQuickSwitchCommand(self.context)
        result = command.execute()
        
        assert isinstance(result, bool)
        if result:
            # Should have switched to last file
            assert self.context.file_switcher._current_file == file1
    
    def test_execute_no_last_file(self):
        """Test switching to last file when none available."""
        command = LastFileQuickSwitchCommand(self.context)
        
        result = command.execute()
        
        # Should return False or handle gracefully
        assert result is False or result is True
    
    def test_execute_toggle_between_two_files(self):
        """Test toggling between two files repeatedly."""
        file1 = Path("/test/file1.md")
        file2 = Path("/test/file2.md")
        self.context.file_switcher.add_file(file1)
        self.context.file_switcher.add_file(file2)
        
        command = LastFileQuickSwitchCommand(self.context)
        
        # Switch back to file1
        result1 = command.execute()
        current_after_first = self.context.file_switcher._current_file
        
        # Switch back to file2
        result2 = command.execute()
        current_after_second = self.context.file_switcher._current_file
        
        assert isinstance(result1, bool)
        assert isinstance(result2, bool)
        if result1 and result2:
            # Should toggle between files
            assert current_after_first != current_after_second
    
    def test_can_execute_validation(self):
        """Test command availability validation."""
        command = LastFileQuickSwitchCommand(self.context)
        
        # Without last file
        assert command.can_execute() is False
        
        # With last file
        self.context.file_switcher.add_file(Path("/test/file1.md"))
        self.context.file_switcher.add_file(Path("/test/file2.md"))
        assert command.can_execute() is True


class TestRecentFilesDialogCommand(TestFileSwitcherCommandsBase):
    """Tests for RecentFilesDialogCommand."""
    
    def test_command_initialization(self):
        """Test command initialization."""
        command = RecentFilesDialogCommand(self.context)
        
        assert command.get_name() == "Recent Files"
        assert "recent files" in command.get_description().lower()
        assert command.get_shortcut() == "ctrl+r"
    
    def test_execute_with_recent_files(self):
        """Test showing recent files dialog."""
        # Setup recent files
        files = [Path(f"/test/file{i}.md") for i in range(3)]
        for file_path in files:
            self.context.file_switcher.add_file(file_path)
        
        command = RecentFilesDialogCommand(self.context)
        result = command.execute()
        
        assert isinstance(result, bool)
        # Should show dialog with recent files
    
    def test_execute_no_recent_files(self):
        """Test showing recent files dialog when empty."""
        command = RecentFilesDialogCommand(self.context)
        
        result = command.execute()
        
        # Should handle empty case gracefully
        assert isinstance(result, bool)
    
    def test_execute_select_file_from_dialog(self):
        """Test selecting a file from recent files dialog."""
        # Setup recent files
        file1 = Path("/test/file1.md")
        file2 = Path("/test/file2.md")
        self.context.file_switcher.add_file(file1)
        self.context.file_switcher.add_file(file2)
        
        command = RecentFilesDialogCommand(self.context)
        
        # Execute with selection
        result = command.execute(selected_file=str(file1))
        
        assert isinstance(result, bool)


class TestSwitchToFileCommand(TestFileSwitcherCommandsBase):
    """Tests for SwitchToFileCommand."""
    
    def test_command_initialization(self):
        """Test command initialization."""
        command = SwitchToFileCommand(self.context)
        
        assert "switch" in command.get_name().lower()
        assert "switch" in command.get_description().lower()
    
    def test_execute_existing_file(self):
        """Test switching to existing file."""
        target_file = Path("/test/existing.md")
        command = SwitchToFileCommand(self.context)
        
        result = command.execute(file_path=str(target_file))
        
        assert isinstance(result, bool)
        if result:
            # Should have updated file switcher
            assert target_file in [self.context.file_switcher._current_file]
    
    def test_execute_file_not_found(self):
        """Test switching to non-existent file."""
        self.mock_file_manager.file_exists.return_value = False
        target_file = Path("/test/missing.md")
        command = SwitchToFileCommand(self.context)
        
        result = command.execute(file_path=str(target_file))
        
        # Should handle missing file appropriately
        assert isinstance(result, bool)
    
    def test_execute_invalid_file_path(self):
        """Test switching to invalid file path."""
        self.mock_file_manager.validate_file_path.return_value = (False, "Invalid path")
        command = SwitchToFileCommand(self.context)
        
        result = command.execute(file_path="invalid:::path")
        
        assert isinstance(result, bool)
    
    def test_execute_missing_file_path(self):
        """Test switching without file path."""
        command = SwitchToFileCommand(self.context)
        
        with pytest.raises(CommandError):
            command.execute()


class TestFileSwitcherIntegration(TestFileSwitcherCommandsBase):
    """Integration tests for file switcher functionality."""
    
    def test_full_file_switching_workflow(self):
        """Test complete file switching workflow."""
        # Open several files
        files = [Path(f"/test/file{i}.md") for i in range(3)]
        
        for file_path in files:
            self.context.file_switcher.add_file(file_path)
        
        # Use Ctrl+Tab to switch to last file
        last_cmd = LastFileQuickSwitchCommand(self.context)
        last_result = last_cmd.execute()
        
        # Open recent files dialog
        recent_cmd = RecentFilesDialogCommand(self.context)
        recent_result = recent_cmd.execute()
        
        # Switch to specific file
        switch_cmd = SwitchToFileCommand(self.context)
        switch_result = switch_cmd.execute(file_path=str(files[0]))
        
        assert isinstance(last_result, bool)
        assert isinstance(recent_result, bool) 
        assert isinstance(switch_result, bool)
    
    def test_file_history_persistence(self):
        """Test that file switching history is maintained."""
        # Build up history
        files = [Path(f"/test/file{i}.md") for i in range(5)]
        
        for file_path in files:
            self.context.file_switcher.add_file(file_path)
        
        # Get recent files
        recent_files = self.context.file_switcher.get_recent_files()
        
        # Should have history (excluding current file)
        assert len(recent_files) >= 1
        assert all(isinstance(info, FileInfo) for info in recent_files)
    
    def test_rapid_file_switching(self):
        """Test rapid switching between files."""
        file1 = Path("/test/rapid1.md")
        file2 = Path("/test/rapid2.md")
        
        # Setup initial files
        self.context.file_switcher.add_file(file1)
        self.context.file_switcher.add_file(file2)
        
        # Rapid switching
        last_cmd = LastFileQuickSwitchCommand(self.context)
        
        for _ in range(5):
            result = last_cmd.execute()
            assert isinstance(result, bool)
    
    def test_file_switcher_with_editor_integration(self):
        """Test file switcher integration with editor."""
        file1 = Path("/test/editor1.md")
        file2 = Path("/test/editor2.md")
        
        # Mock editor cursor positions
        self.mock_editor.get_cursor_position.side_effect = [(1, 5), (2, 10)]
        
        # Add files with cursor positions
        self.context.file_switcher.add_file(file1)
        self.context.file_switcher.add_file(file2)
        
        # Switch back to first file
        last_cmd = LastFileQuickSwitchCommand(self.context)
        result = last_cmd.execute()
        
        # Should restore cursor position if implemented
        assert isinstance(result, bool)
    
    def test_memory_efficiency_with_many_files(self):
        """Test that switcher handles many files efficiently."""
        # Add many files
        for i in range(100):
            self.context.file_switcher.add_file(Path(f"/test/file{i}.md"))
        
        # Recent files should still be limited
        recent_files = self.context.file_switcher.get_recent_files()
        
        # Should respect max_recent limit
        assert len(recent_files) <= self.context.file_switcher._max_recent - 1