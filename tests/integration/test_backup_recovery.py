"""
Integration tests for backup creation and recovery.

Tests backup functionality with real filesystem operations.
"""

import os
import shutil
import tempfile
import time
from pathlib import Path

import pytest

from tino.components.file_manager.backup_manager import BackupManager
from tino.components.file_manager.file_manager import FileManager


class TestBackupRecoveryIntegration:

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = FileManager()
        self.backup_manager = BackupManager()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_backup_creation_workflow(self):
        """Test complete backup creation workflow."""
        test_file = self.temp_dir / "backup_workflow.txt"

        # Step 1: Create original file
        original_content = "Original file content\nWith multiple lines\nFor testing"
        test_file.write_text(original_content)

        # Step 2: Create backup manually
        backup_path = self.backup_manager.create_backup(test_file)

        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.name == "backup_workflow.txt.tino.bak"
        assert backup_path.read_text() == original_content

        # Step 3: Modify original file
        modified_content = "Modified content\nDifferent from original"
        test_file.write_text(modified_content)

        # Step 4: Verify backup still has original content
        assert backup_path.read_text() == original_content
        assert test_file.read_text() == modified_content

    def test_backup_through_save_operations(self):
        """Test backup creation through FileManager save operations."""
        test_file = self.temp_dir / "save_backup.txt"

        # Create original file outside of FileManager
        original_content = "Original content created externally"
        test_file.write_text(original_content)

        # First save through manager should create backup
        new_content = "New content saved through manager"
        success = self.manager.save_file(test_file, new_content)

        assert success

        # Check backup was created
        backup_path = test_file.with_suffix(test_file.suffix + ".tino.bak")
        assert backup_path.exists()
        assert backup_path.read_text() == original_content
        assert test_file.read_text() == new_content

        # Second save should NOT create new backup
        second_content = "Second modification"
        self.manager.save_file(test_file, second_content)

        # Backup should still have original content, not first modification
        assert backup_path.read_text() == original_content
        assert test_file.read_text() == second_content

    def test_backup_restoration_process(self):
        """Test complete backup restoration process."""
        test_file = self.temp_dir / "restore_test.txt"

        # Create and backup file
        original_content = "Content to be backed up"
        test_file.write_text(original_content)
        backup_path = self.backup_manager.create_backup(test_file)

        # Corrupt/modify original file
        corrupted_content = "CORRUPTED DATA"
        test_file.write_text(corrupted_content)

        # Restore from backup
        success = self.backup_manager.restore_from_backup(test_file)

        assert success
        assert test_file.read_text() == original_content
        assert backup_path.exists()  # Backup should still exist

    def test_multiple_file_backup_management(self):
        """Test managing backups for multiple files."""
        files_and_content = [
            ("file1.txt", "Content for file 1"),
            ("file2.md", "# Markdown content\nWith multiple lines"),
            ("file3.py", "# Python code\ndef function():\n    pass"),
        ]

        created_backups = []

        # Create files and backups
        for filename, content in files_and_content:
            test_file = self.temp_dir / filename
            test_file.write_text(content)

            backup_path = self.backup_manager.create_backup(test_file)
            assert backup_path is not None
            created_backups.append((test_file, backup_path, content))

        # Verify all backups exist and have correct content
        for _original_file, backup_path, expected_content in created_backups:
            assert backup_path.exists()
            assert backup_path.read_text() == expected_content

            # Backup path should follow naming convention
            assert str(backup_path).endswith(".tino.bak")

    def test_backup_cleanup_operations(self):
        """Test backup cleanup functionality."""
        # Create several backup files with different ages
        backup_files = []

        for i in range(5):
            test_file = self.temp_dir / f"cleanup_test_{i}.txt"
            test_file.write_text(f"Content {i}")

            backup_path = self.backup_manager.create_backup(test_file)
            backup_files.append(backup_path)

        # Make some backups appear older
        old_time = time.time() - (40 * 24 * 60 * 60)  # 40 days ago
        import os

        for i in range(2):  # Make first 2 backups old
            os.utime(backup_files[i], (old_time, old_time))

        # Clean up old backups (30 day threshold)
        cleaned = self.backup_manager.cleanup_old_backups(
            self.temp_dir, max_age_days=30
        )

        assert cleaned == 2  # Should clean up 2 old backups

        # Verify old backups are gone, recent ones remain
        for i in range(2):
            assert not backup_files[i].exists()
        for i in range(2, 5):
            assert backup_files[i].exists()

    def test_backup_with_different_encodings(self):
        """Test backup creation with files of different encodings."""
        test_cases = [
            ("utf8_backup.txt", "UTF-8 content with émojis 🎉", "utf-8"),
            ("latin1_backup.txt", "Latin-1 content with café", "latin-1"),
        ]

        for filename, content, encoding in test_cases:
            test_file = self.temp_dir / filename

            # Create file with specific encoding
            with open(test_file, "w", encoding=encoding) as f:
                f.write(content)

            # Create backup
            backup_path = self.backup_manager.create_backup(test_file)

            assert backup_path is not None
            assert backup_path.exists()

            # Verify backup content with correct encoding
            with open(backup_path, encoding=encoding) as f:
                backup_content = f.read()

            assert backup_content == content

    def test_backup_file_permissions(self):
        """Test that backup files maintain appropriate permissions."""
        if os.name == "nt":
            pytest.skip("Permission tests not reliable on Windows")

        test_file = self.temp_dir / "permissions_test.txt"
        content = "Permissions test content"
        test_file.write_text(content)

        # Set specific permissions on original file
        import stat

        test_file.chmod(stat.S_IRUSR | stat.S_IWUSR)  # Read/write for owner only

        # Create backup
        backup_path = self.backup_manager.create_backup(test_file)

        assert backup_path is not None

        # Backup should have reasonable permissions (readable by owner)
        backup_stat = backup_path.stat()
        assert backup_stat.st_mode & stat.S_IRUSR  # Owner can read

    def test_backup_atomic_operations(self):
        """Test that backup operations are atomic."""
        test_file = self.temp_dir / "atomic_backup.txt"
        large_content = "Large content line\n" * 1000  # Reasonably large content
        test_file.write_text(large_content)

        # Create backup
        backup_path = self.backup_manager.create_backup(test_file)

        assert backup_path is not None
        assert backup_path.exists()

        # Backup should have complete content
        backup_content = backup_path.read_text()
        assert backup_content == large_content
        assert len(backup_content) == len(large_content)

        # No partial/temp backup files should remain
        temp_backup_files = list(self.temp_dir.glob("*backup*tmp*"))
        assert len(temp_backup_files) == 0

    def test_backup_info_retrieval(self):
        """Test retrieving backup file information."""
        test_file = self.temp_dir / "info_backup.txt"
        content = "Backup info test content"
        test_file.write_text(content)

        # Create backup
        backup_path = self.backup_manager.create_backup(test_file)

        # Get backup info
        info = self.backup_manager.get_backup_info(test_file)

        assert info is not None
        assert info["path"] == backup_path
        assert info["exists"] is True
        assert info["size"] > 0
        assert isinstance(info["modified"], float)

        # Size should match content
        expected_size = len(content.encode("utf-8"))
        assert info["size"] == expected_size

    def test_backup_listing_functionality(self):
        """Test listing backup files in directory."""
        # Create files with backups
        test_files = ["list1.txt", "list2.md", "list3.py"]

        for filename in test_files:
            test_file = self.temp_dir / filename
            test_file.write_text(f"Content for {filename}")
            self.backup_manager.create_backup(test_file)

        # Create some non-backup files
        (self.temp_dir / "regular1.txt").write_text("regular")
        (self.temp_dir / "regular2.log").write_text("log")

        # List backups
        backups = self.backup_manager.list_backups(self.temp_dir)

        # Should find exactly 3 backup files
        assert len(backups) == 3

        # All should be .tino.bak files
        for backup in backups:
            assert str(backup).endswith(".tino.bak")
            assert backup.exists()

    def test_backup_edge_cases(self):
        """Test backup behavior in edge cases."""
        # Test 1: Empty file backup
        empty_file = self.temp_dir / "empty.txt"
        empty_file.touch()

        backup_path = self.backup_manager.create_backup(empty_file)
        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.stat().st_size == 0

        # Test 2: File with only whitespace
        whitespace_file = self.temp_dir / "whitespace.txt"
        whitespace_content = "   \n\t\n   \n"
        whitespace_file.write_text(whitespace_content)

        backup_path = self.backup_manager.create_backup(whitespace_file)
        assert backup_path is not None
        assert backup_path.read_text() == whitespace_content

        # Test 3: File with special characters
        special_file = self.temp_dir / "special_chars.txt"
        special_content = "Content with\x00null\x01bytes\x02and\x03control\x04chars"
        special_file.write_bytes(special_content.encode("utf-8", errors="replace"))

        backup_path = self.backup_manager.create_backup(special_file)
        assert backup_path is not None
        assert backup_path.exists()

    def test_concurrent_backup_operations(self):
        """Test concurrent backup operations don't interfere."""
        import concurrent.futures

        def create_backup_worker(file_index):
            """Worker function for concurrent backup testing."""
            test_file = self.temp_dir / f"concurrent_{file_index}.txt"
            content = f"Concurrent backup content {file_index}\n" * 10
            test_file.write_text(content)

            backup_path = self.backup_manager.create_backup(test_file)
            return test_file, backup_path, content

        # Run concurrent backup operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_backup_worker, i) for i in range(10)]
            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # Verify all backups were created successfully
        assert len(results) == 10

        for test_file, backup_path, expected_content in results:
            assert backup_path is not None
            assert backup_path.exists()
            assert test_file.exists()

            # Verify backup content
            backup_content = backup_path.read_text()
            assert backup_content == expected_content

    def test_backup_manager_integration_with_file_manager(self):
        """Test integration between BackupManager and FileManager."""
        test_file = self.temp_dir / "integration_test.txt"

        # Create file through FileManager
        original_content = "Original content for integration test"
        test_file.write_text(original_content)

        # Modify through FileManager (should create backup)
        new_content = "Modified content through FileManager"
        self.manager.save_file(test_file, new_content)

        # Verify backup exists and can be managed
        backup_path = self.manager.backup_manager.get_backup_path(test_file)
        assert backup_path.exists()

        # Get backup info through both managers
        fm_backup_info = self.manager.backup_manager.get_backup_info(test_file)
        bm_backup_info = self.backup_manager.get_backup_info(test_file)

        # Both should see the same backup
        assert fm_backup_info is not None
        assert bm_backup_info is not None
        assert fm_backup_info["path"] == bm_backup_info["path"]

    def test_backup_recovery_workflow_complete(self):
        """Test complete backup and recovery workflow."""
        test_file = self.temp_dir / "complete_workflow.txt"

        # Phase 1: Create and modify file
        original_content = "Phase 1: Original content"
        test_file.write_text(original_content)

        # Phase 2: First modification (creates backup)
        first_mod = "Phase 2: First modification"
        self.manager.save_file(test_file, first_mod)

        backup_path = test_file.with_suffix(test_file.suffix + ".tino.bak")
        assert backup_path.exists()
        assert backup_path.read_text() == original_content

        # Phase 3: Second modification (no new backup)
        second_mod = "Phase 3: Second modification"
        self.manager.save_file(test_file, second_mod)

        assert test_file.read_text() == second_mod
        assert backup_path.read_text() == original_content  # Still original

        # Phase 4: Simulate data corruption
        corrupted = "CORRUPTED DATA - LOST WORK!"
        test_file.write_text(corrupted)

        # Phase 5: Recovery from backup
        success = self.backup_manager.restore_from_backup(test_file)

        assert success
        assert test_file.read_text() == original_content

        # Phase 6: Continue working (backup protection reset)
        new_work = "Phase 6: New work after recovery"
        self.manager.save_file(test_file, new_work)

        # Should create new backup since we restored
        # (restore clears the "backed up this session" flag)
        assert test_file.read_text() == new_work
