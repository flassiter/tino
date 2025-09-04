"""
File operation commands for the tino editor.

Implements file-related commands including New, Open, Save, SaveAs,
Recent files, and quick file switching functionality.
"""

from pathlib import Path
from typing import Any

from ...core.events.types import FileClosedEvent, FileOpenedEvent, FileSavedEvent
from ...core.interfaces.command import CommandError
from .categories import CommandCategory
from .command_base import FileCommand


class NewFileCommand(FileCommand):
    """Create a new empty file."""

    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute new file command."""
        try:
            # Clear editor content
            if self.context.editor:
                self.context.editor.set_content("")
                self.context.editor.set_modified(False)
                self.context.editor.clear_undo_history()

            # Update application state
            self.context.current_file_path = None
            self.context.application_state["current_file"] = None

            # Store previous state for undo
            self._store_execution_data("previous_file", self.context.current_file_path)
            self._store_execution_data("previous_content", "")

            self._mark_executed(can_undo=False)  # New file can't be undone

            return True

        except Exception as e:
            raise CommandError(f"Failed to create new file: {e}", self.get_name(), e) from e

    def undo(self) -> bool:
        """New file command cannot be undone."""
        return False

    def get_name(self) -> str:
        return "New File"

    def get_description(self) -> str:
        return "Create a new empty file"

    def get_category(self) -> str:
        return CommandCategory.FILE.value

    def get_shortcut(self) -> str | None:
        return "ctrl+n"


class OpenFileCommand(FileCommand):
    """Open an existing file."""

    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute open file command."""
        file_path = kwargs.get("file_path") or (args[0] if args else None)

        if not file_path:
            raise CommandError("No file path provided", self.get_name())

        try:
            file_path = Path(file_path)

            # Validate file path
            is_valid, error_msg = self.file_manager.validate_file_path(file_path)
            if not is_valid:
                raise CommandError(f"Invalid file path: {error_msg}", self.get_name())

            # Check if file exists
            if not self.file_manager.file_exists(file_path):
                raise CommandError(f"File not found: {file_path}", self.get_name())

            # Store previous state for undo
            old_content = (
                self.context.editor.get_content() if self.context.editor else ""
            )
            old_file_path = self.context.current_file_path
            self._store_execution_data("previous_content", old_content)
            self._store_execution_data("previous_file", old_file_path)

            # Read file content
            content = self.file_manager.open_file(file_path)

            # Update editor
            if self.context.editor:
                self.context.editor.set_content(content)
                self.context.editor.set_modified(False)

                # Restore cursor position if remembered
                cursor_pos = self.file_manager.get_cursor_position(file_path)
                if cursor_pos:
                    self.context.editor.set_cursor_position(
                        cursor_pos[0], cursor_pos[1]
                    )

            # Update file manager state
            self.file_manager.add_recent_file(file_path)

            # Update application state
            self.context.current_file_path = str(file_path)
            self.context.application_state["current_file"] = str(file_path)

            # Emit event
            file_info = self.file_manager.get_file_info(file_path)
            event = FileOpenedEvent(
                file_path=file_path,
                encoding=file_info[2],
                size=file_info[0],
                modified=False,
            )
            self._emit_event(event)

            self._mark_executed(can_undo=True)

            return True

        except Exception as e:
            raise CommandError(
                f"Failed to open file {file_path}: {e}", self.get_name(), e
            ) from e

    def undo(self) -> bool:
        """Restore previous file state."""
        if not self.can_undo():
            return False

        try:
            previous_content = self._get_execution_data("previous_content", "")
            previous_file = self._get_execution_data("previous_file")

            if self.context.editor:
                self.context.editor.set_content(previous_content)
                self.context.editor.set_modified(False)

            self.context.current_file_path = previous_file
            self.context.application_state["current_file"] = previous_file

            return True

        except Exception:
            return False

    def get_name(self) -> str:
        return "Open File"

    def get_description(self) -> str:
        return "Open an existing file"

    def get_category(self) -> str:
        return CommandCategory.FILE.value

    def get_shortcut(self) -> str | None:
        return "ctrl+o"

    def validate_parameters(self, *args: Any, **kwargs: Any) -> str | None:
        """Validate file path parameter."""
        file_path = kwargs.get("file_path") or (args[0] if args else None)

        if not file_path:
            return "File path is required"

        try:
            Path(file_path)
        except Exception:
            return "Invalid file path format"

        return None


class SaveFileCommand(FileCommand):
    """Save the current file."""

    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute save file command."""
        if not self.context.current_file_path:
            # No current file, delegate to SaveAs
            save_as_cmd = SaveAsFileCommand(self.context)
            return save_as_cmd.execute(*args, **kwargs)

        try:
            file_path = Path(self.context.current_file_path)

            # Get content from editor
            content = ""
            if self.context.editor:
                content = self.context.editor.get_content()

                # Remember cursor position
                cursor_pos = self.context.editor.get_cursor_position()
                self.file_manager.set_cursor_position(
                    file_path, cursor_pos[0], cursor_pos[1]
                )

            # Store previous state for undo
            self._store_execution_data("file_path", str(file_path))

            # Create backup if this is first modification
            backup_created = False
            if self.context.editor and self.context.editor.is_modified():
                backup_path = self.file_manager.create_backup(file_path)
                backup_created = backup_path is not None

            # Save file
            success = self.file_manager.save_file(file_path, content)

            if success:
                # Update editor state
                if self.context.editor:
                    self.context.editor.set_modified(False)

                # Emit event
                file_info = self.file_manager.get_file_info(file_path)
                event = FileSavedEvent(
                    file_path=file_path,
                    size=file_info[0],
                    encoding=file_info[2],
                    backup_created=backup_created,
                )
                self._emit_event(event)

                self._mark_executed(can_undo=False)  # Save operations can't be undone

                return True

            return False

        except Exception as e:
            raise CommandError(f"Failed to save file: {e}", self.get_name(), e) from e

    def undo(self) -> bool:
        """Save command cannot be undone."""
        return False

    def get_name(self) -> str:
        return "Save File"

    def get_description(self) -> str:
        return "Save the current file"

    def get_category(self) -> str:
        return CommandCategory.FILE.value

    def get_shortcut(self) -> str | None:
        return "ctrl+s"

    def can_execute(self, *args: Any, **kwargs: Any) -> bool:
        """Can execute if editor exists and has content."""
        return super().can_execute(*args, **kwargs) and self.context.editor is not None


class SaveAsFileCommand(FileCommand):
    """Save the current file with a new name."""

    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute save as command."""
        file_path = kwargs.get("file_path") or (args[0] if args else None)

        if not file_path:
            raise CommandError("No file path provided for Save As", self.get_name())

        try:
            file_path = Path(file_path)

            # Validate file path
            is_valid, error_msg = self.file_manager.validate_file_path(file_path)
            if not is_valid:
                raise CommandError(f"Invalid file path: {error_msg}", self.get_name())

            # Get content from editor
            content = ""
            if self.context.editor:
                content = self.context.editor.get_content()

            # Store previous state for undo
            old_file_path = self.context.current_file_path
            self._store_execution_data("previous_file", old_file_path)

            # Save file
            success = self.file_manager.save_file(file_path, content)

            if success:
                # Update application state
                self.context.current_file_path = str(file_path)
                self.context.application_state["current_file"] = str(file_path)

                # Add to recent files
                self.file_manager.add_recent_file(file_path)

                # Update editor state
                if self.context.editor:
                    self.context.editor.set_modified(False)

                    # Remember cursor position
                    cursor_pos = self.context.editor.get_cursor_position()
                    self.file_manager.set_cursor_position(
                        file_path, cursor_pos[0], cursor_pos[1]
                    )

                # Emit event
                file_info = self.file_manager.get_file_info(file_path)
                event = FileSavedEvent(
                    file_path=file_path,
                    size=file_info[0],
                    encoding=file_info[2],
                    backup_created=False,
                )
                self._emit_event(event)

                self._mark_executed(can_undo=True)

                return True

            return False

        except Exception as e:
            raise CommandError(
                f"Failed to save file as {file_path}: {e}", self.get_name(), e
            ) from e

    def undo(self) -> bool:
        """Restore previous file path."""
        if not self.can_undo():
            return False

        try:
            previous_file = self._get_execution_data("previous_file")
            self.context.current_file_path = previous_file
            self.context.application_state["current_file"] = previous_file

            return True

        except Exception:
            return False

    def get_name(self) -> str:
        return "Save As"

    def get_description(self) -> str:
        return "Save the current file with a new name"

    def get_category(self) -> str:
        return CommandCategory.FILE.value

    def get_shortcut(self) -> str | None:
        return "ctrl+shift+s"

    def validate_parameters(self, *args: Any, **kwargs: Any) -> str | None:
        """Validate file path parameter."""
        file_path = kwargs.get("file_path") or (args[0] if args else None)

        if not file_path:
            return "File path is required"

        try:
            Path(file_path)
        except Exception:
            return "Invalid file path format"

        return None


class RecentFilesCommand(FileCommand):
    """Show recent files list."""

    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute recent files command."""
        try:
            limit = kwargs.get("limit", 30)
            recent_files = self.file_manager.get_recent_files(limit)

            # Store in application state for UI to use
            self.context.application_state["recent_files"] = [
                str(p) for p in recent_files
            ]
            self.context.application_state["show_recent_files_dialog"] = True

            self._mark_executed(can_undo=False)  # UI action, no undo needed

            return True

        except Exception as e:
            raise CommandError(f"Failed to get recent files: {e}", self.get_name(), e) from e

    def undo(self) -> bool:
        """Recent files command cannot be undone."""
        return False

    def get_name(self) -> str:
        return "Recent Files"

    def get_description(self) -> str:
        return "Show list of recently opened files"

    def get_category(self) -> str:
        return CommandCategory.FILE.value

    def get_shortcut(self) -> str | None:
        return "ctrl+r"


class LastFileCommand(FileCommand):
    """Switch to the last opened file (quick file switching)."""

    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute last file switch command."""
        try:
            last_file = self.file_manager.get_last_file()

            if not last_file:
                # No last file available
                return False

            # Use OpenFileCommand to open the last file
            open_cmd = OpenFileCommand(self.context)
            return open_cmd.execute(file_path=str(last_file))

        except Exception as e:
            raise CommandError(
                f"Failed to switch to last file: {e}", self.get_name(), e
            ) from e

    def undo(self) -> bool:
        """Undo by switching back (if possible)."""
        # This would require more complex state management
        # For now, return False as it's primarily a navigation command
        return False

    def get_name(self) -> str:
        return "Last File"

    def get_description(self) -> str:
        return "Switch to the last opened file"

    def get_category(self) -> str:
        return CommandCategory.FILE.value

    def get_shortcut(self) -> str | None:
        return "ctrl+tab"

    def can_execute(self, *args: Any, **kwargs: Any) -> bool:
        """Can execute if there's a last file available."""
        try:
            return (
                super().can_execute(*args, **kwargs)
                and self.file_manager.get_last_file() is not None
            )
        except Exception:
            return False


class CloseFileCommand(FileCommand):
    """Close the current file."""

    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute close file command."""
        try:
            current_file = self.context.current_file_path

            # Store current state for undo
            old_content = ""
            was_modified = False
            if self.context.editor:
                old_content = self.context.editor.get_content()
                was_modified = self.context.editor.is_modified()

                # Remember cursor position if file is saved
                if current_file and not was_modified:
                    cursor_pos = self.context.editor.get_cursor_position()
                    self.file_manager.set_cursor_position(
                        Path(current_file), cursor_pos[0], cursor_pos[1]
                    )

            self._store_execution_data("previous_file", current_file)
            self._store_execution_data("previous_content", old_content)
            self._store_execution_data("was_modified", was_modified)

            # Clear editor
            if self.context.editor:
                self.context.editor.set_content("")
                self.context.editor.set_modified(False)
                self.context.editor.clear_undo_history()

            # Emit close event
            if current_file:
                event = FileClosedEvent(
                    file_path=Path(current_file),
                    was_modified=was_modified,
                    saved=not was_modified,
                )
                self._emit_event(event)

            # Update application state
            self.context.current_file_path = None
            self.context.application_state["current_file"] = None

            self._mark_executed(can_undo=True)

            return True

        except Exception as e:
            raise CommandError(f"Failed to close file: {e}", self.get_name(), e) from e

    def undo(self) -> bool:
        """Restore the closed file."""
        if not self.can_undo():
            return False

        try:
            previous_file = self._get_execution_data("previous_file")
            previous_content = self._get_execution_data("previous_content", "")
            was_modified = self._get_execution_data("was_modified", False)

            if self.context.editor:
                self.context.editor.set_content(previous_content)
                self.context.editor.set_modified(was_modified)

            self.context.current_file_path = previous_file
            self.context.application_state["current_file"] = previous_file

            return True

        except Exception:
            return False

    def get_name(self) -> str:
        return "Close File"

    def get_description(self) -> str:
        return "Close the current file"

    def get_category(self) -> str:
        return CommandCategory.FILE.value

    def get_shortcut(self) -> str | None:
        return "ctrl+w"

    def requires_confirmation(self) -> bool:
        """Require confirmation if file is modified."""
        if self.context.editor:
            return self.context.editor.is_modified()
        return False

    def get_confirmation_message(self) -> str:
        """Get confirmation message for unsaved changes."""
        if self.context.current_file_path:
            filename = Path(self.context.current_file_path).name
            return f"Close '{filename}' without saving changes?"
        return "Close file without saving changes?"
