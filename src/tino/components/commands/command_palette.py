"""
Command palette backend for searching and executing commands.

Provides fuzzy search through commands, recent command tracking,
and category-based organization for the command palette UI.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque
import difflib

from .registry import CommandRegistry
from .categories import CommandCategory


@dataclass
class CommandSearchResult:
    """Represents a command search result."""
    
    command_name: str
    display_name: str
    description: str
    category: str
    shortcut: Optional[str]
    score: float  # Search relevance score (0-1)
    match_type: str  # "name", "description", "shortcut"
    

class CommandPalette:
    """
    Command palette backend for searching and managing commands.
    
    Provides fuzzy search, recent command tracking, and command execution
    through a searchable interface.
    """
    
    def __init__(self, command_registry: CommandRegistry, max_recent: int = 20):
        """
        Initialize command palette.
        
        Args:
            command_registry: Command registry to search
            max_recent: Maximum number of recent commands to track
        """
        self._registry = command_registry
        self._max_recent = max_recent
        
        # Recent commands tracking
        self._recent_commands: deque = deque(maxlen=max_recent)
        
        # Search configuration
        self._fuzzy_threshold = 0.3  # Minimum similarity for fuzzy matching
        self._max_results = 50
        
    def search_commands(self, query: str, category: Optional[str] = None, 
                       include_recent: bool = True) -> List[CommandSearchResult]:
        """
        Search for commands matching the query.
        
        Args:
            query: Search query string
            category: Optional category filter
            include_recent: Whether to boost recent commands
            
        Returns:
            List of search results sorted by relevance
        """
        if not query.strip():
            # Empty query - return all commands or recent commands
            if include_recent and self._recent_commands:
                return self._get_recent_commands()
            return self._get_all_commands(category)
        
        query = query.strip().lower()
        results = []
        
        # Get candidate commands
        candidates = self._registry.get_all_command_names()
        if category:
            candidates = self._registry.get_commands_by_category(category)
        
        for command_name in candidates:
            command_info = self._registry.get_command_info(command_name)
            if not command_info:
                continue
            
            # Calculate search score
            score, match_type = self._calculate_score(query, command_info)
            
            if score > 0:
                result = CommandSearchResult(
                    command_name=command_name,
                    display_name=command_info['name'],
                    description=command_info['description'],
                    category=command_info['category'],
                    shortcut=command_info['shortcut'],
                    score=score,
                    match_type=match_type
                )
                
                # Boost recent commands
                if include_recent and command_name in self._recent_commands:
                    result.score += 0.2
                
                results.append(result)
        
        # Sort by score (descending) and limit results
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:self._max_results]
    
    def execute_command(self, command_name: str, *args: Any, **kwargs: Any) -> bool:
        """
        Execute a command through the palette.
        
        Args:
            command_name: Name of command to execute
            *args: Command arguments
            **kwargs: Command keyword arguments
            
        Returns:
            True if command executed successfully
        """
        try:
            success = self._registry.execute_command(command_name, *args, **kwargs)
            
            if success:
                self._add_to_recent(command_name)
            
            return success
            
        except Exception:
            return False
    
    def get_command_info(self, command_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a command."""
        return self._registry.get_command_info(command_name)
    
    def get_recent_commands(self) -> List[CommandSearchResult]:
        """Get recently executed commands."""
        return self._get_recent_commands()
    
    def clear_recent_commands(self) -> None:
        """Clear the recent commands history."""
        self._recent_commands.clear()
    
    def get_commands_by_category(self, category: str) -> List[CommandSearchResult]:
        """Get all commands in a specific category."""
        return self.search_commands("", category=category, include_recent=False)
    
    def get_all_categories(self) -> List[str]:
        """Get all available command categories."""
        return self._registry.get_all_categories()
    
    def get_category_display_name(self, category: str) -> str:
        """Get display name for a category."""
        try:
            return CommandCategory.from_string(category).get_display_name()
        except ValueError:
            return category.title()
    
    def _calculate_score(self, query: str, command_info: Dict[str, Any]) -> Tuple[float, str]:
        """
        Calculate search relevance score for a command.
        
        Returns:
            Tuple of (score, match_type)
        """
        name = command_info['name'].lower()
        description = command_info['description'].lower()
        shortcut = (command_info['shortcut'] or "").lower()
        
        # Exact name match gets highest score
        if query == name:
            return (1.0, "name")
        
        # Name starts with query
        if name.startswith(query):
            return (0.9, "name")
        
        # Name contains query
        if query in name:
            return (0.8, "name")
        
        # Shortcut exact match
        if shortcut and query == shortcut:
            return (0.85, "shortcut")
        
        # Shortcut contains query
        if shortcut and query in shortcut:
            return (0.7, "shortcut")
        
        # Description contains query
        if query in description:
            return (0.6, "description")
        
        # Fuzzy matching on name
        name_similarity = difflib.SequenceMatcher(None, query, name).ratio()
        if name_similarity >= self._fuzzy_threshold:
            return (name_similarity * 0.5, "name")
        
        # Fuzzy matching on description
        desc_similarity = difflib.SequenceMatcher(None, query, description).ratio()
        if desc_similarity >= self._fuzzy_threshold:
            return (desc_similarity * 0.3, "description")
        
        # Word matching in name/description
        query_words = query.split()
        if len(query_words) > 1:
            name_words = name.split()
            desc_words = description.split()
            
            # Check if all query words appear in name
            if all(any(qw in nw for nw in name_words) for qw in query_words):
                return (0.4, "name")
            
            # Check if all query words appear in description
            if all(any(qw in dw for dw in desc_words) for qw in query_words):
                return (0.3, "description")
        
        return (0.0, "none")
    
    def _get_recent_commands(self) -> List[CommandSearchResult]:
        """Get recent commands as search results."""
        results = []
        
        for command_name in reversed(self._recent_commands):
            command_info = self._registry.get_command_info(command_name)
            if command_info:
                result = CommandSearchResult(
                    command_name=command_name,
                    display_name=command_info['name'],
                    description=command_info['description'],
                    category=command_info['category'],
                    shortcut=command_info['shortcut'],
                    score=1.0,  # Recent commands get high score
                    match_type="recent"
                )
                results.append(result)
        
        return results
    
    def _get_all_commands(self, category: Optional[str] = None) -> List[CommandSearchResult]:
        """Get all commands as search results."""
        results = []
        
        candidates = self._registry.get_all_command_names()
        if category:
            candidates = self._registry.get_commands_by_category(category)
        
        for command_name in candidates:
            command_info = self._registry.get_command_info(command_name)
            if command_info:
                result = CommandSearchResult(
                    command_name=command_name,
                    display_name=command_info['name'],
                    description=command_info['description'],
                    category=command_info['category'],
                    shortcut=command_info['shortcut'],
                    score=0.5,  # Default score for browse mode
                    match_type="browse"
                )
                results.append(result)
        
        # Sort alphabetically when browsing
        results.sort(key=lambda x: x.display_name)
        return results
    
    def _add_to_recent(self, command_name: str) -> None:
        """Add a command to recent commands list."""
        # Remove if already exists to move to front
        try:
            self._recent_commands.remove(command_name)
        except ValueError:
            pass
        
        # Add to front
        self._recent_commands.append(command_name)


class CommandAutoComplete:
    """
    Provides auto-completion for command names and parameters.
    
    Used by command palette and other command input interfaces.
    """
    
    def __init__(self, command_registry: CommandRegistry):
        """
        Initialize auto-complete.
        
        Args:
            command_registry: Command registry to use for completion
        """
        self._registry = command_registry
    
    def get_command_completions(self, partial: str) -> List[str]:
        """
        Get command name completions for partial input.
        
        Args:
            partial: Partial command name
            
        Returns:
            List of matching command names
        """
        if not partial:
            return []
        
        partial_lower = partial.lower()
        completions = []
        
        for command_name in self._registry.get_all_command_names():
            if command_name.lower().startswith(partial_lower):
                completions.append(command_name)
        
        return sorted(completions)
    
    def get_parameter_completions(self, command_name: str, parameter: str, 
                                partial: str) -> List[str]:
        """
        Get parameter value completions.
        
        Args:
            command_name: Name of the command
            parameter: Parameter name
            partial: Partial parameter value
            
        Returns:
            List of possible parameter values
        """
        command_info = self._registry.get_command_info(command_name)
        if not command_info:
            return []
        
        parameters = command_info.get('parameters', {})
        param_info = parameters.get(parameter)
        
        if not param_info:
            return []
        
        # Handle specific parameter types
        param_type = param_info.get('type', 'string')
        
        if param_type == 'boolean':
            return ['true', 'false']
        elif param_type == 'integer':
            # Return some common integer suggestions
            if partial.isdigit():
                return [partial + '0', partial + '1', partial + '5']
            return ['1', '5', '10', '50', '100']
        elif parameter == 'category':
            # Special handling for category parameters
            categories = self._registry.get_all_categories()
            matching = [cat for cat in categories if cat.lower().startswith(partial.lower())]
            return matching
        
        # For other types, return empty list (no generic completions)
        return []
    
    def validate_command_syntax(self, command_line: str) -> Tuple[bool, str]:
        """
        Validate command syntax.
        
        Args:
            command_line: Full command line to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not command_line.strip():
            return False, "Empty command"
        
        parts = command_line.strip().split()
        command_name = parts[0]
        
        if not self._registry.has_command(command_name):
            return False, f"Unknown command: {command_name}"
        
        # For now, just validate that the command exists
        # More sophisticated parameter validation could be added here
        return True, ""