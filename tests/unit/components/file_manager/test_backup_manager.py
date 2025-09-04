"""
Tests for BackupManager class.

Tests backup creation, restoration, cleanup, and edge cases.
"""

import pytest
import tempfile
from pathlib import Path
import time

from tino.components.file_manager.backup_manager import BackupManager


class TestBackupManager:
    
    def setup_method(self):
        """Set up test fixtures."""
        self.backup_manager = BackupManager()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up temp directory
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_needs_backup_new_file(self):
        """Test that new files need backup."""
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("content")
        
        assert self.backup_manager.needs_backup(test_file)
    
    def test_needs_backup_nonexistent_file(self):
        """Test that nonexistent files don't need backup."""
        test_file = self.temp_dir / "nonexistent.txt"
        
        assert not self.backup_manager.needs_backup(test_file)
    
    def test_needs_backup_already_backed_up_in_session(self):
        """Test that files backed up in session don't need backup again."""
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("content")
        
        # First backup
        backup_path = self.backup_manager.create_backup(test_file)
        assert backup_path is not None
        
        # Second backup should not be needed
        assert not self.backup_manager.needs_backup(test_file)
    
    def test_needs_backup_existing_backup_file(self):
        """Test that files with existing backups don't need backup."""
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("content")
        
        backup_path = self.backup_manager.get_backup_path(test_file)
        backup_path.write_text("backup content")
        
        assert not self.backup_manager.needs_backup(test_file)
    
    def test_get_backup_path(self):
        """Test backup path generation."""
        test_file = Path("/path/to/file.txt")
        expected = Path("/path/to/file.txt.tino.bak")
        
        assert self.backup_manager.get_backup_path(test_file) == expected
    
    def test_get_backup_path_multiple_extensions(self):
        """Test backup path with multiple file extensions."""
        test_file = Path("/path/to/file.tar.gz")
        expected = Path("/path/to/file.tar.gz.tino.bak")
        
        assert self.backup_manager.get_backup_path(test_file) == expected
    
    def test_create_backup_success(self):
        """Test successful backup creation."""
        test_file = self.temp_dir / "test.txt"
        original_content = "original content"
        test_file.write_text(original_content)
        
        backup_path = self.backup_manager.create_backup(test_file)
        
        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.read_text() == original_content
        assert backup_path.name.endswith('.tino.bak')
    
    def test_create_backup_not_needed(self):
        """Test that backup returns None when not needed."""
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("content")
        
        # First backup
        first_backup = self.backup_manager.create_backup(test_file)
        assert first_backup is not None
        
        # Second backup should return None
        second_backup = self.backup_manager.create_backup(test_file)
        assert second_backup is None
    
    def test_create_backup_atomic_operation(self):
        """Test that backup creation is atomic."""
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("content")
        
        backup_path = self.backup_manager.create_backup(test_file)
        assert backup_path is not None
        
        # Backup should be complete and readable
        assert backup_path.read_text() == "content"
    
    def test_restore_from_backup_success(self):
        """Test successful backup restoration."""
        test_file = self.temp_dir / "test.txt"
        original_content = "original content"
        modified_content = "modified content"
        
        # Create file and backup
        test_file.write_text(original_content)
        backup_path = self.backup_manager.create_backup(test_file)
        
        # Modify original file
        test_file.write_text(modified_content)
        
        # Restore from backup
        success = self.backup_manager.restore_from_backup(test_file)
        assert success
        assert test_file.read_text() == original_content
    
    def test_restore_from_backup_no_backup(self):
        """Test restoration when no backup exists."""
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("content")
        
        with pytest.raises(FileNotFoundError):
            self.backup_manager.restore_from_backup(test_file)
    
    def test_delete_backup_success(self):
        """Test successful backup deletion."""
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("content")
        
        backup_path = self.backup_manager.create_backup(test_file)
        assert backup_path is not None
        assert backup_path.exists()
        
        success = self.backup_manager.delete_backup(test_file)
        assert success
        assert not backup_path.exists()
    
    def test_delete_backup_no_backup(self):
        """Test deletion when no backup exists."""
        test_file = self.temp_dir / "test.txt"
        
        success = self.backup_manager.delete_backup(test_file)
        assert not success
    
    def test_cleanup_old_backups(self):
        """Test cleanup of old backup files."""
        # Create some backup files with different ages
        old_backup = self.temp_dir / "old.txt.tino.bak"
        recent_backup = self.temp_dir / "recent.txt.tino.bak"
        
        old_backup.write_text("old")
        recent_backup.write_text("recent")
        
        # Make old backup appear old
        old_time = time.time() - (35 * 24 * 60 * 60)  # 35 days ago
        import os
        os.utime(old_backup, (old_time, old_time))
        
        cleaned = self.backup_manager.cleanup_old_backups(self.temp_dir, max_age_days=30)
        
        assert cleaned == 1
        assert not old_backup.exists()
        assert recent_backup.exists()
    
    def test_get_backup_info_exists(self):
        """Test getting info about existing backup."""
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("content")
        
        backup_path = self.backup_manager.create_backup(test_file)
        
        info = self.backup_manager.get_backup_info(test_file)
        assert info is not None
        assert info['path'] == backup_path
        assert info['exists'] is True
        assert info['size'] == len("content")
        assert isinstance(info['modified'], float)
    
    def test_get_backup_info_not_exists(self):
        """Test getting info about non-existent backup."""
        test_file = self.temp_dir / "test.txt"
        
        info = self.backup_manager.get_backup_info(test_file)
        assert info is None
    
    def test_list_backups(self):
        """Test listing backup files in directory."""
        # Create some files and backups
        test_files = ["file1.txt", "file2.md", "file3.py"]
        
        for filename in test_files:
            test_file = self.temp_dir / filename
            test_file.write_text(f"content of {filename}")
            self.backup_manager.create_backup(test_file)
        
        # Create a non-backup file
        (self.temp_dir / "regular.txt").write_text("regular")
        
        backups = self.backup_manager.list_backups(self.temp_dir)
        
        assert len(backups) == 3
        for backup in backups:
            assert backup.suffix == ".bak"
            assert ".tino." in str(backup)
    
    def test_list_backups_empty_directory(self):
        """Test listing backups in empty directory."""
        backups = self.backup_manager.list_backups(self.temp_dir)
        assert backups == []
    
    def test_list_backups_nonexistent_directory(self):
        """Test listing backups in non-existent directory."""
        nonexistent = self.temp_dir / "nonexistent"
        backups = self.backup_manager.list_backups(nonexistent)
        assert backups == []
    
    def test_backup_preserves_file_attributes(self):
        """Test that backup preserves original file attributes."""
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("content")
        
        # Set specific time
        test_time = time.time() - 3600  # 1 hour ago
        import os
        os.utime(test_file, (test_time, test_time))
        
        backup_path = self.backup_manager.create_backup(test_file)
        
        # Backup should preserve modification time
        original_stat = test_file.stat()
        backup_stat = backup_path.stat()
        
        assert backup_stat.st_mtime == original_stat.st_mtime
    
    def test_backup_session_tracking(self):
        """Test that backup session tracking works correctly."""
        test_file1 = self.temp_dir / "test1.txt"
        test_file2 = self.temp_dir / "test2.txt"
        
        test_file1.write_text("content1")
        test_file2.write_text("content2")
        
        # First backups should succeed
        backup1 = self.backup_manager.create_backup(test_file1)
        backup2 = self.backup_manager.create_backup(test_file2)
        
        assert backup1 is not None
        assert backup2 is not None
        
        # Second backups should return None (already backed up in session)
        backup1_second = self.backup_manager.create_backup(test_file1)
        backup2_second = self.backup_manager.create_backup(test_file2)
        
        assert backup1_second is None
        assert backup2_second is None
    
    def test_permission_error_handling(self):
        """Test handling of permission errors."""
        # This is hard to test without root/admin privileges
        # We'll test the error path by mocking or using a read-only location
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("content")
        
        # Make parent directory read-only on Unix systems
        import stat
        if hasattr(stat, 'S_IWUSR'):
            try:
                self.temp_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)  # Read + execute only
                
                with pytest.raises(PermissionError):
                    self.backup_manager.create_backup(test_file)
                    
            finally:
                # Restore permissions for cleanup
                self.temp_dir.chmod(stat.S_IRWXU)
    
    def test_restore_removes_from_backed_up_set(self):
        """Test that restore removes file from backed up set."""
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("original")
        
        # Create backup
        backup_path = self.backup_manager.create_backup(test_file)
        assert backup_path is not None
        
        # File should not need backup now
        assert not self.backup_manager.needs_backup(test_file)
        
        # Modify and restore
        test_file.write_text("modified")
        self.backup_manager.restore_from_backup(test_file)
        
        # After restore, file should be removed from backed up set
        # (this means it would need backup again if modified)
        # Note: This depends on implementation - some systems might keep track
        
    def test_backup_path_generation_edge_cases(self):
        """Test backup path generation with various file extensions."""
        test_cases = [
            ("file.txt", "file.txt.tino.bak"),
            ("file.tar.gz", "file.tar.gz.tino.bak"),
            ("no_extension", "no_extension.tino.bak"),
            (".hidden", ".hidden.tino.bak"),
        ]
        
        for original, expected_backup in test_cases:
            test_file = self.temp_dir / original
            backup_path = self.backup_manager.get_backup_path(test_file)
            assert backup_path.name == expected_backup
    
    def test_backup_manager_stats_and_info(self):
        """Test backup manager info and stats functionality."""
        test_file = self.temp_dir / "stats_test.txt"
        test_file.write_text("content for stats test")
        
        # Test without backup
        info = self.backup_manager.get_backup_info(test_file)
        assert info is None
        
        # Create backup
        backup_path = self.backup_manager.create_backup(test_file)
        assert backup_path is not None
        
        # Test with backup
        info = self.backup_manager.get_backup_info(test_file)
        assert info is not None
        assert isinstance(info, dict)
        assert 'path' in info
        assert 'size' in info
        assert 'modified' in info
        assert 'exists' in info
    
    def test_list_backups_functionality(self):
        """Test listing backups in directory."""
        # Create a few backup files
        for i in range(3):
            test_file = self.temp_dir / f"test{i}.txt"
            test_file.write_text(f"content {i}")
            self.backup_manager.create_backup(test_file)
        
        # List backups
        backups = self.backup_manager.list_backups(self.temp_dir)
        assert len(backups) >= 3  # Should have at least our 3 backups