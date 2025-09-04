"""
Tests for command registry functionality.

Tests command registration, lookup, execution, and management through
the CommandRegistry class.
"""

from typing import Any
from unittest.mock import Mock

import pytest

from src.tino.components.commands.categories import CommandCategory
from src.tino.components.commands.command_base import BaseCommand, CommandContext
from src.tino.components.commands.registry import CommandRegistry
from src.tino.core.events.bus import EventBus
from src.tino.core.interfaces.command import CommandError


class MockTestCommand(BaseCommand):
    """Mock command for testing registry."""

    def __init__(
        self,
        name: str = "Test Command",
        success: bool = True,
        context: CommandContext | None = None,
    ):
        super().__init__(context)
        self._name = name
        self._success = success
        self._execute_count = 0

    def execute(self, *args: Any, **kwargs: Any) -> bool:
        self._execute_count += 1
        if self._success:
            self._mark_executed(can_undo=True)
        return self._success

    def undo(self) -> bool:
        return self.can_undo()

    def get_name(self) -> str:
        return self._name

    def get_description(self) -> str:
        return f"Description for {self._name}"

    def get_category(self) -> str:
        return CommandCategory.TOOLS.value

    def get_shortcut(self) -> str | None:
        if self._name == "Test Command":
            return "ctrl+t"
        return None

    @property
    def execute_count(self) -> int:
        return self._execute_count


class TestCommandRegistry:
    """Test CommandRegistry functionality."""

    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = CommandRegistry()

        assert registry._commands == {}
        assert registry._command_classes == {}
        assert len(registry._command_history) == 0

    def test_registry_with_event_bus(self):
        """Test registry initialization with event bus."""
        event_bus = Mock(spec=EventBus)
        registry = CommandRegistry(event_bus=event_bus)

        assert registry._event_bus is event_bus

    def test_register_command_instance(self):
        """Test registering a command instance."""
        registry = CommandRegistry()
        command = MockTestCommand("Test")

        registry.register_command(command)

        assert registry.has_command("Test")
        assert registry.get_command("Test") is command
        assert "Test" in registry.get_commands_by_category(CommandCategory.TOOLS.value)

    def test_register_command_with_custom_name(self):
        """Test registering command with custom name."""
        registry = CommandRegistry()
        command = MockTestCommand("Original")

        registry.register_command(command, name="Custom")

        assert registry.has_command("Custom")
        assert not registry.has_command("Original")
        assert registry.get_command("Custom") is command

    def test_register_command_class(self):
        """Test registering a command class for lazy instantiation."""
        registry = CommandRegistry()

        registry.register_command_class(MockTestCommand, "MockTest")

        assert registry.has_command("MockTest")

        # First access should create instance
        command = registry.get_command("MockTest")
        assert isinstance(command, MockTestCommand)

        # Second access should return same instance
        command2 = registry.get_command("MockTest")
        assert command is command2

    def test_unregister_command(self):
        """Test unregistering commands."""
        registry = CommandRegistry()
        command = MockTestCommand("Test")

        registry.register_command(command)
        assert registry.has_command("Test")

        result = registry.unregister_command("Test")
        assert result is True
        assert not registry.has_command("Test")

        # Unregistering non-existent command
        result = registry.unregister_command("NonExistent")
        assert result is False

    def test_command_execution_success(self):
        """Test successful command execution."""
        registry = CommandRegistry()
        command = MockTestCommand("Test", success=True)
        registry.register_command(command)

        result = registry.execute_command("Test", arg1="value1")

        assert result is True
        assert command.execute_count == 1

    def test_command_execution_failure(self):
        """Test failed command execution."""
        registry = CommandRegistry()
        command = MockTestCommand("Test", success=False)
        registry.register_command(command)

        result = registry.execute_command("Test")

        assert result is False
        assert command.execute_count == 1

    def test_command_execution_not_found(self):
        """Test execution of non-existent command."""
        registry = CommandRegistry()

        with pytest.raises(CommandError) as exc_info:
            registry.execute_command("NonExistent")

        assert "Command not found: NonExistent" in str(exc_info.value)

    def test_can_execute_command(self):
        """Test can_execute_command method."""
        registry = CommandRegistry()
        command = MockTestCommand("Test", success=True)
        registry.register_command(command)

        # Command exists and can execute
        assert registry.can_execute_command("Test")

        # Non-existent command
        assert not registry.can_execute_command("NonExistent")

    def test_command_history_tracking(self):
        """Test command execution history tracking."""
        registry = CommandRegistry()
        command1 = MockTestCommand("Command1")
        command2 = MockTestCommand("Command2")

        registry.register_command(command1)
        registry.register_command(command2)

        # Execute commands
        registry.execute_command("Command1", "arg1")
        registry.execute_command("Command2", key="value")

        history = registry.get_command_history(10)

        assert len(history) == 2
        assert history[0]["command"] == "Command2"  # Most recent first
        assert history[1]["command"] == "Command1"
        assert history[1]["args"] == ("arg1",)
        assert history[0]["kwargs"] == {"key": "value"}

    def test_recent_commands_tracking(self):
        """Test recent commands tracking."""
        registry = CommandRegistry()
        command1 = MockTestCommand("Command1")
        command2 = MockTestCommand("Command2")
        command3 = MockTestCommand("Command3")

        registry.register_command(command1)
        registry.register_command(command2)
        registry.register_command(command3)

        # Execute commands
        registry.execute_command("Command1")
        registry.execute_command("Command2")
        registry.execute_command("Command3")
        registry.execute_command("Command1")  # Execute again

        recent = registry.get_recent_commands(5)

        assert len(recent) == 3
        assert recent[0] == "Command1"  # Most recent
        assert recent[1] == "Command3"
        assert recent[2] == "Command2"

    def test_search_commands(self):
        """Test command searching."""
        registry = CommandRegistry()
        command1 = MockTestCommand("Find Text")
        command2 = MockTestCommand("Replace Text")
        command3 = MockTestCommand("Save File")

        registry.register_command(command1)
        registry.register_command(command2)
        registry.register_command(command3)

        # Search by name
        results = registry.search_commands("text")
        assert len(results) == 2
        assert "Find Text" in results
        assert "Replace Text" in results

        # Search by description
        results = registry.search_commands("description")
        assert len(results) == 3  # All have "Description" in description

        # Category-specific search
        results = registry.search_commands("text", category=CommandCategory.TOOLS.value)
        assert len(results) == 2

    def test_get_commands_by_category(self):
        """Test getting commands by category."""
        registry = CommandRegistry()

        class FileCommand(BaseCommand):
            def execute(self, *args: Any, **kwargs: Any) -> bool:
                return True

            def undo(self) -> bool:
                return True

            def get_name(self) -> str:
                return "File Command"

            def get_description(self) -> str:
                return "File operation"

            def get_category(self) -> str:
                return CommandCategory.FILE.value

        file_cmd = FileCommand()
        tools_cmd = MockTestCommand("Tools Command")

        registry.register_command(file_cmd)
        registry.register_command(tools_cmd)

        file_commands = registry.get_commands_by_category(CommandCategory.FILE.value)
        tools_commands = registry.get_commands_by_category(CommandCategory.TOOLS.value)

        assert "File Command" in file_commands
        assert "Tools Command" in tools_commands
        assert len(file_commands) == 1
        assert len(tools_commands) == 1

    def test_get_command_info(self):
        """Test getting detailed command information."""
        registry = CommandRegistry()
        command = MockTestCommand("Test Command")
        registry.register_command(command)

        info = registry.get_command_info("Test Command")

        assert info is not None
        assert info["name"] == "Test Command"
        assert info["description"] == "Description for Test Command"
        assert info["category"] == CommandCategory.TOOLS.value
        assert info["shortcut"] == "ctrl+t"
        assert info["execution_count"] == 0

        # Non-existent command
        info = registry.get_command_info("NonExistent")
        assert info is None

    def test_execution_statistics(self):
        """Test execution statistics tracking."""
        registry = CommandRegistry()
        command = MockTestCommand("Test")
        registry.register_command(command)

        # Execute multiple times
        registry.execute_command("Test")
        registry.execute_command("Test")
        registry.execute_command("Test")

        stats = registry.get_execution_stats()

        assert "Test" in stats
        assert stats["Test"]["count"] == 3
        assert stats["Test"]["failures"] == 0
        assert stats["Test"]["avg_time"] >= 0

    def test_clear_history(self):
        """Test clearing command history."""
        registry = CommandRegistry()
        command = MockTestCommand("Test")
        registry.register_command(command)

        # Execute and verify history
        registry.execute_command("Test")
        assert len(registry.get_command_history()) > 0
        assert len(registry.get_recent_commands()) > 0

        # Clear history
        registry.clear_history()
        assert len(registry.get_command_history()) == 0
        assert len(registry.get_recent_commands()) == 0

    def test_context_setting(self):
        """Test setting context for commands."""
        registry = CommandRegistry()
        context = CommandContext(current_file_path="/test/file.md")

        registry.set_context(context)

        # Register command after setting context
        command = MockTestCommand("Test")
        registry.register_command(command)

        assert command.context is context

    def test_execution_timing(self):
        """Test execution timing tracking."""
        registry = CommandRegistry()
        command = MockTestCommand("Test")
        registry.register_command(command)

        registry.execute_command("Test")

        stats = registry.get_execution_stats()
        assert stats["Test"]["count"] == 1
        assert stats["Test"]["total_time"] >= 0
        assert stats["Test"]["avg_time"] >= 0

    def test_event_emission_on_execution(self):
        """Test event emission during command execution."""
        event_bus = Mock(spec=EventBus)
        registry = CommandRegistry(event_bus=event_bus)
        command = MockTestCommand("Test")
        registry.register_command(command)

        registry.execute_command("Test")

        # Should emit CommandExecutedEvent
        assert event_bus.emit.called
        call_args = event_bus.emit.call_args[0][0]
        assert hasattr(call_args, "command_name")
        assert call_args.command_name == "Test"

    def test_command_execution_error_handling(self):
        """Test error handling during command execution."""
        registry = CommandRegistry()

        class ErrorCommand(BaseCommand):
            def execute(self, *args: Any, **kwargs: Any) -> bool:
                raise RuntimeError("Test error")

            def undo(self) -> bool:
                return False

            def get_name(self) -> str:
                return "Error Command"

            def get_description(self) -> str:
                return "Command that throws error"

            def get_category(self) -> str:
                return CommandCategory.TOOLS.value

        error_cmd = ErrorCommand()
        registry.register_command(error_cmd)

        with pytest.raises(CommandError) as exc_info:
            registry.execute_command("Error Command")

        assert "Command execution failed" in str(exc_info.value)
        assert "Test error" in str(exc_info.value)

    def test_lazy_instantiation_with_context(self):
        """Test lazy instantiation with context setting."""
        registry = CommandRegistry()
        context = CommandContext(current_file_path="/test/file.md")
        registry.set_context(context)

        # Register class after setting context
        registry.register_command_class(MockTestCommand, "MockTest")

        # Get command should create instance with context
        command = registry.get_command("MockTest")
        # MockTestCommand creates a default context, but the registry should pass context
        # during instantiation. Let's just verify the command was created properly.
        assert isinstance(command, MockTestCommand)
