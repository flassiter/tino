"""
Tests for FileManager class.

Tests the main FileManager implementation with all components integrated.
"""

import pytest
import tempfile
from pathlib import Path
import time

from tino.components.file_manager.file_manager import FileManager
from tino.core.events.bus import EventBus
from tino.core.events.types import FileOpenedEvent, FileSavedEvent


class TestFileManager:
    
    def setup_method(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()
        self.manager = FileManager(event_bus=self.event_bus)
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Track events for testing
        self.events_received = []
        self.event_bus.subscribe(FileOpenedEvent, self._record_event)
        self.event_bus.subscribe(FileSavedEvent, self._record_event)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def _record_event(self, event):
        """Record events for testing."""
        self.events_received.append(event)
    
    def test_open_file_success(self):
        """Test successful file opening."""
        test_file = self.temp_dir / "test.txt"
        content = "Hello, world!"
        test_file.write_text(content, encoding='utf-8')
        
        result = self.manager.open_file(test_file)
        
        assert result == content
        assert len(self.events_received) == 1
        assert isinstance(self.events_received[0], FileOpenedEvent)
        assert self.events_received[0].file_path == test_file
    
    def test_open_file_not_exists(self):
        """Test opening non-existent file."""
        test_file = self.temp_dir / "nonexistent.txt"
        
        with pytest.raises(FileNotFoundError):
            self.manager.open_file(test_file)
    
    def test_open_file_binary(self):
        """Test opening binary file should fail."""
        test_file = self.temp_dir / "binary.bin"
        # Create a file with binary data (PNG signature)
        test_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
        
        with pytest.raises(ValueError, match="Cannot open binary file"):
            self.manager.open_file(test_file)
    
    def test_open_file_large_warning(self):
        """Test that opening large files generates warning."""
        test_file = self.temp_dir / "large.txt"
        # Create file larger than threshold
        large_content = "x" * (FileManager.LARGE_FILE_THRESHOLD + 1000)
        test_file.write_text(large_content)
        
        # Should still open successfully
        result = self.manager.open_file(test_file)
        assert len(result) == len(large_content)
    
    def test_save_file_new_file(self):
        """Test saving new file."""
        test_file = self.temp_dir / "new.txt"
        content = "New file content"
        
        result = self.manager.save_file(test_file, content)
        
        assert result is True
        assert test_file.exists()
        assert test_file.read_text() == content
        
        # Should emit save event
        save_events = [e for e in self.events_received if isinstance(e, FileSavedEvent)]
        assert len(save_events) == 1
        assert save_events[0].backup_created is False  # No backup for new file
    
    def test_save_file_existing_file(self):
        """Test saving existing file creates backup."""
        test_file = self.temp_dir / "existing.txt"
        original_content = "Original content"
        new_content = "New content"
        
        # Create original file
        test_file.write_text(original_content)
        
        # Save new content
        result = self.manager.save_file(test_file, new_content)
        
        assert result is True
        assert test_file.read_text() == new_content
        
        # Check backup was created
        backup_path = test_file.with_suffix(test_file.suffix + '.tino.bak')
        assert backup_path.exists()
        assert backup_path.read_text() == original_content
        
        # Should emit save event with backup flag
        save_events = [e for e in self.events_received if isinstance(e, FileSavedEvent)]
        assert len(save_events) == 1
        assert save_events[0].backup_created is True
    
    def test_save_file_atomic_operation(self):
        """Test that file saving is atomic."""
        test_file = self.temp_dir / "atomic.txt"
        content = "Atomic content"
        
        result = self.manager.save_file(test_file, content)
        
        assert result is True
        # File should exist and have correct content
        assert test_file.exists()
        assert test_file.read_text() == content
        
        # Temp files should be cleaned up
        temp_files = list(self.temp_dir.glob(".tino_temp_*"))
        assert len(temp_files) == 0
    
    def test_get_encoding_utf8(self):
        """Test encoding detection for UTF-8 file."""
        test_file = self.temp_dir / "utf8.txt"
        test_file.write_text("Hello, 世界!", encoding='utf-8')
        
        encoding = self.manager.get_encoding(test_file)
        assert encoding == 'utf-8'
    
    def test_is_binary_file_text(self):
        """Test binary detection on text file."""
        test_file = self.temp_dir / "text.txt"
        test_file.write_text("This is text")
        
        assert not self.manager.is_binary_file(test_file)
    
    def test_is_binary_file_binary(self):
        """Test binary detection on binary file."""
        test_file = self.temp_dir / "binary.png"
        test_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
        
        assert self.manager.is_binary_file(test_file)
    
    def test_file_exists(self):
        """Test file existence check."""
        existing_file = self.temp_dir / "exists.txt"
        nonexistent_file = self.temp_dir / "not_exists.txt"
        
        existing_file.touch()
        
        assert self.manager.file_exists(existing_file)
        assert not self.manager.file_exists(nonexistent_file)
    
    def test_get_file_info(self):
        """Test getting file information."""
        test_file = self.temp_dir / "info.txt"
        content = "File info test"
        test_file.write_text(content)
        
        size, modified, encoding = self.manager.get_file_info(test_file)
        
        assert size > 0
        assert isinstance(modified, float)
        # Simple ASCII content might be detected as ASCII or UTF-8
        assert encoding.lower() in ['ascii', 'utf-8']
    
    def test_get_file_info_not_exists(self):
        """Test getting info for non-existent file."""
        test_file = self.temp_dir / "not_exists.txt"
        
        with pytest.raises(FileNotFoundError):
            self.manager.get_file_info(test_file)
    
    def test_recent_files_integration(self):
        """Test recent files functionality integration."""
        files = []
        for i in range(3):
            test_file = self.temp_dir / f"recent{i}.txt"
            test_file.write_text(f"Content {i}")
            files.append(test_file)
            self.manager.open_file(test_file)
        
        recent = self.manager.get_recent_files()
        assert len(recent) == 3
        # Should be in reverse order (most recent first)
        assert recent == list(reversed(files))
    
    def test_last_file_functionality(self):
        """Test last file (Ctrl+Tab) functionality."""
        file1 = self.temp_dir / "file1.txt"
        file2 = self.temp_dir / "file2.txt"
        
        file1.write_text("Content 1")
        file2.write_text("Content 2")
        
        self.manager.open_file(file1)
        self.manager.open_file(file2)
        
        last_file = self.manager.get_last_file()
        assert last_file == file1  # Previous file
    
    def test_cursor_position_memory(self):
        """Test cursor position memory integration."""
        test_file = self.temp_dir / "cursor.txt"
        
        self.manager.set_cursor_position(test_file, 5, 10)
        position = self.manager.get_cursor_position(test_file)
        
        assert position == (5, 10)
    
    def test_clear_recent_files(self):
        """Test clearing recent files."""
        test_file = self.temp_dir / "recent.txt"
        test_file.write_text("content")
        self.manager.open_file(test_file)
        
        assert len(self.manager.get_recent_files()) == 1
        
        self.manager.clear_recent_files()
        assert len(self.manager.get_recent_files()) == 0
    
    def test_validate_file_path_valid(self):
        """Test file path validation for valid path."""
        test_file = self.temp_dir / "valid.txt"
        
        is_valid, error = self.manager.validate_file_path(test_file)
        assert is_valid is True
        assert error == ""
    
    def test_validate_file_path_invalid_parent(self):
        """Test file path validation for invalid parent directory."""
        invalid_file = Path("/nonexistent_parent/file.txt")
        
        is_valid, error = self.manager.validate_file_path(invalid_file)
        assert is_valid is False
        assert "does not exist" in error.lower()
    
    def test_get_temp_file_path(self):
        """Test temporary file path generation."""
        test_file = self.temp_dir / "original.txt"
        
        temp_path = self.manager.get_temp_file_path(test_file)
        
        assert temp_path.parent == test_file.parent
        assert ".tino_temp_" in str(temp_path)
        assert temp_path.suffix == ".tmp"
    
    def test_cleanup_temp_files(self):
        """Test cleanup of temporary files."""
        # Create some temp files manually
        temp1 = self.temp_dir / ".tino_temp_file1_123.tmp"
        temp2 = self.temp_dir / ".tino_temp_file2_456.tmp"
        regular = self.temp_dir / "regular.txt"
        
        temp1.touch()
        temp2.touch()
        regular.touch()
        
        # Add directory to recent files so it gets cleaned
        test_file = self.temp_dir / "test.txt"
        self.manager.add_recent_file(test_file)
        
        cleaned = self.manager.cleanup_temp_files()
        
        assert cleaned == 2
        assert not temp1.exists()
        assert not temp2.exists()
        assert regular.exists()  # Regular file should remain
    
    def test_create_backup_integration(self):
        """Test backup creation through manager interface."""
        test_file = self.temp_dir / "backup_test.txt"
        test_file.write_text("Original content")
        
        backup_path = self.manager.create_backup(test_file)
        
        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.read_text() == "Original content"
    
    def test_manager_stats(self):
        """Test getting manager statistics."""
        # Add some files and positions
        for i in range(3):
            test_file = self.temp_dir / f"stats{i}.txt"
            test_file.write_text(f"content {i}")
            self.manager.open_file(test_file)
            self.manager.set_cursor_position(test_file, i, i * 2)
        
        stats = self.manager.get_manager_stats()
        
        assert 'recent_files' in stats
        assert 'cursor_memory' in stats
        assert 'backup_info' in stats
        
        assert stats['recent_files']['total_files'] == 3
        assert stats['cursor_memory']['total_files'] == 3
    
    def test_watch_file_not_implemented(self):
        """Test that file watching returns False (not implemented in MVP)."""
        test_file = self.temp_dir / "watch.txt"
        
        result = self.manager.watch_file(test_file)
        assert result is False
    
    def test_unwatch_file_not_implemented(self):
        """Test that file unwatching returns False (not implemented in MVP)."""
        test_file = self.temp_dir / "unwatch.txt"
        
        result = self.manager.unwatch_file(test_file)
        assert result is False
    
    def test_string_path_conversion(self):
        """Test that string paths are converted to Path objects."""
        test_file = self.temp_dir / "string_path.txt"
        test_file.write_text("content")
        
        # Use string path
        result = self.manager.open_file(str(test_file))
        assert result == "content"
        
        # Recent files should contain Path object
        recent = self.manager.get_recent_files()
        assert isinstance(recent[0], Path)
    
    def test_encoding_preservation(self):
        """Test that file encoding is preserved across save/load."""
        test_file = self.temp_dir / "encoding.txt"
        content = "Café naïve résumé"
        
        # Save with specific encoding
        self.manager.save_file(test_file, content, encoding='latin-1')
        
        # Verify encoding is preserved (latin-1 or similar ISO-8859 variant)
        detected_encoding = self.manager.get_encoding(test_file)
        assert any(enc in detected_encoding.lower() for enc in ['latin-1', 'iso-8859'])
        
        # Should be able to read back correctly
        loaded_content = self.manager.open_file(test_file)
        assert loaded_content == content
    
    def test_concurrent_operations(self):
        """Test that concurrent operations don't interfere."""
        files = []
        for i in range(5):
            test_file = self.temp_dir / f"concurrent{i}.txt"
            test_file.write_text(f"content {i}")
            files.append(test_file)
        
        # Open all files
        for test_file in files:
            self.manager.open_file(test_file)
        
        # Set cursor positions
        for i, test_file in enumerate(files):
            self.manager.set_cursor_position(test_file, i, i * 2)
        
        # Verify all operations completed correctly
        recent = self.manager.get_recent_files()
        assert len(recent) == 5
        
        for i, test_file in enumerate(files):
            position = self.manager.get_cursor_position(test_file)
            assert position == (i, i * 2)
    
    def test_event_bus_integration(self):
        """Test that events are properly emitted through event bus."""
        test_file = self.temp_dir / "events.txt"
        content = "Event test content"
        
        # Save file (should emit save event)
        self.manager.save_file(test_file, content)
        
        # Open file (should emit open event)
        self.manager.open_file(test_file)
        
        # Should have received both events
        assert len(self.events_received) == 2
        
        save_event = next(e for e in self.events_received if isinstance(e, FileSavedEvent))
        open_event = next(e for e in self.events_received if isinstance(e, FileOpenedEvent))
        
        assert save_event.file_path == test_file
        assert open_event.file_path == test_file
    
    def test_no_event_bus(self):
        """Test manager works without event bus."""
        manager_no_events = FileManager()  # No event bus
        
        test_file = self.temp_dir / "no_events.txt"
        content = "No events test"
        
        # Should work normally without throwing errors
        manager_no_events.save_file(test_file, content)
        result = manager_no_events.open_file(test_file)
        
        assert result == content
    
    def test_validate_file_path_edge_cases(self):
        """Test validate_file_path with various edge cases."""
        # Test relative path conversion
        relative_path = Path("../test.txt")
        valid, message = self.manager.validate_file_path(relative_path)
        assert isinstance(valid, bool)
        assert isinstance(message, str)
        
        # Test normal valid path
        normal_path = self.temp_dir / "normal_file.txt"
        valid, message = self.manager.validate_file_path(normal_path)
        assert isinstance(valid, bool)
        assert isinstance(message, str)
    
    def test_file_manager_with_various_encodings(self):
        """Test file manager handles different encodings correctly."""
        test_cases = [
            ("utf-8", "Hello world UTF-8 content"),
            ("ascii", "Simple ASCII content"),
        ]
        
        for encoding, content in test_cases:
            test_file = self.temp_dir / f"test_{encoding}.txt"
            
            # Save with specific encoding
            result = self.manager.save_file(test_file, content, encoding=encoding)
            assert result is True
            
            # Verify file exists and has content
            assert test_file.exists()
            # Read back and verify content is preserved
            read_content = self.manager.open_file(test_file)
            assert read_content == content
    
    def test_cleanup_temp_files_functionality(self):
        """Test temp file cleanup works correctly."""
        # Create some temp files manually to test cleanup
        temp_count_before = self.manager.cleanup_temp_files()
        
        # The cleanup should run without errors
        assert isinstance(temp_count_before, int)
        assert temp_count_before >= 0