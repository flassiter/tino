"""
Tests for keybinding manager functionality.

Tests keyboard shortcut management, binding resolution, conflict detection,
and customization through the KeybindingManager class.
"""

import pytest
from unittest.mock import Mock

from src.tino.components.commands.keybindings import KeybindingManager, KeyBinding
from src.tino.core.events.bus import EventBus


class TestKeyBinding:
    """Test KeyBinding dataclass functionality."""
    
    def test_keybinding_creation(self):
        """Test creating a keybinding."""
        binding = KeyBinding(
            shortcut="ctrl+s",
            command_name="file.save",
            description="Save file",
            context="global"
        )
        
        assert binding.shortcut == "ctrl+s"
        assert binding.command_name == "file.save"
        assert binding.description == "Save file"
        assert binding.context == "global"
        assert not binding.user_defined  # Default value
    
    def test_shortcut_normalization(self):
        """Test keyboard shortcut normalization."""
        # Test various input formats
        binding1 = KeyBinding("Ctrl-S", "command1")
        assert binding1.shortcut == "ctrl+s"
        
        binding2 = KeyBinding("CTRL + SHIFT + A", "command2")
        assert binding2.shortcut == "ctrl+shift+a"
        
        binding3 = KeyBinding("alt_meta_f1", "command3")
        assert binding3.shortcut == "alt+f1"
        
        binding4 = KeyBinding("Control Space", "command4")
        assert binding4.shortcut == "ctrl+space"
    
    def test_shortcut_modifier_ordering(self):
        """Test modifier key ordering in shortcuts."""
        # Should normalize to consistent order: ctrl, alt, shift
        binding = KeyBinding("shift+alt+ctrl+a", "command")
        assert binding.shortcut == "ctrl+alt+shift+a"
    
    def test_matches_input(self):
        """Test shortcut matching."""
        binding = KeyBinding("ctrl+s", "save")
        
        assert binding.matches_input("ctrl+s")
        assert binding.matches_input("Ctrl+S")
        assert binding.matches_input("CTRL + S")
        assert not binding.matches_input("ctrl+a")
        assert not binding.matches_input("s")


class TestKeybindingManager:
    """Test KeybindingManager functionality."""
    
    def test_manager_initialization(self):
        """Test keybinding manager initialization."""
        manager = KeybindingManager()
        
        # Should have default bindings loaded
        assert len(manager._bindings) > 0
        assert "global:ctrl+s" in manager._bindings
        assert "global:ctrl+z" in manager._bindings
    
    def test_manager_with_event_bus(self):
        """Test manager initialization with event bus."""
        event_bus = Mock(spec=EventBus)
        manager = KeybindingManager(event_bus)
        
        assert manager._event_bus is event_bus
    
    def test_bind_key(self):
        """Test binding a key to a command."""
        manager = KeybindingManager()
        
        result = manager.bind_key("ctrl+t", "test.command", "Test command")
        
        assert result is True
        assert manager.get_command_for_shortcut("ctrl+t") == "test.command"
        assert "ctrl+t" in manager.get_shortcuts_for_command("test.command")
    
    def test_bind_key_with_context(self):
        """Test binding key with specific context."""
        manager = KeybindingManager()
        
        result = manager.bind_key("f1", "help.show", "Show help", "editor")
        
        assert result is True
        assert manager.get_command_for_shortcut("f1", "editor") == "help.show"
        # Global context should still have its default binding
        assert manager.get_command_for_shortcut("f1", "global") == "view.help"
    
    def test_unbind_key(self):
        """Test unbinding a key."""
        manager = KeybindingManager()
        
        # Bind then unbind
        manager.bind_key("ctrl+t", "test.command")
        assert manager.get_command_for_shortcut("ctrl+t") == "test.command"
        
        result = manager.unbind_key("ctrl+t")
        assert result is True
        assert manager.get_command_for_shortcut("ctrl+t") is None
    
    def test_unbind_nonexistent_key(self):
        """Test unbinding a non-existent key."""
        manager = KeybindingManager()
        
        result = manager.unbind_key("ctrl+nonexistent")
        assert result is False
    
    def test_get_command_for_shortcut_context_fallback(self):
        """Test command lookup with context fallback."""
        manager = KeybindingManager()
        
        # Bind in global context
        manager.bind_key("ctrl+t", "global.command", context="global")
        
        # Should find in specific context that falls back to global
        assert manager.get_command_for_shortcut("ctrl+t", "editor") == "global.command"
        assert manager.get_command_for_shortcut("ctrl+t", "global") == "global.command"
    
    def test_get_shortcuts_for_command(self):
        """Test getting all shortcuts for a command."""
        manager = KeybindingManager()
        
        # Bind multiple shortcuts to same command
        manager.bind_key("ctrl+s", "file.save")
        manager.bind_key("f5", "file.save")  # Alternative shortcut (f5 not used by default)
        
        shortcuts = manager.get_shortcuts_for_command("file.save")
        
        assert "ctrl+s" in shortcuts
        assert "f5" in shortcuts
        assert len(shortcuts) >= 2  # May include defaults
    
    def test_get_primary_shortcut(self):
        """Test getting primary shortcut for a command."""
        manager = KeybindingManager()
        
        # Should have primary shortcut from defaults
        primary = manager.get_primary_shortcut("file.save")
        assert primary == "ctrl+s"
        
        # Non-existent command
        primary = manager.get_primary_shortcut("nonexistent.command")
        assert primary is None
    
    def test_get_all_bindings(self):
        """Test getting all bindings."""
        manager = KeybindingManager()
        
        # All bindings
        all_bindings = manager.get_all_bindings()
        assert len(all_bindings) > 0
        assert all(isinstance(binding, KeyBinding) for binding in all_bindings)
        
        # Context-specific bindings
        global_bindings = manager.get_all_bindings("global")
        assert len(global_bindings) > 0
        assert all(binding.context == "global" for binding in global_bindings)
    
    def test_conflict_detection(self):
        """Test keybinding conflict detection."""
        manager = KeybindingManager()
        
        # First binding should succeed
        result1 = manager.bind_key("ctrl+t", "command1")
        assert result1 is True
        
        # Second binding with same key should conflict
        result2 = manager.bind_key("ctrl+t", "command2")
        assert result2 is False
        
        # Should be recorded as conflict
        conflicts = manager.get_conflicts()
        assert "ctrl+t" in conflicts
    
    def test_conflict_resolution(self):
        """Test resolving keybinding conflicts."""
        manager = KeybindingManager()
        
        # Create conflict
        manager.bind_key("ctrl+t", "command1")
        manager.bind_key("ctrl+t", "command2")  # Creates conflict
        
        # Resolve in favor of command2
        result = manager.resolve_conflict("ctrl+t", "command2")
        
        assert result is True
        assert manager.get_command_for_shortcut("ctrl+t") == "command2"
        assert "ctrl+t" not in manager.get_conflicts()
    
    def test_import_config(self):
        """Test importing keybindings from configuration."""
        manager = KeybindingManager()
        
        config = {
            "ctrl+t": "test.command",
            "f1": "help.show",
            "alt+f4": "app.exit"
        }
        
        errors = manager.import_config(config)
        
        assert len(errors) == 0
        assert manager.get_command_for_shortcut("ctrl+t") == "test.command"
        assert manager.get_command_for_shortcut("f1") == "help.show"
        assert manager.get_command_for_shortcut("alt+f4") == "app.exit"
    
    def test_import_config_with_errors(self):
        """Test importing config with invalid bindings."""
        manager = KeybindingManager()
        
        # Pre-bind a key to create conflict
        manager.bind_key("ctrl+s", "existing.command")
        
        config = {
            "ctrl+s": "file.save",  # Should conflict with default or existing
            "invalid+key": "test.command",  # Invalid format
        }
        
        errors = manager.import_config(config)
        
        # Should have some errors
        assert len(errors) > 0
    
    def test_export_config(self):
        """Test exporting keybindings to configuration."""
        manager = KeybindingManager()
        
        # Add custom bindings
        manager.bind_key("ctrl+t", "test.command")
        manager.bind_key("f12", "debug.toggle")
        
        # Export user-defined only
        config = manager.export_config(include_defaults=False)
        
        assert "ctrl+t" in config
        assert config["ctrl+t"] == "test.command"
        assert "f12" in config
        assert config["f12"] == "debug.toggle"
        
        # Export including defaults
        full_config = manager.export_config(include_defaults=True)
        assert "ctrl+s" in full_config  # Default binding
        assert full_config["ctrl+s"] == "file.save"
    
    def test_validate_shortcut(self):
        """Test shortcut validation."""
        manager = KeybindingManager()
        
        # Valid shortcuts
        valid, error = manager.validate_shortcut("ctrl+s")
        assert valid is True
        assert error == ""
        
        valid, error = manager.validate_shortcut("alt+shift+f1")
        assert valid is True
        
        valid, error = manager.validate_shortcut("f12")
        assert valid is True
        
        # Invalid shortcuts
        valid, error = manager.validate_shortcut("ctrl+")
        assert valid is False
        assert "must end with a key" in error
        
        valid, error = manager.validate_shortcut("invalid+s")
        assert valid is False
        assert "Invalid modifier" in error
        
        valid, error = manager.validate_shortcut("")
        assert valid is False
    
    def test_default_bindings_loaded(self):
        """Test that default Windows-standard bindings are loaded."""
        manager = KeybindingManager()
        
        # Test some essential default bindings
        assert manager.get_command_for_shortcut("ctrl+n") == "file.new"
        assert manager.get_command_for_shortcut("ctrl+o") == "file.open"
        assert manager.get_command_for_shortcut("ctrl+s") == "file.save"
        assert manager.get_command_for_shortcut("ctrl+z") == "edit.undo"
        assert manager.get_command_for_shortcut("ctrl+y") == "edit.redo"
        assert manager.get_command_for_shortcut("ctrl+c") == "edit.copy"
        assert manager.get_command_for_shortcut("ctrl+v") == "edit.paste"
        assert manager.get_command_for_shortcut("ctrl+f") == "navigation.find"
        assert manager.get_command_for_shortcut("f2") == "view.toggle_preview"
    
    def test_user_binding_override_default(self):
        """Test that user bindings can override defaults."""
        manager = KeybindingManager()
        
        # Verify default exists
        assert manager.get_command_for_shortcut("ctrl+s") == "file.save"
        
        # Override with user binding
        manager.unbind_key("ctrl+s")  # Remove default first
        result = manager.bind_key("ctrl+s", "custom.save", "Custom save")
        
        assert result is True
        assert manager.get_command_for_shortcut("ctrl+s") == "custom.save"
    
    def test_context_specific_bindings(self):
        """Test context-specific keybinding behavior."""
        manager = KeybindingManager()
        
        # First unbind f1 from global context (it's bound to view.help by default)
        manager.unbind_key("f1", "global")
        
        # Bind same key to different commands in different contexts
        manager.bind_key("f1", "general.help", context="global")
        manager.bind_key("f1", "editor.help", context="editor")
        
        # Should get context-specific command
        assert manager.get_command_for_shortcut("f1", "editor") == "editor.help"
        assert manager.get_command_for_shortcut("f1", "global") == "general.help"
        
        # Non-existent context should fall back to global
        assert manager.get_command_for_shortcut("f1", "preview") == "general.help"
    
    def test_get_conflicts_details(self):
        """Test getting detailed conflict information."""
        manager = KeybindingManager()
        
        # Create conflicts
        manager.bind_key("ctrl+t", "command1")
        manager.bind_key("ctrl+t", "command2")
        manager.bind_key("ctrl+r", "command3")
        manager.bind_key("ctrl+r", "command4")
        
        conflicts = manager.get_conflicts()
        
        assert "ctrl+t" in conflicts
        assert "ctrl+r" in conflicts
        assert len(conflicts["ctrl+t"]) >= 1
        assert len(conflicts["ctrl+r"]) >= 1
        
        # Each conflict should have KeyBinding objects
        for shortcut, bindings in conflicts.items():
            assert all(isinstance(binding, KeyBinding) for binding in bindings)