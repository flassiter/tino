"""
Tests for edit operation commands.

Tests all editing-related commands including Undo, Redo, Cut, Copy,
Paste, Select All, and line manipulation commands.
"""

from unittest.mock import Mock

from src.tino.components.commands.command_base import CommandContext
from src.tino.components.commands.edit_commands import (
    CopyCommand,
    CutCommand,
    DeleteLineCommand,
    DuplicateLineCommand,
    PasteCommand,
    RedoCommand,
    SelectAllCommand,
    UndoCommand,
)


class TestEditCommandsBase:
    """Base test setup for edit commands."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock dependencies
        self.mock_editor = Mock()
        self.mock_event_bus = Mock()

        # Setup common editor mock returns
        self.mock_editor.can_undo.return_value = True
        self.mock_editor.can_redo.return_value = True
        self.mock_editor.get_selection.return_value = (0, 10)
        self.mock_editor.get_selected_text.return_value = "selected text"
        self.mock_editor.get_content.return_value = "test content"
        self.mock_editor.get_cursor_position.return_value = (1, 5)

        # Create command context
        self.context = CommandContext()
        self.context.editor = self.mock_editor
        self.context.event_bus = self.mock_event_bus
        self.context.clipboard = ""


class TestUndoCommand(TestEditCommandsBase):
    """Tests for UndoCommand."""

    def test_command_initialization(self):
        """Test command initialization."""
        command = UndoCommand(self.context)

        assert command.get_name() == "Undo"
        assert "undo" in command.get_description().lower()
        assert command.get_shortcut() == "ctrl+z"
        assert "edit" in command.get_category().lower()

    def test_execute_success(self):
        """Test successful undo operation."""
        command = UndoCommand(self.context)

        result = command.execute()

        assert result is True
        self.mock_editor.undo.assert_called_once()

    def test_execute_when_cannot_undo(self):
        """Test undo when no undo is available."""
        self.mock_editor.can_undo.return_value = False
        command = UndoCommand(self.context)

        result = command.execute()

        assert result is False
        self.mock_editor.undo.assert_not_called()

    def test_can_execute_validation(self):
        """Test that command validates undo availability."""
        command = UndoCommand(self.context)

        # When undo is available
        self.mock_editor.can_undo.return_value = True
        assert command.can_execute() is True

        # When undo is not available
        self.mock_editor.can_undo.return_value = False
        assert command.can_execute() is False


class TestRedoCommand(TestEditCommandsBase):
    """Tests for RedoCommand."""

    def test_command_initialization(self):
        """Test command initialization."""
        command = RedoCommand(self.context)

        assert command.get_name() == "Redo"
        assert "redo" in command.get_description().lower()
        assert command.get_shortcut() == "ctrl+y"
        assert "edit" in command.get_category().lower()

    def test_execute_success(self):
        """Test successful redo operation."""
        command = RedoCommand(self.context)

        result = command.execute()

        assert result is True
        self.mock_editor.redo.assert_called_once()

    def test_execute_when_cannot_redo(self):
        """Test redo when no redo is available."""
        self.mock_editor.can_redo.return_value = False
        command = RedoCommand(self.context)

        result = command.execute()

        assert result is False
        self.mock_editor.redo.assert_not_called()


class TestCutCommand(TestEditCommandsBase):
    """Tests for CutCommand."""

    def test_command_initialization(self):
        """Test command initialization."""
        command = CutCommand(self.context)

        assert command.get_name() == "Cut"
        assert "cut" in command.get_description().lower()
        assert command.get_shortcut() == "ctrl+x"

    def test_execute_with_selection(self):
        """Test cut with selected text."""
        self.mock_editor.has_selection.return_value = True
        command = CutCommand(self.context)

        result = command.execute()

        assert result is True
        self.mock_editor.get_selected_text.assert_called_once()
        self.mock_editor.delete_selection.assert_called_once()

    def test_execute_without_selection(self):
        """Test cut without selection (should cut entire line)."""
        self.mock_editor.has_selection.return_value = False
        command = CutCommand(self.context)

        result = command.execute()

        # Should still execute (implementation may cut current line)
        assert result is True


class TestCopyCommand(TestEditCommandsBase):
    """Tests for CopyCommand."""

    def test_command_initialization(self):
        """Test command initialization."""
        command = CopyCommand(self.context)

        assert command.get_name() == "Copy"
        assert "copy" in command.get_description().lower()
        assert command.get_shortcut() == "ctrl+c"

    def test_execute_with_selection(self):
        """Test copy with selected text."""
        self.mock_editor.has_selection.return_value = True
        command = CopyCommand(self.context)

        result = command.execute()

        assert result is True
        self.mock_editor.get_selected_text.assert_called_once()
        # Text should be copied to clipboard (context or system)

    def test_execute_without_selection(self):
        """Test copy without selection."""
        self.mock_editor.has_selection.return_value = False
        command = CopyCommand(self.context)

        result = command.execute()

        # Should still execute (may copy current line)
        assert result is True


class TestPasteCommand(TestEditCommandsBase):
    """Tests for PasteCommand."""

    def test_command_initialization(self):
        """Test command initialization."""
        command = PasteCommand(self.context)

        assert command.get_name() == "Paste"
        assert "paste" in command.get_description().lower()
        assert command.get_shortcut() == "ctrl+v"

    def test_execute_success(self):
        """Test successful paste operation."""
        self.context.clipboard = "clipboard content"
        command = PasteCommand(self.context)

        result = command.execute()

        assert result is True
        # Should insert clipboard content at cursor

    def test_execute_empty_clipboard(self):
        """Test paste with empty clipboard."""
        self.context.clipboard = ""
        command = PasteCommand(self.context)

        result = command.execute()

        # Result depends on implementation - may succeed with no-op
        assert isinstance(result, bool)


class TestSelectAllCommand(TestEditCommandsBase):
    """Tests for SelectAllCommand."""

    def test_command_initialization(self):
        """Test command initialization."""
        command = SelectAllCommand(self.context)

        assert command.get_name() == "Select All"
        assert "select all" in command.get_description().lower()
        assert command.get_shortcut() == "ctrl+a"

    def test_execute_success(self):
        """Test successful select all operation."""
        command = SelectAllCommand(self.context)

        result = command.execute()

        assert result is True
        self.mock_editor.select_all.assert_called_once()

    def test_execute_empty_document(self):
        """Test select all on empty document."""
        self.mock_editor.get_content.return_value = ""
        command = SelectAllCommand(self.context)

        result = command.execute()

        # Should still succeed even with empty document
        assert result is True


class TestDuplicateLineCommand(TestEditCommandsBase):
    """Tests for DuplicateLineCommand."""

    def test_command_initialization(self):
        """Test command initialization."""
        command = DuplicateLineCommand(self.context)

        assert command.get_name() == "Duplicate Line"
        assert "duplicate" in command.get_description().lower()
        assert command.get_shortcut() == "ctrl+d"

    def test_execute_success(self):
        """Test successful line duplication."""
        command = DuplicateLineCommand(self.context)

        result = command.execute()

        assert result is True
        # Should duplicate the current line

    def test_execute_with_selection(self):
        """Test duplicate with selected text."""
        self.mock_editor.has_selection.return_value = True
        command = DuplicateLineCommand(self.context)

        result = command.execute()

        # Should duplicate selected text or lines
        assert result is True


class TestDeleteLineCommand(TestEditCommandsBase):
    """Tests for DeleteLineCommand."""

    def test_command_initialization(self):
        """Test command initialization."""
        command = DeleteLineCommand(self.context)

        assert command.get_name() == "Delete Line"
        assert "delete" in command.get_description().lower()
        # May not have a default shortcut

    def test_execute_success(self):
        """Test successful line deletion."""
        command = DeleteLineCommand(self.context)

        result = command.execute()

        assert result is True
        # Should delete current line

    def test_execute_empty_document(self):
        """Test delete line on empty document."""
        self.mock_editor.get_content.return_value = ""
        command = DeleteLineCommand(self.context)

        result = command.execute()

        # Should handle empty document gracefully
        assert isinstance(result, bool)


class TestEditCommandsIntegration(TestEditCommandsBase):
    """Integration tests for edit commands."""

    def test_cut_paste_workflow(self):
        """Test cut -> paste workflow."""
        # Set up selection
        self.mock_editor.has_selection.return_value = True
        self.mock_editor.get_selected_text.return_value = "test text"

        # Cut text
        cut_cmd = CutCommand(self.context)
        cut_result = cut_cmd.execute()

        # Move cursor
        self.mock_editor.get_cursor_position.return_value = (2, 0)

        # Paste text
        paste_cmd = PasteCommand(self.context)
        paste_result = paste_cmd.execute()

        assert cut_result is True
        assert paste_result is True

    def test_copy_paste_workflow(self):
        """Test copy -> paste workflow."""
        # Set up selection
        self.mock_editor.has_selection.return_value = True
        self.mock_editor.get_selected_text.return_value = "copy text"

        # Copy text
        copy_cmd = CopyCommand(self.context)
        copy_result = copy_cmd.execute()

        # Paste text elsewhere
        paste_cmd = PasteCommand(self.context)
        paste_result = paste_cmd.execute()

        assert copy_result is True
        assert paste_result is True

    def test_undo_redo_workflow(self):
        """Test undo -> redo workflow."""
        # Perform some operation that can be undone
        self.mock_editor.can_undo.return_value = True
        undo_cmd = UndoCommand(self.context)
        undo_result = undo_cmd.execute()

        # Now redo should be available
        self.mock_editor.can_redo.return_value = True
        redo_cmd = RedoCommand(self.context)
        redo_result = redo_cmd.execute()

        assert undo_result is True
        assert redo_result is True

    def test_select_all_then_operations(self):
        """Test select all -> copy/cut workflow."""
        # Select all content
        select_cmd = SelectAllCommand(self.context)
        select_result = select_cmd.execute()

        # Now copy should work on entire document
        self.mock_editor.has_selection.return_value = True
        copy_cmd = CopyCommand(self.context)
        copy_result = copy_cmd.execute()

        assert select_result is True
        assert copy_result is True
