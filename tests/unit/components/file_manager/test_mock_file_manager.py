"""
Tests for MockFileManager class.

Tests the mock implementation to ensure it behaves correctly for testing.
"""

import pytest
from pathlib import Path

from tino.components.file_manager.mock import MockFileManager
from tino.core.events.bus import EventBus
from tino.core.events.types import FileOpenedEvent, FileSavedEvent


class TestMockFileManager:
    
    def setup_method(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()
        self.mock = MockFileManager(event_bus=self.event_bus)
        
        # Track events for testing
        self.events_received = []
        self.event_bus.subscribe(FileOpenedEvent, self._record_event)
        self.event_bus.subscribe(FileSavedEvent, self._record_event)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.mock.reset_mock()
    
    def _record_event(self, event):
        """Record events for testing."""
        self.events_received.append(event)
    
    def test_add_mock_file(self):
        """Test adding mock files."""
        test_file = Path("/test/file.txt")
        content = "Test content"
        
        self.mock.add_mock_file(test_file, content, encoding='utf-8')
        
        mock_files = self.mock.get_mock_files()
        assert test_file in mock_files
        assert mock_files[test_file] == content
    
    def test_add_mock_binary_file(self):
        """Test adding binary mock file."""
        test_file = Path("/test/binary.bin")
        content = "binary content"
        
        self.mock.add_mock_file(test_file, content, is_binary=True)
        
        assert self.mock.is_binary_file(test_file)
    
    def test_remove_mock_file(self):
        """Test removing mock file."""
        test_file = Path("/test/file.txt")
        
        self.mock.add_mock_file(test_file, "content")
        assert self.mock.file_exists(test_file)
        
        self.mock.remove_mock_file(test_file)
        assert not self.mock.file_exists(test_file)
    
    def test_open_file_success(self):
        """Test opening existing mock file."""
        test_file = Path("/test/file.txt")
        content = "Test content"
        
        self.mock.add_mock_file(test_file, content)
        result = self.mock.open_file(test_file)
        
        assert result == content
        
        # Should emit event
        assert len(self.events_received) == 1
        assert isinstance(self.events_received[0], FileOpenedEvent)
    
    def test_open_file_not_exists(self):
        """Test opening non-existent mock file."""
        test_file = Path("/test/nonexistent.txt")
        
        with pytest.raises(FileNotFoundError):
            self.mock.open_file(test_file)
    
    def test_open_file_binary(self):
        """Test opening binary mock file should fail."""
        test_file = Path("/test/binary.bin")
        
        self.mock.add_mock_file(test_file, "content", is_binary=True)
        
        with pytest.raises(ValueError, match="Cannot open binary file"):
            self.mock.open_file(test_file)
    
    def test_save_file_new(self):
        """Test saving new mock file."""
        test_file = Path("/test/new.txt")
        content = "New content"
        
        result = self.mock.save_file(test_file, content)
        
        assert result is True
        assert self.mock.file_exists(test_file)
        assert self.mock.get_mock_files()[test_file] == content
        
        # Should emit event
        save_events = [e for e in self.events_received if isinstance(e, FileSavedEvent)]
        assert len(save_events) == 1
        assert not save_events[0].backup_created  # No backup for new file
    
    def test_save_file_existing_creates_backup(self):
        """Test saving existing mock file creates backup."""
        test_file = Path("/test/existing.txt")
        original_content = "Original"
        new_content = "New content"
        
        # Add existing file
        self.mock.add_mock_file(test_file, original_content)
        
        # Save new content
        result = self.mock.save_file(test_file, new_content)
        
        assert result is True
        assert self.mock.get_mock_files()[test_file] == new_content
        
        # Check backup was created
        backup_files = self.mock.get_backup_files()
        backup_path = test_file.with_suffix(test_file.suffix + '.tino.bak')
        assert test_file in backup_files
        assert backup_files[test_file] == backup_path
        assert self.mock.get_mock_files()[backup_path] == original_content
    
    def test_create_backup(self):
        """Test backup creation."""
        test_file = Path("/test/backup.txt")
        content = "Backup me"
        
        self.mock.add_mock_file(test_file, content)
        backup_path = self.mock.create_backup(test_file)
        
        assert backup_path is not None
        assert self.mock.file_exists(backup_path)
        assert self.mock.get_mock_files()[backup_path] == content
    
    def test_create_backup_already_backed_up(self):
        """Test that second backup returns None."""
        test_file = Path("/test/backup.txt")
        
        self.mock.add_mock_file(test_file, "content")
        
        first_backup = self.mock.create_backup(test_file)
        second_backup = self.mock.create_backup(test_file)
        
        assert first_backup is not None
        assert second_backup is None
    
    def test_get_encoding(self):
        """Test encoding retrieval."""
        test_file = Path("/test/encoded.txt")
        
        self.mock.add_mock_file(test_file, "content", encoding='latin-1')
        encoding = self.mock.get_encoding(test_file)
        
        assert encoding == 'latin-1'
    
    def test_get_file_info(self):
        """Test file info retrieval."""
        test_file = Path("/test/info.txt")
        content = "File info test"
        
        self.mock.add_mock_file(test_file, content, encoding='utf-8')
        
        size, modified, encoding = self.mock.get_file_info(test_file)
        
        assert size == len(content.encode('utf-8'))
        assert isinstance(modified, float)
        assert encoding == 'utf-8'
    
    def test_recent_files_functionality(self):
        """Test recent files tracking."""
        files = [Path(f"/test/file{i}.txt") for i in range(3)]
        
        for i, file_path in enumerate(files):
            self.mock.add_mock_file(file_path, f"content {i}")
            self.mock.add_recent_file(file_path)
        
        recent = self.mock.get_recent_files()
        # Should be in reverse order (most recent first)
        assert recent == list(reversed(files))
    
    def test_last_file_functionality(self):
        """Test last file tracking."""
        file1 = Path("/test/file1.txt")
        file2 = Path("/test/file2.txt")
        
        self.mock.add_mock_file(file1, "content1")
        self.mock.add_mock_file(file2, "content2")
        
        self.mock.add_recent_file(file1)
        self.mock.add_recent_file(file2)
        
        last_file = self.mock.get_last_file()
        assert last_file == file1  # Previous file
    
    def test_cursor_position_tracking(self):
        """Test cursor position functionality."""
        test_file = Path("/test/cursor.txt")
        
        self.mock.set_cursor_position(test_file, 5, 10)
        position = self.mock.get_cursor_position(test_file)
        
        assert position == (5, 10)
    
    def test_validate_file_path(self):
        """Test file path validation (always valid in mock)."""
        test_file = Path("/any/path/file.txt")
        
        is_valid, error = self.mock.validate_file_path(test_file)
        
        assert is_valid is True
        assert error == ""
    
    def test_get_temp_file_path(self):
        """Test temporary file path generation."""
        test_file = Path("/test/original.txt")
        
        temp_path = self.mock.get_temp_file_path(test_file)
        
        assert temp_path.suffix == ".tmp"
        assert "original.txt" in str(temp_path)
    
    def test_cleanup_temp_files(self):
        """Test cleanup of temporary files."""
        temp_file = Path("/test/file.tmp")
        regular_file = Path("/test/regular.txt")
        
        self.mock.add_mock_file(temp_file, "temp content")
        self.mock.add_mock_file(regular_file, "regular content")
        
        cleaned = self.mock.cleanup_temp_files()
        
        assert cleaned == 1
        assert not self.mock.file_exists(temp_file)
        assert self.mock.file_exists(regular_file)
    
    def test_operation_history_tracking(self):
        """Test that operations are tracked in history."""
        test_file = Path("/test/history.txt")
        content = "History test"
        
        self.mock.add_mock_file(test_file, content)
        self.mock.open_file(test_file)
        self.mock.save_file(test_file, "new content")
        
        history = self.mock.get_operation_history()
        
        assert len(history) >= 2
        
        # Check operation types are recorded
        operations = [op[0] for op in history]
        assert 'open_file' in operations
        assert 'save_file' in operations
    
    def test_clear_operation_history(self):
        """Test clearing operation history."""
        test_file = Path("/test/clear.txt")
        
        self.mock.add_mock_file(test_file, "content")
        self.mock.open_file(test_file)
        
        assert len(self.mock.get_operation_history()) > 0
        
        self.mock.clear_operation_history()
        assert len(self.mock.get_operation_history()) == 0
    
    def test_simulate_error(self):
        """Test error simulation functionality."""
        test_file = Path("/test/error.txt")
        
        # Simulate FileNotFoundError on open_file
        self.mock.simulate_error('open_file', FileNotFoundError("Simulated error"))
        
        with pytest.raises(FileNotFoundError, match="Simulated error"):
            self.mock.open_file(test_file)
    
    def test_clear_error_simulation(self):
        """Test clearing error simulation."""
        test_file = Path("/test/clear_error.txt")
        
        # Set up error simulation
        self.mock.simulate_error('open_file', ValueError("Test error"))
        
        # Clear it
        self.mock.clear_error_simulation('open_file')
        
        # Add file and try to open (should work now)
        self.mock.add_mock_file(test_file, "content")
        result = self.mock.open_file(test_file)
        assert result == "content"
    
    def test_reset_mock(self):
        """Test resetting mock to initial state."""
        test_file = Path("/test/reset.txt")
        
        # Add some data
        self.mock.add_mock_file(test_file, "content")
        self.mock.add_recent_file(test_file)
        self.mock.set_cursor_position(test_file, 5, 10)
        self.mock.open_file(test_file)
        
        # Verify data exists
        assert len(self.mock.get_mock_files()) > 0
        assert len(self.mock.get_recent_files()) > 0
        assert len(self.mock.get_operation_history()) > 0
        
        # Reset
        self.mock.reset_mock()
        
        # Verify everything is cleared
        assert len(self.mock.get_mock_files()) == 0
        assert len(self.mock.get_recent_files()) == 0
        assert self.mock.get_cursor_position(test_file) is None
        assert len(self.mock.get_operation_history()) == 0
    
    def test_file_watching_not_implemented(self):
        """Test file watching returns False (not implemented)."""
        test_file = Path("/test/watch.txt")
        
        assert self.mock.watch_file(test_file) is False
        assert self.mock.unwatch_file(test_file) is False
    
    def test_max_recent_files_configuration(self):
        """Test configuring maximum recent files."""
        self.mock.max_recent_files = 3
        
        # Add more files than limit
        for i in range(5):
            test_file = Path(f"/test/file{i}.txt")
            self.mock.add_mock_file(test_file, f"content {i}")
            self.mock.add_recent_file(test_file)
        
        recent = self.mock.get_recent_files()
        assert len(recent) == 3  # Should be limited
    
    def test_string_path_conversion(self):
        """Test that string paths are handled correctly."""
        test_file_str = "/test/string_path.txt"
        test_file_path = Path(test_file_str)
        content = "String path test"
        
        # Add with string
        self.mock.add_mock_file(test_file_str, content)
        
        # Should be accessible with Path object
        assert self.mock.file_exists(test_file_path)
        result = self.mock.open_file(test_file_path)
        assert result == content
    
    def test_event_emission_without_bus(self):
        """Test that mock works without event bus."""
        mock_no_events = MockFileManager()  # No event bus
        
        test_file = Path("/test/no_events.txt")
        content = "No events test"
        
        # Should work normally
        mock_no_events.add_mock_file(test_file, content)
        result = mock_no_events.open_file(test_file)
        
        assert result == content
    
    def test_binary_file_marking(self):
        """Test binary file marking and detection."""
        text_file = Path("/test/text.txt")
        binary_file = Path("/test/binary.bin")
        
        self.mock.add_mock_file(text_file, "text content", is_binary=False)
        self.mock.add_mock_file(binary_file, "binary content", is_binary=True)
        
        assert not self.mock.is_binary_file(text_file)
        assert self.mock.is_binary_file(binary_file)
    
    def test_backup_cleanup_on_file_removal(self):
        """Test that removing file cleans up related data."""
        test_file = Path("/test/cleanup.txt")
        
        # Add file and create backup
        self.mock.add_mock_file(test_file, "content")
        self.mock.add_recent_file(test_file)
        self.mock.set_cursor_position(test_file, 5, 10)
        backup_path = self.mock.create_backup(test_file)
        
        # Verify data exists
        assert self.mock.file_exists(test_file)
        assert backup_path in self.mock.get_mock_files()
        assert test_file in self.mock.get_recent_files()
        assert self.mock.get_cursor_position(test_file) is not None
        
        # Remove file
        self.mock.remove_mock_file(test_file)
        
        # Verify cleanup
        assert not self.mock.file_exists(test_file)
        assert test_file not in self.mock.get_recent_files()
        assert self.mock.get_cursor_position(test_file) is None
        assert test_file not in self.mock.get_backup_files()