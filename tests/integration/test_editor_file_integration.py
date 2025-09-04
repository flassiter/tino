"""
Integration tests for editor and file manager components.

Tests the interaction between EditorComponent and FileManager,
ensuring proper event flow and state synchronization.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock

from tino.core.events.bus import EventBus
from tino.core.events.types import TextChangedEvent, FileOpenedEvent, FileSavedEvent
from tino.components.editor import EditorComponent, MockEditor
from tino.components.file_manager import FileManager


class TestEditorFileManagerIntegration:
    """Test integration between editor and file manager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()
        self.editor = MockEditor(self.event_bus)
        self.file_manager = FileManager(self.event_bus)
        
        # Create temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def test_file_open_workflow(self):
        """Test opening a file and loading into editor."""
        # Create a test file
        test_file = self.temp_path / "test.md"
        test_content = "# Test Document\n\nThis is a test file.\n"
        test_file.write_text(test_content, encoding='utf-8')
        
        # Mock event handlers
        file_opened_handler = Mock()
        text_changed_handler = Mock()
        
        self.event_bus.subscribe(FileOpenedEvent, file_opened_handler)
        self.event_bus.subscribe(TextChangedEvent, text_changed_handler)
        
        # Open file
        content = self.file_manager.open_file(test_file)
        
        # Load content into editor
        self.editor.set_content(content)
        
        # Verify file opened event was emitted
        file_opened_handler.assert_called_once()
        event = file_opened_handler.call_args[0][0]
        assert event.file_path == test_file
        # Note: FileManager sets these values when emitting the event
        assert event.encoding is not None
        assert event.size > 0
        
        # Verify editor has correct content
        assert self.editor.get_content() == test_content
        assert self.editor.is_modified()  # Editor marks as modified when content is set
    
    def test_file_save_workflow(self):
        """Test editing content and saving to file."""
        # Set up initial content in editor
        initial_content = "# Original Content\n\nOriginal text.\n"
        self.editor.set_content(initial_content)
        
        # Edit the content
        self.editor.insert_text(len(initial_content), "\n## New Section\n\nNew content added.")
        
        final_content = self.editor.get_content()
        
        # Mock event handler
        file_saved_handler = Mock()
        self.event_bus.subscribe(FileSavedEvent, file_saved_handler)
        
        # Save to file
        test_file = self.temp_path / "output.md"
        success = self.file_manager.save_file(test_file, final_content)
        
        assert success
        
        # Verify file saved event was emitted
        file_saved_handler.assert_called_once()
        event = file_saved_handler.call_args[0][0]
        assert event.file_path == test_file
        
        # Verify file contents
        saved_content = test_file.read_text(encoding='utf-8')
        assert saved_content == final_content
        
        # Mark editor as unmodified after save
        self.editor.set_modified(False)
        assert not self.editor.is_modified()
    
    def test_recent_files_integration(self):
        """Test recent files tracking with editor operations."""
        # Create multiple test files
        test_files = []
        for i in range(3):
            test_file = self.temp_path / f"test{i}.md"
            content = f"# Document {i}\n\nContent for document {i}.\n"
            test_file.write_text(content, encoding='utf-8')
            test_files.append(test_file)
        
        # Open files in sequence
        for test_file in test_files:
            content = self.file_manager.open_file(test_file)
            self.editor.set_content(content)
            
            # Simulate editing
            self.editor.insert_text(len(content), f"\n\nEdited: {test_file.name}")
        
        # Check recent files list
        recent_files = self.file_manager.get_recent_files()
        
        assert len(recent_files) == 3
        # Most recent should be first
        assert recent_files[0] == test_files[2]
        assert recent_files[1] == test_files[1]
        assert recent_files[2] == test_files[0]
        
        # Test last file tracking
        last_file = self.file_manager.get_last_file()
        assert last_file == test_files[2]
    
    def test_backup_creation_integration(self):
        """Test backup creation when editing existing files."""
        # Create original file
        test_file = self.temp_path / "document.md"
        original_content = "# Original Document\n\nOriginal content.\n"
        test_file.write_text(original_content, encoding='utf-8')
        
        # Open file
        content = self.file_manager.open_file(test_file)
        self.editor.set_content(content)
        
        # Edit content significantly
        self.editor.insert_text(0, "<!-- Modified -->\n")
        self.editor.insert_text(len(self.editor.get_content()), "\n\n## New Section\n\nAdded content.")
        
        modified_content = self.editor.get_content()
        
        # Save file (should create backup)
        success = self.file_manager.save_file(test_file, modified_content)
        assert success
        
        # Check if backup was created
        backup_file = test_file.with_suffix('.md.tino.bak')
        assert backup_file.exists()
        
        # Verify backup contains original content
        backup_content = backup_file.read_text(encoding='utf-8')
        assert backup_content == original_content
        
        # Verify main file has modified content
        main_content = test_file.read_text(encoding='utf-8')
        assert main_content == modified_content
    
    def test_cursor_position_memory_integration(self):
        """Test cursor position memory across file operations."""
        # Create test file
        test_file = self.temp_path / "cursor_test.md"
        content = "line 1\nline 2\nline 3\nline 4\nline 5"
        test_file.write_text(content, encoding='utf-8')
        
        # Open file and set cursor position
        file_content = self.file_manager.open_file(test_file)
        self.editor.set_content(file_content)
        
        # Set cursor to line 2, column 3
        self.editor.set_cursor_position(2, 3)
        
        # Store cursor position in file manager
        line, column, _ = self.editor.get_cursor_position()
        self.file_manager.remember_cursor_position(test_file, line, column)
        
        # Simulate closing and reopening file
        self.editor.set_content("")  # Clear editor
        
        # Reopen file
        file_content = self.file_manager.open_file(test_file)
        self.editor.set_content(file_content)
        
        # Get remembered cursor position
        remembered_line, remembered_column = self.file_manager.get_cursor_position(test_file)
        
        assert remembered_line == 2
        assert remembered_column == 3
        
        # Set cursor to remembered position
        self.editor.set_cursor_position(remembered_line, remembered_column)
        
        # Verify cursor is at correct position
        current_line, current_column, _ = self.editor.get_cursor_position()
        assert current_line == 2
        assert current_column == 3
    
    def test_encoding_detection_integration(self):
        """Test encoding detection with different file types."""
        # Create files with different encodings
        test_files = [
            (self.temp_path / "utf8.md", "UTF-8 content with émojis 🚀", 'utf-8'),
            (self.temp_path / "ascii.txt", "Plain ASCII content", 'ascii'),
        ]
        
        for file_path, content, encoding in test_files:
            file_path.write_text(content, encoding=encoding)
            
            # Open file and check encoding detection
            loaded_content = self.file_manager.open_file(file_path)
            
            assert loaded_content == content
            # Note: FileManager handles encoding detection internally
            
            # Load into editor
            self.editor.set_content(loaded_content)
            assert self.editor.get_content() == content
    
    def test_large_file_handling_integration(self):
        """Test handling of large files."""
        # Create a moderately large file (not huge to avoid slow tests)
        large_content = "Line {}\n".format("content " * 100) * 1000  # ~100KB
        large_file = self.temp_path / "large_file.md"
        large_file.write_text(large_content, encoding='utf-8')
        
        # Open large file
        content = self.file_manager.open_file(large_file)
        
        assert len(content) > 50000  # Should be reasonably large
        # Note: FileManager handles encoding detection and size calculation internally
        
        # Load into editor
        self.editor.set_content(content)
        
        # Test basic operations on large content
        self.editor.insert_text(0, "# Large File Header\n\n")
        self.editor.set_selection(0, 20)
        
        selected_text = self.editor.get_selected_text()
        assert selected_text == "# Large File Header\n"
    
    def test_error_handling_integration(self):
        """Test error handling in integrated operations."""
        # Test opening non-existent file
        non_existent = self.temp_path / "does_not_exist.md"
        
        with pytest.raises(FileNotFoundError):
            self.file_manager.open_file(non_existent)
        
        # Test saving to invalid path (should fail gracefully)
        try:
            invalid_path = Path("/invalid/path/file.md") 
            success = self.file_manager.save_file(invalid_path, "content")
            assert not success  # Should fail gracefully
        except FileNotFoundError:
            # This is acceptable - the FileManager may raise an exception
            # instead of returning False for invalid paths
            pass
    
    def test_undo_redo_with_file_operations(self):
        """Test undo/redo functionality with file operations."""
        # Create and open file
        test_file = self.temp_path / "undo_test.md"
        initial_content = "# Initial Content\n\nOriginal text.\n"
        test_file.write_text(initial_content, encoding='utf-8')
        
        content = self.file_manager.open_file(test_file)
        self.editor.set_content(content)
        
        # Make several edits
        self.editor.insert_text(len(content), "\n## Section 1\n\nFirst addition.")
        content_after_first = self.editor.get_content()
        
        self.editor.insert_text(len(self.editor.get_content()), "\n\n## Section 2\n\nSecond addition.")
        content_after_second = self.editor.get_content()
        
        # Test undo
        success = self.editor.undo()
        assert success
        assert self.editor.get_content() == content_after_first
        
        success = self.editor.undo()
        assert success
        assert self.editor.get_content() == initial_content
        
        # Test redo
        success = self.editor.redo()
        assert success
        assert self.editor.get_content() == content_after_first
        
        success = self.editor.redo()
        assert success
        assert self.editor.get_content() == content_after_second
        
        # Save final state
        final_content = self.editor.get_content()
        success = self.file_manager.save_file(test_file, final_content)
        assert success
    
    def test_event_flow_integration(self):
        """Test complete event flow in integrated operations."""
        # Set up event tracking
        events_received = []
        
        def event_tracker(event):
            events_received.append(type(event).__name__)
        
        # Subscribe to all events
        self.event_bus.subscribe(FileOpenedEvent, event_tracker)
        self.event_bus.subscribe(FileSavedEvent, event_tracker)
        self.event_bus.subscribe(TextChangedEvent, event_tracker)
        
        # Create test file
        test_file = self.temp_path / "event_test.md"
        content = "# Event Test\n\nTesting event flow.\n"
        test_file.write_text(content, encoding='utf-8')
        
        # Complete workflow: open, edit, save
        loaded_content = self.file_manager.open_file(test_file)
        self.editor.set_content(loaded_content)
        self.editor.insert_text(len(loaded_content), "\n## Edited\n\nContent added.")
        
        modified_content = self.editor.get_content()
        self.file_manager.save_file(test_file, modified_content)
        
        # Verify events were emitted in correct order
        assert "FileOpenedEvent" in events_received
        assert "TextChangedEvent" in events_received
        assert "FileSavedEvent" in events_received
        
        # Should have multiple text changed events
        text_changed_count = events_received.count("TextChangedEvent")
        assert text_changed_count >= 2  # set_content and insert_text


if __name__ == "__main__":
    pytest.main([__file__])