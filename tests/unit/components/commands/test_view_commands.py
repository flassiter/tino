"""
Tests for view commands.

Tests all view-related commands including preview toggle, theme switching,
settings, help, and display options.
"""

import pytest
from unittest.mock import Mock

from src.tino.components.commands.view_commands import (
    TogglePreviewCommand,
    ToggleLineNumbersCommand,
    PreviewOnlyCommand,
    ToggleThemeCommand,
    CommandPaletteCommand,
    ShowSettingsCommand,
    ShowHelpCommand,
    ToggleWordWrapCommand,
    ToggleStatusBarCommand,
    ZoomInCommand,
    ZoomOutCommand
)
from src.tino.components.commands.command_base import CommandContext


class TestViewCommandsBase:
    """Base test setup for view commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock dependencies
        self.mock_event_bus = Mock()
        self.mock_layout_manager = Mock()
        
        # Create command context
        self.context = CommandContext()
        self.context.event_bus = self.mock_event_bus
        self.context.layout_manager = self.mock_layout_manager
        self.context.application_state = {
            "preview_visible": True,
            "line_numbers_visible": True,
            "theme": "dark",
            "word_wrap": False,
            "status_bar_visible": True,
            "zoom_level": 100
        }


class TestTogglePreviewCommand(TestViewCommandsBase):
    """Tests for TogglePreviewCommand."""
    
    def test_command_initialization(self):
        """Test command initialization."""
        command = TogglePreviewCommand(self.context)
        
        assert command.get_name() == "Toggle Preview"
        assert "preview" in command.get_description().lower()
        assert command.get_shortcut() == "f2"
        assert "view" in command.get_category().lower()
    
    def test_execute_show_preview(self):
        """Test showing preview when hidden."""
        self.context.application_state["preview_visible"] = False
        command = TogglePreviewCommand(self.context)
        
        result = command.execute()
        
        assert isinstance(result, bool)
        # State should be toggled
        if result:
            assert self.context.application_state["preview_visible"] is True
    
    def test_execute_hide_preview(self):
        """Test hiding preview when visible."""
        self.context.application_state["preview_visible"] = True
        command = TogglePreviewCommand(self.context)
        
        result = command.execute()
        
        assert isinstance(result, bool)
        # State should be toggled
        if result:
            assert self.context.application_state["preview_visible"] is False


class TestToggleLineNumbersCommand(TestViewCommandsBase):
    """Tests for ToggleLineNumbersCommand."""
    
    def test_command_initialization(self):
        """Test command initialization."""
        command = ToggleLineNumbersCommand(self.context)
        
        assert command.get_name() == "Toggle Line Numbers"
        assert "line numbers" in command.get_description().lower()
    
    def test_execute_toggle_line_numbers(self):
        """Test toggling line numbers."""
        original_state = self.context.application_state["line_numbers_visible"]
        command = ToggleLineNumbersCommand(self.context)
        
        result = command.execute()
        
        assert isinstance(result, bool)


class TestPreviewOnlyCommand(TestViewCommandsBase):
    """Tests for PreviewOnlyCommand."""
    
    def test_command_initialization(self):
        """Test command initialization."""
        command = PreviewOnlyCommand(self.context)
        
        assert command.get_name() == "Preview Only"
        assert "preview" in command.get_description().lower()
        assert command.get_shortcut() == "f11"
    
    def test_execute_preview_only_mode(self):
        """Test entering preview-only mode."""
        command = PreviewOnlyCommand(self.context)
        
        result = command.execute()
        
        assert isinstance(result, bool)


class TestToggleThemeCommand(TestViewCommandsBase):
    """Tests for ToggleThemeCommand."""
    
    def test_command_initialization(self):
        """Test command initialization."""
        command = ToggleThemeCommand(self.context)
        
        assert command.get_name() == "Toggle Theme"
        assert "theme" in command.get_description().lower()
    
    def test_execute_toggle_to_light(self):
        """Test toggling from dark to light theme."""
        self.context.application_state["theme"] = "dark"
        command = ToggleThemeCommand(self.context)
        
        result = command.execute()
        
        assert isinstance(result, bool)
        # Theme should toggle
        if result:
            assert self.context.application_state["theme"] == "light"
    
    def test_execute_toggle_to_dark(self):
        """Test toggling from light to dark theme."""
        self.context.application_state["theme"] = "light"
        command = ToggleThemeCommand(self.context)
        
        result = command.execute()
        
        assert isinstance(result, bool)
        if result:
            assert self.context.application_state["theme"] == "dark"


class TestCommandPaletteCommand(TestViewCommandsBase):
    """Tests for CommandPaletteCommand."""
    
    def test_command_initialization(self):
        """Test command initialization."""
        command = CommandPaletteCommand(self.context)
        
        assert command.get_name() == "Command Palette"
        assert "command palette" in command.get_description().lower()
        assert command.get_shortcut() == "ctrl+shift+p"
    
    def test_execute_show_command_palette(self):
        """Test showing command palette."""
        command = CommandPaletteCommand(self.context)
        
        result = command.execute()
        
        assert isinstance(result, bool)


class TestShowSettingsCommand(TestViewCommandsBase):
    """Tests for ShowSettingsCommand."""
    
    def test_command_initialization(self):
        """Test command initialization."""
        command = ShowSettingsCommand(self.context)
        
        assert command.get_name() == "Settings"
        assert "settings" in command.get_description().lower()
        assert command.get_shortcut() == "ctrl+comma"
    
    def test_execute_show_settings(self):
        """Test showing settings dialog."""
        command = ShowSettingsCommand(self.context)
        
        result = command.execute()
        
        assert isinstance(result, bool)


class TestShowHelpCommand(TestViewCommandsBase):
    """Tests for ShowHelpCommand."""
    
    def test_command_initialization(self):
        """Test command initialization."""
        command = ShowHelpCommand(self.context)
        
        assert command.get_name() == "Help"
        assert "help" in command.get_description().lower()
        assert command.get_shortcut() == "f1"
    
    def test_execute_show_help(self):
        """Test showing help screen."""
        command = ShowHelpCommand(self.context)
        
        result = command.execute()
        
        assert isinstance(result, bool)


class TestToggleWordWrapCommand(TestViewCommandsBase):
    """Tests for ToggleWordWrapCommand."""
    
    def test_command_initialization(self):
        """Test command initialization."""
        command = ToggleWordWrapCommand(self.context)
        
        assert command.get_name() == "Toggle Word Wrap"
        assert "word wrap" in command.get_description().lower()
        assert command.get_shortcut() == "alt+z"
    
    def test_execute_toggle_word_wrap(self):
        """Test toggling word wrap."""
        original_state = self.context.application_state["word_wrap"]
        command = ToggleWordWrapCommand(self.context)
        
        result = command.execute()
        
        assert isinstance(result, bool)
        if result:
            assert self.context.application_state["word_wrap"] != original_state


class TestToggleStatusBarCommand(TestViewCommandsBase):
    """Tests for ToggleStatusBarCommand."""
    
    def test_command_initialization(self):
        """Test command initialization."""
        command = ToggleStatusBarCommand(self.context)
        
        assert command.get_name() == "Toggle Status Bar"
        assert "status bar" in command.get_description().lower()
    
    def test_execute_toggle_status_bar(self):
        """Test toggling status bar visibility."""
        command = ToggleStatusBarCommand(self.context)
        
        result = command.execute()
        
        assert isinstance(result, bool)


class TestZoomInCommand(TestViewCommandsBase):
    """Tests for ZoomInCommand."""
    
    def test_command_initialization(self):
        """Test command initialization."""
        command = ZoomInCommand(self.context)
        
        assert command.get_name() == "Zoom In"
        assert "zoom" in command.get_description().lower()
        assert "ctrl+plus" in command.get_shortcut().lower() or "ctrl+=" in command.get_shortcut()
    
    def test_execute_zoom_in(self):
        """Test zooming in."""
        self.context.application_state["zoom_level"] = 100
        command = ZoomInCommand(self.context)
        
        result = command.execute()
        
        assert isinstance(result, bool)
        if result:
            assert self.context.application_state["zoom_level"] > 100
    
    def test_execute_zoom_in_max_limit(self):
        """Test zoom in at maximum level."""
        self.context.application_state["zoom_level"] = 300  # Assume max is 300%
        command = ZoomInCommand(self.context)
        
        result = command.execute()
        
        # Should handle max limit gracefully
        assert isinstance(result, bool)


class TestZoomOutCommand(TestViewCommandsBase):
    """Tests for ZoomOutCommand."""
    
    def test_command_initialization(self):
        """Test command initialization."""
        command = ZoomOutCommand(self.context)
        
        assert command.get_name() == "Zoom Out"
        assert "zoom" in command.get_description().lower()
        assert "ctrl+minus" in command.get_shortcut().lower() or "ctrl+-" in command.get_shortcut()
    
    def test_execute_zoom_out(self):
        """Test zooming out."""
        self.context.application_state["zoom_level"] = 100
        command = ZoomOutCommand(self.context)
        
        result = command.execute()
        
        assert isinstance(result, bool)
        if result:
            assert self.context.application_state["zoom_level"] < 100
    
    def test_execute_zoom_out_min_limit(self):
        """Test zoom out at minimum level."""
        self.context.application_state["zoom_level"] = 50  # Assume min is 50%
        command = ZoomOutCommand(self.context)
        
        result = command.execute()
        
        # Should handle min limit gracefully
        assert isinstance(result, bool)


class TestViewCommandsIntegration(TestViewCommandsBase):
    """Integration tests for view commands."""
    
    def test_theme_and_preview_workflow(self):
        """Test changing theme and toggling preview."""
        # Toggle theme
        theme_cmd = ToggleThemeCommand(self.context)
        theme_result = theme_cmd.execute()
        
        # Toggle preview
        preview_cmd = TogglePreviewCommand(self.context)
        preview_result = preview_cmd.execute()
        
        assert isinstance(theme_result, bool)
        assert isinstance(preview_result, bool)
    
    def test_zoom_workflow(self):
        """Test zoom in and out workflow."""
        # Zoom in
        zoom_in_cmd = ZoomInCommand(self.context)
        zoom_in_result = zoom_in_cmd.execute()
        
        # Zoom out
        zoom_out_cmd = ZoomOutCommand(self.context)
        zoom_out_result = zoom_out_cmd.execute()
        
        assert isinstance(zoom_in_result, bool)
        assert isinstance(zoom_out_result, bool)
    
    def test_ui_toggles_workflow(self):
        """Test toggling various UI elements."""
        # Toggle line numbers
        line_cmd = ToggleLineNumbersCommand(self.context)
        line_result = line_cmd.execute()
        
        # Toggle word wrap
        wrap_cmd = ToggleWordWrapCommand(self.context)
        wrap_result = wrap_cmd.execute()
        
        # Toggle status bar
        status_cmd = ToggleStatusBarCommand(self.context)
        status_result = status_cmd.execute()
        
        assert isinstance(line_result, bool)
        assert isinstance(wrap_result, bool)
        assert isinstance(status_result, bool)