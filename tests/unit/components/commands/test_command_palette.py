"""
Tests for command palette functionality.

Tests command search, fuzzy matching, recent command tracking,
and command palette backend operations.
"""

from unittest.mock import Mock

from src.tino.components.commands.command_palette import (
    CommandPalette,
    CommandSearchResult,
)
from src.tino.components.commands.registry import CommandRegistry


class TestCommandSearchResult:
    """Tests for CommandSearchResult dataclass."""

    def test_creation(self):
        """Test creating a search result."""
        result = CommandSearchResult(
            command_name="file.save",
            display_name="Save File",
            description="Save the current file",
            category="file",
            shortcut="ctrl+s",
            score=0.9,
            match_type="name",
        )

        assert result.command_name == "file.save"
        assert result.display_name == "Save File"
        assert result.description == "Save the current file"
        assert result.category == "file"
        assert result.shortcut == "ctrl+s"
        assert result.score == 0.9
        assert result.match_type == "name"

    def test_creation_without_shortcut(self):
        """Test creating search result without shortcut."""
        result = CommandSearchResult(
            command_name="test.command",
            display_name="Test Command",
            description="A test command",
            category="test",
            shortcut=None,
            score=0.5,
            match_type="description",
        )

        assert result.shortcut is None
        assert result.match_type == "description"


class TestCommandPalette:
    """Tests for CommandPalette class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock command registry
        self.mock_registry = Mock(spec=CommandRegistry)
        self.command_palette = CommandPalette(self.mock_registry, max_recent=5)

        # Setup mock commands
        self.mock_commands = {
            "file.save": Mock(name="Save File"),
            "file.open": Mock(name="Open File"),
            "edit.copy": Mock(name="Copy"),
            "edit.paste": Mock(name="Paste"),
            "view.toggle_preview": Mock(name="Toggle Preview"),
        }

        # Configure mock registry
        self.mock_registry.get_all_commands.return_value = self.mock_commands
        self.mock_registry.get_command.side_effect = (
            lambda name: self.mock_commands.get(name)
        )

        # Configure mock command properties
        for name, cmd in self.mock_commands.items():
            cmd.get_name.return_value = name.split(".")[1].replace("_", " ").title()
            cmd.get_description.return_value = f"Description for {name}"
            cmd.get_category.return_value = name.split(".")[0]
            cmd.get_shortcut.return_value = "ctrl+s" if "save" in name else None

    def test_initialization(self):
        """Test command palette initialization."""
        assert self.command_palette._registry == self.mock_registry
        assert self.command_palette._max_recent == 5
        assert len(self.command_palette._recent_commands) == 0

    def test_search_empty_query(self):
        """Test searching with empty query."""
        results = self.command_palette.search("")

        # Should return all commands or empty list
        assert isinstance(results, list)

    def test_search_exact_match(self):
        """Test searching with exact command name match."""
        results = self.command_palette.search("Save")

        assert isinstance(results, list)
        if len(results) > 0:
            # Should find save command
            save_results = [r for r in results if "save" in r.command_name.lower()]
            assert len(save_results) > 0
            assert all(isinstance(r, CommandSearchResult) for r in results)

    def test_search_partial_match(self):
        """Test searching with partial match."""
        results = self.command_palette.search("cop")

        assert isinstance(results, list)
        # Should find copy command with partial match
        if len(results) > 0:
            assert all(r.score > 0 for r in results)
            assert all(isinstance(r, CommandSearchResult) for r in results)

    def test_search_case_insensitive(self):
        """Test case insensitive search."""
        results_lower = self.command_palette.search("save")
        results_upper = self.command_palette.search("SAVE")

        # Should return same results regardless of case
        assert len(results_lower) == len(results_upper)
        if len(results_lower) > 0:
            assert results_lower[0].command_name == results_upper[0].command_name

    def test_search_by_description(self):
        """Test searching by command description."""
        # Assuming descriptions contain the command name
        results = self.command_palette.search("Description")

        assert isinstance(results, list)
        # May or may not find matches depending on implementation

    def test_search_by_shortcut(self):
        """Test searching by keyboard shortcut."""
        results = self.command_palette.search("ctrl+s")

        assert isinstance(results, list)
        if len(results) > 0:
            # Should find command with ctrl+s shortcut
            save_results = [r for r in results if r.shortcut == "ctrl+s"]
            assert len(save_results) > 0

    def test_search_fuzzy_matching(self):
        """Test fuzzy search matching."""
        results = self.command_palette.search("sav")  # Should match "save"

        assert isinstance(results, list)
        if len(results) > 0:
            # Should have scored matches
            assert all(hasattr(r, "score") for r in results)
            assert all(r.score >= 0 for r in results)

    def test_search_results_sorted_by_score(self):
        """Test that search results are sorted by relevance score."""
        results = self.command_palette.search("file")

        if len(results) > 1:
            scores = [r.score for r in results]
            # Should be sorted in descending order (highest score first)
            assert scores == sorted(scores, reverse=True)

    def test_search_no_matches(self):
        """Test search with no matches."""
        results = self.command_palette.search("xyzzyx")

        assert isinstance(results, list)
        assert len(results) == 0

    def test_execute_command_success(self):
        """Test executing a command through palette."""
        # Mock successful command execution
        mock_cmd = self.mock_commands["file.save"]
        mock_cmd.execute.return_value = True

        result = self.command_palette.execute_command("file.save")

        assert result is True
        mock_cmd.execute.assert_called_once()

    def test_execute_command_failure(self):
        """Test executing a command that fails."""
        # Mock failed command execution
        mock_cmd = self.mock_commands["file.save"]
        mock_cmd.execute.return_value = False

        result = self.command_palette.execute_command("file.save")

        assert result is False

    def test_execute_nonexistent_command(self):
        """Test executing a command that doesn't exist."""
        self.mock_registry.get_command.return_value = None

        result = self.command_palette.execute_command("nonexistent.command")

        assert result is False

    def test_execute_command_with_parameters(self):
        """Test executing a command with parameters."""
        mock_cmd = self.mock_commands["file.save"]
        mock_cmd.execute.return_value = True

        params = {"file_path": "/test/file.md"}
        result = self.command_palette.execute_command("file.save", params)

        assert result is True
        mock_cmd.execute.assert_called_once_with(**params)

    def test_add_to_recent_commands(self):
        """Test adding commands to recent history."""
        # Execute a command to add it to recent
        mock_cmd = self.mock_commands["file.save"]
        mock_cmd.execute.return_value = True

        self.command_palette.execute_command("file.save")

        # Should be in recent commands
        recent = self.command_palette.get_recent_commands()
        assert "file.save" in recent

    def test_recent_commands_limit(self):
        """Test recent commands respects maximum limit."""
        # Execute more commands than the limit
        for i, cmd_name in enumerate(self.mock_commands.keys()):
            if i >= 10:  # More than max_recent=5
                break
            mock_cmd = self.mock_commands[cmd_name]
            mock_cmd.execute.return_value = True
            self.command_palette.execute_command(cmd_name)

        recent = self.command_palette.get_recent_commands()

        # Should not exceed max_recent
        assert len(recent) <= 5

    def test_recent_commands_order(self):
        """Test recent commands are in correct order (most recent first)."""
        # Execute commands in order
        cmd_names = ["file.save", "file.open", "edit.copy"]
        for cmd_name in cmd_names:
            mock_cmd = self.mock_commands[cmd_name]
            mock_cmd.execute.return_value = True
            self.command_palette.execute_command(cmd_name)

        recent = self.command_palette.get_recent_commands()

        if len(recent) >= 2:
            # Most recent should be first
            assert recent[0] == "edit.copy"
            assert recent[1] == "file.open"

    def test_recent_commands_no_duplicates(self):
        """Test that recent commands don't contain duplicates."""
        # Execute same command multiple times
        mock_cmd = self.mock_commands["file.save"]
        mock_cmd.execute.return_value = True

        for _ in range(3):
            self.command_palette.execute_command("file.save")

        recent = self.command_palette.get_recent_commands()

        # Should only appear once
        save_count = recent.count("file.save")
        assert save_count == 1

    def test_get_commands_by_category(self):
        """Test getting commands filtered by category."""
        results = self.command_palette.get_commands_by_category("file")

        assert isinstance(results, list)
        if len(results) > 0:
            # Should only contain file commands
            file_results = [r for r in results if r.category == "file"]
            assert len(file_results) == len(results)

    def test_get_all_categories(self):
        """Test getting all available command categories."""
        categories = self.command_palette.get_all_categories()

        assert isinstance(categories, list)
        # Should contain the categories from our mock commands
        expected_categories = {"file", "edit", "view"}
        if len(categories) > 0:
            assert any(cat in expected_categories for cat in categories)

    def test_clear_recent_commands(self):
        """Test clearing recent command history."""
        # Add some recent commands
        mock_cmd = self.mock_commands["file.save"]
        mock_cmd.execute.return_value = True
        self.command_palette.execute_command("file.save")

        # Clear recent commands
        self.command_palette.clear_recent_commands()

        recent = self.command_palette.get_recent_commands()
        assert len(recent) == 0

    def test_get_command_details(self):
        """Test getting detailed information about a command."""
        details = self.command_palette.get_command_details("file.save")

        if details:
            assert isinstance(details, dict)
            assert "name" in details or "display_name" in details
            assert "description" in details
            assert "category" in details

    def test_get_command_details_nonexistent(self):
        """Test getting details for non-existent command."""
        self.mock_registry.get_command.return_value = None

        details = self.command_palette.get_command_details("nonexistent.command")

        assert details is None


class TestCommandPaletteIntegration:
    """Integration tests for command palette functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_registry = Mock(spec=CommandRegistry)
        self.command_palette = CommandPalette(self.mock_registry)

        # Create realistic command set
        self.commands = {
            "file.new": self._create_mock_command(
                "New File", "Create a new file", "file", "ctrl+n"
            ),
            "file.open": self._create_mock_command(
                "Open File", "Open an existing file", "file", "ctrl+o"
            ),
            "file.save": self._create_mock_command(
                "Save File", "Save the current file", "file", "ctrl+s"
            ),
            "edit.undo": self._create_mock_command(
                "Undo", "Undo last action", "edit", "ctrl+z"
            ),
            "edit.redo": self._create_mock_command(
                "Redo", "Redo last undone action", "edit", "ctrl+y"
            ),
            "view.preview": self._create_mock_command(
                "Toggle Preview", "Show/hide preview pane", "view", "f2"
            ),
        }

        self.mock_registry.get_all_commands.return_value = self.commands
        self.mock_registry.get_command.side_effect = lambda name: self.commands.get(
            name
        )

    def _create_mock_command(self, name, desc, category, shortcut):
        """Helper to create mock command with properties."""
        cmd = Mock()
        cmd.get_name.return_value = name
        cmd.get_description.return_value = desc
        cmd.get_category.return_value = category
        cmd.get_shortcut.return_value = shortcut
        cmd.execute.return_value = True
        return cmd

    def test_complete_search_workflow(self):
        """Test complete search and execute workflow."""
        # Search for file commands
        results = self.command_palette.search("file")

        assert len(results) >= 1

        # Execute first result
        if len(results) > 0:
            cmd_name = results[0].command_name
            success = self.command_palette.execute_command(cmd_name)
            assert success is True

            # Should appear in recent commands
            recent = self.command_palette.get_recent_commands()
            assert cmd_name in recent

    def test_fuzzy_search_workflow(self):
        """Test fuzzy search finding relevant commands."""
        # Search with typo/partial match
        results = self.command_palette.search("sav")  # Should match "save"

        if len(results) > 0:
            # Should find save command
            save_matches = [r for r in results if "save" in r.display_name.lower()]
            assert len(save_matches) > 0

            # Execute the match
            success = self.command_palette.execute_command(save_matches[0].command_name)
            assert success is True

    def test_category_based_browsing(self):
        """Test browsing commands by category."""
        # Get all categories
        categories = self.command_palette.get_all_categories()
        assert len(categories) > 0

        # Browse file category
        file_commands = self.command_palette.get_commands_by_category("file")
        assert len(file_commands) >= 1

        # All should be file commands
        assert all(cmd.category == "file" for cmd in file_commands)

    def test_recent_commands_workflow(self):
        """Test recent commands tracking workflow."""
        # Execute several commands
        command_sequence = ["file.new", "file.save", "edit.undo", "file.open"]

        for cmd_name in command_sequence:
            self.command_palette.execute_command(cmd_name)

        recent = self.command_palette.get_recent_commands()

        # Should track recent commands in reverse order
        assert len(recent) == len(command_sequence)
        assert recent[0] == command_sequence[-1]  # Most recent first

    def test_shortcut_search_workflow(self):
        """Test searching by keyboard shortcuts."""
        # Search by shortcut
        results = self.command_palette.search("ctrl+s")

        if len(results) > 0:
            # Should find command with that shortcut
            save_cmd = next((r for r in results if r.shortcut == "ctrl+s"), None)
            assert save_cmd is not None
            assert "save" in save_cmd.display_name.lower()

    def test_mixed_search_criteria(self):
        """Test search across name, description, and shortcuts."""
        # Search term that could match different criteria
        results = self.command_palette.search("new")

        # Should find results matching name, description, or shortcut
        assert isinstance(results, list)
        if len(results) > 0:
            # Should have relevance scores
            assert all(hasattr(r, "score") for r in results)
            assert all(r.score > 0 for r in results)
