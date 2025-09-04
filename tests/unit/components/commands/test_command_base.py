"""
Tests for command base classes and interfaces.

Tests the BaseCommand, EditorCommand, FileCommand, and other base classes
used throughout the command system.
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Any, Optional

from src.tino.components.commands.command_base import (
    BaseCommand, EditorCommand, FileCommand, AsyncCommand, MockCommand,
    CommandContext
)
from src.tino.components.commands.categories import CommandCategory
from src.tino.core.interfaces.command import CommandError
from src.tino.core.events.bus import EventBus


class ConcreteTestCommand(BaseCommand):
    """Test command implementation."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        test_arg = kwargs.get('test_arg', False)
        if test_arg:
            self._mark_executed(can_undo=True)
            return True
        return False
    
    def undo(self) -> bool:
        return self.can_undo()
    
    def get_name(self) -> str:
        return "Test Command"
    
    def get_description(self) -> str:
        return "A test command for unit testing"
    
    def get_category(self) -> str:
        return CommandCategory.TOOLS.value


class ConcreteEditorCommand(EditorCommand):
    """Concrete editor command for testing."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        if self.context.editor:
            return True
        return False
    
    def undo(self) -> bool:
        return True
    
    def get_name(self) -> str:
        return "Test Editor Command"
    
    def get_description(self) -> str:
        return "A test editor command"
    
    def get_category(self) -> str:
        return CommandCategory.EDIT.value


class ConcreteFileCommand(FileCommand):
    """Concrete file command for testing."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        if self.context.file_manager:
            return True
        return False
    
    def undo(self) -> bool:
        return True
    
    def get_name(self) -> str:
        return "Test File Command"
    
    def get_description(self) -> str:
        return "A test file command"
    
    def get_category(self) -> str:
        return CommandCategory.FILE.value


class TestCommandBase:
    """Test BaseCommand functionality."""
    
    def test_command_initialization(self):
        """Test command initialization with context."""
        context = CommandContext()
        command = ConcreteTestCommand(context)
        
        assert command.context is context
        assert not command._executed
        assert not command._can_undo
    
    def test_command_execution_success(self):
        """Test successful command execution."""
        command = ConcreteTestCommand()
        
        result = command.execute(test_arg=True)
        
        assert result is True
        assert command._executed
        assert command.can_undo()
    
    def test_command_execution_failure(self):
        """Test command execution failure."""
        command = ConcreteTestCommand()
        
        result = command.execute(test_arg=False)
        
        assert result is False
        assert not command._executed
        assert not command.can_undo()
    
    def test_command_undo(self):
        """Test command undo functionality."""
        command = ConcreteTestCommand()
        
        # Cannot undo before execution
        assert not command.undo()
        
        # Execute command
        command.execute(test_arg=True)
        assert command.can_undo()
        
        # Undo should work
        assert command.undo()
    
    def test_can_execute_validation(self):
        """Test command execution validation."""
        command = ConcreteTestCommand()
        
        # Should be able to execute by default
        assert command.can_execute()
        assert command.can_execute(test_arg=True)
    
    def test_parameter_validation(self):
        """Test parameter validation."""
        command = ConcreteTestCommand()
        
        # Default implementation accepts any parameters
        assert command.validate_parameters() is None
        assert command.validate_parameters("arg1", "arg2", key="value") is None
    
    def test_execution_data_storage(self):
        """Test execution data storage and retrieval."""
        command = ConcreteTestCommand()
        
        # Store and retrieve data
        command._store_execution_data("test_key", "test_value")
        assert command._get_execution_data("test_key") == "test_value"
        assert command._get_execution_data("missing_key", "default") == "default"
    
    def test_event_emission(self):
        """Test event emission through context."""
        event_bus = Mock(spec=EventBus)
        context = CommandContext(event_bus=event_bus)
        command = ConcreteTestCommand(context)
        
        # Create mock event
        mock_event = Mock()
        command._emit_event(mock_event)
        
        event_bus.emit.assert_called_once_with(mock_event)
    
    def test_execution_context(self):
        """Test execution context information."""
        context = CommandContext()
        command = ConcreteTestCommand(context)
        
        exec_context = command.get_execution_context()
        
        assert 'has_editor' in exec_context
        assert 'has_file_manager' in exec_context
        assert 'executed' in exec_context
        assert 'can_undo' in exec_context
    
    def test_shortcut_and_parameters(self):
        """Test shortcut and parameter definitions."""
        command = ConcreteTestCommand()
        
        # Default implementations
        assert command.get_shortcut() is None
        assert command.get_parameters() == {}
        assert not command.is_async()
        assert not command.requires_confirmation()
        assert command.get_estimated_duration() == 0.0


class TestEditorCommand:
    """Test EditorCommand functionality."""
    
    def test_editor_context_validation(self):
        """Test editor context validation."""
        # Without editor
        context = CommandContext()
        command = ConcreteEditorCommand(context)
        
        assert not command._check_context()
        
        # With editor
        mock_editor = Mock()
        context.editor = mock_editor
        command = ConcreteEditorCommand(context)
        
        assert command._check_context()
    
    def test_editor_property_access(self):
        """Test editor property access."""
        mock_editor = Mock()
        context = CommandContext(editor=mock_editor)
        command = ConcreteEditorCommand(context)
        
        assert command.editor is mock_editor
    
    def test_editor_property_error(self):
        """Test editor property error when no editor available."""
        context = CommandContext()
        command = ConcreteEditorCommand(context)
        
        with pytest.raises(CommandError) as exc_info:
            _ = command.editor
        
        assert "No editor available" in str(exc_info.value)


class TestFileCommand:
    """Test FileCommand functionality."""
    
    def test_file_manager_context_validation(self):
        """Test file manager context validation."""
        # Without file manager
        context = CommandContext()
        command = ConcreteFileCommand(context)
        
        assert not command._check_context()
        
        # With file manager
        mock_file_manager = Mock()
        context.file_manager = mock_file_manager
        command = ConcreteFileCommand(context)
        
        assert command._check_context()
    
    def test_file_manager_property_access(self):
        """Test file manager property access."""
        mock_file_manager = Mock()
        context = CommandContext(file_manager=mock_file_manager)
        command = ConcreteFileCommand(context)
        
        assert command.file_manager is mock_file_manager
    
    def test_file_manager_property_error(self):
        """Test file manager property error when not available."""
        context = CommandContext()
        command = ConcreteFileCommand(context)
        
        with pytest.raises(CommandError) as exc_info:
            _ = command.file_manager
        
        assert "No file manager available" in str(exc_info.value)


class TestAsyncCommand:
    """Test AsyncCommand functionality."""
    
    async def async_test_command_impl(self, *args: Any, **kwargs: Any) -> bool:
        """Test async command implementation."""
        return kwargs.get('success', True)
    
    def test_async_command_is_async(self):
        """Test async command identification."""
        # Create a simple async command for testing
        class TestAsyncCommand(AsyncCommand):
            async def _execute_async_impl(self, *args: Any, **kwargs: Any) -> bool:
                return kwargs.get('success', True)
            
            def undo(self) -> bool:
                return True
            
            def get_name(self) -> str:
                return "Test Async"
            
            def get_description(self) -> str:
                return "Test async command"
            
            def get_category(self) -> str:
                return CommandCategory.TOOLS.value
        
        command = TestAsyncCommand()
        assert command.is_async()
    
    @pytest.mark.asyncio
    async def test_async_command_execution(self):
        """Test async command execution."""
        class TestAsyncCommand(AsyncCommand):
            async def _execute_async_impl(self, *args: Any, **kwargs: Any) -> bool:
                return kwargs.get('success', True)
            
            def undo(self) -> bool:
                return True
            
            def get_name(self) -> str:
                return "Test Async"
            
            def get_description(self) -> str:
                return "Test async command"
            
            def get_category(self) -> str:
                return CommandCategory.TOOLS.value
        
        command = TestAsyncCommand()
        
        result = await command.execute_async(success=True)
        assert result is True
        
        result = await command.execute_async(success=False)
        assert result is False


class TestMockCommand:
    """Test MockCommand functionality."""
    
    def test_mock_command_initialization(self):
        """Test mock command initialization."""
        command = MockCommand("Test Mock", CommandCategory.TOOLS)
        
        assert command.get_name() == "Test Mock"
        assert command.get_category() == CommandCategory.TOOLS.value
        assert command.get_description() == "Mock command: Test Mock"
        assert command.get_execution_count() == 0
        assert command.get_undo_count() == 0
    
    def test_mock_command_execution_tracking(self):
        """Test mock command execution tracking."""
        command = MockCommand("Test Mock", CommandCategory.TOOLS)
        
        # Execute multiple times
        result1 = command.execute()
        result2 = command.execute("arg")
        result3 = command.execute(key="value")
        
        assert result1 is True
        assert result2 is True
        assert result3 is True
        assert command.get_execution_count() == 3
    
    def test_mock_command_undo_tracking(self):
        """Test mock command undo tracking."""
        command = MockCommand("Test Mock", CommandCategory.TOOLS)
        
        # Cannot undo before execution
        assert not command.undo()
        assert command.get_undo_count() == 0
        
        # Execute then undo
        command.execute()
        result1 = command.undo()
        result2 = command.undo()  # Should still work with mock
        
        assert result1 is True
        assert result2 is True
        assert command.get_undo_count() == 2
    
    def test_mock_command_result_control(self):
        """Test controlling mock command results."""
        command = MockCommand("Test Mock", CommandCategory.TOOLS)
        
        # Control execution result
        command.set_execute_result(False)
        assert command.execute() is False
        
        command.set_execute_result(True)
        assert command.execute() is True
        
        # Control undo result
        command.set_undo_result(False)
        assert command.undo() is False
        
        command.set_undo_result(True)
        assert command.undo() is True


class TestCommandContext:
    """Test CommandContext functionality."""
    
    def test_context_initialization(self):
        """Test context initialization."""
        context = CommandContext()
        
        assert context.editor is None
        assert context.file_manager is None
        assert context.event_bus is None
        assert context.current_file_path is None
        assert context.application_state == {}
    
    def test_context_with_components(self):
        """Test context with all components."""
        mock_editor = Mock()
        mock_file_manager = Mock()
        mock_event_bus = Mock()
        
        context = CommandContext(
            editor=mock_editor,
            file_manager=mock_file_manager,
            event_bus=mock_event_bus,
            current_file_path="/test/file.md",
            application_state={'key': 'value'}
        )
        
        assert context.editor is mock_editor
        assert context.file_manager is mock_file_manager
        assert context.event_bus is mock_event_bus
        assert context.current_file_path == "/test/file.md"
        assert context.application_state == {'key': 'value'}
    
    def test_context_modification(self):
        """Test context state modification."""
        context = CommandContext()
        
        # Modify application state
        context.application_state['new_key'] = 'new_value'
        assert context.application_state['new_key'] == 'new_value'
        
        # Modify current file
        context.current_file_path = "/new/file.md"
        assert context.current_file_path == "/new/file.md"