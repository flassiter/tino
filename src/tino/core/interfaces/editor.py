"""
Editor interface for text editing operations.

Defines the contract for editor components that provide text editing functionality
with undo/redo support, selection management, and cursor tracking.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple


class IEditor(ABC):
    """
    Interface for editor components that provide text editing capabilities.
    
    All editor implementations must support basic text operations, selection
    management, and undo/redo functionality.
    """
    
    @abstractmethod
    def get_content(self) -> str:
        """
        Get the current text content of the editor.
        
        Returns:
            The complete text content as a string
        """
        pass
    
    @abstractmethod
    def set_content(self, text: str) -> None:
        """
        Set the entire text content of the editor.
        
        Args:
            text: The new text content
        """
        pass
    
    @abstractmethod
    def insert_text(self, position: int, text: str) -> None:
        """
        Insert text at the specified position.
        
        Args:
            position: Character position to insert at (0-based)
            text: Text to insert
        """
        pass
    
    @abstractmethod
    def delete_range(self, start: int, end: int) -> str:
        """
        Delete text within the specified range.
        
        Args:
            start: Start position (inclusive, 0-based)
            end: End position (exclusive, 0-based)
            
        Returns:
            The deleted text
        """
        pass
    
    @abstractmethod
    def get_selection(self) -> Tuple[int, int]:
        """
        Get the current selection range.
        
        Returns:
            Tuple of (start, end) positions (0-based)
            If no selection, both values will be equal (cursor position)
        """
        pass
    
    @abstractmethod
    def set_selection(self, start: int, end: int) -> None:
        """
        Set the selection range.
        
        Args:
            start: Start position (inclusive, 0-based)
            end: End position (exclusive, 0-based)
        """
        pass
    
    @abstractmethod
    def get_cursor_position(self) -> Tuple[int, int, int]:
        """
        Get the current cursor position.
        
        Returns:
            Tuple of (line, column, absolute_position) (0-based)
        """
        pass
    
    @abstractmethod
    def set_cursor_position(self, line: int, column: int) -> None:
        """
        Set the cursor position.
        
        Args:
            line: Line number (0-based)
            column: Column number (0-based)
        """
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        """
        Undo the last operation.
        
        Returns:
            True if an operation was undone, False if nothing to undo
        """
        pass
    
    @abstractmethod
    def redo(self) -> bool:
        """
        Redo the last undone operation.
        
        Returns:
            True if an operation was redone, False if nothing to redo
        """
        pass
    
    @abstractmethod
    def can_undo(self) -> bool:
        """
        Check if undo is available.
        
        Returns:
            True if undo operations are available
        """
        pass
    
    @abstractmethod
    def can_redo(self) -> bool:
        """
        Check if redo is available.
        
        Returns:
            True if redo operations are available  
        """
        pass
    
    @abstractmethod
    def get_selected_text(self) -> str:
        """
        Get the currently selected text.
        
        Returns:
            The selected text, or empty string if no selection
        """
        pass
    
    @abstractmethod
    def replace_selection(self, text: str) -> None:
        """
        Replace the current selection with new text.
        
        Args:
            text: Text to replace selection with
        """
        pass
    
    @abstractmethod
    def get_line_count(self) -> int:
        """
        Get the number of lines in the document.
        
        Returns:
            Total number of lines
        """
        pass
    
    @abstractmethod
    def get_line_text(self, line_number: int) -> str:
        """
        Get the text of a specific line.
        
        Args:
            line_number: Line number (0-based)
            
        Returns:
            Text content of the line
            
        Raises:
            IndexError: If line number is out of range
        """
        pass
    
    @abstractmethod
    def find_text(self, pattern: str, start: int = 0, case_sensitive: bool = True) -> Optional[Tuple[int, int]]:
        """
        Find the next occurrence of text.
        
        Args:
            pattern: Text to find
            start: Position to start searching from (0-based)
            case_sensitive: Whether search should be case sensitive
            
        Returns:
            Tuple of (start, end) positions if found, None otherwise
        """
        pass
    
    @abstractmethod
    def is_modified(self) -> bool:
        """
        Check if the content has been modified since last save.
        
        Returns:
            True if content has been modified
        """
        pass
    
    @abstractmethod
    def set_modified(self, modified: bool) -> None:
        """
        Set the modified state.
        
        Args:
            modified: Whether content should be marked as modified
        """
        pass
    
    @abstractmethod
    def clear_undo_history(self) -> None:
        """Clear the undo/redo history."""
        pass