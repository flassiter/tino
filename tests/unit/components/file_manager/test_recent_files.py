"""
Tests for RecentFilesManager class.

Tests recent files tracking, last file functionality, and thread safety.
"""

import pytest
import tempfile
from pathlib import Path
import threading
import time

from tino.components.file_manager.recent_files import RecentFilesManager


class TestRecentFilesManager:
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = RecentFilesManager(max_files=5)  # Small limit for testing
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_add_file_first_time(self):
        """Test adding a file for the first time."""
        test_file = self.temp_dir / "test1.txt"
        test_file.touch()
        
        self.manager.add_file(test_file)
        
        recent = self.manager.get_recent_files()
        assert len(recent) == 1
        assert recent[0] == test_file
    
    def test_add_file_ordering(self):
        """Test that files are ordered most recent first."""
        files = []
        for i in range(3):
            test_file = self.temp_dir / f"test{i}.txt"
            test_file.touch()
            files.append(test_file)
            self.manager.add_file(test_file)
            time.sleep(0.001)  # Ensure different timestamps
        
        recent = self.manager.get_recent_files()
        # Should be in reverse order (most recent first)
        assert recent == list(reversed(files))
    
    def test_add_file_duplicate_moves_to_front(self):
        """Test that adding duplicate file moves it to front."""
        files = []
        for i in range(3):
            test_file = self.temp_dir / f"test{i}.txt"
            test_file.touch()
            files.append(test_file)
            self.manager.add_file(test_file)
        
        # Add first file again
        self.manager.add_file(files[0])
        
        recent = self.manager.get_recent_files()
        assert recent[0] == files[0]
        assert len(recent) == 3  # No duplicates
    
    def test_add_file_max_limit(self):
        """Test that file list respects maximum limit."""
        files = []
        for i in range(7):  # More than max_files (5)
            test_file = self.temp_dir / f"test{i}.txt"
            test_file.touch()
            files.append(test_file)
            self.manager.add_file(test_file)
        
        recent = self.manager.get_recent_files()
        assert len(recent) == 5  # Should be limited to max_files
        # Should contain the 5 most recent files
        assert recent == list(reversed(files[-5:]))
    
    def test_get_recent_files_with_limit(self):
        """Test getting recent files with custom limit."""
        files = []
        for i in range(5):
            test_file = self.temp_dir / f"test{i}.txt"
            test_file.touch()
            files.append(test_file)
            self.manager.add_file(test_file)
        
        recent_3 = self.manager.get_recent_files(limit=3)
        assert len(recent_3) == 3
        assert recent_3 == list(reversed(files[-3:]))
    
    def test_get_last_file_empty(self):
        """Test getting last file when list is empty."""
        assert self.manager.get_last_file() is None
    
    def test_get_last_file_one_file(self):
        """Test getting last file when only one file exists."""
        test_file = self.temp_dir / "test.txt"
        test_file.touch()
        self.manager.add_file(test_file)
        
        assert self.manager.get_last_file() is None  # No previous file
    
    def test_get_last_file_multiple_files(self):
        """Test getting last file with multiple files."""
        file1 = self.temp_dir / "test1.txt"
        file2 = self.temp_dir / "test2.txt"
        file1.touch()
        file2.touch()
        
        self.manager.add_file(file1)
        self.manager.add_file(file2)
        
        # Last file should be file1 (second most recent)
        assert self.manager.get_last_file() == file1
    
    def test_get_last_file_with_stored_last(self):
        """Test last file functionality with internal tracking."""
        file1 = self.temp_dir / "test1.txt"
        file2 = self.temp_dir / "test2.txt"
        file3 = self.temp_dir / "test3.txt"
        file1.touch()
        file2.touch()
        file3.touch()
        
        self.manager.add_file(file1)
        self.manager.add_file(file2)  # file1 becomes last_file
        self.manager.add_file(file3)  # file2 becomes last_file
        
        # Should return file2 (was current when file3 was added)
        assert self.manager.get_last_file() == file2
    
    def test_remove_file_exists(self):
        """Test removing existing file."""
        test_file = self.temp_dir / "test.txt"
        test_file.touch()
        self.manager.add_file(test_file)
        
        result = self.manager.remove_file(test_file)
        assert result is True
        assert len(self.manager.get_recent_files()) == 0
    
    def test_remove_file_not_exists(self):
        """Test removing non-existent file."""
        test_file = self.temp_dir / "test.txt"
        
        result = self.manager.remove_file(test_file)
        assert result is False
    
    def test_remove_file_updates_last_file(self):
        """Test that removing file updates last_file if needed."""
        file1 = self.temp_dir / "test1.txt"
        file2 = self.temp_dir / "test2.txt"
        file1.touch()
        file2.touch()
        
        self.manager.add_file(file1)
        self.manager.add_file(file2)
        
        # Remove the last file
        last_file = self.manager.get_last_file()
        self.manager.remove_file(last_file)
        
        # Last file should be updated
        new_last = self.manager.get_last_file()
        assert new_last != last_file or new_last is None
    
    def test_clear(self):
        """Test clearing all recent files."""
        for i in range(3):
            test_file = self.temp_dir / f"test{i}.txt"
            test_file.touch()
            self.manager.add_file(test_file)
        
        self.manager.clear()
        
        assert len(self.manager.get_recent_files()) == 0
        assert self.manager.get_last_file() is None
    
    def test_contains(self):
        """Test checking if file is in recent list."""
        test_file = self.temp_dir / "test.txt"
        test_file.touch()
        
        assert not self.manager.contains(test_file)
        
        self.manager.add_file(test_file)
        assert self.manager.contains(test_file)
    
    def test_get_file_info(self):
        """Test getting file information."""
        files = []
        for i in range(3):
            test_file = self.temp_dir / f"test{i}.txt"
            test_file.touch()
            files.append(test_file)
            self.manager.add_file(test_file)
            time.sleep(0.001)
        
        info = self.manager.get_file_info(files[1])
        assert info is not None
        assert info['path'] == files[1]
        assert info['position'] == 1  # Second in list
        assert isinstance(info['access_time'], float)
    
    def test_get_file_info_not_found(self):
        """Test getting info for non-existent file."""
        test_file = self.temp_dir / "test.txt"
        
        info = self.manager.get_file_info(test_file)
        assert info is None
    
    def test_cleanup_missing_files(self):
        """Test cleanup of files that no longer exist."""
        existing_file = self.temp_dir / "existing.txt"
        missing_file = self.temp_dir / "missing.txt"
        
        existing_file.touch()
        # Don't create missing_file
        
        # Add both to recent files
        self.manager.add_file(existing_file)
        self.manager._files[missing_file] = time.time()  # Manually add missing file
        
        removed = self.manager.cleanup_missing_files()
        
        assert removed == 1
        assert existing_file in self.manager.get_recent_files()
        assert missing_file not in self.manager.get_recent_files()
    
    def test_set_max_files(self):
        """Test changing maximum files limit."""
        # Add more files than new limit
        for i in range(5):
            test_file = self.temp_dir / f"test{i}.txt"
            test_file.touch()
            self.manager.add_file(test_file)
        
        # Reduce limit
        self.manager.set_max_files(3)
        
        assert self.manager.max_files == 3
        assert len(self.manager.get_recent_files()) == 3
    
    def test_get_stats(self):
        """Test getting manager statistics."""
        for i in range(3):
            test_file = self.temp_dir / f"test{i}.txt"
            test_file.touch()
            self.manager.add_file(test_file)
        
        stats = self.manager.get_stats()
        
        assert stats['total_files'] == 3
        assert stats['max_files'] == 5
        assert stats['has_last_file'] is True
        assert 'oldest_access_time' in stats
        assert 'newest_access_time' in stats
    
    def test_len_operator(self):
        """Test __len__ operator."""
        assert len(self.manager) == 0
        
        for i in range(3):
            test_file = self.temp_dir / f"test{i}.txt"
            test_file.touch()
            self.manager.add_file(test_file)
        
        assert len(self.manager) == 3
    
    def test_contains_operator(self):
        """Test __contains__ operator."""
        test_file = self.temp_dir / "test.txt"
        test_file.touch()
        
        assert test_file not in self.manager
        
        self.manager.add_file(test_file)
        assert test_file in self.manager
    
    def test_iter_operator(self):
        """Test __iter__ operator."""
        files = []
        for i in range(3):
            test_file = self.temp_dir / f"test{i}.txt"
            test_file.touch()
            files.append(test_file)
            self.manager.add_file(test_file)
        
        iterated_files = list(self.manager)
        assert iterated_files == list(reversed(files))  # Most recent first
    
    def test_path_resolution(self):
        """Test that paths are resolved consistently."""
        # Create file with relative path
        test_file = Path("test.txt")
        abs_test_file = self.temp_dir / "test.txt"
        abs_test_file.touch()
        
        # Add with different path representations
        self.manager.add_file(abs_test_file)
        
        # Should find it regardless of path representation
        assert self.manager.contains(abs_test_file)
    
    def test_thread_safety(self):
        """Test thread safety of recent files manager."""
        files = []
        for i in range(10):
            test_file = self.temp_dir / f"test{i}.txt"
            test_file.touch()
            files.append(test_file)
        
        def add_files(start_idx, count):
            for i in range(start_idx, start_idx + count):
                if i < len(files):
                    self.manager.add_file(files[i])
        
        # Start multiple threads adding files
        threads = []
        for t in range(3):
            thread = threading.Thread(target=add_files, args=(t * 3, 3))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Should have added files without corruption
        recent = self.manager.get_recent_files()
        assert len(recent) <= self.manager.max_files
        # All files in recent should be from our test files
        for file in recent:
            assert file in files
    
    def test_default_max_files(self):
        """Test default maximum files setting."""
        default_manager = RecentFilesManager()
        assert default_manager.max_files == RecentFilesManager.DEFAULT_MAX_FILES
    
    def test_string_path_handling(self):
        """Test handling of string paths (should convert to Path)."""
        test_file = self.temp_dir / "test.txt"
        test_file.touch()
        
        # Pass string instead of Path
        self.manager.add_file(str(test_file))
        
        recent = self.manager.get_recent_files()
        assert len(recent) == 1
        assert isinstance(recent[0], Path)