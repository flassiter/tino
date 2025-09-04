"""
Tests for file operation commands.

Tests all file-related commands including New, Open, Save, SaveAs,
Recent files, and quick file switching functionality.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.tino.components.commands.command_base import CommandContext
from src.tino.components.commands.file_commands import (
    CloseFileCommand,
    LastFileCommand,
    NewFileCommand,
    OpenFileCommand,
    RecentFilesCommand,
    SaveAsFileCommand,
    SaveFileCommand,
)
from src.tino.core.events.types import FileClosedEvent, FileOpenedEvent, FileSavedEvent
from src.tino.core.interfaces.command import CommandError


class TestFileCommandsBase:
    """Base test setup for file commands."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock dependencies
        self.mock_editor = Mock()
        self.mock_file_manager = Mock()
        self.mock_event_bus = Mock()

        # Setup common editor mock returns
        self.mock_editor.get_content.return_value = "test content"
        self.mock_editor.is_modified.return_value = False
        self.mock_editor.get_cursor_position.return_value = (0, 0)

        # Setup common file manager mock returns
        self.mock_file_manager.validate_file_path.return_value = (True, "")
        self.mock_file_manager.file_exists.return_value = True
        self.mock_file_manager.save_file.return_value = True
        self.mock_file_manager.get_file_info.return_value = (
            1024,
            "2024-01-01",
            "utf-8",
        )
        self.mock_file_manager.get_cursor_position.return_value = None
        self.mock_file_manager.create_backup.return_value = Path("/backup/file.bak")

        # Create command context
        self.context = CommandContext()
        self.context.editor = self.mock_editor
        self.context.file_manager = self.mock_file_manager
        self.context.event_bus = self.mock_event_bus
        self.context.current_file_path = None
        self.context.application_state = {}


class TestNewFileCommand(TestFileCommandsBase):
    """Tests for NewFileCommand."""

    def test_command_initialization(self):
        """Test command initialization."""
        command = NewFileCommand(self.context)

        assert command.get_name() == "New File"
        assert command.get_description() == "Create a new empty file"
        assert command.get_shortcut() == "ctrl+n"
        assert "file" in command.get_category().lower()

    def test_execute_success(self):
        """Test successful new file creation."""
        command = NewFileCommand(self.context)

        # Execute command
        result = command.execute()

        assert result is True

        # Verify editor operations
        self.mock_editor.set_content.assert_called_once_with("")
        self.mock_editor.set_modified.assert_called_once_with(False)
        self.mock_editor.clear_undo_history.assert_called_once()

        # Verify context updates
        assert self.context.current_file_path is None
        assert self.context.application_state["current_file"] is None

    def test_execute_without_editor(self):
        """Test new file when no editor is available."""
        self.context.editor = None
        command = NewFileCommand(self.context)

        result = command.execute()

        assert result is True  # Should still succeed
        assert self.context.current_file_path is None

    def test_execute_editor_error(self):
        """Test handling editor errors."""
        self.mock_editor.set_content.side_effect = Exception("Editor error")
        command = NewFileCommand(self.context)

        with pytest.raises(CommandError) as exc_info:
            command.execute()

        assert "Failed to create new file" in str(exc_info.value)
        assert "Editor error" in str(exc_info.value)

    def test_undo_not_supported(self):
        """Test that new file cannot be undone."""
        command = NewFileCommand(self.context)

        result = command.undo()

        assert result is False


class TestOpenFileCommand(TestFileCommandsBase):
    """Tests for OpenFileCommand."""

    def test_execute_success_with_path_arg(self):
        """Test successful file opening with path argument."""
        test_path = Path("/test/file.md")
        command = OpenFileCommand(self.context)

        # Setup mocks
        self.mock_file_manager.validate_file_path.return_value = (True, "")
        self.mock_file_manager.file_exists.return_value = True
        self.mock_file_manager.open_file.return_value = "Test content"
        self.mock_file_manager.get_cursor_position.return_value = (5, 10)
        self.mock_file_manager.get_file_info.return_value = (
            1024,
            "2024-01-01",
            "utf-8",
        )  # size, modified, encoding
        self.mock_editor.get_content.return_value = "Previous content"

        # Execute command
        result = command.execute(test_path)

        assert result is True

        # Verify file manager calls
        self.mock_file_manager.validate_file_path.assert_called_once_with(test_path)
        self.mock_file_manager.file_exists.assert_called_once_with(test_path)
        self.mock_file_manager.open_file.assert_called_once_with(test_path)
        self.mock_file_manager.add_recent_file.assert_called_once_with(test_path)

        # Verify editor updates
        self.mock_editor.set_content.assert_called_once_with("Test content")
        self.mock_editor.set_modified.assert_called_once_with(False)

        # Verify event emission
        self.mock_event_bus.emit.assert_called()
        event = self.mock_event_bus.emit.call_args[0][0]
        assert isinstance(event, FileOpenedEvent)

        # Verify context updates
        assert self.context.current_file_path == test_path

    def test_execute_success_with_kwargs(self):
        """Test successful file opening with keyword arguments."""
        test_path = Path("/test/file.md")
        command = OpenFileCommand(self.context)

        # Setup mocks
        self.mock_file_manager.validate_file_path.return_value = (True, "")
        self.mock_file_manager.file_exists.return_value = True
        self.mock_file_manager.open_file.return_value = "Test content"
        self.mock_editor.get_content.return_value = ""

        # Execute command with kwargs
        result = command.execute(file_path=str(test_path))

        assert result is True
        self.mock_file_manager.open_file.assert_called_once_with(test_path)

    def test_execute_no_path_provided(self):
        """Test error when no file path is provided."""
        command = OpenFileCommand(self.context)

        with pytest.raises(CommandError) as exc_info:
            command.execute()

        assert "No file path provided" in str(exc_info.value)

    def test_execute_invalid_file_path(self):
        """Test error for invalid file path."""
        test_path = Path("/invalid/path")
        command = OpenFileCommand(self.context)

        self.mock_file_manager.validate_file_path.return_value = (False, "Invalid path")

        with pytest.raises(CommandError) as exc_info:
            command.execute(test_path)

        assert "Invalid file path" in str(exc_info.value)

    def test_execute_file_not_found(self):
        """Test error when file does not exist."""
        test_path = Path("/missing/file.md")
        command = OpenFileCommand(self.context)

        self.mock_file_manager.validate_file_path.return_value = (True, "")
        self.mock_file_manager.file_exists.return_value = False

        with pytest.raises(CommandError) as exc_info:
            command.execute(test_path)

        assert "File not found" in str(exc_info.value)

    def test_undo_restores_previous_state(self):
        """Test that undo restores the previous file and content."""
        test_path = Path("/test/file.md")
        command = OpenFileCommand(self.context)

        # Setup for successful execute
        self.mock_file_manager.validate_file_path.return_value = (True, "")
        self.mock_file_manager.file_exists.return_value = True
        self.mock_file_manager.open_file.return_value = "New content"
        self.mock_editor.get_content.return_value = "Old content"
        self.context.current_file_path = Path("/old/file.md")

        # Execute then undo
        command.execute(test_path)
        result = command.undo()

        assert result is True

        # Verify restoration
        self.mock_editor.set_content.assert_called_with("Old content")
        assert self.context.current_file_path == Path("/old/file.md")


class TestSaveFileCommand(TestFileCommandsBase):
    """Tests for SaveFileCommand."""

    def test_execute_success_existing_file(self):
        """Test successful save of existing file."""
        test_path = Path("/test/file.md")
        self.context.current_file_path = test_path
        command = SaveFileCommand(self.context)

        # Setup mocks
        self.mock_editor.get_content.return_value = "File content"
        self.mock_editor.is_modified.return_value = True
        self.mock_file_manager.save_file.return_value = True

        # Execute command
        result = command.execute()

        assert result is True

        # Verify save operation
        self.mock_file_manager.save_file.assert_called_once_with(
            test_path, "File content"
        )
        self.mock_editor.set_modified.assert_called_once_with(False)

        # Verify event emission
        self.mock_event_bus.emit.assert_called()
        event = self.mock_event_bus.emit.call_args[0][0]
        assert isinstance(event, FileSavedEvent)

    def test_execute_no_current_file_prompts_save_as(self):
        """Test that save without current file prompts for path."""
        self.context.current_file_path = None
        command = SaveFileCommand(self.context)

        self.mock_editor.get_content.return_value = "Content"

        with patch(
            "src.tino.components.commands.file_commands.SaveAsFileCommand"
        ) as mock_save_as:
            mock_save_as_instance = Mock()
            mock_save_as_instance.execute.return_value = True
            mock_save_as.return_value = mock_save_as_instance

            result = command.execute()

            assert result is True
            mock_save_as_instance.execute.assert_called_once()

    def test_execute_file_not_modified(self):
        """Test save when file is not modified."""
        test_path = Path("/test/file.md")
        self.context.current_file_path = test_path
        command = SaveFileCommand(self.context)

        self.mock_editor.is_modified.return_value = False

        result = command.execute()

        assert result is True
        # Should not call save_file since not modified
        self.mock_file_manager.save_file.assert_not_called()

    def test_execute_save_failure(self):
        """Test handling of save failure."""
        test_path = Path("/test/file.md")
        self.context.current_file_path = test_path
        command = SaveFileCommand(self.context)

        self.mock_editor.get_content.return_value = "Content"
        self.mock_editor.is_modified.return_value = True
        self.mock_file_manager.save_file.return_value = False

        with pytest.raises(CommandError) as exc_info:
            command.execute()

        assert "Failed to save file" in str(exc_info.value)


class TestSaveAsFileCommand(TestFileCommandsBase):
    """Tests for SaveAsFileCommand."""

    def test_execute_success(self):
        """Test successful save as operation."""
        new_path = Path("/new/location/file.md")
        command = SaveAsFileCommand(self.context)

        # Setup mocks
        self.mock_editor.get_content.return_value = "File content"
        self.mock_file_manager.save_file.return_value = True

        # Execute command
        result = command.execute(file_path=str(new_path))

        assert result is True

        # Verify save operation
        self.mock_file_manager.save_file.assert_called_once_with(
            new_path, "File content"
        )

        # Verify context update
        assert self.context.current_file_path == new_path
        self.context.application_state["current_file"] = str(new_path)

    def test_execute_no_path_provided(self):
        """Test error when no file path is provided."""
        command = SaveAsFileCommand(self.context)

        with pytest.raises(CommandError) as exc_info:
            command.execute()

        assert "No file path provided" in str(exc_info.value)


class TestRecentFilesCommand(TestFileCommandsBase):
    """Tests for RecentFilesCommand."""

    def test_execute_returns_recent_files(self):
        """Test that command returns recent files list."""
        recent_files = [Path("/file1.md"), Path("/file2.md")]
        command = RecentFilesCommand(self.context)

        self.mock_file_manager.get_recent_files.return_value = recent_files

        result = command.execute()

        assert result is True
        self.mock_file_manager.get_recent_files.assert_called_once()

        # Command should execute successfully
        assert command.was_executed()


class TestLastFileCommand(TestFileCommandsBase):
    """Tests for LastFileCommand."""

    def test_execute_success(self):
        """Test successful switch to last file."""
        last_file = Path("/last/file.md")
        command = LastFileCommand(self.context)

        self.mock_file_manager.get_last_file.return_value = last_file

        with patch(
            "src.tino.components.commands.file_commands.OpenFileCommand"
        ) as mock_open:
            mock_open_instance = Mock()
            mock_open_instance.execute.return_value = True
            mock_open.return_value = mock_open_instance

            result = command.execute()

            assert result is True
            mock_open_instance.execute.assert_called_once_with(file_path=str(last_file))

    def test_execute_no_last_file(self):
        """Test when there is no last file."""
        command = LastFileCommand(self.context)

        self.mock_file_manager.get_last_file.return_value = None

        result = command.execute()

        assert result is False  # No last file to switch to


class TestCloseFileCommand(TestFileCommandsBase):
    """Tests for CloseFileCommand."""

    def test_execute_success(self):
        """Test successful file close."""
        test_path = Path("/test/file.md")
        self.context.current_file_path = test_path
        command = CloseFileCommand(self.context)

        # Setup mocks
        self.mock_editor.get_content.return_value = "Content"
        self.mock_editor.is_modified.return_value = False

        result = command.execute()

        assert result is True

        # Verify context cleanup
        assert self.context.current_file_path is None
        assert self.context.application_state.get("current_file") is None

        # Verify event emission
        self.mock_event_bus.emit.assert_called()
        event = self.mock_event_bus.emit.call_args[0][0]
        assert isinstance(event, FileClosedEvent)

    def test_execute_with_unsaved_changes(self):
        """Test close file with unsaved changes."""
        test_path = Path("/test/file.md")
        self.context.current_file_path = test_path
        command = CloseFileCommand(self.context)

        self.mock_editor.is_modified.return_value = True

        # Should prompt for save (implementation detail)
        # This test verifies the command handles modified files
        result = command.execute()

        # Behavior depends on user choice in actual implementation
        # For now, just verify it doesn't crash
        assert isinstance(result, bool)

    def test_undo_restores_file(self):
        """Test that undo restores the closed file."""
        test_path = Path("/test/file.md")
        self.context.current_file_path = test_path
        command = CloseFileCommand(self.context)

        # Setup for close
        self.mock_editor.get_content.return_value = "Content"
        self.mock_editor.is_modified.return_value = False

        # Execute close then undo
        command.execute()
        result = command.undo()

        assert result is True

        # Should restore the file path
        assert self.context.current_file_path == test_path


class TestFileCommandsIntegration(TestFileCommandsBase):
    """Integration tests for file commands."""

    def test_new_then_save_as_workflow(self):
        """Test new file -> save as workflow."""
        # Create new file
        new_cmd = NewFileCommand(self.context)
        new_cmd.execute()

        # Add content and save as
        self.mock_editor.get_content.return_value = "New content"
        self.mock_file_manager.save_file.return_value = True

        save_as_cmd = SaveAsFileCommand(self.context)
        result = save_as_cmd.execute(file_path="/new/file.md")

        assert result is True
        assert self.context.current_file_path == Path("/new/file.md")

    def test_open_then_save_workflow(self):
        """Test open file -> modify -> save workflow."""
        test_path = Path("/test/file.md")

        # Open file
        self.mock_file_manager.validate_file_path.return_value = (True, "")
        self.mock_file_manager.file_exists.return_value = True
        self.mock_file_manager.open_file.return_value = "Original content"
        self.mock_editor.get_content.return_value = ""

        open_cmd = OpenFileCommand(self.context)
        open_cmd.execute(test_path)

        # Save modified content
        self.mock_editor.get_content.return_value = "Modified content"
        self.mock_editor.is_modified.return_value = True
        self.mock_file_manager.save_file.return_value = True

        save_cmd = SaveFileCommand(self.context)
        result = save_cmd.execute()

        assert result is True
        self.mock_file_manager.save_file.assert_called_with(
            test_path, "Modified content"
        )
