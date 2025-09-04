"""
Cursor position tracking and management.

Handles cursor position in various coordinate systems and provides
utilities for cursor movement and position calculations.
"""

from typing import Tuple, Optional


class CursorTracker:
    """
    Tracks and manages cursor position in text content.
    
    Provides conversion between absolute positions and line/column
    coordinates, with utilities for cursor movement operations.
    """
    
    def __init__(self) -> None:
        """Initialize cursor tracker."""
        self._line: int = 0
        self._column: int = 0  
        self._position: int = 0
        self._content: str = ""
        self._line_starts: list[int] = [0]  # Cache line start positions
        self._line_count: int = 1
    
    def set_content(self, content: str) -> None:
        """
        Set the content for cursor tracking.
        
        Args:
            content: The text content
        """
        self._content = content
        self._build_line_cache()
        
        # Validate and clamp current position
        self._validate_position()
    
    def set_position(self, position: int) -> None:
        """
        Set cursor position by absolute character index.
        
        Args:
            position: Absolute position in text (0-based)
        """
        self._position = max(0, min(position, len(self._content)))
        self._update_line_column_from_position()
    
    def set_line_column(self, line: int, column: int) -> None:
        """
        Set cursor position by line and column.
        
        Args:
            line: Line number (0-based)
            column: Column number (0-based)
        """
        line = max(0, min(line, self._line_count - 1))
        
        # Get line start and end positions
        line_start = self._line_starts[line]
        
        if line + 1 < len(self._line_starts):
            line_end = self._line_starts[line + 1] - 1  # Subtract 1 for newline
        else:
            line_end = len(self._content)
            
        # Clamp column within line bounds
        max_column = line_end - line_start
        column = max(0, min(column, max_column))
        
        self._line = line
        self._column = column
        self._position = line_start + column
    
    def get_position(self) -> int:
        """
        Get the current absolute cursor position.
        
        Returns:
            Absolute position in text (0-based)
        """
        return self._position
    
    def get_line_column(self) -> Tuple[int, int]:
        """
        Get the current line and column.
        
        Returns:
            Tuple of (line, column) (0-based)
        """
        return (self._line, self._column)
    
    def get_line_column_position(self) -> Tuple[int, int, int]:
        """
        Get all position information.
        
        Returns:
            Tuple of (line, column, absolute_position) (0-based)
        """
        return (self._line, self._column, self._position)
    
    def move_by_offset(self, offset: int) -> None:
        """
        Move cursor by character offset.
        
        Args:
            offset: Number of characters to move (can be negative)
        """
        new_position = self._position + offset
        self.set_position(new_position)
    
    def move_to_line_start(self) -> None:
        """Move cursor to the start of current line."""
        self.set_line_column(self._line, 0)
    
    def move_to_line_end(self) -> None:
        """Move cursor to the end of current line."""
        line_start = self._line_starts[self._line]
        
        if self._line + 1 < len(self._line_starts):
            line_end = self._line_starts[self._line + 1] - 1  # Subtract 1 for newline
        else:
            line_end = len(self._content)
            
        max_column = line_end - line_start
        self.set_line_column(self._line, max_column)
    
    def move_up(self, lines: int = 1) -> None:
        """
        Move cursor up by specified number of lines.
        
        Args:
            lines: Number of lines to move up
        """
        new_line = max(0, self._line - lines)
        self.set_line_column(new_line, self._column)
    
    def move_down(self, lines: int = 1) -> None:
        """
        Move cursor down by specified number of lines.
        
        Args:
            lines: Number of lines to move down
        """
        new_line = min(self._line_count - 1, self._line + lines)
        self.set_line_column(new_line, self._column)
    
    def move_left(self, chars: int = 1) -> None:
        """
        Move cursor left by specified number of characters.
        
        Args:
            chars: Number of characters to move left
        """
        self.move_by_offset(-chars)
    
    def move_right(self, chars: int = 1) -> None:
        """
        Move cursor right by specified number of characters.
        
        Args:
            chars: Number of characters to move right
        """
        self.move_by_offset(chars)
    
    def find_word_boundary_left(self) -> int:
        """
        Find the start of the word to the left of cursor.
        
        Returns:
            Position of word boundary
        """
        if self._position == 0:
            return 0
            
        pos = self._position - 1
        
        # Skip non-word characters
        while pos >= 0 and not self._is_word_char(self._content[pos]):
            pos -= 1
            
        # Skip word characters to find start
        while pos >= 0 and self._is_word_char(self._content[pos]):
            pos -= 1
            
        return pos + 1
    
    def find_word_boundary_right(self) -> int:
        """
        Find the end of the word to the right of cursor.
        
        Returns:
            Position of word boundary
        """
        content_len = len(self._content)
        if self._position >= content_len:
            return content_len
            
        pos = self._position
        
        # Skip non-word characters
        while pos < content_len and not self._is_word_char(self._content[pos]):
            pos += 1
            
        # Skip word characters to find end
        while pos < content_len and self._is_word_char(self._content[pos]):
            pos += 1
            
        return pos
    
    def move_to_word_left(self) -> None:
        """Move cursor to the start of the previous word."""
        new_pos = self.find_word_boundary_left()
        self.set_position(new_pos)
    
    def move_to_word_right(self) -> None:
        """Move cursor to the start of the next word."""
        new_pos = self.find_word_boundary_right()
        self.set_position(new_pos)
    
    def get_line_text(self, line_number: Optional[int] = None) -> str:
        """
        Get the text of a specific line.
        
        Args:
            line_number: Line number (0-based), or None for current line
            
        Returns:
            Text content of the line
        """
        if line_number is None:
            line_number = self._line
            
        if line_number < 0 or line_number >= self._line_count:
            return ""
            
        line_start = self._line_starts[line_number]
        
        if line_number + 1 < len(self._line_starts):
            line_end = self._line_starts[line_number + 1] - 1  # Subtract 1 for newline
        else:
            line_end = len(self._content)
            
        return self._content[line_start:line_end]
    
    def _build_line_cache(self) -> None:
        """Build cache of line start positions."""
        self._line_starts = [0]
        
        for i, char in enumerate(self._content):
            if char == '\n':
                self._line_starts.append(i + 1)
        
        self._line_count = len(self._line_starts)
    
    def _update_line_column_from_position(self) -> None:
        """Update line/column based on current position."""
        if not self._content:
            self._line = 0
            self._column = 0
            return
            
        # Binary search for the line containing position
        line = 0
        for i in range(len(self._line_starts) - 1):
            if self._position >= self._line_starts[i + 1]:
                line = i + 1
            else:
                break
                
        # Handle position at very end
        if line >= self._line_count:
            line = self._line_count - 1
            
        self._line = line
        self._column = self._position - self._line_starts[line]
    
    def _validate_position(self) -> None:
        """Ensure current position is valid."""
        self._position = max(0, min(self._position, len(self._content)))
        self._update_line_column_from_position()
    
    def _is_word_char(self, char: str) -> bool:
        """
        Check if character is part of a word.
        
        Args:
            char: Character to check
            
        Returns:
            True if character is alphanumeric or underscore
        """
        return char.isalnum() or char == '_'