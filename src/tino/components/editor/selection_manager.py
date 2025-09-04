"""
Selection management for text editors.

Handles text selection operations, including validation, normalization,
and conversion between different selection representations.
"""

from typing import Tuple, Optional


class SelectionManager:
    """
    Manages text selection operations and state.
    
    Provides utilities for working with text selections, including
    validation, normalization, and conversion between different
    coordinate systems.
    """
    
    def __init__(self):
        """Initialize selection manager."""
        self._start: int = 0
        self._end: int = 0
        self._anchor: int = 0  # Where selection started
        self._content_length: int = 0
    
    def set_content_length(self, length: int) -> None:
        """
        Set the content length for validation.
        
        Args:
            length: Total length of the text content
        """
        self._content_length = length
        # Ensure current selection is still valid
        self._validate_and_clamp()
    
    def set_selection(self, start: int, end: int, anchor: Optional[int] = None) -> None:
        """
        Set the current selection.
        
        Args:
            start: Start position (inclusive)
            end: End position (exclusive)  
            anchor: Anchor position (where selection started)
        """
        # Normalize order
        if start > end:
            start, end = end, start
            
        self._start = max(0, min(start, self._content_length))
        self._end = max(0, min(end, self._content_length))
        
        if anchor is not None:
            self._anchor = max(0, min(anchor, self._content_length))
        else:
            self._anchor = self._start
    
    def get_selection(self) -> Tuple[int, int]:
        """
        Get the current selection range.
        
        Returns:
            Tuple of (start, end) positions
        """
        return (self._start, self._end)
    
    def get_selection_with_anchor(self) -> Tuple[int, int, int]:
        """
        Get selection with anchor information.
        
        Returns:
            Tuple of (start, end, anchor) positions
        """
        return (self._start, self._end, self._anchor)
    
    def has_selection(self) -> bool:
        """
        Check if there is an active selection.
        
        Returns:
            True if start != end
        """
        return self._start != self._end
    
    def get_selection_length(self) -> int:
        """
        Get the length of the current selection.
        
        Returns:
            Number of characters selected
        """
        return self._end - self._start
    
    def clear_selection(self) -> None:
        """Clear the current selection by setting end = start."""
        self._end = self._start
        self._anchor = self._start
    
    def select_all(self, content_length: int) -> None:
        """
        Select all content.
        
        Args:
            content_length: Total length of content to select
        """
        self._content_length = content_length
        self._start = 0
        self._end = content_length
        self._anchor = 0
    
    def extend_selection(self, new_end: int) -> None:
        """
        Extend the selection to a new end position.
        
        Args:
            new_end: New end position
        """
        new_end = max(0, min(new_end, self._content_length))
        
        if new_end >= self._anchor:
            self._start = self._anchor
            self._end = new_end
        else:
            self._start = new_end  
            self._end = self._anchor
    
    def move_selection(self, offset: int) -> None:
        """
        Move the entire selection by an offset.
        
        Args:
            offset: Number of positions to move (can be negative)
        """
        new_start = self._start + offset
        new_end = self._end + offset
        
        # Clamp to content bounds
        if new_start < 0:
            new_end -= new_start  # Adjust end by same amount
            new_start = 0
        elif new_end > self._content_length:
            new_start -= (new_end - self._content_length)
            new_end = self._content_length
        
        new_start = max(0, new_start)
        new_end = min(self._content_length, new_end)
        
        self._start = new_start
        self._end = new_end
        self._anchor = new_start
    
    def select_word_at(self, position: int, content: str) -> None:
        """
        Select the word at the given position.
        
        Args:
            position: Position to select word at
            content: The text content
        """
        if not content or position < 0 or position >= len(content):
            return
            
        # Find word boundaries
        start = position
        end = position
        
        # Find start of word
        while start > 0 and self._is_word_char(content[start - 1]):
            start -= 1
            
        # Find end of word
        while end < len(content) and self._is_word_char(content[end]):
            end += 1
        
        self.set_selection(start, end, start)
    
    def select_line_at(self, position: int, content: str) -> None:
        """
        Select the entire line at the given position.
        
        Args:
            position: Position within the line to select
            content: The text content
        """
        if not content or position < 0 or position >= len(content):
            return
            
        # Find line boundaries
        start = position
        end = position
        
        # Find start of line
        while start > 0 and content[start - 1] != '\n':
            start -= 1
            
        # Find end of line
        while end < len(content) and content[end] != '\n':
            end += 1
            
        # Include the newline in selection if present
        if end < len(content) and content[end] == '\n':
            end += 1
            
        self.set_selection(start, end, start)
    
    def get_selected_text(self, content: str) -> str:
        """
        Get the text within the current selection.
        
        Args:
            content: The full text content
            
        Returns:
            The selected text
        """
        if not self.has_selection() or not content:
            return ""
            
        start, end = self.get_selection()
        return content[start:end]
    
    def replace_selection(self, content: str, replacement: str) -> Tuple[str, int]:
        """
        Replace the selected text with new content.
        
        Args:
            content: The current text content
            replacement: Text to replace selection with
            
        Returns:
            Tuple of (new_content, new_cursor_position)
        """
        if not content:
            return replacement, len(replacement)
            
        start, end = self.get_selection()
        
        # Build new content
        new_content = content[:start] + replacement + content[end:]
        new_cursor = start + len(replacement)
        
        # Update selection to cursor position after replacement
        self._start = new_cursor
        self._end = new_cursor
        self._anchor = new_cursor
        self._content_length = len(new_content)
        
        return new_content, new_cursor
    
    def _is_word_char(self, char: str) -> bool:
        """
        Check if character is part of a word.
        
        Args:
            char: Character to check
            
        Returns:
            True if character is alphanumeric or underscore
        """
        return char.isalnum() or char == '_'
    
    def _validate_and_clamp(self) -> None:
        """Ensure current selection is within content bounds."""
        self._start = max(0, min(self._start, self._content_length))
        self._end = max(self._start, min(self._end, self._content_length))
        self._anchor = max(0, min(self._anchor, self._content_length))