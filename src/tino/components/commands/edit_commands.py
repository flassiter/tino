"""
Edit operation commands for the tino editor.

Implements text editing commands including Cut, Copy, Paste, Undo, Redo,
DuplicateLine, and SelectAll functionality.
"""

from typing import Any, Dict, Optional
import re

from ...core.interfaces.command import CommandError
from ...core.events.types import TextChangedEvent, SelectionChangedEvent
from .command_base import EditorCommand, CommandContext
from .categories import CommandCategory


class UndoCommand(EditorCommand):
    """Undo the last operation."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute undo command."""
        try:
            if not self.editor.can_undo():
                return False
            
            # Store current state for redo
            current_content = self.editor.get_content()
            current_cursor = self.editor.get_cursor_position()
            
            self._store_execution_data("content_before_undo", current_content)
            self._store_execution_data("cursor_before_undo", (current_cursor[0], current_cursor[1]))
            
            # Perform undo
            success = self.editor.undo()
            
            if success:
                # Emit text change event
                new_content = self.editor.get_content()
                event = TextChangedEvent(
                    content=new_content,
                    old_content=current_content,
                    change_type="undo"
                )
                self._emit_event(event)
                
                self._mark_executed(can_undo=True)
            
            return success
            
        except Exception as e:
            raise CommandError(f"Failed to undo: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Redo what was undone (redo operation)."""
        if not self.can_undo():
            return False
        
        try:
            # This is essentially a redo operation
            return self.editor.redo()
        except Exception:
            return False
    
    def get_name(self) -> str:
        return "Undo"
    
    def get_description(self) -> str:
        return "Undo the last operation"
    
    def get_category(self) -> str:
        return CommandCategory.EDIT.value
    
    def get_shortcut(self) -> Optional[str]:
        return "ctrl+z"
    
    def can_execute(self, *args: Any, **kwargs: Any) -> bool:
        """Can execute if editor has undo operations available."""
        return (super().can_execute(*args, **kwargs) and 
                self.editor.can_undo())


class RedoCommand(EditorCommand):
    """Redo the last undone operation."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute redo command."""
        try:
            if not self.editor.can_redo():
                return False
            
            # Store current state
            current_content = self.editor.get_content()
            
            # Perform redo
            success = self.editor.redo()
            
            if success:
                # Emit text change event
                new_content = self.editor.get_content()
                event = TextChangedEvent(
                    content=new_content,
                    old_content=current_content,
                    change_type="redo"
                )
                self._emit_event(event)
                
                self._mark_executed(can_undo=False)  # Redo can't be undone directly
            
            return success
            
        except Exception as e:
            raise CommandError(f"Failed to redo: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Cannot undo a redo operation directly."""
        return False
    
    def get_name(self) -> str:
        return "Redo"
    
    def get_description(self) -> str:
        return "Redo the last undone operation"
    
    def get_category(self) -> str:
        return CommandCategory.EDIT.value
    
    def get_shortcut(self) -> Optional[str]:
        return "ctrl+y"
    
    def can_execute(self, *args: Any, **kwargs: Any) -> bool:
        """Can execute if editor has redo operations available."""
        return (super().can_execute(*args, **kwargs) and 
                self.editor.can_redo())


class CutCommand(EditorCommand):
    """Cut selected text to clipboard."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute cut command."""
        try:
            selected_text = self.editor.get_selected_text()
            
            if not selected_text:
                return False  # Nothing to cut
            
            # Store state for undo
            selection_range = self.editor.get_selection()
            self._store_execution_data("cut_text", selected_text)
            self._store_execution_data("cut_position", selection_range)
            
            # Replace selection with empty string (cut)
            self.editor.replace_selection("")
            
            # Store in application state (clipboard simulation)
            self.context.application_state["clipboard"] = selected_text
            
            # Emit events
            text_event = TextChangedEvent(
                content=self.editor.get_content(),
                change_type="delete",
                position=selection_range[0],
                length=len(selected_text)
            )
            self._emit_event(text_event)
            
            self._mark_executed(can_undo=True)
            
            return True
            
        except Exception as e:
            raise CommandError(f"Failed to cut text: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Restore cut text."""
        if not self.can_undo():
            return False
        
        try:
            cut_text = self._get_execution_data("cut_text", "")
            cut_position = self._get_execution_data("cut_position", (0, 0))
            
            # Insert the cut text back
            self.editor.set_selection(cut_position[0], cut_position[0])
            self.editor.replace_selection(cut_text)
            
            # Restore selection
            self.editor.set_selection(cut_position[0], cut_position[1])
            
            return True
            
        except Exception:
            return False
    
    def get_name(self) -> str:
        return "Cut"
    
    def get_description(self) -> str:
        return "Cut selected text to clipboard"
    
    def get_category(self) -> str:
        return CommandCategory.EDIT.value
    
    def get_shortcut(self) -> Optional[str]:
        return "ctrl+x"
    
    def can_execute(self, *args: Any, **kwargs: Any) -> bool:
        """Can execute if there's selected text."""
        return (super().can_execute(*args, **kwargs) and 
                bool(self.editor.get_selected_text()))


class CopyCommand(EditorCommand):
    """Copy selected text to clipboard."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute copy command."""
        try:
            selected_text = self.editor.get_selected_text()
            
            if not selected_text:
                return False  # Nothing to copy
            
            # Store in application state (clipboard simulation)
            self.context.application_state["clipboard"] = selected_text
            
            self._mark_executed(can_undo=False)  # Copy doesn't change content
            
            return True
            
        except Exception as e:
            raise CommandError(f"Failed to copy text: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Copy command cannot be undone."""
        return False
    
    def get_name(self) -> str:
        return "Copy"
    
    def get_description(self) -> str:
        return "Copy selected text to clipboard"
    
    def get_category(self) -> str:
        return CommandCategory.EDIT.value
    
    def get_shortcut(self) -> Optional[str]:
        return "ctrl+c"
    
    def can_execute(self, *args: Any, **kwargs: Any) -> bool:
        """Can execute if there's selected text."""
        return (super().can_execute(*args, **kwargs) and 
                bool(self.editor.get_selected_text()))


class PasteCommand(EditorCommand):
    """Paste text from clipboard."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute paste command."""
        try:
            # Get text from clipboard (application state)
            clipboard_text = self.context.application_state.get("clipboard", "")
            
            if not clipboard_text:
                return False  # Nothing to paste
            
            # Store state for undo
            selection_range = self.editor.get_selection()
            old_selected_text = self.editor.get_selected_text()
            
            self._store_execution_data("paste_text", clipboard_text)
            self._store_execution_data("old_selection", selection_range)
            self._store_execution_data("old_selected_text", old_selected_text)
            
            # Replace selection with clipboard content
            self.editor.replace_selection(clipboard_text)
            
            # Emit text change event
            event = TextChangedEvent(
                content=self.editor.get_content(),
                change_type="insert",
                position=selection_range[0],
                length=len(clipboard_text)
            )
            self._emit_event(event)
            
            self._mark_executed(can_undo=True)
            
            return True
            
        except Exception as e:
            raise CommandError(f"Failed to paste text: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Undo paste operation."""
        if not self.can_undo():
            return False
        
        try:
            paste_text = self._get_execution_data("paste_text", "")
            old_selection = self._get_execution_data("old_selection", (0, 0))
            old_selected_text = self._get_execution_data("old_selected_text", "")
            
            # Calculate where the pasted text ends
            paste_end = old_selection[0] + len(paste_text)
            
            # Select the pasted text and replace with original
            self.editor.set_selection(old_selection[0], paste_end)
            self.editor.replace_selection(old_selected_text)
            
            # Restore original selection
            if old_selected_text:
                self.editor.set_selection(old_selection[0], old_selection[1])
            
            return True
            
        except Exception:
            return False
    
    def get_name(self) -> str:
        return "Paste"
    
    def get_description(self) -> str:
        return "Paste text from clipboard"
    
    def get_category(self) -> str:
        return CommandCategory.EDIT.value
    
    def get_shortcut(self) -> Optional[str]:
        return "ctrl+v"
    
    def can_execute(self, *args: Any, **kwargs: Any) -> bool:
        """Can execute if there's content in clipboard."""
        return (super().can_execute(*args, **kwargs) and 
                bool(self.context.application_state.get("clipboard", "")))


class SelectAllCommand(EditorCommand):
    """Select all text in the editor."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute select all command."""
        try:
            # Store current selection for undo
            old_selection = self.editor.get_selection()
            self._store_execution_data("old_selection", old_selection)
            
            # Select all content
            content_length = len(self.editor.get_content())
            self.editor.set_selection(0, content_length)
            
            # Emit selection change event
            event = SelectionChangedEvent(
                start=0,
                end=content_length,
                selected_text=self.editor.get_content()
            )
            self._emit_event(event)
            
            self._mark_executed(can_undo=True)
            
            return True
            
        except Exception as e:
            raise CommandError(f"Failed to select all: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Restore previous selection."""
        if not self.can_undo():
            return False
        
        try:
            old_selection = self._get_execution_data("old_selection", (0, 0))
            self.editor.set_selection(old_selection[0], old_selection[1])
            
            return True
            
        except Exception:
            return False
    
    def get_name(self) -> str:
        return "Select All"
    
    def get_description(self) -> str:
        return "Select all text in the editor"
    
    def get_category(self) -> str:
        return CommandCategory.EDIT.value
    
    def get_shortcut(self) -> Optional[str]:
        return "ctrl+a"


class DuplicateLineCommand(EditorCommand):
    """Duplicate the current line or selected lines."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute duplicate line command."""
        try:
            cursor_pos = self.editor.get_cursor_position()
            current_line = cursor_pos[0]
            
            # Get current line text
            line_text = self.editor.get_line_text(current_line)
            
            # Store state for undo
            self._store_execution_data("duplicated_line", current_line)
            self._store_execution_data("line_text", line_text)
            self._store_execution_data("old_cursor", cursor_pos)
            
            # Find end of current line
            content = self.editor.get_content()
            lines = content.split('\n')
            
            if current_line < len(lines):
                # Calculate position to insert duplicate
                line_start = sum(len(line) + 1 for line in lines[:current_line])
                line_end = line_start + len(line_text)
                
                # Insert duplicate line after current line
                duplicate_text = '\n' + line_text
                self.editor.insert_text(line_end, duplicate_text)
                
                # Move cursor to duplicated line
                new_cursor_line = current_line + 1
                self.editor.set_cursor_position(new_cursor_line, cursor_pos[1])
                
                # Emit text change event
                event = TextChangedEvent(
                    content=self.editor.get_content(),
                    old_content=content,
                    change_type="insert",
                    position=line_end,
                    length=len(duplicate_text)
                )
                self._emit_event(event)
                
                self._mark_executed(can_undo=True)
                
                return True
            
            return False
            
        except Exception as e:
            raise CommandError(f"Failed to duplicate line: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Remove the duplicated line."""
        if not self.can_undo():
            return False
        
        try:
            duplicated_line = self._get_execution_data("duplicated_line", 0)
            line_text = self._get_execution_data("line_text", "")
            old_cursor = self._get_execution_data("old_cursor", (0, 0))
            
            # Calculate position of duplicated line (which is one line after original)
            content = self.editor.get_content()
            lines = content.split('\n')
            
            duplicate_line_index = duplicated_line + 1
            
            if duplicate_line_index < len(lines):
                # Calculate start and end positions of duplicated line
                line_start = sum(len(line) + 1 for line in lines[:duplicate_line_index])
                line_end = line_start + len(lines[duplicate_line_index])
                
                # Include the newline before the duplicated line
                if duplicate_line_index > 0:
                    line_start -= 1
                    line_end += 1 if duplicate_line_index < len(lines) - 1 else 0
                
                # Delete the duplicated line
                self.editor.delete_range(line_start, line_end)
                
                # Restore cursor position
                self.editor.set_cursor_position(old_cursor[0], old_cursor[1])
                
                return True
            
            return False
            
        except Exception:
            return False
    
    def get_name(self) -> str:
        return "Duplicate Line"
    
    def get_description(self) -> str:
        return "Duplicate the current line"
    
    def get_category(self) -> str:
        return CommandCategory.EDIT.value
    
    def get_shortcut(self) -> Optional[str]:
        return "ctrl+d"


class DeleteLineCommand(EditorCommand):
    """Delete the current line."""
    
    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute delete line command."""
        try:
            cursor_pos = self.editor.get_cursor_position()
            current_line = cursor_pos[0]
            
            # Get current line text for undo
            line_text = self.editor.get_line_text(current_line)
            
            # Store state for undo
            self._store_execution_data("deleted_line", current_line)
            self._store_execution_data("line_text", line_text)
            self._store_execution_data("old_cursor", cursor_pos)
            
            # Calculate line boundaries
            content = self.editor.get_content()
            lines = content.split('\n')
            
            if current_line < len(lines):
                # Calculate start and end positions of current line
                line_start = sum(len(line) + 1 for line in lines[:current_line])
                line_end = line_start + len(line_text)
                
                # Include newline character if not the last line
                if current_line < len(lines) - 1:
                    line_end += 1
                elif current_line > 0:
                    # If it's the last line, include the preceding newline
                    line_start -= 1
                
                # Delete the line
                deleted_text = self.editor.delete_range(line_start, line_end)
                
                # Adjust cursor position
                new_line = min(current_line, self.editor.get_line_count() - 1)
                new_line = max(0, new_line)
                self.editor.set_cursor_position(new_line, 0)
                
                # Emit text change event
                event = TextChangedEvent(
                    content=self.editor.get_content(),
                    old_content=content,
                    change_type="delete",
                    position=line_start,
                    length=len(deleted_text)
                )
                self._emit_event(event)
                
                self._mark_executed(can_undo=True)
                
                return True
            
            return False
            
        except Exception as e:
            raise CommandError(f"Failed to delete line: {e}", self.get_name(), e)
    
    def undo(self) -> bool:
        """Restore the deleted line."""
        if not self.can_undo():
            return False
        
        try:
            deleted_line = self._get_execution_data("deleted_line", 0)
            line_text = self._get_execution_data("line_text", "")
            old_cursor = self._get_execution_data("old_cursor", (0, 0))
            
            # Calculate insertion position
            current_line_count = self.editor.get_line_count()
            
            if deleted_line >= current_line_count:
                # Insert at end
                content = self.editor.get_content()
                if content and not content.endswith('\n'):
                    self.editor.insert_text(len(content), '\n' + line_text)
                else:
                    self.editor.insert_text(len(content), line_text)
            else:
                # Insert at the original position
                content = self.editor.get_content()
                lines = content.split('\n')
                insertion_pos = sum(len(line) + 1 for line in lines[:deleted_line])
                
                restore_text = line_text
                if deleted_line < len(lines):
                    restore_text += '\n'
                else:
                    restore_text = '\n' + restore_text
                
                self.editor.insert_text(insertion_pos, restore_text)
            
            # Restore cursor position
            self.editor.set_cursor_position(old_cursor[0], old_cursor[1])
            
            return True
            
        except Exception:
            return False
    
    def get_name(self) -> str:
        return "Delete Line"
    
    def get_description(self) -> str:
        return "Delete the current line"
    
    def get_category(self) -> str:
        return CommandCategory.EDIT.value
    
    def get_shortcut(self) -> Optional[str]:
        return "ctrl+shift+k"