"""
Keybinding manager for mapping keyboard shortcuts to commands.

Provides Windows-standard keyboard shortcuts with user customization support,
conflict detection, and resolution.
"""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass

from ...core.events.bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class KeyBinding:
    """Represents a keyboard shortcut binding."""

    shortcut: str
    command_name: str
    description: str = ""
    context: str = "global"  # "global", "editor", "preview", etc.
    user_defined: bool = False

    def __post_init__(self) -> None:
        """Normalize shortcut format."""
        self.shortcut = self._normalize_shortcut(self.shortcut)

    def _normalize_shortcut(self, shortcut: str) -> str:
        """
        Normalize keyboard shortcut format.

        Converts various formats to standard lowercase with + separators.
        """
        # First, replace common separators with +, keeping case
        normalized = re.sub(r"[-_\s]+", "+", shortcut)

        # Convert to lowercase after separating
        normalized = normalized.lower()

        # Split on + to handle each part
        parts = [part.strip() for part in normalized.split("+") if part.strip()]

        modifiers = []
        key = ""

        for part in parts:
            if part in ("ctrl", "control"):
                if "ctrl" not in modifiers:
                    modifiers.append("ctrl")
            elif part in ("alt", "meta"):
                if "alt" not in modifiers:
                    modifiers.append("alt")
            elif part in ("shift",):
                if "shift" not in modifiers:
                    modifiers.append("shift")
            else:
                key = part

        # Sort modifiers for consistency
        modifier_order = {"ctrl": 1, "alt": 2, "shift": 3}
        modifiers.sort(key=lambda x: modifier_order.get(x, 4))

        if key:
            modifiers.append(key)

        return "+".join(modifiers)

    def matches_input(self, input_shortcut: str) -> bool:
        """Check if this binding matches the input shortcut."""
        return self.shortcut == self._normalize_shortcut(input_shortcut)


class KeybindingManager:
    """
    Manages keyboard shortcuts and their mapping to commands.

    Provides Windows-standard defaults with user customization support,
    conflict detection, and context-aware binding resolution.
    """

    def __init__(self, event_bus: EventBus | None = None):
        """
        Initialize keybinding manager.

        Args:
            event_bus: Event bus for keybinding events
        """
        self._event_bus = event_bus

        # Keybinding storage
        self._bindings: dict[str, KeyBinding] = {}  # shortcut -> binding
        self._command_shortcuts: dict[str, set[str]] = defaultdict(
            set
        )  # command -> shortcuts
        self._context_bindings: dict[str, dict[str, KeyBinding]] = defaultdict(dict)

        # Conflict tracking
        self._conflicts: dict[str, list[KeyBinding]] = defaultdict(list)

        # Load default bindings
        self._load_default_bindings()

    def bind_key(
        self,
        shortcut: str,
        command_name: str,
        description: str = "",
        context: str = "global",
    ) -> bool:
        """
        Bind a keyboard shortcut to a command.

        Args:
            shortcut: Keyboard shortcut (e.g., "ctrl+s")
            command_name: Name of command to execute
            description: Optional description
            context: Context where binding is active

        Returns:
            True if binding was successful, False if conflict exists
        """
        binding = KeyBinding(
            shortcut=shortcut,
            command_name=command_name,
            description=description,
            context=context,
            user_defined=True,
        )

        # Check for conflicts
        if self._has_conflict(binding):
            logger.warning(f"Keybinding conflict for {shortcut} in context {context}")
            self._conflicts[shortcut].append(binding)
            return False

        # Remove any existing binding for this shortcut in this context
        self.unbind_key(shortcut, context)

        # Add new binding
        self._bindings[f"{context}:{shortcut}"] = binding
        self._command_shortcuts[command_name].add(shortcut)
        self._context_bindings[context][shortcut] = binding

        logger.debug(f"Bound {shortcut} to {command_name} in {context}")
        return True

    def unbind_key(self, shortcut: str, context: str = "global") -> bool:
        """
        Remove a keyboard shortcut binding.

        Args:
            shortcut: Keyboard shortcut to unbind
            context: Context to unbind from

        Returns:
            True if binding was removed, False if not found
        """
        binding_key = f"{context}:{shortcut}"

        if binding_key not in self._bindings:
            return False

        binding = self._bindings.pop(binding_key)
        self._command_shortcuts[binding.command_name].discard(shortcut)
        self._context_bindings[context].pop(shortcut, None)

        # Clean up empty sets
        if not self._command_shortcuts[binding.command_name]:
            del self._command_shortcuts[binding.command_name]

        logger.debug(f"Unbound {shortcut} from {binding.command_name} in {context}")
        return True

    def get_command_for_shortcut(
        self, shortcut: str, context: str = "global"
    ) -> str | None:
        """
        Get the command bound to a keyboard shortcut.

        Args:
            shortcut: Keyboard shortcut
            context: Context to search in

        Returns:
            Command name or None if no binding found
        """
        # Check specific context first
        binding_key = f"{context}:{shortcut}"
        if binding_key in self._bindings:
            return self._bindings[binding_key].command_name

        # Fall back to global context if not global already
        if context != "global":
            global_key = f"global:{shortcut}"
            if global_key in self._bindings:
                return self._bindings[global_key].command_name

        return None

    def get_shortcuts_for_command(self, command_name: str) -> list[str]:
        """
        Get all shortcuts bound to a command.

        Args:
            command_name: Command name

        Returns:
            List of keyboard shortcuts for the command
        """
        return list(self._command_shortcuts.get(command_name, set()))

    def get_primary_shortcut(self, command_name: str) -> str | None:
        """
        Get the primary (first) shortcut for a command.

        Args:
            command_name: Command name

        Returns:
            Primary keyboard shortcut or None
        """
        shortcuts = self.get_shortcuts_for_command(command_name)
        return shortcuts[0] if shortcuts else None

    def get_all_bindings(self, context: str = None) -> list[KeyBinding]:
        """
        Get all keybindings, optionally filtered by context.

        Args:
            context: Optional context filter

        Returns:
            List of keybindings
        """
        if context:
            return list(self._context_bindings.get(context, {}).values())

        return list(self._bindings.values())

    def get_conflicts(self) -> dict[str, list[KeyBinding]]:
        """Get all keybinding conflicts."""
        return dict(self._conflicts)

    def resolve_conflict(self, shortcut: str, preferred_command: str) -> bool:
        """
        Resolve a keybinding conflict by choosing a preferred command.

        Args:
            shortcut: Conflicting shortcut
            preferred_command: Command to bind the shortcut to

        Returns:
            True if conflict was resolved
        """
        if shortcut not in self._conflicts:
            return False

        conflicts = self._conflicts[shortcut]
        preferred_binding = None

        # Find the preferred binding
        for binding in conflicts:
            if binding.command_name == preferred_command:
                preferred_binding = binding
                break

        if not preferred_binding:
            return False

        # Remove conflict and bind the preferred command
        del self._conflicts[shortcut]

        # First unbind any existing binding
        self.unbind_key(shortcut, preferred_binding.context)

        return self.bind_key(
            preferred_binding.shortcut,
            preferred_binding.command_name,
            preferred_binding.description,
            preferred_binding.context,
        )

    def import_config(self, config: dict[str, str]) -> list[str]:
        """
        Import keybindings from configuration.

        Args:
            config: Dictionary mapping shortcuts to command names

        Returns:
            List of error messages for failed bindings
        """
        errors = []

        for shortcut, command_name in config.items():
            try:
                # Validate shortcut format first
                is_valid, validation_error = self.validate_shortcut(shortcut)
                if not is_valid:
                    errors.append(f"Invalid shortcut '{shortcut}': {validation_error}")
                    continue

                # Force bind by first unbinding any existing binding
                self.unbind_key(shortcut, "global")
                if not self.bind_key(shortcut, command_name, context="global"):
                    errors.append(f"Failed to bind {shortcut} to {command_name}")
            except Exception as e:
                errors.append(f"Error binding {shortcut} to {command_name}: {e}")

        return errors

    def export_config(self, include_defaults: bool = False) -> dict[str, str]:
        """
        Export keybindings to configuration format.

        Args:
            include_defaults: Whether to include default bindings

        Returns:
            Dictionary mapping shortcuts to command names
        """
        config = {}

        for binding in self._bindings.values():
            if include_defaults or binding.user_defined:
                config[binding.shortcut] = binding.command_name

        return config

    def validate_shortcut(self, shortcut: str) -> tuple[bool, str]:
        """
        Validate a keyboard shortcut format.

        Args:
            shortcut: Shortcut to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # First check for obvious format issues
            if not shortcut.strip():
                return False, "Shortcut cannot be empty"

            if shortcut.endswith("+") or shortcut.endswith("-"):
                return False, "Shortcut must end with a key"

            # Parse original parts before normalization
            original_parts = re.split(r"[-_\s+]+", shortcut.lower())
            original_parts = [part.strip() for part in original_parts if part.strip()]

            if len(original_parts) == 0:
                return False, "Shortcut must contain at least one key"

            # Check for invalid modifiers before normalization
            valid_modifiers = {"ctrl", "control", "alt", "meta", "shift"}
            for _i, part in enumerate(
                original_parts[:-1]
            ):  # All but last should be modifiers
                if part not in valid_modifiers:
                    return False, f"Invalid modifier: {part}"

            # Check key name
            key = original_parts[-1]
            if len(key) == 0:
                return False, "Shortcut must end with a key"
            if len(key) > 20:  # Reasonable limit
                return False, "Key name too long"

            # Try normalization to catch other issues
            normalized = KeyBinding("", "")._normalize_shortcut(shortcut)
            if not normalized:
                return False, "Failed to normalize shortcut"

            return True, ""

        except Exception as e:
            return False, f"Invalid shortcut format: {e}"

    def _has_conflict(self, new_binding: KeyBinding) -> bool:
        """Check if a binding would create a conflict."""
        key = f"{new_binding.context}:{new_binding.shortcut}"

        # Check exact match in same context
        if key in self._bindings:
            existing = self._bindings[key]
            return existing.command_name != new_binding.command_name

        return False

    def _load_default_bindings(self) -> None:
        """Load Windows-standard default keybindings."""
        defaults = [
            # File operations
            ("ctrl+n", "file.new", "New file"),
            ("ctrl+o", "file.open", "Open file"),
            ("ctrl+s", "file.save", "Save file"),
            ("ctrl+shift+s", "file.save_as", "Save file as"),
            ("ctrl+r", "file.recent", "Recent files"),
            ("ctrl+tab", "file.last", "Switch to last file"),
            ("ctrl+q", "file.quit", "Quit application"),
            # Edit operations
            ("ctrl+z", "edit.undo", "Undo"),
            ("ctrl+y", "edit.redo", "Redo"),
            ("ctrl+x", "edit.cut", "Cut"),
            ("ctrl+c", "edit.copy", "Copy"),
            ("ctrl+v", "edit.paste", "Paste"),
            ("ctrl+a", "edit.select_all", "Select all"),
            ("ctrl+d", "edit.duplicate_line", "Duplicate line"),
            # Format operations (Markdown)
            ("ctrl+b", "format.bold", "Bold text"),
            ("ctrl+i", "format.italic", "Italic text"),
            ("ctrl+k", "format.link", "Insert link"),
            ("ctrl+shift+c", "format.code", "Inline code"),
            # Navigation
            ("ctrl+f", "navigation.find", "Find text"),
            ("ctrl+h", "navigation.replace", "Replace text"),
            ("ctrl+g", "navigation.goto_line", "Go to line"),
            ("f3", "navigation.find_next", "Find next"),
            ("shift+f3", "navigation.find_previous", "Find previous"),
            # View
            ("f2", "view.toggle_preview", "Toggle preview"),
            ("f11", "view.preview_only", "Preview only mode"),
            ("ctrl+shift+p", "view.command_palette", "Command palette"),
            ("f1", "view.help", "Help"),
            ("ctrl+comma", "view.settings", "Settings"),
        ]

        for shortcut, command, description in defaults:
            binding = KeyBinding(
                shortcut=shortcut,
                command_name=command,
                description=description,
                context="global",
                user_defined=False,
            )

            key = f"global:{binding.shortcut}"
            self._bindings[key] = binding
            self._command_shortcuts[command].add(binding.shortcut)
            self._context_bindings["global"][binding.shortcut] = binding

        logger.debug(f"Loaded {len(defaults)} default keybindings")
