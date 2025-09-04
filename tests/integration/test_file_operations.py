"""
Integration tests for file operations.

Tests real filesystem operations with the FileManager component.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import os
import stat
import time

from tino.components.file_manager.file_manager import FileManager
from tino.core.events.bus import EventBus


class TestFileOperationsIntegration:
    
    def setup_method(self):
        """Set up test fixtures with real filesystem."""
        self.event_bus = EventBus()
        self.manager = FileManager(event_bus=self.event_bus)
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_full_file_lifecycle(self):
        """Test complete file lifecycle: create, edit, backup, restore."""
        test_file = self.temp_dir / "lifecycle.txt"
        
        # 1. Create new file
        original_content = "Original content\nLine 2\nLine 3"
        self.manager.save_file(test_file, original_content)
        
        assert test_file.exists()
        assert test_file.read_text() == original_content
        
        # 2. Open file
        loaded_content = self.manager.open_file(test_file)
        assert loaded_content == original_content
        
        # 3. Modify file (should create backup)
        modified_content = "Modified content\nNew line 2\nLine 3"
        self.manager.save_file(test_file, modified_content)
        
        # 4. Verify backup was created
        backup_path = test_file.with_suffix(test_file.suffix + '.tino.bak')
        assert backup_path.exists()
        assert backup_path.read_text() == original_content
        
        # 5. Verify current file has new content
        assert test_file.read_text() == modified_content
    
    def test_atomic_save_operation(self):
        """Test that file saves are atomic (no partial writes)."""
        test_file = self.temp_dir / "atomic.txt"
        large_content = "Large content\n" * 10000  # Larger content
        
        # Save large file
        success = self.manager.save_file(test_file, large_content)
        
        assert success
        assert test_file.exists()
        
        # File should have complete content, not partial
        saved_content = test_file.read_text()
        assert saved_content == large_content
        assert len(saved_content) == len(large_content)
        
        # No temp files should remain
        temp_files = list(self.temp_dir.glob(".tino_temp_*"))
        assert len(temp_files) == 0
    
    def test_cross_platform_paths(self):
        """Test cross-platform path handling."""
        # Test with various path formats
        paths_to_test = [
            "simple.txt",
            "with spaces.txt",
            "with-dashes.txt",
            "with_underscores.txt",
            "with.multiple.dots.txt",
        ]
        
        for filename in paths_to_test:
            test_file = self.temp_dir / filename
            content = f"Content for {filename}"
            
            # Save and load
            self.manager.save_file(test_file, content)
            loaded = self.manager.open_file(test_file)
            
            assert loaded == content
            assert test_file.exists()
    
    def test_encoding_detection_real_files(self):
        """Test encoding detection with real files."""
        test_cases = [
            ("utf8.txt", "Hello, 世界! 🌍", 'utf-8'),
            ("latin1.txt", "Café naïve résumé", 'latin-1'),
            ("ascii.txt", "Simple ASCII text", 'ascii'),
        ]
        
        for filename, content, encoding in test_cases:
            test_file = self.temp_dir / filename
            
            # Write with specific encoding
            with open(test_file, 'w', encoding=encoding) as f:
                f.write(content)
            
            # Detect encoding
            detected = self.manager.get_encoding(test_file)
            
            # Should detect encoding or compatible one
            if encoding == 'ascii':
                # ASCII is compatible with UTF-8
                assert detected in ['ascii', 'utf-8']
            elif encoding == 'latin-1':
                # Latin-1 might be detected as various ISO-8859 variants
                assert any(enc in detected.lower() for enc in ['latin-1', 'iso-8859'])
            else:
                assert detected.lower() in [encoding.lower(), encoding.replace('-', '')]
    
    def test_large_file_handling(self):
        """Test handling of large files."""
        test_file = self.temp_dir / "large.txt"
        
        # Create file larger than warning threshold
        line_content = "This is a line of text that makes the file large.\n"
        lines_needed = (FileManager.LARGE_FILE_THRESHOLD // len(line_content)) + 1000
        large_content = line_content * lines_needed
        
        # Should handle large file without errors
        success = self.manager.save_file(test_file, large_content)
        assert success
        
        # Should be able to read it back
        loaded_content = self.manager.open_file(test_file)
        assert len(loaded_content) == len(large_content)
        
        # Verify file info
        size, modified, encoding = self.manager.get_file_info(test_file)
        assert size > FileManager.LARGE_FILE_THRESHOLD
    
    def test_binary_file_detection(self):
        """Test binary file detection with real binary data."""
        test_cases = [
            ("image.png", b'\x89PNG\r\n\x1a\n' + b'\x00' * 100, True),
            ("text.txt", b'Plain text content', False),
            ("mixed.dat", b'\x00\x00\x00\x00' + b'Text\x00with\x00nulls\x00' * 10, True),  # More null bytes
        ]
        
        for filename, data, should_be_binary in test_cases:
            test_file = self.temp_dir / filename
            
            # Write binary data
            test_file.write_bytes(data)
            
            # Test detection
            is_binary = self.manager.is_binary_file(test_file)
            assert is_binary == should_be_binary
    
    def test_permission_handling(self):
        """Test handling of permission errors."""
        if os.name == 'nt':  # Skip on Windows (harder to test permissions)
            pytest.skip("Permission tests not reliable on Windows")
        
        test_file = self.temp_dir / "permission.txt"
        test_file.write_text("original content")
        
        # Make parent directory read-only instead of the file
        # This is more likely to cause a PermissionError across platforms
        test_dir = self.temp_dir / "readonly_dir"
        test_dir.mkdir()
        test_file = test_dir / "permission.txt"
        test_file.write_text("original content")
        
        # Make directory read-only
        test_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)  # Read + execute only
        
        try:
            # Should raise PermissionError when trying to create temp file
            with pytest.raises((PermissionError, OSError)):
                self.manager.save_file(test_file, "new content")
        finally:
            # Restore permissions for cleanup
            test_dir.chmod(stat.S_IRWXU)
    
    def test_backup_creation_and_management(self):
        """Test backup creation and management scenarios."""
        test_file = self.temp_dir / "backup_test.txt"
        
        # Create original file
        original_content = "Original content"
        test_file.write_text(original_content)
        
        # First save should create backup
        modified_content = "First modification"
        self.manager.save_file(test_file, modified_content)
        
        backup_path = test_file.with_suffix(test_file.suffix + '.tino.bak')
        assert backup_path.exists()
        assert backup_path.read_text() == original_content
        
        # Second save should NOT create new backup (already backed up in session)
        second_modified = "Second modification"
        self.manager.save_file(test_file, second_modified)
        
        # Backup should still have original content
        assert backup_path.read_text() == original_content
        assert test_file.read_text() == second_modified
    
    def test_recent_files_persistence_across_operations(self):
        """Test recent files tracking across various operations."""
        files = []
        
        # Create and open multiple files
        for i in range(5):
            test_file = self.temp_dir / f"recent{i}.txt"
            test_file.write_text(f"Content {i}")
            files.append(test_file)
            
            self.manager.open_file(test_file)
            time.sleep(0.001)  # Ensure different timestamps
        
        # Check recent files order
        recent = self.manager.get_recent_files()
        assert len(recent) == 5
        # Should be in reverse order (most recent first)
        assert recent == list(reversed(files))
        
        # Open an older file again
        self.manager.open_file(files[1])
        
        # Should move to front
        recent_after = self.manager.get_recent_files()
        assert recent_after[0] == files[1]
    
    def test_cursor_position_memory_integration(self):
        """Test cursor position memory with real file operations."""
        files_and_positions = [
            (self.temp_dir / "file1.txt", (5, 10)),
            (self.temp_dir / "file2.txt", (15, 25)),
            (self.temp_dir / "file3.txt", (0, 0)),
        ]
        
        for test_file, position in files_and_positions:
            # Create file
            test_file.write_text("Some content\nWith multiple lines\nFor cursor testing")
            
            # Open file and set cursor position
            self.manager.open_file(test_file)
            self.manager.set_cursor_position(test_file, position[0], position[1])
        
        # Verify all positions are remembered
        for test_file, expected_position in files_and_positions:
            stored_position = self.manager.get_cursor_position(test_file)
            assert stored_position == expected_position
    
    def test_concurrent_file_operations(self):
        """Test concurrent file operations don't interfere."""
        import threading
        import concurrent.futures
        
        def file_operations(file_index):
            """Perform file operations for testing concurrency."""
            test_file = self.temp_dir / f"concurrent{file_index}.txt"
            content = f"Content for file {file_index}\n" * 100
            
            # Save file
            self.manager.save_file(test_file, content)
            
            # Open file
            loaded = self.manager.open_file(test_file)
            
            # Set cursor position
            self.manager.set_cursor_position(test_file, file_index, file_index * 2)
            
            return test_file, len(loaded)
        
        # Run concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(file_operations, i) for i in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Verify all operations completed successfully
        assert len(results) == 10
        
        for test_file, content_length in results:
            assert test_file.exists()
            assert content_length > 0
            
            # Verify cursor position was set
            position = self.manager.get_cursor_position(test_file)
            assert position is not None
    
    def test_file_validation_edge_cases(self):
        """Test file path validation with edge cases."""
        # Valid cases
        valid_file = self.temp_dir / "valid.txt"
        is_valid, error = self.manager.validate_file_path(valid_file)
        assert is_valid
        assert error == ""
        
        # Invalid parent directory
        invalid_file = Path("/nonexistent_parent_12345/file.txt")
        is_valid, error = self.manager.validate_file_path(invalid_file)
        assert not is_valid
        assert "does not exist" in error.lower()
    
    def test_temp_file_cleanup_integration(self):
        """Test temp file cleanup in real scenarios."""
        # Perform several save operations
        for i in range(3):
            test_file = self.temp_dir / f"cleanup{i}.txt"
            self.manager.save_file(test_file, f"Content {i}")
        
        # Manually create some temp files (simulating interrupted operations)
        temp_files = [
            self.temp_dir / ".tino_temp_file1_123.tmp",
            self.temp_dir / ".tino_temp_file2_456.tmp"
        ]
        
        for temp_file in temp_files:
            temp_file.write_text("temp content")
        
        # Cleanup should remove temp files
        cleaned = self.manager.cleanup_temp_files()
        
        assert cleaned >= len(temp_files)
        for temp_file in temp_files:
            assert not temp_file.exists()
    
    def test_encoding_preservation_cycle(self):
        """Test encoding preservation through save/load cycles."""
        test_cases = [
            ("utf8_cycle.txt", "UTF-8 with émojis 🎉", 'utf-8'),
            ("latin1_cycle.txt", "Latin-1 with café", 'latin-1'),
        ]
        
        for filename, content, encoding in test_cases:
            test_file = self.temp_dir / filename
            
            # Save with specific encoding
            self.manager.save_file(test_file, content, encoding)
            
            # Verify encoding detection
            detected = self.manager.get_encoding(test_file)
            
            # Load content
            loaded = self.manager.open_file(test_file)
            
            # Content should match
            assert loaded == content
            
            # Save again (should preserve encoding)
            modified_content = content + "\nAdded line"
            self.manager.save_file(test_file, modified_content)
            
            # Load again
            final_loaded = self.manager.open_file(test_file)
            assert final_loaded == modified_content
    
    def test_file_info_accuracy(self):
        """Test accuracy of file information."""
        test_file = self.temp_dir / "info_test.txt"
        content = "Test content for file info\nWith multiple lines"
        
        self.manager.save_file(test_file, content, encoding='utf-8')
        
        # Get info through manager
        size, modified, encoding = self.manager.get_file_info(test_file)
        
        # Verify against actual file stats
        actual_stat = test_file.stat()
        actual_content = test_file.read_text(encoding='utf-8')
        
        assert size == actual_stat.st_size
        assert abs(modified - actual_stat.st_mtime) < 1  # Allow small timing difference
        # Simple ASCII content might be detected as ASCII or UTF-8
        assert encoding.lower() in ['ascii', 'utf-8']
        assert len(actual_content) > 0
    
    def test_manager_stats_accuracy(self):
        """Test accuracy of manager statistics."""
        # Create some files and operations
        for i in range(3):
            test_file = self.temp_dir / f"stats{i}.txt"
            content = f"Stats test content {i}"
            
            self.manager.save_file(test_file, content)
            self.manager.open_file(test_file)
            self.manager.set_cursor_position(test_file, i, i * 2)
        
        stats = self.manager.get_manager_stats()
        
        # Verify statistics accuracy
        assert stats['recent_files']['total_files'] == 3
        assert stats['cursor_memory']['total_files'] == 3
        assert stats['backup_info']['backed_up_files'] >= 0
        
        # Verify stat ranges make sense
        assert stats['cursor_memory']['max_line'] >= 0
        assert stats['cursor_memory']['max_column'] >= 0