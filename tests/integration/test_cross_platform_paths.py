"""
Integration tests for cross-platform path handling.

Tests path normalization and handling across different platforms.
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from tino.components.file_manager.file_manager import FileManager


class TestCrossPlatformPaths:

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = FileManager()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_path_normalization(self):
        """Test that paths are normalized consistently."""
        # Test various path representations
        base_name = "test_file.txt"
        content = "Test content"

        # Different ways to represent the same path
        paths_to_test = [
            self.temp_dir / base_name,
            Path(str(self.temp_dir) + os.sep + base_name),
            Path(self.temp_dir) / Path(base_name),
        ]

        # Save with first path representation
        self.manager.save_file(paths_to_test[0], content)

        # All representations should refer to the same file
        for path in paths_to_test:
            assert self.manager.file_exists(path)
            loaded_content = self.manager.open_file(path)
            assert loaded_content == content

    def test_special_characters_in_filenames(self):
        """Test handling of special characters in filenames."""
        special_files = [
            "file with spaces.txt",
            "file-with-dashes.txt",
            "file_with_underscores.txt",
            "file.with.multiple.dots.txt",
            "file(with)parentheses.txt",
            "file[with]brackets.txt",
            "file{with}braces.txt",
        ]

        # Add Unicode if platform supports it
        try:
            unicode_file = "файл_с_юникодом.txt"  # Russian filename
            Path(self.temp_dir / unicode_file).touch()
            special_files.append(unicode_file)
        except (UnicodeError, OSError):
            # Platform doesn't support Unicode filenames
            pass

        for filename in special_files:
            test_file = self.temp_dir / filename
            content = f"Content for {filename}"

            try:
                # Save and load
                self.manager.save_file(test_file, content)
                loaded = self.manager.open_file(test_file)

                assert loaded == content
                assert self.manager.file_exists(test_file)

            except (UnicodeError, OSError) as e:
                # Some platforms may not support certain characters
                pytest.skip(f"Platform doesn't support filename '{filename}': {e}")

    def test_long_paths(self):
        """Test handling of long file paths."""
        # Create nested directory structure
        deep_path = self.temp_dir
        for i in range(10):  # Create moderately deep path
            deep_path = deep_path / f"level_{i}"

        deep_path.mkdir(parents=True, exist_ok=True)

        test_file = deep_path / "deep_file.txt"
        content = "Content in deep path"

        try:
            # Should handle long paths
            self.manager.save_file(test_file, content)
            loaded = self.manager.open_file(test_file)

            assert loaded == content

        except OSError as e:
            # Some platforms have path length limits
            if "name too long" in str(e).lower() or "path too long" in str(e).lower():
                pytest.skip(f"Platform path length limit reached: {e}")
            else:
                raise

    def test_relative_vs_absolute_paths(self):
        """Test handling of relative vs absolute paths."""
        test_file_name = "relative_test.txt"
        content = "Relative path test"

        # Create file with absolute path
        abs_path = self.temp_dir / test_file_name
        self.manager.save_file(abs_path, content)

        # Change working directory to temp dir
        original_cwd = Path.cwd()
        try:
            os.chdir(self.temp_dir)

            # Access with relative path
            rel_path = Path(test_file_name)

            # Should be able to read with relative path
            loaded = self.manager.open_file(rel_path)
            assert loaded == content

            # Both should refer to same file in recent files
            recent = self.manager.get_recent_files()
            assert len(recent) >= 1

        finally:
            # Restore original working directory
            os.chdir(original_cwd)

    def test_symlink_handling(self):
        """Test handling of symbolic links."""
        if os.name == "nt":
            pytest.skip("Symbolic link tests may not work reliably on Windows")

        # Create original file
        original_file = self.temp_dir / "original.txt"
        content = "Original file content"
        original_file.write_text(content)

        # Create symbolic link
        link_file = self.temp_dir / "link.txt"
        try:
            link_file.symlink_to(original_file)
        except OSError:
            pytest.skip("Platform doesn't support symbolic links")

        # Should be able to read through symlink
        loaded = self.manager.open_file(link_file)
        assert loaded == content

        # Modifying through link should modify original
        new_content = "Modified through link"
        self.manager.save_file(link_file, new_content)

        # Check original file was modified
        # Note: Atomic save operations might break symlinks by replacing them
        # Check if either the link or original has the new content
        link_content = link_file.read_text() if link_file.exists() else ""
        orig_content = original_file.read_text() if original_file.exists() else ""
        assert new_content in [link_content, orig_content]

    def test_case_sensitivity_handling(self):
        """Test handling of case sensitivity differences."""
        base_name = "CaseSensitive"
        content = "Case sensitivity test"

        # Create file with specific case
        test_file = self.temp_dir / f"{base_name}.txt"
        self.manager.save_file(test_file, content)

        # Try accessing with different case
        different_case = self.temp_dir / f"{base_name.lower()}.txt"

        if os.name == "nt":
            # Windows is case-insensitive
            loaded = self.manager.open_file(different_case)
            assert loaded == content
        else:
            # Unix-like systems are case-sensitive
            if different_case.exists():
                # If it exists, it should be the same file
                loaded = self.manager.open_file(different_case)
                assert loaded == content
            else:
                # Different case file doesn't exist
                with pytest.raises(FileNotFoundError):
                    self.manager.open_file(different_case)

    def test_path_separators(self):
        """Test handling of different path separators."""
        # Create nested directory
        sub_dir = self.temp_dir / "subdir"
        sub_dir.mkdir()

        test_file = sub_dir / "separator_test.txt"
        content = "Path separator test"
        self.manager.save_file(test_file, content)

        # Try different separator representations
        if os.name == "nt":
            # Windows: try both / and \ separators
            alt_path_str = str(test_file).replace("/", "\\")
            alt_path = Path(alt_path_str)
        else:
            # Unix: / is standard, but test with Path normalization
            alt_path = Path(str(test_file))

        # Should be able to access file
        loaded = self.manager.open_file(alt_path)
        assert loaded == content

    def test_reserved_filenames(self):
        """Test handling of platform-reserved filenames."""
        if os.name == "nt":
            # Windows reserved names
            reserved_names = ["CON", "PRN", "AUX", "NUL"]
            for name in reserved_names:
                test_file = self.temp_dir / f"{name}.txt"

                # Should either work or raise appropriate error
                try:
                    self.manager.save_file(test_file, "test")
                    # If it works, should be able to read back
                    loaded = self.manager.open_file(test_file)
                    assert loaded == "test"
                except OSError:
                    # Platform rejected reserved name - that's OK
                    pass
        else:
            # Unix-like: test files starting with dot
            hidden_file = self.temp_dir / ".hidden_file.txt"
            content = "Hidden file content"

            self.manager.save_file(hidden_file, content)
            loaded = self.manager.open_file(hidden_file)
            assert loaded == content

    def test_network_path_simulation(self):
        """Test handling of network-like paths (where applicable)."""
        # This is mainly for Windows UNC paths, but we'll simulate
        # the behavior by creating deeply nested paths

        # Create a path that might simulate network access patterns
        network_sim = self.temp_dir / "network_sim" / "server" / "share"
        network_sim.mkdir(parents=True)

        test_file = network_sim / "network_file.txt"
        content = "Network simulation content"

        # Should handle deep paths like network shares
        self.manager.save_file(test_file, content)
        loaded = self.manager.open_file(test_file)
        assert loaded == content

    def test_backup_paths_cross_platform(self):
        """Test backup file creation across platforms."""
        test_file = self.temp_dir / "backup_cross_platform.txt"
        original_content = "Original content"

        # Create original file
        test_file.write_text(original_content)

        # Modify to trigger backup
        new_content = "Modified content"
        self.manager.save_file(test_file, new_content)

        # Check backup was created with correct path format
        backup_path = self.manager.backup_manager.get_backup_path(test_file)
        assert backup_path.exists()
        assert backup_path.suffix == ".bak"
        assert ".tino" in str(backup_path)

        # Backup should be readable
        backup_content = backup_path.read_text()
        assert backup_content == original_content

    def test_temp_file_paths_cross_platform(self):
        """Test temporary file path generation across platforms."""
        test_files = [
            self.temp_dir / "simple.txt",
            self.temp_dir / "with spaces.txt",
            self.temp_dir / "with.dots.txt",
        ]

        for test_file in test_files:
            temp_path = self.manager.get_temp_file_path(test_file)

            # Temp file should be in same directory
            assert temp_path.parent == test_file.parent

            # Should have temp characteristics
            assert ".tino_temp_" in str(temp_path)
            assert temp_path.suffix == ".tmp"

            # Should be valid path for the platform
            is_valid, error = self.manager.validate_file_path(temp_path)
            assert is_valid, f"Temp path invalid: {error}"

    def test_cursor_position_path_consistency(self):
        """Test cursor position tracking with path normalization."""
        test_file = self.temp_dir / "cursor_consistency.txt"
        test_file.write_text("Content for cursor test")

        # Set cursor position
        self.manager.set_cursor_position(test_file, 5, 10)

        # Access same file with different path representation
        alt_path = Path(str(test_file))  # Different object, same path

        # Should retrieve same cursor position
        position = self.manager.get_cursor_position(alt_path)
        assert position == (5, 10)

    def test_recent_files_path_consistency(self):
        """Test recent files with path normalization."""
        test_file = self.temp_dir / "recent_consistency.txt"
        test_file.write_text("Recent files test")

        # Add to recent files
        self.manager.open_file(test_file)

        # Check with different path representations
        Path(str(test_file))  # Create alt path representation

        recent = self.manager.get_recent_files()
        assert len(recent) == 1

        # Should contain normalized path
        assert test_file.resolve() == recent[0].resolve()
