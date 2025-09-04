"""
Text metrics calculation and analysis.

Provides utilities for calculating various text statistics including
line count, word count, character count, and other text metrics.
"""

import re
from typing import Dict, Any, Optional


class TextMetrics:
    """
    Calculates and caches text metrics for efficient access.
    
    Provides various text statistics while maintaining a cache
    for performance when content doesn't change frequently.
    """
    
    def __init__(self) -> None:
        """Initialize text metrics calculator."""
        self._content: str = ""
        self._content_hash: int = 0
        self._cached_metrics: Optional[Dict[str, Any]] = None
        
        # Word boundary patterns
        self._word_pattern = re.compile(r'\b\w+\b')
        self._line_pattern = re.compile(r'\n')
        self._paragraph_pattern = re.compile(r'\n\s*\n')
    
    def set_content(self, content: str) -> None:
        """
        Set the content for metrics calculation.
        
        Args:
            content: The text content to analyze
        """
        new_hash = hash(content)
        if new_hash != self._content_hash:
            self._content = content
            self._content_hash = new_hash
            self._cached_metrics = None  # Invalidate cache
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive text metrics.
        
        Returns:
            Dictionary containing all calculated metrics
        """
        if self._cached_metrics is None:
            self._calculate_metrics()
        
        if self._cached_metrics is not None:
            return self._cached_metrics.copy()
        return {}
    
    def get_line_count(self) -> int:
        """
        Get the number of lines in the text.
        
        Returns:
            Total number of lines (minimum 1)
        """
        if not self._content:
            return 1
            
        return self._content.count('\n') + 1
    
    def get_word_count(self) -> int:
        """
        Get the number of words in the text.
        
        Returns:
            Total number of words
        """
        if not self._content:
            return 0
            
        words = self._word_pattern.findall(self._content)
        return len(words)
    
    def get_character_count(self) -> int:
        """
        Get the total number of characters.
        
        Returns:
            Total character count including whitespace and newlines
        """
        return len(self._content)
    
    def get_character_count_no_spaces(self) -> int:
        """
        Get the character count excluding whitespace.
        
        Returns:
            Character count excluding spaces, tabs, and newlines
        """
        return len(re.sub(r'\s', '', self._content))
    
    def get_paragraph_count(self) -> int:
        """
        Get the number of paragraphs.
        
        Returns:
            Number of paragraphs (separated by blank lines)
        """
        if not self._content.strip():
            return 0
            
        # Split by double newlines (blank lines)
        paragraphs = self._paragraph_pattern.split(self._content.strip())
        return len([p for p in paragraphs if p.strip()])
    
    def get_sentence_count(self) -> int:
        """
        Get an approximate sentence count.
        
        Returns:
            Estimated number of sentences
        """
        if not self._content:
            return 0
            
        # Simple sentence detection (periods, exclamation marks, question marks)
        sentences = re.findall(r'[.!?]+', self._content)
        return len(sentences)
    
    def get_average_words_per_line(self) -> float:
        """
        Get the average number of words per line.
        
        Returns:
            Average words per line
        """
        line_count = self.get_line_count()
        word_count = self.get_word_count()
        
        if line_count == 0:
            return 0.0
            
        return word_count / line_count
    
    def get_average_characters_per_line(self) -> float:
        """
        Get the average number of characters per line.
        
        Returns:
            Average characters per line
        """
        line_count = self.get_line_count()
        char_count = self.get_character_count()
        
        if line_count == 0:
            return 0.0
            
        return char_count / line_count
    
    def get_longest_line_length(self) -> int:
        """
        Get the length of the longest line.
        
        Returns:
            Length of the longest line in characters
        """
        if not self._content:
            return 0
            
        lines = self._content.split('\n')
        return max(len(line) for line in lines)
    
    def get_shortest_line_length(self) -> int:
        """
        Get the length of the shortest line.
        
        Returns:
            Length of the shortest line in characters
        """
        if not self._content:
            return 0
            
        lines = self._content.split('\n')
        return min(len(line) for line in lines)
    
    def get_empty_line_count(self) -> int:
        """
        Get the number of empty lines.
        
        Returns:
            Number of lines that are empty or contain only whitespace
        """
        if not self._content:
            return 1  # Single empty line
            
        lines = self._content.split('\n')
        return sum(1 for line in lines if not line.strip())
    
    def get_reading_time_estimate(self, words_per_minute: int = 200) -> int:
        """
        Estimate reading time in minutes.
        
        Args:
            words_per_minute: Reading speed (default 200 WPM)
            
        Returns:
            Estimated reading time in minutes
        """
        word_count = self.get_word_count()
        if word_count == 0:
            return 0
            
        return max(1, int(word_count / words_per_minute))
    
    def get_line_metrics(self, line_number: int) -> Dict[str, Any]:
        """
        Get metrics for a specific line.
        
        Args:
            line_number: Line number (0-based)
            
        Returns:
            Dictionary with line-specific metrics
        """
        lines = self._content.split('\n')
        
        if line_number < 0 or line_number >= len(lines):
            return {
                'exists': False,
                'length': 0,
                'words': 0,
                'is_empty': True,
                'indent_level': 0
            }
            
        line = lines[line_number]
        words = self._word_pattern.findall(line)
        
        # Calculate indent level (assuming tabs or 4 spaces)
        indent_level = 0
        for char in line:
            if char == '\t':
                indent_level += 1
            elif char == ' ':
                indent_level = int(indent_level + 0.25)
            else:
                break
        
        return {
            'exists': True,
            'length': len(line),
            'words': len(words),
            'is_empty': not line.strip(),
            'indent_level': int(indent_level),
            'content': line
        }
    
    def _calculate_metrics(self) -> None:
        """Calculate and cache all metrics."""
        self._cached_metrics = {
            'lines': self.get_line_count(),
            'words': self.get_word_count(),
            'characters': self.get_character_count(),
            'characters_no_spaces': self.get_character_count_no_spaces(),
            'paragraphs': self.get_paragraph_count(),
            'sentences': self.get_sentence_count(),
            'empty_lines': self.get_empty_line_count(),
            'longest_line': self.get_longest_line_length(),
            'shortest_line': self.get_shortest_line_length(),
            'avg_words_per_line': self.get_average_words_per_line(),
            'avg_chars_per_line': self.get_average_characters_per_line(),
            'reading_time_minutes': self.get_reading_time_estimate()
        }