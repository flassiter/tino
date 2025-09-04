"""
Command interface for implementing the command pattern.

Defines the contract for command objects that encapsulate actions with undo/redo
support, enabling features like command history, macros, and keybinding.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ICommand(ABC):
    """
    Interface for command objects implementing the command pattern.
    
    Commands encapsulate actions that can be executed, undone, and redone.
    They support parameter validation and provide metadata for UI display.
    """
    
    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """
        Execute the command.
        
        Args:
            *args: Positional arguments for the command
            **kwargs: Keyword arguments for the command
            
        Returns:
            True if command executed successfully, False otherwise
            
        Raises:
            CommandError: If command cannot be executed
        """
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        """
        Undo the command if it was previously executed.
        
        Returns:
            True if command was undone successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def can_execute(self, *args: Any, **kwargs: Any) -> bool:
        """
        Check if the command can be executed with given parameters.
        
        Args:
            *args: Positional arguments to validate
            **kwargs: Keyword arguments to validate
            
        Returns:
            True if command can be executed, False otherwise
        """
        pass
    
    @abstractmethod
    def can_undo(self) -> bool:
        """
        Check if the command can be undone.
        
        Returns:
            True if command supports undo and has been executed
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Get the display name of the command.
        
        Returns:
            Human-readable name for the command
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """
        Get a description of what the command does.
        
        Returns:
            Description text for the command
        """
        pass
    
    @abstractmethod
    def get_category(self) -> str:
        """
        Get the category this command belongs to.
        
        Returns:
            Category name (e.g., "File", "Edit", "Format")
        """
        pass
    
    @abstractmethod
    def get_shortcut(self) -> Optional[str]:
        """
        Get the default keyboard shortcut for this command.
        
        Returns:
            Keyboard shortcut string (e.g., "ctrl+s") or None if no default
        """
        pass
    
    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """
        Get parameter definitions for this command.
        
        Returns:
            Dictionary mapping parameter names to their specifications
        """
        pass
    
    @abstractmethod
    def is_async(self) -> bool:
        """
        Check if this command requires async execution.
        
        Returns:
            True if command should be executed asynchronously
        """
        pass
    
    @abstractmethod
    def get_execution_context(self) -> Dict[str, Any]:
        """
        Get context information needed for execution.
        
        Returns:
            Dictionary with context information (editor state, etc.)
        """
        pass
    
    @abstractmethod
    def validate_parameters(self, *args: Any, **kwargs: Any) -> Optional[str]:
        """
        Validate command parameters.
        
        Args:
            *args: Positional arguments to validate
            **kwargs: Keyword arguments to validate
            
        Returns:
            Error message if validation fails, None if valid
        """
        pass
    
    def get_undo_name(self) -> str:
        """
        Get the display name for the undo operation.
        
        Returns:
            Human-readable name for undoing this command
        """
        return f"Undo {self.get_name()}"
    
    def get_redo_name(self) -> str:
        """
        Get the display name for the redo operation.
        
        Returns:
            Human-readable name for redoing this command
        """
        return f"Redo {self.get_name()}"
    
    def supports_batching(self) -> bool:
        """
        Check if this command can be batched with others.
        
        Returns:
            True if command supports batching for performance
        """
        return False
    
    def get_estimated_duration(self) -> float:
        """
        Get estimated execution duration in milliseconds.
        
        Returns:
            Estimated duration, or 0.0 if instantaneous
        """
        return 0.0
    
    def requires_confirmation(self) -> bool:
        """
        Check if this command requires user confirmation.
        
        Returns:
            True if command should prompt for confirmation
        """
        return False
    
    def get_confirmation_message(self) -> str:
        """
        Get confirmation message to show user.
        
        Returns:
            Message to display in confirmation dialog
        """
        return f"Execute {self.get_name()}?"


class CommandError(Exception):
    """Exception raised when a command cannot be executed."""
    
    def __init__(self, message: str, command_name: str = "", cause: Optional[Exception] = None):
        """
        Initialize command error.
        
        Args:
            message: Error description
            command_name: Name of the command that failed
            cause: Optional underlying exception
        """
        self.command_name = command_name
        self.cause = cause
        super().__init__(message)