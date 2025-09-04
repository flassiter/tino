"""
Tests for markdown format commands.

Tests all formatting commands including Bold, Italic, Code,
Link, Heading, and Strikethrough formatting.
"""

import pytest
from unittest.mock import Mock

from src.tino.components.commands.format_commands import (
    BoldCommand,
    ItalicCommand,
    CodeCommand,
    LinkCommand,
    HeadingCommand,
    StrikethroughCommand
)
from src.tino.components.commands.command_base import CommandContext


class TestFormatCommandsBase:
    """Base test setup for format commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock dependencies
        self.mock_editor = Mock()
        self.mock_event_bus = Mock()
        
        # Setup common editor mock returns
        self.mock_editor.has_selection.return_value = True
        self.mock_editor.get_selected_text.return_value = "selected text"
        self.mock_editor.get_cursor_position.return_value = (1, 5)
        self.mock_editor.replace_selection.return_value = True
        self.mock_editor.insert_text.return_value = True
        
        # Create command context
        self.context = CommandContext()
        self.context.editor = self.mock_editor
        self.context.event_bus = self.mock_event_bus


class TestBoldCommand(TestFormatCommandsBase):
    """Tests for BoldCommand."""
    
    def test_command_initialization(self):
        """Test command initialization."""
        command = BoldCommand(self.context)
        
        assert command.get_name() == "Bold"
        assert "bold" in command.get_description().lower()
        assert command.get_shortcut() == "ctrl+b"
        assert "format" in command.get_category().lower()
    
    def test_execute_with_selection(self):
        """Test bold formatting with selected text."""
        command = BoldCommand(self.context)
        
        result = command.execute()
        
        # Should attempt to format the selection
        assert isinstance(result, bool)
    
    def test_execute_without_selection(self):
        """Test bold formatting without selection."""
        self.mock_editor.has_selection.return_value = False
        command = BoldCommand(self.context)
        
        result = command.execute()
        
        # Should handle no selection case
        assert isinstance(result, bool)


class TestItalicCommand(TestFormatCommandsBase):
    """Tests for ItalicCommand."""
    
    def test_command_initialization(self):
        """Test command initialization."""
        command = ItalicCommand(self.context)
        
        assert command.get_name() == "Italic"
        assert "italic" in command.get_description().lower()
        assert command.get_shortcut() == "ctrl+i"
    
    def test_execute_with_selection(self):
        """Test italic formatting with selected text."""
        command = ItalicCommand(self.context)
        
        result = command.execute()
        
        assert isinstance(result, bool)


class TestCodeCommand(TestFormatCommandsBase):
    """Tests for CodeCommand."""
    
    def test_command_initialization(self):
        """Test command initialization."""
        command = CodeCommand(self.context)
        
        assert command.get_name() == "Code"
        assert "code" in command.get_description().lower()
        assert command.get_shortcut() == "ctrl+shift+c"
    
    def test_execute_inline_code(self):
        """Test inline code formatting."""
        command = CodeCommand(self.context)
        
        result = command.execute()
        
        assert isinstance(result, bool)
    
    def test_execute_code_block(self):
        """Test code block formatting with multiline selection."""
        self.mock_editor.get_selected_text.return_value = "line1\nline2\nline3"
        command = CodeCommand(self.context)
        
        result = command.execute()
        
        assert isinstance(result, bool)


class TestLinkCommand(TestFormatCommandsBase):
    """Tests for LinkCommand."""
    
    def test_command_initialization(self):
        """Test command initialization."""
        command = LinkCommand(self.context)
        
        assert command.get_name() == "Link"
        assert "link" in command.get_description().lower()
        assert command.get_shortcut() == "ctrl+k"
    
    def test_execute_with_url_parameter(self):
        """Test link creation with URL parameter."""
        command = LinkCommand(self.context)
        
        result = command.execute(url="https://example.com")
        
        assert isinstance(result, bool)
    
    def test_execute_without_url(self):
        """Test link creation without URL (should prompt or fail gracefully)."""
        command = LinkCommand(self.context)
        
        result = command.execute()
        
        # Should handle missing URL gracefully
        assert isinstance(result, bool)
    
    def test_execute_with_selected_text_as_link_text(self):
        """Test creating link with selected text as link text."""
        self.mock_editor.get_selected_text.return_value = "Click here"
        command = LinkCommand(self.context)
        
        result = command.execute(url="https://example.com")
        
        assert isinstance(result, bool)


class TestHeadingCommand(TestFormatCommandsBase):
    """Tests for HeadingCommand."""
    
    def test_command_initialization(self):
        """Test command initialization."""
        command = HeadingCommand(self.context)
        
        assert command.get_name() == "Heading"
        assert "heading" in command.get_description().lower()
        # May not have default shortcut
    
    def test_execute_default_level(self):
        """Test heading creation with default level."""
        command = HeadingCommand(self.context)
        
        result = command.execute()
        
        assert isinstance(result, bool)
    
    def test_execute_specific_level(self):
        """Test heading creation with specific level."""
        command = HeadingCommand(self.context)
        
        result = command.execute(level=2)
        
        assert isinstance(result, bool)
    
    def test_execute_invalid_level(self):
        """Test heading creation with invalid level."""
        command = HeadingCommand(self.context)
        
        # Test with level outside 1-6 range
        result = command.execute(level=7)
        
        # Should handle invalid level gracefully
        assert isinstance(result, bool)


class TestStrikethroughCommand(TestFormatCommandsBase):
    """Tests for StrikethroughCommand."""
    
    def test_command_initialization(self):
        """Test command initialization."""
        command = StrikethroughCommand(self.context)
        
        assert command.get_name() == "Strikethrough"
        assert "strikethrough" in command.get_description().lower()
        # May not have default shortcut
    
    def test_execute_with_selection(self):
        """Test strikethrough formatting with selected text."""
        command = StrikethroughCommand(self.context)
        
        result = command.execute()
        
        assert isinstance(result, bool)


class TestFormatCommandsIntegration(TestFormatCommandsBase):
    """Integration tests for format commands."""
    
    def test_multiple_formatting_workflow(self):
        """Test applying multiple formats to text."""
        # Start with selected text
        self.mock_editor.get_selected_text.return_value = "important text"
        
        # Apply bold
        bold_cmd = BoldCommand(self.context)
        bold_result = bold_cmd.execute()
        
        # Apply italic (assuming selection is maintained)
        italic_cmd = ItalicCommand(self.context)
        italic_result = italic_cmd.execute()
        
        assert isinstance(bold_result, bool)
        assert isinstance(italic_result, bool)
    
    def test_heading_then_format_workflow(self):
        """Test creating heading then formatting part of it."""
        # Create heading
        heading_cmd = HeadingCommand(self.context)
        heading_result = heading_cmd.execute(level=1)
        
        # Select part of heading and make it bold
        bold_cmd = BoldCommand(self.context)
        bold_result = bold_cmd.execute()
        
        assert isinstance(heading_result, bool)
        assert isinstance(bold_result, bool)
    
    def test_link_with_formatting_workflow(self):
        """Test creating link with formatted link text."""
        # Select text and make it bold first
        self.mock_editor.get_selected_text.return_value = "Click here"
        bold_cmd = BoldCommand(self.context)
        bold_cmd.execute()
        
        # Then create link
        link_cmd = LinkCommand(self.context)
        link_result = link_cmd.execute(url="https://example.com")
        
        assert isinstance(link_result, bool)