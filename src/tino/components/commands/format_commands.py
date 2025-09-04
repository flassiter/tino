"""
Markdown formatting commands for the tino editor.

Implements markdown formatting commands including Bold, Italic, Link, Code,
and other common markdown formatting operations.
"""

import re
from typing import Any, Dict, Optional, Tuple

from ...core.interfaces.command import CommandError
from ...core.events.types import TextChangedEvent, SelectionChangedEvent
from .command_base import EditorCommand, CommandContext
from .categories import CommandCategory


class BoldCommand(EditorCommand):
    """Apply or remove bold formatting (**text**)."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute bold formatting command."""
        try:
            selection_range = self.editor.get_selection()
            selected_text = self.editor.get_selected_text()
            
            # Store state for undo
            self._store_execution_data("old_selection", selection_range)
            self._store_execution_data("old_text", selected_text)
            self._store_execution_data("old_content", self.editor.get_content())
            
            if selected_text:
                # Check if already bold
                if self._is_bold(selected_text):
                    # Remove bold formatting
                    new_text = self._remove_bold(selected_text)
                    self._store_execution_data("action", "remove")
                else:
                    # Add bold formatting
                    new_text = f"**{selected_text}**"
                    self._store_execution_data("action", "add")
                
                # Replace selection
                self.editor.replace_selection(new_text)
                
                # Update selection to include the new formatting
                if self._get_execution_data("action") == "add":
                    new_end = selection_range[0] + len(new_text)
                    self.editor.set_selection(selection_range[0], new_end)
                else:
                    new_end = selection_range[0] + len(new_text)
                    self.editor.set_selection(selection_range[0] + 2, new_end - 2)
                
            else:
                # No selection, insert bold markers and position cursor
                cursor_pos = selection_range[0]
                self.editor.insert_text(cursor_pos, "****")
                self.editor.set_cursor_position(*self._pos_to_line_col(cursor_pos + 2))
                self._store_execution_data("action", "insert_empty")
            
            # Emit events
            event = TextChangedEvent(
                content=self.editor.get_content(),
                old_content=self._get_execution_data("old_content"),
                change_type="format"
            )
            self._emit_event(event)
            
            self._mark_executed(can_undo=True)
            
            return True
            
        except Exception as e:
            raise CommandError(f"Failed to apply bold formatting: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Undo bold formatting."""
        if not self.can_undo():
            return False
        
        try:
            old_content = self._get_execution_data("old_content")
            old_selection = self._get_execution_data("old_selection")
            
            self.editor.set_content(old_content)
            self.editor.set_selection(old_selection[0], old_selection[1])
            
            return True
            
        except Exception:
            return False
    
    def _is_bold(self, text: str) -> bool:
        """Check if text is already bold formatted."""
        return text.startswith("**") and text.endswith("**") and len(text) > 4
    
    def _remove_bold(self, text: str) -> str:
        """Remove bold formatting from text."""
        if self._is_bold(text):
            return text[2:-2]
        return text
    
    def _pos_to_line_col(self, pos: int) -> Tuple[int, int]:
        """Convert absolute position to line,column."""
        content = self.editor.get_content()
        lines = content[:pos].split('\n')
        line = len(lines) - 1
        col = len(lines[-1])
        return line, col
    
    def get_name(self) -> str:
        return "Bold"
    
    def get_description(self) -> str:
        return "Apply or remove bold formatting"
    
    def get_category(self) -> str:
        return CommandCategory.FORMAT.value
    
    def get_shortcut(self) -> Optional[str]:
        return "ctrl+b"


class ItalicCommand(EditorCommand):
    """Apply or remove italic formatting (*text*)."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute italic formatting command."""
        try:
            selection_range = self.editor.get_selection()
            selected_text = self.editor.get_selected_text()
            
            # Store state for undo
            self._store_execution_data("old_selection", selection_range)
            self._store_execution_data("old_text", selected_text)
            self._store_execution_data("old_content", self.editor.get_content())
            
            if selected_text:
                # Check if already italic
                if self._is_italic(selected_text):
                    # Remove italic formatting
                    new_text = self._remove_italic(selected_text)
                    self._store_execution_data("action", "remove")
                else:
                    # Add italic formatting
                    new_text = f"*{selected_text}*"
                    self._store_execution_data("action", "add")
                
                # Replace selection
                self.editor.replace_selection(new_text)
                
                # Update selection
                if self._get_execution_data("action") == "add":
                    new_end = selection_range[0] + len(new_text)
                    self.editor.set_selection(selection_range[0], new_end)
                else:
                    new_end = selection_range[0] + len(new_text)
                    self.editor.set_selection(selection_range[0] + 1, new_end - 1)
                
            else:
                # No selection, insert italic markers and position cursor
                cursor_pos = selection_range[0]
                self.editor.insert_text(cursor_pos, "**")
                self.editor.set_cursor_position(*self._pos_to_line_col(cursor_pos + 1))
                self._store_execution_data("action", "insert_empty")
            
            # Emit events
            event = TextChangedEvent(
                content=self.editor.get_content(),
                old_content=self._get_execution_data("old_content"),
                change_type="format"
            )
            self._emit_event(event)
            
            self._mark_executed(can_undo=True)
            
            return True
            
        except Exception as e:
            raise CommandError(f"Failed to apply italic formatting: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Undo italic formatting."""
        if not self.can_undo():
            return False
        
        try:
            old_content = self._get_execution_data("old_content")
            old_selection = self._get_execution_data("old_selection")
            
            self.editor.set_content(old_content)
            self.editor.set_selection(old_selection[0], old_selection[1])
            
            return True
            
        except Exception:
            return False
    
    def _is_italic(self, text: str) -> bool:
        """Check if text is already italic formatted."""
        return (text.startswith("*") and text.endswith("*") and 
                not text.startswith("**") and len(text) > 2)
    
    def _remove_italic(self, text: str) -> str:
        """Remove italic formatting from text."""
        if self._is_italic(text):
            return text[1:-1]
        return text
    
    def _pos_to_line_col(self, pos: int) -> Tuple[int, int]:
        """Convert absolute position to line,column."""
        content = self.editor.get_content()
        lines = content[:pos].split('\n')
        line = len(lines) - 1
        col = len(lines[-1])
        return line, col
    
    def get_name(self) -> str:
        return "Italic"
    
    def get_description(self) -> str:
        return "Apply or remove italic formatting"
    
    def get_category(self) -> str:
        return CommandCategory.FORMAT.value
    
    def get_shortcut(self) -> Optional[str]:
        return "ctrl+i"


class CodeCommand(EditorCommand):
    """Apply or remove inline code formatting (`code`)."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute code formatting command."""
        try:
            selection_range = self.editor.get_selection()
            selected_text = self.editor.get_selected_text()
            
            # Store state for undo
            self._store_execution_data("old_selection", selection_range)
            self._store_execution_data("old_text", selected_text)
            self._store_execution_data("old_content", self.editor.get_content())
            
            if selected_text:
                # Check if already code formatted
                if self._is_code(selected_text):
                    # Remove code formatting
                    new_text = self._remove_code(selected_text)
                    self._store_execution_data("action", "remove")
                else:
                    # Add code formatting
                    new_text = f"`{selected_text}`"
                    self._store_execution_data("action", "add")
                
                # Replace selection
                self.editor.replace_selection(new_text)
                
                # Update selection
                if self._get_execution_data("action") == "add":
                    new_end = selection_range[0] + len(new_text)
                    self.editor.set_selection(selection_range[0], new_end)
                else:
                    new_end = selection_range[0] + len(new_text)
                    self.editor.set_selection(selection_range[0] + 1, new_end - 1)
                
            else:
                # No selection, insert code markers and position cursor
                cursor_pos = selection_range[0]
                self.editor.insert_text(cursor_pos, "``")
                self.editor.set_cursor_position(*self._pos_to_line_col(cursor_pos + 1))
                self._store_execution_data("action", "insert_empty")
            
            # Emit events
            event = TextChangedEvent(
                content=self.editor.get_content(),
                old_content=self._get_execution_data("old_content"),
                change_type="format"
            )
            self._emit_event(event)
            
            self._mark_executed(can_undo=True)
            
            return True
            
        except Exception as e:
            raise CommandError(f"Failed to apply code formatting: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Undo code formatting."""
        if not self.can_undo():
            return False
        
        try:
            old_content = self._get_execution_data("old_content")
            old_selection = self._get_execution_data("old_selection")
            
            self.editor.set_content(old_content)
            self.editor.set_selection(old_selection[0], old_selection[1])
            
            return True
            
        except Exception:
            return False
    
    def _is_code(self, text: str) -> bool:
        """Check if text is already code formatted."""
        return text.startswith("`") and text.endswith("`") and len(text) > 2
    
    def _remove_code(self, text: str) -> str:
        """Remove code formatting from text."""
        if self._is_code(text):
            return text[1:-1]
        return text
    
    def _pos_to_line_col(self, pos: int) -> Tuple[int, int]:
        """Convert absolute position to line,column."""
        content = self.editor.get_content()
        lines = content[:pos].split('\n')
        line = len(lines) - 1
        col = len(lines[-1])
        return line, col
    
    def get_name(self) -> str:
        return "Inline Code"
    
    def get_description(self) -> str:
        return "Apply or remove inline code formatting"
    
    def get_category(self) -> str:
        return CommandCategory.FORMAT.value
    
    def get_shortcut(self) -> Optional[str]:
        return "ctrl+shift+c"


class LinkCommand(EditorCommand):
    """Insert or edit a markdown link."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute link formatting command."""
        try:
            selection_range = self.editor.get_selection()
            selected_text = self.editor.get_selected_text()
            
            # Get URL from parameters or use default
            url = kwargs.get('url', '')
            link_text = kwargs.get('text', selected_text or 'Link Text')
            
            # Store state for undo
            self._store_execution_data("old_selection", selection_range)
            self._store_execution_data("old_text", selected_text)
            self._store_execution_data("old_content", self.editor.get_content())
            
            # Check if selection is already a link
            if selected_text and self._is_link(selected_text):
                # Edit existing link
                link_parts = self._parse_link(selected_text)
                if link_parts:
                    existing_text, existing_url = link_parts
                    new_text = f"[{link_text or existing_text}]({url or existing_url})"
                else:
                    new_text = f"[{link_text}]({url})"
                self._store_execution_data("action", "edit")
            else:
                # Create new link
                if not url:
                    # If no URL provided, create a template link
                    new_text = f"[{link_text}](url)"
                else:
                    new_text = f"[{link_text}]({url})"
                self._store_execution_data("action", "create")
            
            # Replace selection
            self.editor.replace_selection(new_text)
            
            # Position cursor appropriately
            if not url:
                # Position cursor at URL placeholder
                start_pos = selection_range[0]
                url_start = start_pos + len(f"[{link_text}](")
                url_end = url_start + len("url")
                self.editor.set_selection(url_start, url_end)
            else:
                # Select the entire link
                new_end = selection_range[0] + len(new_text)
                self.editor.set_selection(selection_range[0], new_end)
            
            # Emit events
            event = TextChangedEvent(
                content=self.editor.get_content(),
                old_content=self._get_execution_data("old_content"),
                change_type="format"
            )
            self._emit_event(event)
            
            self._mark_executed(can_undo=True)
            
            return True
            
        except Exception as e:
            raise CommandError(f"Failed to insert link: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Undo link insertion."""
        if not self.can_undo():
            return False
        
        try:
            old_content = self._get_execution_data("old_content")
            old_selection = self._get_execution_data("old_selection")
            
            self.editor.set_content(old_content)
            self.editor.set_selection(old_selection[0], old_selection[1])
            
            return True
            
        except Exception:
            return False
    
    def _is_link(self, text: str) -> bool:
        """Check if text is a markdown link."""
        link_pattern = r'\[.*?\]\(.*?\)'
        return bool(re.match(link_pattern, text.strip()))
    
    def _parse_link(self, text: str) -> Optional[Tuple[str, str]]:
        """Parse markdown link text and URL."""
        link_pattern = r'\[(.*?)\]\((.*?)\)'
        match = re.match(link_pattern, text.strip())
        if match:
            return match.group(1), match.group(2)
        return None
    
    def get_name(self) -> str:
        return "Insert Link"
    
    def get_description(self) -> str:
        return "Insert or edit a markdown link"
    
    def get_category(self) -> str:
        return CommandCategory.FORMAT.value
    
    def get_shortcut(self) -> Optional[str]:
        return "ctrl+k"
    
    def get_parameters(self) -> Dict[str, Any]:
        """Define parameters for the link command."""
        return {
            'url': {
                'type': 'string',
                'description': 'URL for the link',
                'required': False,
                'default': ''
            },
            'text': {
                'type': 'string', 
                'description': 'Display text for the link',
                'required': False,
                'default': ''
            }
        }


class HeadingCommand(EditorCommand):
    """Apply heading formatting (# Heading)."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute heading formatting command."""
        try:
            level = kwargs.get('level', 1)
            level = max(1, min(6, level))  # Ensure level is between 1-6
            
            cursor_pos = self.editor.get_cursor_position()
            current_line = cursor_pos[0]
            
            # Store state for undo
            line_text = self.editor.get_line_text(current_line)
            self._store_execution_data("old_line", current_line)
            self._store_execution_data("old_line_text", line_text)
            self._store_execution_data("old_content", self.editor.get_content())
            
            # Check if line is already a heading
            heading_match = re.match(r'^(#{1,6})\s*(.*)', line_text)
            
            if heading_match:
                # Modify existing heading
                current_level = len(heading_match.group(1))
                heading_text = heading_match.group(2)
                
                if current_level == level:
                    # Remove heading
                    new_line_text = heading_text
                    self._store_execution_data("action", "remove")
                else:
                    # Change heading level
                    new_line_text = f"{'#' * level} {heading_text}"
                    self._store_execution_data("action", "change")
            else:
                # Add heading to existing line
                new_line_text = f"{'#' * level} {line_text}"
                self._store_execution_data("action", "add")
            
            # Replace line
            content = self.editor.get_content()
            lines = content.split('\n')
            
            if current_line < len(lines):
                lines[current_line] = new_line_text
                new_content = '\n'.join(lines)
                
                self.editor.set_content(new_content)
                
                # Position cursor at end of heading
                self.editor.set_cursor_position(current_line, len(new_line_text))
            
            # Emit events
            event = TextChangedEvent(
                content=self.editor.get_content(),
                old_content=self._get_execution_data("old_content"),
                change_type="format"
            )
            self._emit_event(event)
            
            self._mark_executed(can_undo=True)
            
            return True
            
        except Exception as e:
            raise CommandError(f"Failed to apply heading: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Undo heading formatting."""
        if not self.can_undo():
            return False
        
        try:
            old_content = self._get_execution_data("old_content")
            old_line = self._get_execution_data("old_line")
            
            self.editor.set_content(old_content)
            
            # Restore cursor position  
            old_line_text = self._get_execution_data("old_line_text", "")
            self.editor.set_cursor_position(old_line, len(old_line_text))
            
            return True
            
        except Exception:
            return False
    
    def get_name(self) -> str:
        return "Heading"
    
    def get_description(self) -> str:
        return "Apply heading formatting to current line"
    
    def get_category(self) -> str:
        return CommandCategory.FORMAT.value
    
    def get_parameters(self) -> Dict[str, Any]:
        """Define parameters for the heading command."""
        return {
            'level': {
                'type': 'integer',
                'description': 'Heading level (1-6)',
                'required': False,
                'default': 1,
                'min': 1,
                'max': 6
            }
        }


class StrikethroughCommand(EditorCommand):
    """Apply or remove strikethrough formatting (~~text~~)."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute strikethrough formatting command."""
        try:
            selection_range = self.editor.get_selection()
            selected_text = self.editor.get_selected_text()
            
            # Store state for undo
            self._store_execution_data("old_selection", selection_range)
            self._store_execution_data("old_text", selected_text)
            self._store_execution_data("old_content", self.editor.get_content())
            
            if selected_text:
                # Check if already strikethrough
                if self._is_strikethrough(selected_text):
                    # Remove strikethrough formatting
                    new_text = self._remove_strikethrough(selected_text)
                    self._store_execution_data("action", "remove")
                else:
                    # Add strikethrough formatting
                    new_text = f"~~{selected_text}~~"
                    self._store_execution_data("action", "add")
                
                # Replace selection
                self.editor.replace_selection(new_text)
                
                # Update selection
                if self._get_execution_data("action") == "add":
                    new_end = selection_range[0] + len(new_text)
                    self.editor.set_selection(selection_range[0], new_end)
                else:
                    new_end = selection_range[0] + len(new_text)
                    self.editor.set_selection(selection_range[0] + 2, new_end - 2)
                
            else:
                # No selection, insert strikethrough markers and position cursor
                cursor_pos = selection_range[0]
                self.editor.insert_text(cursor_pos, "~~~~")
                self.editor.set_cursor_position(*self._pos_to_line_col(cursor_pos + 2))
                self._store_execution_data("action", "insert_empty")
            
            # Emit events
            event = TextChangedEvent(
                content=self.editor.get_content(),
                old_content=self._get_execution_data("old_content"),
                change_type="format"
            )
            self._emit_event(event)
            
            self._mark_executed(can_undo=True)
            
            return True
            
        except Exception as e:
            raise CommandError(f"Failed to apply strikethrough: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Undo strikethrough formatting."""
        if not self.can_undo():
            return False
        
        try:
            old_content = self._get_execution_data("old_content")
            old_selection = self._get_execution_data("old_selection")
            
            self.editor.set_content(old_content)
            self.editor.set_selection(old_selection[0], old_selection[1])
            
            return True
            
        except Exception:
            return False
    
    def _is_strikethrough(self, text: str) -> bool:
        """Check if text is already strikethrough formatted."""
        return text.startswith("~~") and text.endswith("~~") and len(text) > 4
    
    def _remove_strikethrough(self, text: str) -> str:
        """Remove strikethrough formatting from text."""
        if self._is_strikethrough(text):
            return text[2:-2]
        return text
    
    def _pos_to_line_col(self, pos: int) -> Tuple[int, int]:
        """Convert absolute position to line,column."""
        content = self.editor.get_content()
        lines = content[:pos].split('\n')
        line = len(lines) - 1
        col = len(lines[-1])
        return line, col
    
    def get_name(self) -> str:
        return "Strikethrough"
    
    def get_description(self) -> str:
        return "Apply or remove strikethrough formatting"
    
    def get_category(self) -> str:
        return CommandCategory.FORMAT.value