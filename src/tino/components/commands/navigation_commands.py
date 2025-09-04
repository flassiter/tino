"""
Navigation commands for the tino editor.

Implements text navigation and search commands including Find, Replace,
GoToLine, and other navigation functionality.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from ...core.interfaces.command import CommandError
from ...core.events.types import SearchEvent, ReplaceEvent, CursorMovedEvent
from .command_base import EditorCommand, CommandContext
from .categories import CommandCategory


class FindCommand(EditorCommand):
    """Find text in the editor."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute find command."""
        try:
            pattern = kwargs.get('pattern', '') or (args[0] if args else '')
            case_sensitive = kwargs.get('case_sensitive', False)
            whole_word = kwargs.get('whole_word', False)
            from_cursor = kwargs.get('from_cursor', True)
            
            if not pattern:
                raise CommandError("No search pattern provided", self.get_name())
            
            # Store search parameters for find next/previous
            self._store_execution_data("pattern", pattern)
            self._store_execution_data("case_sensitive", case_sensitive)
            self._store_execution_data("whole_word", whole_word)
            self._store_execution_data("old_cursor", self.editor.get_cursor_position())
            
            # Determine starting position
            start_pos = 0
            if from_cursor:
                cursor_pos = self.editor.get_cursor_position()
                start_pos = cursor_pos[2]  # Absolute position
            
            # Perform search
            match_range = self._find_text(pattern, start_pos, case_sensitive, whole_word)
            
            if match_range:
                # Move cursor to match and select it
                self.editor.set_selection(match_range[0], match_range[1])
                
                # Find all matches for count
                all_matches = self._find_all_matches(pattern, case_sensitive, whole_word)
                current_match = self._get_match_index(all_matches, match_range[0]) + 1
                
                # Store results in application state
                self.context.application_state.update({
                    'search_pattern': pattern,
                    'search_results': all_matches,
                    'current_match': current_match,
                    'total_matches': len(all_matches),
                    'case_sensitive': case_sensitive,
                    'whole_word': whole_word
                })
                
                # Emit search event
                event = SearchEvent(
                    pattern=pattern,
                    case_sensitive=case_sensitive,
                    whole_word=whole_word,
                    matches_found=len(all_matches),
                    current_match=current_match
                )
                self._emit_event(event)
                
                self._mark_executed(can_undo=True)
                return True
            else:
                # No matches found
                self.context.application_state.update({
                    'search_pattern': pattern,
                    'search_results': [],
                    'current_match': 0,
                    'total_matches': 0,
                    'case_sensitive': case_sensitive,
                    'whole_word': whole_word
                })
                
                event = SearchEvent(
                    pattern=pattern,
                    case_sensitive=case_sensitive,
                    whole_word=whole_word,
                    matches_found=0,
                    current_match=0
                )
                self._emit_event(event)
                
                return False
            
        except Exception as e:
            raise CommandError(f"Failed to find text: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Restore cursor position before search."""
        if not self.can_undo():
            return False
        
        try:
            old_cursor = self._get_execution_data("old_cursor", (0, 0, 0))
            self.editor.set_cursor_position(old_cursor[0], old_cursor[1])
            
            # Clear search state
            self.context.application_state.pop('search_pattern', None)
            self.context.application_state.pop('search_results', None)
            
            return True
            
        except Exception:
            return False
    
    def _find_text(self, pattern: str, start: int, case_sensitive: bool, whole_word: bool) -> Optional[Tuple[int, int]]:
        """Find the first occurrence of pattern starting from position."""
        content = self.editor.get_content()
        
        if whole_word:
            pattern = r'\b' + re.escape(pattern) + r'\b'
        else:
            pattern = re.escape(pattern)
        
        flags = 0 if case_sensitive else re.IGNORECASE
        
        try:
            match = re.search(pattern, content[start:], flags)
            if match:
                return (start + match.start(), start + match.end())
        except re.error:
            pass
        
        return None
    
    def _find_all_matches(self, pattern: str, case_sensitive: bool, whole_word: bool) -> List[Tuple[int, int]]:
        """Find all occurrences of pattern in the document."""
        content = self.editor.get_content()
        matches = []
        
        if whole_word:
            pattern = r'\b' + re.escape(pattern) + r'\b'
        else:
            pattern = re.escape(pattern)
        
        flags = 0 if case_sensitive else re.IGNORECASE
        
        try:
            for match in re.finditer(pattern, content, flags):
                matches.append((match.start(), match.end()))
        except re.error:
            pass
        
        return matches
    
    def _get_match_index(self, matches: List[Tuple[int, int]], position: int) -> int:
        """Get the index of the match at the given position."""
        for i, (start, end) in enumerate(matches):
            if start == position:
                return i
        return 0
    
    def get_name(self) -> str:
        return "Find"
    
    def get_description(self) -> str:
        return "Find text in the document"
    
    def get_category(self) -> str:
        return CommandCategory.NAVIGATION.value
    
    def get_shortcut(self) -> Optional[str]:
        return "ctrl+f"
    
    def get_parameters(self) -> Dict[str, Any]:
        """Define parameters for the find command."""
        return {
            'pattern': {
                'type': 'string',
                'description': 'Text to search for',
                'required': True
            },
            'case_sensitive': {
                'type': 'boolean',
                'description': 'Whether search should be case sensitive',
                'required': False,
                'default': False
            },
            'whole_word': {
                'type': 'boolean',
                'description': 'Whether to match whole words only',
                'required': False,
                'default': False
            },
            'from_cursor': {
                'type': 'boolean',
                'description': 'Whether to start search from cursor position',
                'required': False,
                'default': True
            }
        }


class FindNextCommand(EditorCommand):
    """Find next occurrence of the current search pattern."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute find next command."""
        try:
            # Get current search state
            search_results = self.context.application_state.get('search_results', [])
            current_match = self.context.application_state.get('current_match', 0)
            
            if not search_results:
                return False  # No active search
            
            # Calculate next match index
            next_match = (current_match) % len(search_results)  # Wrap around
            
            if next_match < len(search_results):
                match_range = search_results[next_match]
                
                # Select the match
                self.editor.set_selection(match_range[0], match_range[1])
                
                # Update application state
                self.context.application_state['current_match'] = next_match + 1
                
                self._mark_executed(can_undo=False)  # Navigation doesn't need undo
                return True
            
            return False
            
        except Exception as e:
            raise CommandError(f"Failed to find next: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Find next cannot be undone."""
        return False
    
    def get_name(self) -> str:
        return "Find Next"
    
    def get_description(self) -> str:
        return "Find next occurrence of search pattern"
    
    def get_category(self) -> str:
        return CommandCategory.NAVIGATION.value
    
    def get_shortcut(self) -> Optional[str]:
        return "f3"
    
    def can_execute(self, *args: Any, **kwargs: Any) -> bool:
        """Can execute if there are search results."""
        return (super().can_execute(*args, **kwargs) and 
                bool(self.context.application_state.get('search_results', [])))


class FindPreviousCommand(EditorCommand):
    """Find previous occurrence of the current search pattern."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute find previous command."""
        try:
            # Get current search state
            search_results = self.context.application_state.get('search_results', [])
            current_match = self.context.application_state.get('current_match', 1)
            
            if not search_results:
                return False  # No active search
            
            # Calculate previous match index
            prev_match = (current_match - 2) % len(search_results)  # Wrap around
            
            if prev_match >= 0 and prev_match < len(search_results):
                match_range = search_results[prev_match]
                
                # Select the match
                self.editor.set_selection(match_range[0], match_range[1])
                
                # Update application state
                self.context.application_state['current_match'] = prev_match + 1
                
                self._mark_executed(can_undo=False)  # Navigation doesn't need undo
                return True
            
            return False
            
        except Exception as e:
            raise CommandError(f"Failed to find previous: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Find previous cannot be undone."""
        return False
    
    def get_name(self) -> str:
        return "Find Previous"
    
    def get_description(self) -> str:
        return "Find previous occurrence of search pattern"
    
    def get_category(self) -> str:
        return CommandCategory.NAVIGATION.value
    
    def get_shortcut(self) -> Optional[str]:
        return "shift+f3"
    
    def can_execute(self, *args: Any, **kwargs: Any) -> bool:
        """Can execute if there are search results."""
        return (super().can_execute(*args, **kwargs) and 
                bool(self.context.application_state.get('search_results', [])))


class ReplaceCommand(EditorCommand):
    """Replace text in the editor."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute replace command."""
        try:
            pattern = kwargs.get('pattern', '') or (args[0] if len(args) > 0 else '')
            replacement = kwargs.get('replacement', '') or (args[1] if len(args) > 1 else '')
            replace_all = kwargs.get('replace_all', False)
            case_sensitive = kwargs.get('case_sensitive', False)
            whole_word = kwargs.get('whole_word', False)
            
            if not pattern:
                raise CommandError("No search pattern provided", self.get_name())
            
            # Store state for undo
            old_content = self.editor.get_content()
            old_cursor = self.editor.get_cursor_position()
            
            self._store_execution_data("old_content", old_content)
            self._store_execution_data("old_cursor", old_cursor)
            self._store_execution_data("pattern", pattern)
            self._store_execution_data("replacement", replacement)
            
            if replace_all:
                # Replace all occurrences
                replacements_made = self._replace_all(pattern, replacement, case_sensitive, whole_word)
            else:
                # Replace current selection or find and replace next occurrence
                replacements_made = self._replace_current(pattern, replacement, case_sensitive, whole_word)
            
            if replacements_made > 0:
                # Emit replace event
                event = ReplaceEvent(
                    pattern=pattern,
                    replacement=replacement,
                    replacements_made=replacements_made,
                    case_sensitive=case_sensitive,
                    whole_word=whole_word
                )
                self._emit_event(event)
                
                self._store_execution_data("replacements_made", replacements_made)
                self._mark_executed(can_undo=True)
                
                return True
            
            return False
            
        except Exception as e:
            raise CommandError(f"Failed to replace text: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Undo replace operation."""
        if not self.can_undo():
            return False
        
        try:
            old_content = self._get_execution_data("old_content")
            old_cursor = self._get_execution_data("old_cursor")
            
            self.editor.set_content(old_content)
            self.editor.set_cursor_position(old_cursor[0], old_cursor[1])
            
            return True
            
        except Exception:
            return False
    
    def _replace_all(self, pattern: str, replacement: str, case_sensitive: bool, whole_word: bool) -> int:
        """Replace all occurrences of pattern with replacement."""
        content = self.editor.get_content()
        
        if whole_word:
            pattern = r'\b' + re.escape(pattern) + r'\b'
        else:
            pattern = re.escape(pattern)
        
        flags = 0 if case_sensitive else re.IGNORECASE
        
        try:
            new_content, count = re.subn(pattern, replacement, content, flags=flags)
            self.editor.set_content(new_content)
            return count
        except re.error:
            return 0
    
    def _replace_current(self, pattern: str, replacement: str, case_sensitive: bool, whole_word: bool) -> int:
        """Replace current selection or find and replace next occurrence."""
        selection_range = self.editor.get_selection()
        selected_text = self.editor.get_selected_text()
        
        # Check if current selection matches the pattern
        if selected_text and self._matches_pattern(selected_text, pattern, case_sensitive, whole_word):
            # Replace selected text
            self.editor.replace_selection(replacement)
            return 1
        else:
            # Find next occurrence and replace it
            cursor_pos = self.editor.get_cursor_position()
            match_range = self._find_text(pattern, cursor_pos[2], case_sensitive, whole_word)
            
            if match_range:
                self.editor.set_selection(match_range[0], match_range[1])
                self.editor.replace_selection(replacement)
                return 1
        
        return 0
    
    def _find_text(self, pattern: str, start: int, case_sensitive: bool, whole_word: bool) -> Optional[Tuple[int, int]]:
        """Find the first occurrence of pattern starting from position."""
        content = self.editor.get_content()
        
        if whole_word:
            pattern = r'\b' + re.escape(pattern) + r'\b'
        else:
            pattern = re.escape(pattern)
        
        flags = 0 if case_sensitive else re.IGNORECASE
        
        try:
            match = re.search(pattern, content[start:], flags)
            if match:
                return (start + match.start(), start + match.end())
        except re.error:
            pass
        
        return None
    
    def _matches_pattern(self, text: str, pattern: str, case_sensitive: bool, whole_word: bool) -> bool:
        """Check if text matches the search pattern."""
        if whole_word:
            pattern = r'\b' + re.escape(pattern) + r'\b'
        else:
            pattern = re.escape(pattern)
        
        flags = 0 if case_sensitive else re.IGNORECASE
        
        try:
            return bool(re.fullmatch(pattern, text, flags))
        except re.error:
            return False
    
    def get_name(self) -> str:
        return "Replace"
    
    def get_description(self) -> str:
        return "Replace text in the document"
    
    def get_category(self) -> str:
        return CommandCategory.NAVIGATION.value
    
    def get_shortcut(self) -> Optional[str]:
        return "ctrl+h"
    
    def get_parameters(self) -> Dict[str, Any]:
        """Define parameters for the replace command."""
        return {
            'pattern': {
                'type': 'string',
                'description': 'Text to search for',
                'required': True
            },
            'replacement': {
                'type': 'string',
                'description': 'Replacement text',
                'required': True
            },
            'replace_all': {
                'type': 'boolean',
                'description': 'Whether to replace all occurrences',
                'required': False,
                'default': False
            },
            'case_sensitive': {
                'type': 'boolean',
                'description': 'Whether search should be case sensitive',
                'required': False,
                'default': False
            },
            'whole_word': {
                'type': 'boolean',
                'description': 'Whether to match whole words only',
                'required': False,
                'default': False
            }
        }


class GoToLineCommand(EditorCommand):
    """Navigate to a specific line number."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute go to line command."""
        try:
            line_number = kwargs.get('line', 0) or (args[0] if args else 0)
            
            if isinstance(line_number, str):
                try:
                    line_number = int(line_number)
                except ValueError:
                    raise CommandError("Invalid line number format", self.get_name())
            
            if line_number <= 0:
                raise CommandError("Line number must be positive", self.get_name())
            
            # Store old position for undo
            old_cursor = self.editor.get_cursor_position()
            self._store_execution_data("old_cursor", old_cursor)
            
            # Convert to 0-based line number
            target_line = line_number - 1
            max_line = self.editor.get_line_count() - 1
            
            # Clamp to valid range
            target_line = max(0, min(target_line, max_line))
            
            # Move cursor to beginning of target line
            self.editor.set_cursor_position(target_line, 0)
            
            # Emit cursor moved event
            new_cursor = self.editor.get_cursor_position()
            event = CursorMovedEvent(
                line=new_cursor[0],
                column=new_cursor[1],
                position=new_cursor[2],
                old_line=old_cursor[0],
                old_column=old_cursor[1],
                old_position=old_cursor[2]
            )
            self._emit_event(event)
            
            self._mark_executed(can_undo=True)
            
            return True
            
        except Exception as e:
            raise CommandError(f"Failed to go to line: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Restore previous cursor position."""
        if not self.can_undo():
            return False
        
        try:
            old_cursor = self._get_execution_data("old_cursor", (0, 0, 0))
            self.editor.set_cursor_position(old_cursor[0], old_cursor[1])
            
            return True
            
        except Exception:
            return False
    
    def get_name(self) -> str:
        return "Go to Line"
    
    def get_description(self) -> str:
        return "Navigate to a specific line number"
    
    def get_category(self) -> str:
        return CommandCategory.NAVIGATION.value
    
    def get_shortcut(self) -> Optional[str]:
        return "ctrl+g"
    
    def get_parameters(self) -> Dict[str, Any]:
        """Define parameters for the go to line command."""
        return {
            'line': {
                'type': 'integer',
                'description': 'Line number to navigate to (1-based)',
                'required': True,
                'min': 1
            }
        }
    
    def validate_parameters(self, *args: Any, **kwargs: Any) -> Optional[str]:
        """Validate line number parameter."""
        line_number = kwargs.get('line') or (args[0] if args else None)
        
        if line_number is None:
            return "Line number is required"
        
        try:
            line_num = int(line_number)
            if line_num <= 0:
                return "Line number must be positive"
        except (ValueError, TypeError):
            return "Line number must be a valid integer"
        
        return None