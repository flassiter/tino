"""
Command registry for managing and executing commands by name.

Provides centralized command registration, lookup, and execution with
support for command history and error handling.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Type
from collections import defaultdict, deque

from ...core.interfaces.command import ICommand, CommandError
from ...core.events.bus import EventBus
from ...core.events.types import CommandExecutedEvent, CommandFailedEvent
from .command_base import BaseCommand, CommandContext
from .categories import CommandCategory

logger = logging.getLogger(__name__)


class CommandRegistry:
    """
    Registry for managing commands and their execution.
    
    Provides command registration, lookup by name, execution with context,
    and command history management.
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None, max_history: int = 100):
        """
        Initialize command registry.
        
        Args:
            event_bus: Event bus for command events
            max_history: Maximum number of commands to keep in history
        """
        self._event_bus = event_bus
        self._max_history = max_history
        
        # Command storage
        self._commands: Dict[str, ICommand] = {}
        self._command_classes: Dict[str, Type[ICommand]] = {}
        self._categories: Dict[str, Set[str]] = defaultdict(set)
        
        # Execution state
        self._context: Optional[CommandContext] = None
        self._command_history: deque = deque(maxlen=max_history)
        self._recent_commands: deque = deque(maxlen=20)
        
        # Performance tracking
        self._execution_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'failures': 0,
            'avg_time': 0.0
        })
    
    def set_context(self, context: CommandContext) -> None:
        """Set the execution context for all commands."""
        self._context = context
    
    def register_command(self, command: ICommand, name: Optional[str] = None) -> None:
        """
        Register a command instance.
        
        Args:
            command: Command instance to register
            name: Optional name override (uses command.get_name() if not provided)
        """
        cmd_name = name or command.get_name()
        
        if cmd_name in self._commands:
            logger.warning(f"Overriding existing command: {cmd_name}")
        
        # Set context if available
        if self._context and hasattr(command, 'set_context'):
            command.set_context(self._context)
        
        self._commands[cmd_name] = command
        
        # Organize by category
        category = command.get_category()
        self._categories[category].add(cmd_name)
        
        logger.debug(f"Registered command: {cmd_name} (category: {category})")
    
    def register_command_class(self, command_class: Type[ICommand], name: Optional[str] = None) -> None:
        """
        Register a command class for lazy instantiation.
        
        Args:
            command_class: Command class to register
            name: Optional name override
        """
        # Create temporary instance to get metadata
        temp_instance = command_class(self._context)
        cmd_name = name or temp_instance.get_name()
        
        self._command_classes[cmd_name] = command_class
        
        # Organize by category
        category = temp_instance.get_category()
        self._categories[category].add(cmd_name)
        
        logger.debug(f"Registered command class: {cmd_name} -> {command_class.__name__}")
    
    def unregister_command(self, name: str) -> bool:
        """
        Unregister a command.
        
        Args:
            name: Name of command to unregister
            
        Returns:
            True if command was found and removed
        """
        if name not in self._commands and name not in self._command_classes:
            return False
        
        # Remove from commands
        command = self._commands.pop(name, None)
        self._command_classes.pop(name, None)
        
        # Remove from categories
        if command:
            category = command.get_category()
            self._categories[category].discard(name)
            if not self._categories[category]:
                del self._categories[category]
        
        logger.debug(f"Unregistered command: {name}")
        return True
    
    def get_command(self, name: str) -> Optional[ICommand]:
        """
        Get a command by name.
        
        Args:
            name: Command name
            
        Returns:
            Command instance or None if not found
        """
        # Check instance cache first
        if name in self._commands:
            return self._commands[name]
        
        # Try lazy instantiation
        if name in self._command_classes:
            command_class = self._command_classes[name]
            command = command_class(self._context)
            
            # Cache the instance
            self._commands[name] = command
            return command
        
        return None
    
    def has_command(self, name: str) -> bool:
        """Check if a command is registered."""
        return name in self._commands or name in self._command_classes
    
    def execute_command(self, name: str, *args: Any, **kwargs: Any) -> bool:
        """
        Execute a command by name.
        
        Args:
            name: Command name
            *args: Positional arguments for command
            **kwargs: Keyword arguments for command
            
        Returns:
            True if command executed successfully
            
        Raises:
            CommandError: If command cannot be executed
        """
        command = self.get_command(name)
        if not command:
            raise CommandError(f"Command not found: {name}")
        
        # Check if command can be executed
        if not command.can_execute(*args, **kwargs):
            error_msg = f"Command cannot be executed: {name}"
            validation_error = command.validate_parameters(*args, **kwargs)
            if validation_error:
                error_msg += f" - {validation_error}"
            raise CommandError(error_msg, name)
        
        try:
            # Record start time for statistics
            import time
            start_time = time.time()
            
            # Execute command
            result = command.execute(*args, **kwargs)
            
            # Update statistics
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            self._update_stats(name, execution_time, success=result)
            
            if result:
                # Add to history
                self._add_to_history(name, args, kwargs)
                self._add_to_recent(name)
                
                # Emit success event
                if self._event_bus:
                    event = CommandExecutedEvent(
                        command_name=name,
                        args=args,
                        kwargs=kwargs,
                        execution_time=execution_time
                    )
                    self._event_bus.emit(event)
                
                logger.debug(f"Command executed successfully: {name}")
            else:
                logger.warning(f"Command execution failed: {name}")
                
            return result
            
        except Exception as e:
            # Update failure statistics
            self._update_stats(name, 0, success=False)
            
            # Emit failure event
            if self._event_bus:
                event = CommandFailedEvent(
                    command_name=name,
                    error_message=str(e),
                    args=args,
                    kwargs=kwargs
                )
                self._event_bus.emit(event)
            
            logger.error(f"Command execution error: {name} - {e}")
            raise CommandError(f"Command execution failed: {name} - {e}", name, e)
    
    def can_execute_command(self, name: str, *args: Any, **kwargs: Any) -> bool:
        """
        Check if a command can be executed.
        
        Args:
            name: Command name
            *args: Positional arguments for command
            **kwargs: Keyword arguments for command
            
        Returns:
            True if command can be executed
        """
        command = self.get_command(name)
        if not command:
            return False
        
        return command.can_execute(*args, **kwargs)
    
    def get_commands_by_category(self, category: str) -> List[str]:
        """
        Get all command names in a category.
        
        Args:
            category: Category name
            
        Returns:
            List of command names in the category
        """
        return list(self._categories.get(category, set()))
    
    def get_all_command_names(self) -> List[str]:
        """Get all registered command names."""
        all_commands = set(self._commands.keys())
        all_commands.update(self._command_classes.keys())
        return sorted(all_commands)
    
    def get_all_categories(self) -> List[str]:
        """Get all command categories."""
        return sorted(self._categories.keys())
    
    def get_recent_commands(self, limit: int = 10) -> List[str]:
        """
        Get recently executed commands.
        
        Args:
            limit: Maximum number of commands to return
            
        Returns:
            List of recent command names, most recent first
        """
        return list(list(self._recent_commands)[-limit:])[::-1]
    
    def get_command_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get command execution history.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of execution records, most recent first
        """
        history = list(self._command_history)[-limit:]
        return history[::-1]  # Most recent first
    
    def search_commands(self, query: str, category: Optional[str] = None) -> List[str]:
        """
        Search for commands by name or description.
        
        Args:
            query: Search query (case-insensitive)
            category: Optional category filter
            
        Returns:
            List of matching command names
        """
        query_lower = query.lower()
        matches = []
        
        # Get candidate commands
        candidates = self.get_all_command_names()
        if category:
            candidates = self.get_commands_by_category(category)
        
        for name in candidates:
            command = self.get_command(name)
            if command:
                # Check name match
                if query_lower in name.lower():
                    matches.append(name)
                    continue
                
                # Check description match
                if query_lower in command.get_description().lower():
                    matches.append(name)
        
        return sorted(matches)
    
    def get_command_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a command.
        
        Args:
            name: Command name
            
        Returns:
            Dictionary with command information or None if not found
        """
        command = self.get_command(name)
        if not command:
            return None
        
        stats = self._execution_stats.get(name, {})
        
        return {
            'name': name,
            'description': command.get_description(),
            'category': command.get_category(),
            'shortcut': command.get_shortcut(),
            'can_undo': command.can_undo(),
            'is_async': command.is_async(),
            'parameters': command.get_parameters(),
            'requires_confirmation': command.requires_confirmation(),
            'execution_count': stats.get('count', 0),
            'average_execution_time': stats.get('avg_time', 0.0),
            'failure_count': stats.get('failures', 0),
        }
    
    def clear_history(self) -> None:
        """Clear command execution history."""
        self._command_history.clear()
        self._recent_commands.clear()
        logger.debug("Command history cleared")
    
    def get_execution_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get execution statistics for all commands."""
        return dict(self._execution_stats)
    
    def _add_to_history(self, name: str, args: tuple, kwargs: dict) -> None:
        """Add command execution to history."""
        import time
        record = {
            'command': name,
            'args': args,
            'kwargs': kwargs,
            'timestamp': time.time(),
        }
        self._command_history.append(record)
    
    def _add_to_recent(self, name: str) -> None:
        """Add command to recent commands list."""
        # Remove if already exists to move to front
        try:
            self._recent_commands.remove(name)
        except ValueError:
            pass
        
        self._recent_commands.append(name)
    
    def _update_stats(self, name: str, execution_time: float, success: bool) -> None:
        """Update execution statistics for a command."""
        stats = self._execution_stats[name]
        
        if success:
            stats['count'] += 1
            stats['total_time'] += execution_time
            if stats['count'] > 0:
                stats['avg_time'] = stats['total_time'] / stats['count']
        else:
            stats['failures'] += 1