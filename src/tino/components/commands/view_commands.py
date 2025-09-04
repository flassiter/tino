"""
View and UI commands for the tino editor.

Implements view-related commands including TogglePreview, ToggleLineNumbers,
theme switching, and other UI control commands.
"""

from typing import Any

from ...core.interfaces.command import CommandError
from .categories import CommandCategory
from .command_base import BaseCommand


class TogglePreviewCommand(BaseCommand):
    """Toggle the markdown preview pane."""

    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute toggle preview command."""
        try:
            # Get current preview state
            preview_visible = self.context.application_state.get(
                "preview_visible", True
            )

            # Store old state for undo
            self._store_execution_data("old_preview_state", preview_visible)

            # Toggle state
            new_state = not preview_visible
            self.context.application_state["preview_visible"] = new_state

            # Store action for UI
            self.context.application_state["ui_action"] = "toggle_preview"
            self.context.application_state["ui_action_data"] = {"visible": new_state}

            self._mark_executed(can_undo=True)

            return True

        except Exception as e:
            raise CommandError(f"Failed to toggle preview: {e}", self.get_name(), e) from e

    def undo(self) -> bool:
        """Restore previous preview state."""
        if not self.can_undo():
            return False

        try:
            old_state = self._get_execution_data("old_preview_state", True)
            self.context.application_state["preview_visible"] = old_state

            # Trigger UI update
            self.context.application_state["ui_action"] = "toggle_preview"
            self.context.application_state["ui_action_data"] = {"visible": old_state}

            return True

        except Exception:
            return False

    def get_name(self) -> str:
        return "Toggle Preview"

    def get_description(self) -> str:
        return "Toggle the markdown preview pane"

    def get_category(self) -> str:
        return CommandCategory.VIEW.value

    def get_shortcut(self) -> str | None:
        return "f2"


class ToggleLineNumbersCommand(BaseCommand):
    """Toggle line number display."""

    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute toggle line numbers command."""
        try:
            # Get current line numbers state
            line_numbers_visible = self.context.application_state.get(
                "line_numbers_visible", True
            )

            # Store old state for undo
            self._store_execution_data("old_line_numbers_state", line_numbers_visible)

            # Toggle state
            new_state = not line_numbers_visible
            self.context.application_state["line_numbers_visible"] = new_state

            # Store action for UI
            self.context.application_state["ui_action"] = "toggle_line_numbers"
            self.context.application_state["ui_action_data"] = {"visible": new_state}

            self._mark_executed(can_undo=True)

            return True

        except Exception as e:
            raise CommandError(
                f"Failed to toggle line numbers: {e}", self.get_name(), e
            )

    def undo(self) -> bool:
        """Restore previous line numbers state."""
        if not self.can_undo():
            return False

        try:
            old_state = self._get_execution_data("old_line_numbers_state", True)
            self.context.application_state["line_numbers_visible"] = old_state

            # Trigger UI update
            self.context.application_state["ui_action"] = "toggle_line_numbers"
            self.context.application_state["ui_action_data"] = {"visible": old_state}

            return True

        except Exception:
            return False

    def get_name(self) -> str:
        return "Toggle Line Numbers"

    def get_description(self) -> str:
        return "Toggle line number display in editor"

    def get_category(self) -> str:
        return CommandCategory.VIEW.value


class PreviewOnlyCommand(BaseCommand):
    """Show preview only mode (hide editor)."""

    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute preview only command."""
        try:
            # Store current layout state
            old_layout = {
                "editor_visible": self.context.application_state.get(
                    "editor_visible", True
                ),
                "preview_visible": self.context.application_state.get(
                    "preview_visible", True
                ),
                "layout_mode": self.context.application_state.get(
                    "layout_mode", "split"
                ),
            }
            self._store_execution_data("old_layout", old_layout)

            # Set preview only mode
            self.context.application_state.update(
                {
                    "editor_visible": False,
                    "preview_visible": True,
                    "layout_mode": "preview_only",
                }
            )

            # Store action for UI
            self.context.application_state["ui_action"] = "layout_change"
            self.context.application_state["ui_action_data"] = {"mode": "preview_only"}

            self._mark_executed(can_undo=True)

            return True

        except Exception as e:
            raise CommandError(
                f"Failed to switch to preview only: {e}", self.get_name(), e
            )

    def undo(self) -> bool:
        """Restore previous layout."""
        if not self.can_undo():
            return False

        try:
            old_layout = self._get_execution_data("old_layout", {})
            self.context.application_state.update(old_layout)

            # Trigger UI update
            self.context.application_state["ui_action"] = "layout_change"
            self.context.application_state["ui_action_data"] = {
                "mode": old_layout.get("layout_mode", "split")
            }

            return True

        except Exception:
            return False

    def get_name(self) -> str:
        return "Preview Only"

    def get_description(self) -> str:
        return "Show preview only (hide editor)"

    def get_category(self) -> str:
        return CommandCategory.VIEW.value

    def get_shortcut(self) -> str | None:
        return "f11"


class ToggleThemeCommand(BaseCommand):
    """Toggle between dark and light themes."""

    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute toggle theme command."""
        try:
            # Get current theme
            current_theme = self.context.application_state.get("theme", "dark")

            # Store old theme for undo
            self._store_execution_data("old_theme", current_theme)

            # Toggle theme
            new_theme = "light" if current_theme == "dark" else "dark"
            self.context.application_state["theme"] = new_theme

            # Store action for UI
            self.context.application_state["ui_action"] = "theme_change"
            self.context.application_state["ui_action_data"] = {"theme": new_theme}

            self._mark_executed(can_undo=True)

            return True

        except Exception as e:
            raise CommandError(f"Failed to toggle theme: {e}", self.get_name(), e) from e

    def undo(self) -> bool:
        """Restore previous theme."""
        if not self.can_undo():
            return False

        try:
            old_theme = self._get_execution_data("old_theme", "dark")
            self.context.application_state["theme"] = old_theme

            # Trigger UI update
            self.context.application_state["ui_action"] = "theme_change"
            self.context.application_state["ui_action_data"] = {"theme": old_theme}

            return True

        except Exception:
            return False

    def get_name(self) -> str:
        return "Toggle Theme"

    def get_description(self) -> str:
        return "Toggle between dark and light themes"

    def get_category(self) -> str:
        return CommandCategory.VIEW.value


class CommandPaletteCommand(BaseCommand):
    """Show the command palette."""

    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute command palette command."""
        try:
            # Store action for UI
            self.context.application_state["ui_action"] = "show_command_palette"
            self.context.application_state["ui_action_data"] = {"visible": True}

            self._mark_executed(can_undo=False)  # UI action, no undo needed

            return True

        except Exception as e:
            raise CommandError(
                f"Failed to show command palette: {e}", self.get_name(), e
            )

    def undo(self) -> bool:
        """Command palette cannot be undone."""
        return False

    def get_name(self) -> str:
        return "Command Palette"

    def get_description(self) -> str:
        return "Show the command palette"

    def get_category(self) -> str:
        return CommandCategory.VIEW.value

    def get_shortcut(self) -> str | None:
        return "ctrl+shift+p"


class ShowSettingsCommand(BaseCommand):
    """Show the settings dialog."""

    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute show settings command."""
        try:
            # Store action for UI
            self.context.application_state["ui_action"] = "show_settings"
            self.context.application_state["ui_action_data"] = {"visible": True}

            self._mark_executed(can_undo=False)  # UI action, no undo needed

            return True

        except Exception as e:
            raise CommandError(f"Failed to show settings: {e}", self.get_name(), e) from e

    def undo(self) -> bool:
        """Settings dialog cannot be undone."""
        return False

    def get_name(self) -> str:
        return "Settings"

    def get_description(self) -> str:
        return "Show the settings dialog"

    def get_category(self) -> str:
        return CommandCategory.VIEW.value

    def get_shortcut(self) -> str | None:
        return "ctrl+comma"


class ShowHelpCommand(BaseCommand):
    """Show the help screen."""

    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute show help command."""
        try:
            # Store action for UI
            self.context.application_state["ui_action"] = "show_help"
            self.context.application_state["ui_action_data"] = {"visible": True}

            self._mark_executed(can_undo=False)  # UI action, no undo needed

            return True

        except Exception as e:
            raise CommandError(f"Failed to show help: {e}", self.get_name(), e) from e

    def undo(self) -> bool:
        """Help screen cannot be undone."""
        return False

    def get_name(self) -> str:
        return "Help"

    def get_description(self) -> str:
        return "Show the help screen"

    def get_category(self) -> str:
        return CommandCategory.HELP.value

    def get_shortcut(self) -> str | None:
        return "f1"


class ToggleWordWrapCommand(BaseCommand):
    """Toggle word wrap in the editor."""

    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute toggle word wrap command."""
        try:
            # Get current word wrap state
            word_wrap_enabled = self.context.application_state.get(
                "word_wrap_enabled", True
            )

            # Store old state for undo
            self._store_execution_data("old_word_wrap_state", word_wrap_enabled)

            # Toggle state
            new_state = not word_wrap_enabled
            self.context.application_state["word_wrap_enabled"] = new_state

            # Store action for UI
            self.context.application_state["ui_action"] = "toggle_word_wrap"
            self.context.application_state["ui_action_data"] = {"enabled": new_state}

            self._mark_executed(can_undo=True)

            return True

        except Exception as e:
            raise CommandError(f"Failed to toggle word wrap: {e}", self.get_name(), e) from e

    def undo(self) -> bool:
        """Restore previous word wrap state."""
        if not self.can_undo():
            return False

        try:
            old_state = self._get_execution_data("old_word_wrap_state", True)
            self.context.application_state["word_wrap_enabled"] = old_state

            # Trigger UI update
            self.context.application_state["ui_action"] = "toggle_word_wrap"
            self.context.application_state["ui_action_data"] = {"enabled": old_state}

            return True

        except Exception:
            return False

    def get_name(self) -> str:
        return "Toggle Word Wrap"

    def get_description(self) -> str:
        return "Toggle word wrap in the editor"

    def get_category(self) -> str:
        return CommandCategory.VIEW.value

    def get_shortcut(self) -> str | None:
        return "alt+z"


class ToggleStatusBarCommand(BaseCommand):
    """Toggle the status bar visibility."""

    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute toggle status bar command."""
        try:
            # Get current status bar state
            status_bar_visible = self.context.application_state.get(
                "status_bar_visible", True
            )

            # Store old state for undo
            self._store_execution_data("old_status_bar_state", status_bar_visible)

            # Toggle state
            new_state = not status_bar_visible
            self.context.application_state["status_bar_visible"] = new_state

            # Store action for UI
            self.context.application_state["ui_action"] = "toggle_status_bar"
            self.context.application_state["ui_action_data"] = {"visible": new_state}

            self._mark_executed(can_undo=True)

            return True

        except Exception as e:
            raise CommandError(f"Failed to toggle status bar: {e}", self.get_name(), e) from e

    def undo(self) -> bool:
        """Restore previous status bar state."""
        if not self.can_undo():
            return False

        try:
            old_state = self._get_execution_data("old_status_bar_state", True)
            self.context.application_state["status_bar_visible"] = old_state

            # Trigger UI update
            self.context.application_state["ui_action"] = "toggle_status_bar"
            self.context.application_state["ui_action_data"] = {"visible": old_state}

            return True

        except Exception:
            return False

    def get_name(self) -> str:
        return "Toggle Status Bar"

    def get_description(self) -> str:
        return "Toggle the status bar visibility"

    def get_category(self) -> str:
        return CommandCategory.VIEW.value


class ZoomInCommand(BaseCommand):
    """Increase editor font size."""

    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute zoom in command."""
        try:
            # Get current font size
            current_size = self.context.application_state.get("font_size", 14)

            # Store old size for undo
            self._store_execution_data("old_font_size", current_size)

            # Increase font size (max 32)
            new_size = min(32, current_size + 1)
            self.context.application_state["font_size"] = new_size

            # Store action for UI
            self.context.application_state["ui_action"] = "font_size_change"
            self.context.application_state["ui_action_data"] = {"size": new_size}

            self._mark_executed(can_undo=True)

            return new_size != current_size  # Only successful if size actually changed

        except Exception as e:
            raise CommandError(f"Failed to zoom in: {e}", self.get_name(), e) from e

    def undo(self) -> bool:
        """Restore previous font size."""
        if not self.can_undo():
            return False

        try:
            old_size = self._get_execution_data("old_font_size", 14)
            self.context.application_state["font_size"] = old_size

            # Trigger UI update
            self.context.application_state["ui_action"] = "font_size_change"
            self.context.application_state["ui_action_data"] = {"size": old_size}

            return True

        except Exception:
            return False

    def get_name(self) -> str:
        return "Zoom In"

    def get_description(self) -> str:
        return "Increase editor font size"

    def get_category(self) -> str:
        return CommandCategory.VIEW.value

    def get_shortcut(self) -> str | None:
        return "ctrl+plus"


class ZoomOutCommand(BaseCommand):
    """Decrease editor font size."""

    def execute(self, *args: Any, **kwargs: Any) -> bool:
        """Execute zoom out command."""
        try:
            # Get current font size
            current_size = self.context.application_state.get("font_size", 14)

            # Store old size for undo
            self._store_execution_data("old_font_size", current_size)

            # Decrease font size (min 8)
            new_size = max(8, current_size - 1)
            self.context.application_state["font_size"] = new_size

            # Store action for UI
            self.context.application_state["ui_action"] = "font_size_change"
            self.context.application_state["ui_action_data"] = {"size": new_size}

            self._mark_executed(can_undo=True)

            return new_size != current_size  # Only successful if size actually changed

        except Exception as e:
            raise CommandError(f"Failed to zoom out: {e}", self.get_name(), e) from e

    def undo(self) -> bool:
        """Restore previous font size."""
        if not self.can_undo():
            return False

        try:
            old_size = self._get_execution_data("old_font_size", 14)
            self.context.application_state["font_size"] = old_size

            # Trigger UI update
            self.context.application_state["ui_action"] = "font_size_change"
            self.context.application_state["ui_action_data"] = {"size": old_size}

            return True

        except Exception:
            return False

    def get_name(self) -> str:
        return "Zoom Out"

    def get_description(self) -> str:
        return "Decrease editor font size"

    def get_category(self) -> str:
        return CommandCategory.VIEW.value

    def get_shortcut(self) -> str | None:
        return "ctrl+minus"
