"""
Tests for CursorMemory class.

Tests cursor position tracking, validation, and thread safety.
"""

import tempfile
import threading
from pathlib import Path

from tino.components.file_manager.cursor_memory import CursorMemory


class TestCursorMemory:

    def setup_method(self):
        """Set up test fixtures."""
        self.memory = CursorMemory()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_set_cursor_position(self):
        """Test setting cursor position for a file."""
        test_file = self.temp_dir / "test.txt"

        self.memory.set_cursor_position(test_file, 5, 10)

        position = self.memory.get_cursor_position(test_file)
        assert position == (5, 10)

    def test_set_cursor_position_negative_values(self):
        """Test that negative cursor positions are normalized to zero."""
        test_file = self.temp_dir / "test.txt"

        self.memory.set_cursor_position(test_file, -5, -10)

        position = self.memory.get_cursor_position(test_file)
        assert position == (0, 0)

    def test_get_cursor_position_not_found(self):
        """Test getting cursor position for file not in memory."""
        test_file = self.temp_dir / "test.txt"

        position = self.memory.get_cursor_position(test_file)
        assert position is None

    def test_has_cursor_position(self):
        """Test checking if cursor position exists."""
        test_file = self.temp_dir / "test.txt"

        assert not self.memory.has_cursor_position(test_file)

        self.memory.set_cursor_position(test_file, 1, 2)
        assert self.memory.has_cursor_position(test_file)

    def test_remove_cursor_position_exists(self):
        """Test removing existing cursor position."""
        test_file = self.temp_dir / "test.txt"

        self.memory.set_cursor_position(test_file, 1, 2)
        result = self.memory.remove_cursor_position(test_file)

        assert result is True
        assert not self.memory.has_cursor_position(test_file)

    def test_remove_cursor_position_not_exists(self):
        """Test removing non-existent cursor position."""
        test_file = self.temp_dir / "test.txt"

        result = self.memory.remove_cursor_position(test_file)
        assert result is False

    def test_clear_all_positions(self):
        """Test clearing all cursor positions."""
        files = []
        for i in range(3):
            test_file = self.temp_dir / f"test{i}.txt"
            files.append(test_file)
            self.memory.set_cursor_position(test_file, i, i * 2)

        self.memory.clear_all_positions()

        for test_file in files:
            assert not self.memory.has_cursor_position(test_file)

    def test_get_all_positions(self):
        """Test getting all cursor positions."""
        files_positions = {
            self.temp_dir / "test1.txt": (1, 5),
            self.temp_dir / "test2.txt": (3, 7),
            self.temp_dir / "test3.txt": (2, 4),
        }

        for file_path, position in files_positions.items():
            self.memory.set_cursor_position(file_path, position[0], position[1])

        all_positions = self.memory.get_all_positions()

        assert len(all_positions) == 3
        for file_path, expected_position in files_positions.items():
            assert all_positions[file_path] == expected_position

    def test_update_cursor_position_exists(self):
        """Test updating existing cursor position with delta."""
        test_file = self.temp_dir / "test.txt"

        self.memory.set_cursor_position(test_file, 5, 10)
        new_position = self.memory.update_cursor_position(test_file, 2, -3)

        assert new_position == (7, 7)
        assert self.memory.get_cursor_position(test_file) == (7, 7)

    def test_update_cursor_position_not_exists(self):
        """Test updating cursor position for non-existent file."""
        test_file = self.temp_dir / "test.txt"

        result = self.memory.update_cursor_position(test_file, 2, 3)
        assert result is None

    def test_update_cursor_position_negative_result(self):
        """Test updating cursor position with negative result."""
        test_file = self.temp_dir / "test.txt"

        self.memory.set_cursor_position(test_file, 2, 3)
        new_position = self.memory.update_cursor_position(test_file, -5, -10)

        # Should clamp to (0, 0)
        assert new_position == (0, 0)

    def test_cleanup_missing_files(self):
        """Test cleanup of cursor positions for missing files."""
        existing_file = self.temp_dir / "existing.txt"
        missing_file = self.temp_dir / "missing.txt"

        existing_file.touch()
        # Don't create missing_file

        self.memory.set_cursor_position(existing_file, 1, 2)
        self.memory.set_cursor_position(missing_file, 3, 4)

        removed = self.memory.cleanup_missing_files()

        assert removed == 1
        assert self.memory.has_cursor_position(existing_file)
        assert not self.memory.has_cursor_position(missing_file)

    def test_get_stats(self):
        """Test getting cursor memory statistics."""
        files_positions = [
            (self.temp_dir / "test1.txt", (1, 5)),
            (self.temp_dir / "test2.txt", (10, 20)),
            (self.temp_dir / "test3.txt", (2, 15)),
        ]

        for file_path, position in files_positions:
            self.memory.set_cursor_position(file_path, position[0], position[1])

        stats = self.memory.get_stats()

        assert stats["total_files"] == 3
        assert stats["max_line"] == 10
        assert stats["max_column"] == 20
        assert stats["avg_line"] == (1 + 10 + 2) / 3
        assert stats["avg_column"] == (5 + 20 + 15) / 3

    def test_get_stats_empty(self):
        """Test getting statistics when no positions stored."""
        stats = self.memory.get_stats()

        assert stats["total_files"] == 0
        assert stats["max_line"] is None
        assert stats["max_column"] is None
        assert stats["avg_line"] is None
        assert stats["avg_column"] is None

    def test_validate_position_valid(self):
        """Test position validation with valid position."""
        test_file = self.temp_dir / "test.txt"

        self.memory.set_cursor_position(test_file, 5, 10)
        position = self.memory.validate_position(test_file, max_lines=20)

        assert position == (5, 10)

    def test_validate_position_line_too_high(self):
        """Test position validation with line number too high."""
        test_file = self.temp_dir / "test.txt"

        self.memory.set_cursor_position(test_file, 25, 10)
        position = self.memory.validate_position(test_file, max_lines=20)

        # Should adjust line to max_lines - 1
        assert position == (19, 10)

    def test_validate_position_no_position(self):
        """Test position validation for non-existent position."""
        test_file = self.temp_dir / "test.txt"

        position = self.memory.validate_position(test_file, max_lines=20)
        assert position is None

    def test_validate_position_no_max_lines(self):
        """Test position validation without max_lines constraint."""
        test_file = self.temp_dir / "test.txt"

        self.memory.set_cursor_position(test_file, 100, 50)
        position = self.memory.validate_position(test_file)

        # Should return position unchanged
        assert position == (100, 50)

    def test_import_positions(self):
        """Test importing positions from dictionary."""
        positions_to_import = {
            self.temp_dir / "test1.txt": (1, 5),
            self.temp_dir / "test2.txt": (3, 7),
            self.temp_dir / "test3.txt": [2, 4],  # List instead of tuple
        }

        imported = self.memory.import_positions(positions_to_import)

        assert imported == 3
        assert self.memory.get_cursor_position(self.temp_dir / "test1.txt") == (1, 5)
        assert self.memory.get_cursor_position(self.temp_dir / "test2.txt") == (3, 7)
        assert self.memory.get_cursor_position(self.temp_dir / "test3.txt") == (2, 4)

    def test_import_positions_invalid_data(self):
        """Test importing positions with invalid data."""
        invalid_positions = {
            self.temp_dir / "test1.txt": (1, 5),  # Valid
            self.temp_dir / "test2.txt": (3,),  # Too few values
            self.temp_dir / "test3.txt": "invalid",  # Invalid type
            self.temp_dir / "test4.txt": [2, 4],  # Valid list
        }

        imported = self.memory.import_positions(invalid_positions)

        # Should import only valid entries
        assert imported == 2
        assert self.memory.has_cursor_position(self.temp_dir / "test1.txt")
        assert not self.memory.has_cursor_position(self.temp_dir / "test2.txt")
        assert not self.memory.has_cursor_position(self.temp_dir / "test3.txt")
        assert self.memory.has_cursor_position(self.temp_dir / "test4.txt")

    def test_len_operator(self):
        """Test __len__ operator."""
        assert len(self.memory) == 0

        for i in range(3):
            test_file = self.temp_dir / f"test{i}.txt"
            self.memory.set_cursor_position(test_file, i, i * 2)

        assert len(self.memory) == 3

    def test_contains_operator(self):
        """Test __contains__ operator."""
        test_file = self.temp_dir / "test.txt"

        assert test_file not in self.memory

        self.memory.set_cursor_position(test_file, 1, 2)
        assert test_file in self.memory

    def test_path_resolution(self):
        """Test that paths are resolved consistently."""
        test_file = self.temp_dir / "test.txt"
        test_file.touch()

        # Add with absolute path
        self.memory.set_cursor_position(test_file, 5, 10)

        # Should find it regardless of path representation
        assert self.memory.has_cursor_position(test_file)

    def test_thread_safety(self):
        """Test thread safety of cursor memory."""
        files = []
        for i in range(10):
            test_file = self.temp_dir / f"test{i}.txt"
            files.append(test_file)

        def set_positions(start_idx, count):
            for i in range(start_idx, start_idx + count):
                if i < len(files):
                    self.memory.set_cursor_position(files[i], i, i * 2)

        # Start multiple threads setting positions
        threads = []
        for t in range(3):
            thread = threading.Thread(target=set_positions, args=(t * 3, 3))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should have set positions without corruption
        assert len(self.memory) <= 10

        # Verify some positions
        for _i, file_path in enumerate(files[: len(self.memory)]):
            if self.memory.has_cursor_position(file_path):
                position = self.memory.get_cursor_position(file_path)
                assert isinstance(position, tuple)
                assert len(position) == 2
                assert position[0] >= 0
                assert position[1] >= 0

    def test_string_path_handling(self):
        """Test handling of string paths (should convert to Path)."""
        test_file = self.temp_dir / "test.txt"

        # Pass string instead of Path
        self.memory.set_cursor_position(str(test_file), 5, 10)

        # Should work with Path object
        position = self.memory.get_cursor_position(test_file)
        assert position == (5, 10)

    def test_float_coordinates_conversion(self):
        """Test that float coordinates are converted to integers."""
        test_file = self.temp_dir / "test.txt"

        self.memory.set_cursor_position(test_file, 5.7, 10.3)

        position = self.memory.get_cursor_position(test_file)
        assert position == (5, 10)  # Should be converted to int

    def test_position_updates_logging(self):
        """Test that position updates are tracked properly."""
        test_file = self.temp_dir / "test.txt"

        # Set initial position
        self.memory.set_cursor_position(test_file, 1, 1)
        old_position = self.memory.get_cursor_position(test_file)

        # Update position
        self.memory.set_cursor_position(test_file, 5, 10)
        new_position = self.memory.get_cursor_position(test_file)

        assert old_position != new_position
        assert new_position == (5, 10)
