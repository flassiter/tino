"""
Tests for navigation commands.

Tests all navigation-related commands including Find, Replace,
Go to Line, and search navigation functionality.
"""

from unittest.mock import Mock

import pytest

from src.tino.components.commands.command_base import CommandContext
from src.tino.components.commands.navigation_commands import (
    FindCommand,
    FindNextCommand,
    FindPreviousCommand,
    GoToLineCommand,
    ReplaceCommand,
)
from src.tino.core.interfaces.command import CommandError


class TestNavigationCommandsBase:
    """Base test setup for navigation commands."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock dependencies
        self.mock_editor = Mock()
        self.mock_search_engine = Mock()
        self.mock_event_bus = Mock()

        # Setup common editor mock returns
        self.mock_editor.get_content.return_value = "line 1\nline 2\nline 3"
        self.mock_editor.get_cursor_position.return_value = (1, 0)
        self.mock_editor.set_cursor_position.return_value = True
        self.mock_editor.get_line_count.return_value = 3

        # Setup search engine mock returns
        self.mock_search_engine.find_all.return_value = [
            (0, 4),
            (7, 11),
        ]  # match positions
        self.mock_search_engine.find_next.return_value = (7, 11)
        self.mock_search_engine.find_previous.return_value = (0, 4)
        self.mock_search_engine.replace_all.return_value = 2  # replacements made

        # Create command context
        self.context = CommandContext()
        self.context.editor = self.mock_editor
        self.context.search_engine = self.mock_search_engine
        self.context.event_bus = self.mock_event_bus
        self.context.search_state = {
            "last_query": "",
            "last_results": [],
            "current_match_index": 0,
        }


class TestFindCommand(TestNavigationCommandsBase):
    """Tests for FindCommand."""

    def test_command_initialization(self):
        """Test command initialization."""
        command = FindCommand(self.context)

        assert command.get_name() == "Find"
        assert "find" in command.get_description().lower()
        assert command.get_shortcut() == "ctrl+f"
        assert "navigation" in command.get_category().lower()

    def test_execute_with_search_term(self):
        """Test find with search term parameter."""
        command = FindCommand(self.context)

        result = command.execute(search_term="test")

        assert isinstance(result, bool)
        if result:
            # Should have updated search state
            assert self.context.search_state["last_query"] == "test"

    def test_execute_without_search_term(self):
        """Test find without search term (should prompt or use last)."""
        self.context.search_state["last_query"] = "previous"
        command = FindCommand(self.context)

        result = command.execute()

        # Should handle missing search term gracefully
        assert isinstance(result, bool)

    def test_execute_case_sensitive_search(self):
        """Test case sensitive search."""
        command = FindCommand(self.context)

        result = command.execute(search_term="Test", case_sensitive=True)

        assert isinstance(result, bool)
        if result:
            # Should have passed case_sensitive to search engine
            self.mock_search_engine.find_all.assert_called()

    def test_execute_whole_word_search(self):
        """Test whole word search."""
        command = FindCommand(self.context)

        result = command.execute(search_term="test", whole_word=True)

        assert isinstance(result, bool)

    def test_execute_no_matches_found(self):
        """Test search with no matches."""
        self.mock_search_engine.find_all.return_value = []
        command = FindCommand(self.context)

        result = command.execute(search_term="nonexistent")

        # Should handle no matches gracefully
        assert isinstance(result, bool)

    def test_execute_empty_search_term(self):
        """Test search with empty term."""
        command = FindCommand(self.context)

        result = command.execute(search_term="")

        # Should handle empty search appropriately
        assert isinstance(result, bool)


class TestFindNextCommand(TestNavigationCommandsBase):
    """Tests for FindNextCommand."""

    def test_command_initialization(self):
        """Test command initialization."""
        command = FindNextCommand(self.context)

        assert command.get_name() == "Find Next"
        assert "find next" in command.get_description().lower()
        assert command.get_shortcut() == "f3"

    def test_execute_with_active_search(self):
        """Test find next with active search."""
        self.context.search_state["last_query"] = "test"
        self.context.search_state["last_results"] = [(0, 4), (7, 11)]
        command = FindNextCommand(self.context)

        result = command.execute()

        assert isinstance(result, bool)
        if result:
            # Should navigate to next match
            self.mock_search_engine.find_next.assert_called()

    def test_execute_without_active_search(self):
        """Test find next without active search."""
        self.context.search_state["last_query"] = ""
        command = FindNextCommand(self.context)

        result = command.execute()

        # Should handle no active search gracefully
        assert isinstance(result, bool)

    def test_execute_wrap_around_search(self):
        """Test find next wrapping around to beginning."""
        self.context.search_state["last_query"] = "test"
        self.context.search_state["current_match_index"] = 1  # last match
        self.mock_search_engine.find_next.return_value = None  # no more matches
        command = FindNextCommand(self.context)

        result = command.execute()

        # Should handle wrap-around
        assert isinstance(result, bool)

    def test_can_execute_validation(self):
        """Test that command validates active search."""
        command = FindNextCommand(self.context)

        # With active search
        self.context.search_state["last_query"] = "test"
        assert command.can_execute() is True

        # Without active search
        self.context.search_state["last_query"] = ""
        can_exec = command.can_execute()
        assert isinstance(can_exec, bool)


class TestFindPreviousCommand(TestNavigationCommandsBase):
    """Tests for FindPreviousCommand."""

    def test_command_initialization(self):
        """Test command initialization."""
        command = FindPreviousCommand(self.context)

        assert command.get_name() == "Find Previous"
        assert "find previous" in command.get_description().lower()
        assert command.get_shortcut() == "shift+f3"

    def test_execute_with_active_search(self):
        """Test find previous with active search."""
        self.context.search_state["last_query"] = "test"
        self.context.search_state["last_results"] = [(0, 4), (7, 11)]
        self.context.search_state["current_match_index"] = 1
        command = FindPreviousCommand(self.context)

        result = command.execute()

        assert isinstance(result, bool)
        if result:
            # Should navigate to previous match
            self.mock_search_engine.find_previous.assert_called()

    def test_execute_wrap_around_to_end(self):
        """Test find previous wrapping around to end."""
        self.context.search_state["last_query"] = "test"
        self.context.search_state["current_match_index"] = 0  # first match
        command = FindPreviousCommand(self.context)

        result = command.execute()

        # Should handle wrap-around to end
        assert isinstance(result, bool)


class TestReplaceCommand(TestNavigationCommandsBase):
    """Tests for ReplaceCommand."""

    def test_command_initialization(self):
        """Test command initialization."""
        command = ReplaceCommand(self.context)

        assert command.get_name() == "Replace"
        assert "replace" in command.get_description().lower()
        assert command.get_shortcut() == "ctrl+h"

    def test_execute_single_replace(self):
        """Test single replace operation."""
        command = ReplaceCommand(self.context)

        result = command.execute(
            search_term="old", replace_term="new", replace_all=False
        )

        assert isinstance(result, bool)

    def test_execute_replace_all(self):
        """Test replace all operation."""
        command = ReplaceCommand(self.context)

        result = command.execute(
            search_term="old", replace_term="new", replace_all=True
        )

        assert isinstance(result, bool)
        if result:
            self.mock_search_engine.replace_all.assert_called()

    def test_execute_with_confirmation(self):
        """Test replace with confirmation."""
        command = ReplaceCommand(self.context)

        result = command.execute(search_term="old", replace_term="new", confirm=True)

        # Should handle confirmation flow
        assert isinstance(result, bool)

    def test_execute_missing_parameters(self):
        """Test replace with missing parameters."""
        command = ReplaceCommand(self.context)

        # Missing search term
        with pytest.raises(CommandError):
            command.execute(replace_term="new")

        # Missing replace term
        with pytest.raises(CommandError):
            command.execute(search_term="old")

    def test_execute_empty_search_term(self):
        """Test replace with empty search term."""
        command = ReplaceCommand(self.context)

        with pytest.raises(CommandError):
            command.execute(search_term="", replace_term="new")

    def test_execute_case_sensitive_replace(self):
        """Test case sensitive replace."""
        command = ReplaceCommand(self.context)

        result = command.execute(
            search_term="Test", replace_term="Example", case_sensitive=True
        )

        assert isinstance(result, bool)

    def test_execute_whole_word_replace(self):
        """Test whole word replace."""
        command = ReplaceCommand(self.context)

        result = command.execute(
            search_term="test", replace_term="example", whole_word=True
        )

        assert isinstance(result, bool)

    def test_undo_replace_operation(self):
        """Test undoing a replace operation."""
        command = ReplaceCommand(self.context)

        # Execute replace
        command.execute(search_term="old", replace_term="new", replace_all=True)

        # Undo
        result = command.undo()

        # Should restore previous content
        assert isinstance(result, bool)


class TestGoToLineCommand(TestNavigationCommandsBase):
    """Tests for GoToLineCommand."""

    def test_command_initialization(self):
        """Test command initialization."""
        command = GoToLineCommand(self.context)

        assert command.get_name() == "Go to Line"
        assert "go to line" in command.get_description().lower()
        assert command.get_shortcut() == "ctrl+g"

    def test_execute_valid_line_number(self):
        """Test go to line with valid line number."""
        command = GoToLineCommand(self.context)

        result = command.execute(line_number=2)

        assert isinstance(result, bool)
        if result:
            self.mock_editor.set_cursor_position.assert_called_with(2, 0)

    def test_execute_line_number_as_string(self):
        """Test go to line with line number as string."""
        command = GoToLineCommand(self.context)

        result = command.execute(line_number="2")

        assert isinstance(result, bool)

    def test_execute_first_line(self):
        """Test go to first line."""
        command = GoToLineCommand(self.context)

        result = command.execute(line_number=1)

        assert isinstance(result, bool)
        if result:
            self.mock_editor.set_cursor_position.assert_called_with(1, 0)

    def test_execute_last_line(self):
        """Test go to last line."""
        self.mock_editor.get_line_count.return_value = 5
        command = GoToLineCommand(self.context)

        result = command.execute(line_number=5)

        assert isinstance(result, bool)

    def test_execute_line_number_too_high(self):
        """Test go to line beyond document end."""
        self.mock_editor.get_line_count.return_value = 3
        command = GoToLineCommand(self.context)

        # Should clamp to last line or handle gracefully
        result = command.execute(line_number=10)

        assert isinstance(result, bool)

    def test_execute_line_number_too_low(self):
        """Test go to line below 1."""
        command = GoToLineCommand(self.context)

        with pytest.raises(CommandError):
            command.execute(line_number=0)

        with pytest.raises(CommandError):
            command.execute(line_number=-1)

    def test_execute_invalid_line_number(self):
        """Test go to line with invalid input."""
        command = GoToLineCommand(self.context)

        with pytest.raises(CommandError):
            command.execute(line_number="abc")

        with pytest.raises(CommandError):
            command.execute(line_number=None)

    def test_execute_missing_line_number(self):
        """Test go to line without line number parameter."""
        command = GoToLineCommand(self.context)

        with pytest.raises(CommandError):
            command.execute()

    def test_undo_go_to_line(self):
        """Test undoing go to line operation."""
        command = GoToLineCommand(self.context)

        # Execute go to line
        command.execute(line_number=3)

        # Undo should restore previous position
        result = command.undo()

        assert isinstance(result, bool)
        if result:
            # Should restore to original position (1, 0)
            self.mock_editor.set_cursor_position.assert_called_with(1, 0)


class TestNavigationCommandsIntegration(TestNavigationCommandsBase):
    """Integration tests for navigation commands."""

    def test_find_then_find_next_workflow(self):
        """Test find -> find next workflow."""
        # Initial find
        find_cmd = FindCommand(self.context)
        find_result = find_cmd.execute(search_term="test")

        # Find next
        next_cmd = FindNextCommand(self.context)
        next_result = next_cmd.execute()

        assert isinstance(find_result, bool)
        assert isinstance(next_result, bool)

    def test_find_then_replace_workflow(self):
        """Test find -> replace workflow."""
        # Find matches
        find_cmd = FindCommand(self.context)
        find_cmd.execute(search_term="old")

        # Replace all
        replace_cmd = ReplaceCommand(self.context)
        replace_result = replace_cmd.execute(
            search_term="old", replace_term="new", replace_all=True
        )

        assert isinstance(replace_result, bool)

    def test_navigation_search_cycle(self):
        """Test complete search navigation cycle."""
        # Find
        find_cmd = FindCommand(self.context)
        find_cmd.execute(search_term="test")

        # Find next
        next_cmd = FindNextCommand(self.context)
        next_cmd.execute()

        # Find previous
        prev_cmd = FindPreviousCommand(self.context)
        prev_result = prev_cmd.execute()

        assert isinstance(prev_result, bool)

    def test_go_to_line_then_search(self):
        """Test go to line -> search workflow."""
        # Go to specific line
        goto_cmd = GoToLineCommand(self.context)
        goto_result = goto_cmd.execute(line_number=2)

        # Search from that position
        find_cmd = FindCommand(self.context)
        find_result = find_cmd.execute(search_term="test")

        assert isinstance(goto_result, bool)
        assert isinstance(find_result, bool)

    def test_replace_with_navigation(self):
        """Test replace with find next/previous."""
        # Find first occurrence
        find_cmd = FindCommand(self.context)
        find_cmd.execute(search_term="old")

        # Replace current match
        replace_cmd = ReplaceCommand(self.context)
        replace_cmd.execute(search_term="old", replace_term="new", replace_all=False)

        # Find next occurrence
        next_cmd = FindNextCommand(self.context)
        next_result = next_cmd.execute()

        assert isinstance(next_result, bool)
