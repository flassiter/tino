"""
Tests for interface contracts.

Tests that all interfaces have the expected methods and can be properly
implemented by concrete classes and mocks.
"""

import pytest
from abc import ABC
from typing import get_type_hints
from pathlib import Path
from unittest.mock import Mock

from tino.core.interfaces import IEditor, IFileManager, IRenderer, ICommand
from tino.core.interfaces.renderer import Heading, ValidationIssue, RenderResult


class TestInterfaceContracts:
    """Test that interfaces define proper contracts."""
    
    def test_ieditor_interface_methods(self):
        """Test that IEditor has all expected methods."""
        expected_methods = {
            'get_content', 'set_content', 'insert_text', 'delete_range',
            'get_selection', 'set_selection', 'get_cursor_position', 'set_cursor_position',
            'undo', 'redo', 'can_undo', 'can_redo',
            'get_selected_text', 'replace_selection',
            'get_line_count', 'get_line_text', 'find_text',
            'is_modified', 'set_modified', 'clear_undo_history'
        }
        
        actual_methods = set(dir(IEditor))
        for method in expected_methods:
            assert method in actual_methods, f"IEditor missing method: {method}"
    
    def test_ifile_manager_interface_methods(self):
        """Test that IFileManager has all expected methods."""
        expected_methods = {
            'open_file', 'save_file', 'create_backup', 'get_encoding',
            'watch_file', 'unwatch_file', 'file_exists', 'get_file_info',
            'is_binary_file', 'add_recent_file', 'get_recent_files',
            'get_last_file', 'clear_recent_files', 'set_cursor_position',
            'get_cursor_position', 'validate_file_path', 'get_temp_file_path',
            'cleanup_temp_files'
        }
        
        actual_methods = set(dir(IFileManager))
        for method in expected_methods:
            assert method in actual_methods, f"IFileManager missing method: {method}"
    
    def test_irenderer_interface_methods(self):
        """Test that IRenderer has all expected methods."""
        expected_methods = {
            'render_html', 'render_preview', 'get_outline', 'validate',
            'supports_format', 'get_supported_formats', 'set_theme',
            'get_available_themes', 'clear_cache', 'get_cache_stats',
            'export_html', 'get_word_count', 'find_links', 'validate_links'
        }
        
        actual_methods = set(dir(IRenderer))
        for method in expected_methods:
            assert method in actual_methods, f"IRenderer missing method: {method}"
    
    def test_icommand_interface_methods(self):
        """Test that ICommand has all expected methods."""
        expected_methods = {
            'execute', 'undo', 'can_execute', 'can_undo',
            'get_name', 'get_description', 'get_category', 'get_shortcut',
            'get_parameters', 'is_async', 'get_execution_context',
            'validate_parameters'
        }
        
        actual_methods = set(dir(ICommand))
        for method in expected_methods:
            assert method in actual_methods, f"ICommand missing method: {method}"
    
    def test_interfaces_are_abstract(self):
        """Test that interfaces cannot be instantiated directly."""
        with pytest.raises(TypeError):
            IEditor()
        
        with pytest.raises(TypeError):
            IFileManager()
        
        with pytest.raises(TypeError):
            IRenderer()
        
        with pytest.raises(TypeError):
            ICommand()


class MockEditor(IEditor):
    """Mock implementation of IEditor for testing."""
    
    def __init__(self):
        self.content = ""
        self.cursor_line = 0
        self.cursor_column = 0
        self.selection_start = 0
        self.selection_end = 0
        self.modified = False
        self.undo_stack = []
        self.redo_stack = []
    
    def get_content(self) -> str:
        return self.content
    
    def set_content(self, text: str) -> None:
        self.undo_stack.append(self.content)
        self.content = text
        self.modified = True
    
    def insert_text(self, position: int, text: str) -> None:
        self.undo_stack.append(self.content)
        self.content = self.content[:position] + text + self.content[position:]
        self.modified = True
    
    def delete_range(self, start: int, end: int) -> str:
        self.undo_stack.append(self.content)
        deleted = self.content[start:end]
        self.content = self.content[:start] + self.content[end:]
        self.modified = True
        return deleted
    
    def get_selection(self) -> tuple[int, int]:
        return (self.selection_start, self.selection_end)
    
    def set_selection(self, start: int, end: int) -> None:
        self.selection_start = start
        self.selection_end = end
    
    def get_cursor_position(self) -> tuple[int, int, int]:
        lines = self.content[:self.selection_start].split('\n')
        line = len(lines) - 1
        column = len(lines[-1]) if lines else 0
        return (line, column, self.selection_start)
    
    def set_cursor_position(self, line: int, column: int) -> None:
        self.cursor_line = line
        self.cursor_column = column
    
    def undo(self) -> bool:
        if self.undo_stack:
            self.redo_stack.append(self.content)
            self.content = self.undo_stack.pop()
            return True
        return False
    
    def redo(self) -> bool:
        if self.redo_stack:
            self.undo_stack.append(self.content)
            self.content = self.redo_stack.pop()
            return True
        return False
    
    def can_undo(self) -> bool:
        return len(self.undo_stack) > 0
    
    def can_redo(self) -> bool:
        return len(self.redo_stack) > 0
    
    def get_selected_text(self) -> str:
        return self.content[self.selection_start:self.selection_end]
    
    def replace_selection(self, text: str) -> None:
        self.delete_range(self.selection_start, self.selection_end)
        self.insert_text(self.selection_start, text)
    
    def get_line_count(self) -> int:
        return len(self.content.split('\n'))
    
    def get_line_text(self, line_number: int) -> str:
        lines = self.content.split('\n')
        if 0 <= line_number < len(lines):
            return lines[line_number]
        raise IndexError(f"Line {line_number} out of range")
    
    def find_text(self, pattern: str, start: int = 0, case_sensitive: bool = True) -> tuple[int, int] | None:
        content = self.content if case_sensitive else self.content.lower()
        pattern = pattern if case_sensitive else pattern.lower()
        pos = content.find(pattern, start)
        if pos != -1:
            return (pos, pos + len(pattern))
        return None
    
    def is_modified(self) -> bool:
        return self.modified
    
    def set_modified(self, modified: bool) -> None:
        self.modified = modified
    
    def clear_undo_history(self) -> None:
        self.undo_stack.clear()
        self.redo_stack.clear()


class MockFileManager(IFileManager):
    """Mock implementation of IFileManager for testing."""
    
    def __init__(self):
        self.files = {}
        self.recent_files = []
        self.cursor_positions = {}
    
    def open_file(self, file_path: Path) -> str:
        return self.files.get(str(file_path), "")
    
    def save_file(self, file_path: Path, content: str, encoding: str | None = None) -> bool:
        self.files[str(file_path)] = content
        return True
    
    def create_backup(self, file_path: Path) -> Path | None:
        if str(file_path) in self.files:
            backup_path = Path(str(file_path) + ".bak")
            self.files[str(backup_path)] = self.files[str(file_path)]
            return backup_path
        return None
    
    def get_encoding(self, file_path: Path) -> str:
        return "utf-8"
    
    def watch_file(self, file_path: Path) -> bool:
        return True
    
    def unwatch_file(self, file_path: Path) -> bool:
        return True
    
    def file_exists(self, file_path: Path) -> bool:
        return str(file_path) in self.files
    
    def get_file_info(self, file_path: Path) -> tuple[int, float, str]:
        content = self.files.get(str(file_path), "")
        return (len(content), 0.0, "utf-8")
    
    def is_binary_file(self, file_path: Path) -> bool:
        return False
    
    def add_recent_file(self, file_path: Path) -> None:
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
    
    def get_recent_files(self, limit: int | None = None) -> list[Path]:
        if limit:
            return self.recent_files[:limit]
        return self.recent_files[:]
    
    def get_last_file(self) -> Path | None:
        return self.recent_files[0] if self.recent_files else None
    
    def clear_recent_files(self) -> None:
        self.recent_files.clear()
    
    def set_cursor_position(self, file_path: Path, line: int, column: int) -> None:
        self.cursor_positions[str(file_path)] = (line, column)
    
    def get_cursor_position(self, file_path: Path) -> tuple[int, int] | None:
        return self.cursor_positions.get(str(file_path))
    
    def validate_file_path(self, file_path: Path) -> tuple[bool, str]:
        return (True, "")
    
    def get_temp_file_path(self, original_path: Path) -> Path:
        return Path(str(original_path) + ".tmp")
    
    def cleanup_temp_files(self) -> int:
        return 0


class MockRenderer(IRenderer):
    """Mock implementation of IRenderer for testing."""
    
    def render_html(self, content: str, file_path: str | None = None) -> RenderResult:
        return RenderResult(
            html=f"<p>{content}</p>",
            outline=[],
            issues=[],
            render_time_ms=1.0
        )
    
    def render_preview(self, content: str, file_path: str | None = None):
        from unittest.mock import Mock
        widget = Mock()
        widget.content = content
        return widget
    
    def get_outline(self, content: str) -> list[Heading]:
        return []
    
    def validate(self, content: str, file_path: str | None = None) -> list[ValidationIssue]:
        return []
    
    def supports_format(self, file_extension: str) -> bool:
        return file_extension in [".md", ".txt"]
    
    def get_supported_formats(self) -> list[str]:
        return [".md", ".txt"]
    
    def set_theme(self, theme_name: str) -> None:
        pass
    
    def get_available_themes(self) -> list[str]:
        return ["dark", "light"]
    
    def clear_cache(self) -> None:
        pass
    
    def get_cache_stats(self) -> dict[str, any]:
        return {"hits": 0, "misses": 0}
    
    def export_html(self, content: str, output_path: str, standalone: bool = True, include_css: bool = True) -> bool:
        return True
    
    def get_word_count(self, content: str) -> dict[str, int]:
        words = len(content.split())
        return {"words": words, "characters": len(content)}
    
    def find_links(self, content: str) -> list[dict[str, any]]:
        return []
    
    def validate_links(self, content: str, file_path: str | None = None) -> list[ValidationIssue]:
        return []


class MockCommand(ICommand):
    """Mock implementation of ICommand for testing."""
    
    def __init__(self, name: str = "test_command"):
        self.name = name
        self.executed = False
        self.undone = False
    
    def execute(self, *args, **kwargs) -> bool:
        self.executed = True
        return True
    
    def undo(self) -> bool:
        if self.executed:
            self.undone = True
            return True
        return False
    
    def can_execute(self, *args, **kwargs) -> bool:
        return True
    
    def can_undo(self) -> bool:
        return self.executed and not self.undone
    
    def get_name(self) -> str:
        return self.name
    
    def get_description(self) -> str:
        return f"Test command: {self.name}"
    
    def get_category(self) -> str:
        return "Test"
    
    def get_shortcut(self) -> str | None:
        return "ctrl+t"
    
    def get_parameters(self) -> dict[str, any]:
        return {}
    
    def is_async(self) -> bool:
        return False
    
    def get_execution_context(self) -> dict[str, any]:
        return {}
    
    def validate_parameters(self, *args, **kwargs) -> str | None:
        return None


class TestInterfaceImplementations:
    """Test that mock implementations properly implement interfaces."""
    
    def test_mock_editor_implementation(self):
        """Test that MockEditor properly implements IEditor."""
        editor = MockEditor()
        
        # Test basic functionality
        editor.set_content("Hello, world!")
        assert editor.get_content() == "Hello, world!"
        assert editor.is_modified() is True
        
        # Test text insertion
        editor.insert_text(7, "beautiful ")
        assert editor.get_content() == "Hello, beautiful world!"
        
        # Test deletion
        deleted = editor.delete_range(7, 17)
        assert deleted == "beautiful "
        assert editor.get_content() == "Hello, world!"
        
        # Test undo/redo
        assert editor.can_undo() is True
        assert editor.undo() is True
        assert editor.get_content() == "Hello, beautiful world!"
        
        assert editor.can_redo() is True
        assert editor.redo() is True
        assert editor.get_content() == "Hello, world!"
        
        # Test selection
        editor.set_selection(0, 5)
        assert editor.get_selection() == (0, 5)
        assert editor.get_selected_text() == "Hello"
        
        # Test line operations
        editor.set_content("Line 1\nLine 2\nLine 3")
        assert editor.get_line_count() == 3
        assert editor.get_line_text(1) == "Line 2"
        
        # Test find
        result = editor.find_text("Line 2")
        assert result == (7, 13)
    
    def test_mock_file_manager_implementation(self):
        """Test that MockFileManager properly implements IFileManager."""
        fm = MockFileManager()
        test_path = Path("test.txt")
        
        # Test file operations
        fm.save_file(test_path, "Test content")
        assert fm.file_exists(test_path) is True
        assert fm.open_file(test_path) == "Test content"
        
        # Test backup
        backup_path = fm.create_backup(test_path)
        assert backup_path is not None
        assert fm.open_file(backup_path) == "Test content"
        
        # Test recent files
        fm.add_recent_file(test_path)
        recent = fm.get_recent_files()
        assert len(recent) == 1
        assert recent[0] == test_path
        assert fm.get_last_file() == test_path
        
        # Test cursor position memory
        fm.set_cursor_position(test_path, 10, 5)
        pos = fm.get_cursor_position(test_path)
        assert pos == (10, 5)
        
        # Test file info
        size, timestamp, encoding = fm.get_file_info(test_path)
        assert size == len("Test content")
        assert encoding == "utf-8"
    
    def test_mock_renderer_implementation(self):
        """Test that MockRenderer properly implements IRenderer."""
        renderer = MockRenderer()
        
        # Test rendering
        result = renderer.render_html("# Test")
        assert isinstance(result, RenderResult)
        assert "<p># Test</p>" in result.html
        
        # Test preview
        widget = renderer.render_preview("Test content")
        assert widget.content == "Test content"
        
        # Test format support
        assert renderer.supports_format(".md") is True
        assert renderer.supports_format(".xyz") is False
        
        formats = renderer.get_supported_formats()
        assert ".md" in formats
        assert ".txt" in formats
        
        # Test themes
        themes = renderer.get_available_themes()
        assert "dark" in themes
        assert "light" in themes
        
        # Test word count
        stats = renderer.get_word_count("Hello world test")
        assert stats["words"] == 3
        assert stats["characters"] == 16
        
        # Test export
        result = renderer.export_html("content", "output.html")
        assert result is True
    
    def test_mock_command_implementation(self):
        """Test that MockCommand properly implements ICommand."""
        cmd = MockCommand("test_cmd")
        
        # Test basic info
        assert cmd.get_name() == "test_cmd"
        assert cmd.get_description() == "Test command: test_cmd"
        assert cmd.get_category() == "Test"
        assert cmd.get_shortcut() == "ctrl+t"
        
        # Test execution
        assert cmd.can_execute() is True
        assert cmd.executed is False
        
        result = cmd.execute()
        assert result is True
        assert cmd.executed is True
        
        # Test undo
        assert cmd.can_undo() is True
        result = cmd.undo()
        assert result is True
        assert cmd.undone is True
        
        # Test parameter validation
        error = cmd.validate_parameters()
        assert error is None
        
        # Test async check
        assert cmd.is_async() is False


class TestInterfaceInheritance:
    """Test interface inheritance and type checking."""
    
    def test_isinstance_checks(self):
        """Test that implementations are instances of their interfaces."""
        assert isinstance(MockEditor(), IEditor)
        assert isinstance(MockFileManager(), IFileManager)
        assert isinstance(MockRenderer(), IRenderer)
        assert isinstance(MockCommand(), ICommand)
    
    def test_abc_registration(self):
        """Test that interfaces are properly registered as ABCs."""
        assert issubclass(MockEditor, IEditor)
        assert issubclass(MockFileManager, IFileManager)
        assert issubclass(MockRenderer, IRenderer)
        assert issubclass(MockCommand, ICommand)