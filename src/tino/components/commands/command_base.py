"""
Base command implementation for the command pattern.

Provides abstract base class for all commands with common functionality
including undo/redo support, parameter validation, and metadata.
"""

import asyncio
from abc import abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass, field

from ...core.interfaces.command import ICommand, CommandError
from ...core.interfaces.editor import IEditor
from ...core.interfaces.file_manager import IFileManager
from ...core.events.bus import EventBus
from .categories import CommandCategory


@dataclass
class CommandContext:
    """
    Context information passed to commands for execution.
    
    Contains references to core components and current application state.
    """
    editor: Optional[IEditor] = None
    file_manager: Optional[IFileManager] = None
    event_bus: Optional[EventBus] = None
    current_file_path: Optional[str] = None
    application_state: Dict[str, Any] = field(default_factory=dict)


class BaseCommand(ICommand):
    """
    Base implementation of the command pattern.
    
    Provides common functionality for all commands including parameter validation,
    error handling, and basic undo/redo support.
    """
    
    def __init__(self, context: Optional[CommandContext] = None):
        """
        Initialize base command.
        
        Args:
            context: Command execution context
        """
        self._context = context or CommandContext()
        self._executed = False
        self._can_undo = False
        self._execution_data: Dict[str, Any] = {}
        
    @property
    def context(self) -> CommandContext:
        """Get the command execution context."""
        return self._context
    
    def set_context(self, context: CommandContext) -> None:
        """Set the command execution context."""
        self._context = context
    
    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute the command. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        """Undo the command. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the command name. Must be implemented by subclasses."""
        pass
    
    @abstractmethod  
    def get_description(self) -> str:
        """Get the command description. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def get_category(self) -> str:
        """Get the command category. Must be implemented by subclasses."""
        pass
    
    def can_execute(self, *args: Any, **kwargs: Any) -> bool:
        """
        Check if command can be executed with given parameters.
        
        Default implementation validates parameters and checks context.
        """
        # Validate parameters
        validation_error = self.validate_parameters(*args, **kwargs)
        if validation_error:
            return False
        
        # Check if required context is available
        return self._check_context()
    
    def can_undo(self) -> bool:
        """Check if command can be undone."""
        return self._executed and self._can_undo
    
    def get_shortcut(self) -> Optional[str]:
        """Get default keyboard shortcut. Override in subclasses."""
        return None
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get parameter definitions. Override in subclasses if needed."""
        return {}
    
    def is_async(self) -> bool:
        """Check if command requires async execution. Override if needed."""
        return False
    
    def get_execution_context(self) -> Dict[str, Any]:
        """Get context information for execution."""
        return {
            'has_editor': self._context.editor is not None,
            'has_file_manager': self._context.file_manager is not None,
            'current_file': self._context.current_file_path,
            'executed': self._executed,
            'can_undo': self._can_undo,
        }
    
    def validate_parameters(self, *args: Any, **kwargs: Any) -> Optional[str]:
        """
        Validate command parameters. Override in subclasses if needed.
        
        Returns:
            Error message if invalid, None if valid
        """
        # Default implementation accepts any parameters
        return None
    
    def requires_confirmation(self) -> bool:
        """Check if command requires user confirmation. Override if needed."""
        return False
    
    def get_confirmation_message(self) -> str:
        """Get confirmation message. Override if needed."""
        return f"Execute {self.get_name()}?"
    
    def supports_batching(self) -> bool:
        """Check if command can be batched. Override if needed."""
        return False
    
    def get_estimated_duration(self) -> float:
        """Get estimated execution duration in milliseconds."""
        return 0.0
    
    def _check_context(self) -> bool:
        """Check if required context is available for execution."""
        # Base implementation just checks if context exists
        return self._context is not None
    
    def _mark_executed(self, can_undo: bool = True) -> None:
        """Mark command as executed."""
        self._executed = True
        self._can_undo = can_undo
    
    def _store_execution_data(self, key: str, value: Any) -> None:
        """Store data needed for undo operations."""
        self._execution_data[key] = value
    
    def _get_execution_data(self, key: str, default: Any = None) -> Any:
        """Retrieve stored execution data."""
        return self._execution_data.get(key, default)
    
    def _emit_event(self, event) -> None:
        """Emit an event if event bus is available."""
        if self._context.event_bus:
            self._context.event_bus.emit(event)
    
    async def _emit_event_async(self, event) -> None:
        """Emit an event asynchronously if event bus is available."""
        if self._context.event_bus:
            await self._context.event_bus.emit_async(event)


class EditorCommand(BaseCommand):
    """
    Base class for commands that operate on the editor.
    
    Provides editor-specific validation and helper methods.
    """
    
    def _check_context(self) -> bool:
        """Check if editor is available in context."""
        return super()._check_context() and self._context.editor is not None
    
    @property
    def editor(self) -> IEditor:
        """Get the editor from context."""
        if not self._context.editor:
            raise CommandError("No editor available in context", self.get_name())
        return self._context.editor


class FileCommand(BaseCommand):
    """
    Base class for commands that operate on files.
    
    Provides file manager-specific validation and helper methods.
    """
    
    def _check_context(self) -> bool:
        """Check if file manager is available in context."""
        return super()._check_context() and self._context.file_manager is not None
    
    @property
    def file_manager(self) -> IFileManager:
        """Get the file manager from context."""
        if not self._context.file_manager:
            raise CommandError("No file manager available in context", self.get_name())
        return self._context.file_manager


class AsyncCommand(BaseCommand):
    """
    Base class for asynchronous commands.
    
    Provides async execution pattern and proper error handling.
    """
    
    def is_async(self) -> bool:
        """This is an async command."""
        return True
    
    async def execute_async(self, *args: Any, **kwargs: Any) -> bool:
        """
        Execute the command asynchronously.
        
        Subclasses should override this instead of execute().
        """
        return await self._execute_async_impl(*args, **kwargs)
    
    @abstractmethod
    async def _execute_async_impl(self, *args: Any, **kwargs: Any) -> bool:
        """Async implementation to be overridden by subclasses."""
        pass
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Sync wrapper for async execution."""
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, create a task
            task = loop.create_task(self.execute_async(*args, **kwargs))
            # For now, just return True - the actual result will be handled async
            return True
        except RuntimeError:
            # No event loop, run synchronously
            return asyncio.run(self.execute_async(*args, **kwargs))


class MockCommand(BaseCommand):
    """
    Mock command implementation for testing.
    
    Records execution history and provides controllable behavior.
    """
    
    def __init__(self, name: str, category: CommandCategory, context: Optional[CommandContext] = None):
        super().__init__(context)
        self._name = name
        self._category = category.value
        self._execute_result = True
        self._undo_result = True
        self._execution_count = 0
        self._undo_count = 0
        
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Mock execution."""
        self._execution_count += 1
        if self._execute_result:
            self._mark_executed(can_undo=True)
        return self._execute_result
    
    def undo(self) -> bool:
        """Mock undo."""
        if self.can_undo():
            self._undo_count += 1
            return self._undo_result
        return False
    
    def get_name(self) -> str:
        return self._name
    
    def get_description(self) -> str:
        return f"Mock command: {self._name}"
    
    def get_category(self) -> str:
        return self._category
    
    def set_execute_result(self, result: bool) -> None:
        """Control execution result for testing."""
        self._execute_result = result
    
    def set_undo_result(self, result: bool) -> None:
        """Control undo result for testing."""
        self._undo_result = result
    
    def get_execution_count(self) -> int:
        """Get number of times executed."""
        return self._execution_count
    
    def get_undo_count(self) -> int:
        """Get number of times undone."""
        return self._undo_count