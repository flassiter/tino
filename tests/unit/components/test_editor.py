"""
Unit tests for the editor component.

Tests all aspects of the EditorComponent and supporting classes including
undo/redo, selection management, cursor tracking, and event emission.
"""

import pytest
from unittest.mock import Mock, MagicMock

from src.tino.core.events.bus import EventBus
from src.tino.core.events.types import TextChangedEvent, SelectionChangedEvent, CursorMovedEvent
from src.tino.components.editor import (
    EditorComponent, MockEditor, UndoStack, UndoOperation,
    SelectionManager, CursorTracker, TextMetrics
)


class TestUndoStack:
    """Test the UndoStack class."""
    
    def test_initialization(self):
        """Test undo stack initialization."""
        stack = UndoStack(max_size=50)
        
        assert not stack.can_undo()
        assert not stack.can_redo()
        assert stack.get_undo_count() == 0
        assert stack.get_redo_count() == 0
    
    def test_push_operation(self):
        """Test pushing operations to the stack."""
        stack = UndoStack()
        
        operation = UndoOperation(
            operation_type="insert",
            position=0,
            old_text="",
            new_text="hello",
            old_cursor=(0, 0),
            new_cursor=(0, 5)
        )
        
        stack.push_operation(operation)
        
        assert stack.can_undo()
        assert not stack.can_redo()
        assert stack.get_undo_count() == 1
    
    def test_undo_redo(self):
        """Test undo and redo operations."""
        stack = UndoStack()
        
        operation = UndoOperation(
            operation_type="insert",
            position=0,
            old_text="",
            new_text="hello",
            old_cursor=(0, 0),
            new_cursor=(0, 5)
        )
        
        stack.push_operation(operation)
        
        # Test undo
        undone = stack.undo()
        assert undone == operation
        assert not stack.can_undo()
        assert stack.can_redo()
        
        # Test redo
        redone = stack.redo()
        assert redone == operation
        assert stack.can_undo()
        assert not stack.can_redo()
    
    def test_max_size_limit(self):
        """Test that stack respects maximum size."""
        stack = UndoStack(max_size=2)
        
        for i in range(3):
            operation = UndoOperation(
                operation_type="insert",
                position=i,
                old_text="",
                new_text=f"text{i}",
                old_cursor=(0, 0),
                new_cursor=(0, i+1)
            )
            stack.push_operation(operation)
        
        # Should only keep last 2 operations
        assert stack.get_undo_count() == 2
    
    def test_operation_grouping(self):
        """Test operation grouping functionality."""
        stack = UndoStack()
        
        # Start a group
        stack.start_group("test_group")
        
        # Add operations to group
        for i in range(3):
            operation = UndoOperation(
                operation_type="insert",
                position=i,
                old_text="",
                new_text=f"char{i}",
                old_cursor=(0, i),
                new_cursor=(0, i+1)
            )
            stack.push_operation(operation)
        
        # End group
        stack.end_group()
        
        # Should have one compound operation
        assert stack.get_undo_count() == 1
        
        # Undoing should undo the entire group
        undone = stack.undo()
        assert undone.operation_type == "group"
        assert hasattr(undone, 'group_operations')
    
    def test_clear(self):
        """Test clearing the stack."""
        stack = UndoStack()
        
        operation = UndoOperation(
            operation_type="insert",
            position=0,
            old_text="",
            new_text="hello",
            old_cursor=(0, 0),
            new_cursor=(0, 5)
        )
        
        stack.push_operation(operation)
        stack.undo()  # Move to redo stack
        
        stack.clear()
        
        assert not stack.can_undo()
        assert not stack.can_redo()
        assert stack.get_undo_count() == 0
        assert stack.get_redo_count() == 0


class TestSelectionManager:
    """Test the SelectionManager class."""
    
    def test_initialization(self):
        """Test selection manager initialization."""
        manager = SelectionManager()
        
        start, end = manager.get_selection()
        assert start == 0
        assert end == 0
        assert not manager.has_selection()
    
    def test_set_selection(self):
        """Test setting selection range."""
        manager = SelectionManager()
        manager.set_content_length(100)
        
        manager.set_selection(10, 20)
        start, end = manager.get_selection()
        
        assert start == 10
        assert end == 20
        assert manager.has_selection()
        assert manager.get_selection_length() == 10
    
    def test_selection_normalization(self):
        """Test that selection is normalized (start <= end)."""
        manager = SelectionManager()
        manager.set_content_length(100)
        
        # Set backwards selection
        manager.set_selection(20, 10)
        start, end = manager.get_selection()
        
        assert start == 10
        assert end == 20
    
    def test_selection_clamping(self):
        """Test that selection is clamped to content bounds."""
        manager = SelectionManager()
        manager.set_content_length(50)
        
        # Try to select beyond content
        manager.set_selection(-5, 100)
        start, end = manager.get_selection()
        
        assert start == 0
        assert end == 50
    
    def test_extend_selection(self):
        """Test extending selection."""
        manager = SelectionManager()
        manager.set_content_length(100)
        
        # Set initial selection with anchor
        manager.set_selection(10, 15, anchor=10)
        
        # Extend forward
        manager.extend_selection(25)
        start, end = manager.get_selection()
        assert start == 10
        assert end == 25
        
        # Extend backward past anchor
        manager.extend_selection(5)
        start, end = manager.get_selection()
        assert start == 5
        assert end == 10
    
    def test_select_all(self):
        """Test selecting all content."""
        manager = SelectionManager()
        
        manager.select_all(100)
        start, end = manager.get_selection()
        
        assert start == 0
        assert end == 100
        assert manager.has_selection()
    
    def test_clear_selection(self):
        """Test clearing selection."""
        manager = SelectionManager()
        manager.set_content_length(100)
        manager.set_selection(10, 20)
        
        assert manager.has_selection()
        
        manager.clear_selection()
        
        assert not manager.has_selection()
        start, end = manager.get_selection()
        assert start == end
    
    def test_word_selection(self):
        """Test word selection."""
        manager = SelectionManager()
        content = "hello world test"
        manager.set_content_length(len(content))
        
        # Select word at position 7 ('w' in 'world')
        manager.select_word_at(7, content)
        
        selected_text = manager.get_selected_text(content)
        assert selected_text == "world"
    
    def test_line_selection(self):
        """Test line selection."""
        manager = SelectionManager()
        content = "first line\nsecond line\nthird line"
        manager.set_content_length(len(content))
        
        # Select line containing position 15 (in 'second line')
        manager.select_line_at(15, content)
        
        selected_text = manager.get_selected_text(content)
        assert selected_text == "second line\n"
    
    def test_replace_selection(self):
        """Test replacing selected text."""
        manager = SelectionManager()
        content = "hello world"
        manager.set_content_length(len(content))
        
        # Select "world"
        manager.set_selection(6, 11)
        
        # Replace with "universe"
        new_content, new_cursor = manager.replace_selection(content, "universe")
        
        assert new_content == "hello universe"
        assert new_cursor == 14  # End of replacement


class TestCursorTracker:
    """Test the CursorTracker class."""
    
    def test_initialization(self):
        """Test cursor tracker initialization."""
        tracker = CursorTracker()
        
        line, column, position = tracker.get_line_column_position()
        assert line == 0
        assert column == 0
        assert position == 0
    
    def test_set_content(self):
        """Test setting content and building line cache."""
        tracker = CursorTracker()
        content = "line1\nline2\nline3"
        
        tracker.set_content(content)
        
        # Should have built line cache correctly
        assert tracker._line_count == 3
        assert tracker._line_starts == [0, 6, 12]
    
    def test_position_conversion(self):
        """Test conversion between absolute position and line/column."""
        tracker = CursorTracker()
        content = "hello\nworld\ntest"
        tracker.set_content(content)
        
        # Test absolute position to line/column
        tracker.set_position(8)  # 'r' in 'world'
        line, column, position = tracker.get_line_column_position()
        
        assert line == 1
        assert column == 2
        assert position == 8
        
        # Test line/column to absolute position
        tracker.set_line_column(2, 1)  # 'e' in 'test'
        line, column, position = tracker.get_line_column_position()
        
        assert line == 2
        assert column == 1
        assert position == 13
    
    def test_cursor_movement(self):
        """Test cursor movement operations."""
        tracker = CursorTracker()
        content = "hello\nworld\ntest"
        tracker.set_content(content)
        
        # Start at position 0
        tracker.set_position(0)
        
        # Move right
        tracker.move_right(3)
        line, column, position = tracker.get_line_column_position()
        assert position == 3
        
        # Move down
        tracker.move_down(1)
        line, column, position = tracker.get_line_column_position()
        assert line == 1
        assert column == 3
        
        # Move to line start
        tracker.move_to_line_start()
        line, column, position = tracker.get_line_column_position()
        assert column == 0
        
        # Move to line end
        tracker.move_to_line_end()
        line, column, position = tracker.get_line_column_position()
        assert column == 5  # End of "world"
    
    def test_word_boundaries(self):
        """Test word boundary detection."""
        tracker = CursorTracker()
        content = "hello world test"
        tracker.set_content(content)
        
        # Start in middle of "world"
        tracker.set_position(8)
        
        # Find word boundary left
        left_boundary = tracker.find_word_boundary_left()
        assert left_boundary == 6  # Start of "world"
        
        # Find word boundary right
        right_boundary = tracker.find_word_boundary_right()
        assert right_boundary == 11  # End of "world"
    
    def test_line_text_retrieval(self):
        """Test getting text of specific lines."""
        tracker = CursorTracker()
        content = "first\nsecond\nthird"
        tracker.set_content(content)
        
        assert tracker.get_line_text(0) == "first"
        assert tracker.get_line_text(1) == "second"
        assert tracker.get_line_text(2) == "third"
        
        # Test current line
        tracker.set_line_column(1, 0)
        assert tracker.get_line_text() == "second"
    
    def test_position_validation(self):
        """Test position validation and clamping."""
        tracker = CursorTracker()
        content = "hello"
        tracker.set_content(content)
        
        # Try to set position beyond content
        tracker.set_position(100)
        position = tracker.get_position()
        assert position == len(content)
        
        # Try to set negative position
        tracker.set_position(-5)
        position = tracker.get_position()
        assert position == 0


class TestTextMetrics:
    """Test the TextMetrics class."""
    
    def test_initialization(self):
        """Test text metrics initialization."""
        metrics = TextMetrics()
        
        # Should handle empty content
        assert metrics.get_line_count() == 1
        assert metrics.get_word_count() == 0
        assert metrics.get_character_count() == 0
    
    def test_basic_metrics(self):
        """Test basic text metrics calculation."""
        metrics = TextMetrics()
        content = "Hello world!\nThis is a test.\n\nAnother paragraph."
        
        metrics.set_content(content)
        
        assert metrics.get_line_count() == 4
        assert metrics.get_word_count() == 8  # "Hello world! This is a test. Another paragraph." = 8 words
        assert metrics.get_character_count() == len(content)
        assert metrics.get_paragraph_count() == 2
        assert metrics.get_sentence_count() == 3  # "Hello world!" + "This is a test." + "Another paragraph." = 3 sentences
    
    def test_metrics_caching(self):
        """Test that metrics are cached for performance."""
        metrics = TextMetrics()
        content = "Test content"
        
        # Set content and get metrics
        metrics.set_content(content)
        metrics_dict = metrics.get_metrics()
        
        # Should return same object (cached)
        metrics_dict2 = metrics.get_metrics()
        assert metrics_dict == metrics_dict2
        
        # Change content should invalidate cache
        metrics.set_content("Different content")
        metrics_dict3 = metrics.get_metrics()
        assert metrics_dict != metrics_dict3
    
    def test_line_specific_metrics(self):
        """Test line-specific metrics."""
        metrics = TextMetrics()
        content = "hello world\n    indented line\n\nempty above"
        
        metrics.set_content(content)
        
        # Test first line
        line_metrics = metrics.get_line_metrics(0)
        assert line_metrics['exists']
        assert line_metrics['length'] == 11
        assert line_metrics['words'] == 2
        assert not line_metrics['is_empty']
        assert line_metrics['indent_level'] == 0
        
        # Test indented line
        line_metrics = metrics.get_line_metrics(1)
        assert line_metrics['indent_level'] == 1  # 4 spaces = 1 indent level
        
        # Test empty line
        line_metrics = metrics.get_line_metrics(2)
        assert line_metrics['is_empty']
        
        # Test out of range
        line_metrics = metrics.get_line_metrics(100)
        assert not line_metrics['exists']
    
    def test_average_calculations(self):
        """Test average calculations."""
        metrics = TextMetrics()
        content = "short\nmedium line\nvery long line here"
        
        metrics.set_content(content)
        
        avg_chars = metrics.get_average_characters_per_line()
        assert avg_chars > 0
        
        avg_words = metrics.get_average_words_per_line()
        assert avg_words > 0
    
    def test_reading_time_estimate(self):
        """Test reading time estimation."""
        metrics = TextMetrics()
        
        # Create content with known word count
        words = ["word"] * 400  # 400 words
        content = " ".join(words)
        
        metrics.set_content(content)
        
        # At 200 WPM, should be 2 minutes
        reading_time = metrics.get_reading_time_estimate(200)
        assert reading_time == 2


class TestMockEditor:
    """Test the MockEditor implementation."""
    
    def test_initialization(self):
        """Test mock editor initialization."""
        editor = MockEditor()
        
        assert editor.get_content() == ""
        assert not editor.is_modified()
        assert not editor.can_undo()
        assert not editor.can_redo()
        assert editor.get_selection() == (0, 0)
    
    def test_content_operations(self):
        """Test basic content operations."""
        editor = MockEditor()
        
        # Set content
        editor.set_content("Hello world")
        
        assert editor.get_content() == "Hello world"
        assert editor.is_modified()
        assert editor.can_undo()
        
        # Insert text
        editor.insert_text(5, " beautiful")
        
        assert editor.get_content() == "Hello beautiful world"
        
        # Delete range
        deleted = editor.delete_range(5, 15)
        
        assert deleted == " beautiful"
        assert editor.get_content() == "Hello world"
    
    def test_selection_operations(self):
        """Test selection operations."""
        editor = MockEditor()
        editor.set_content("Hello world test")
        
        # Set selection
        editor.set_selection(6, 11)
        
        assert editor.get_selection() == (6, 11)
        assert editor.get_selected_text() == "world"
        
        # Replace selection
        editor.replace_selection("universe")
        
        assert editor.get_content() == "Hello universe test"
    
    def test_cursor_operations(self):
        """Test cursor operations."""
        editor = MockEditor()
        editor.set_content("line1\nline2\nline3")
        
        # Set cursor position
        editor.set_cursor_position(1, 3)
        
        line, column, position = editor.get_cursor_position()
        assert line == 1
        assert column == 3
    
    def test_undo_redo(self):
        """Test undo/redo functionality."""
        editor = MockEditor()
        
        # Make some changes
        editor.set_content("Hello")
        editor.insert_text(5, " world")
        
        assert editor.get_content() == "Hello world"
        assert editor.can_undo()
        
        # Undo
        success = editor.undo()
        
        assert success
        assert editor.can_redo()
        
        # Redo
        success = editor.redo()
        
        assert success
    
    def test_line_operations(self):
        """Test line-specific operations."""
        editor = MockEditor()
        content = "first line\nsecond line\nthird line"
        editor.set_content(content)
        
        assert editor.get_line_count() == 3
        assert editor.get_line_text(0) == "first line"
        assert editor.get_line_text(1) == "second line"
        assert editor.get_line_text(2) == "third line"
        
        # Test out of range
        with pytest.raises(IndexError):
            editor.get_line_text(5)
    
    def test_find_operations(self):
        """Test text finding."""
        editor = MockEditor()
        editor.set_content("Hello world, hello universe")
        
        # Find first occurrence
        result = editor.find_text("hello", case_sensitive=False)
        
        assert result == (0, 5)
        
        # Find second occurrence
        result = editor.find_text("hello", start=1, case_sensitive=False)
        
        assert result == (13, 18)
        
        # Not found
        result = editor.find_text("xyz")
        
        assert result is None
    
    def test_operation_history(self):
        """Test operation history tracking."""
        editor = MockEditor()
        
        # Perform some operations
        editor.set_content("test")
        editor.insert_text(4, " content")
        editor.set_selection(0, 4)
        
        # Check history
        history = editor.get_operation_history()
        
        assert len(history) >= 3
        assert any(op['operation'] == 'set_content' for op in history)
        assert any(op['operation'] == 'insert_text' for op in history)
        assert any(op['operation'] == 'set_selection' for op in history)
    
    def test_event_emission(self):
        """Test event emission with event bus."""
        event_bus = Mock()
        editor = MockEditor(event_bus)
        
        # Make changes that should emit events
        editor.set_content("Hello")
        editor.set_selection(0, 5)
        editor.set_cursor_position(0, 5)
        
        # Check that events were emitted
        assert event_bus.emit.call_count >= 3
        
        # Check event history
        event_history = editor.get_event_history()
        assert len(event_history) >= 3
    
    def test_failure_simulation(self):
        """Test failure simulation for testing edge cases."""
        editor = MockEditor()
        
        # Enable failure simulation
        editor.set_simulate_failures(find_failures=True, undo_failures=True)
        
        # Operations should fail
        editor.set_content("test")
        
        result = editor.find_text("test")
        assert result is None
        
        success = editor.undo()
        assert not success
        assert not editor.can_undo()


class TestEditorComponent:
    """Test the EditorComponent (requires more complex setup)."""
    
    def test_initialization(self):
        """Test editor component initialization."""
        event_bus = EventBus()
        editor = EditorComponent(event_bus)
        
        assert editor.get_content() == ""
        assert not editor.is_modified()
        assert not editor.can_undo()
        assert not editor.can_redo()
    
    def test_basic_operations_without_textarea(self):
        """Test basic operations without TextArea widget."""
        event_bus = EventBus()
        editor = EditorComponent(event_bus)
        
        # Should work even without TextArea
        editor.set_content("Hello world")
        
        assert editor.get_content() == "Hello world"
        assert editor.is_modified()
        assert editor.can_undo()
    
    def test_event_emission(self):
        """Test that events are properly emitted."""
        event_bus = EventBus()
        
        # Mock event handler
        text_changed_handler = Mock()
        cursor_moved_handler = Mock()
        selection_changed_handler = Mock()
        
        event_bus.subscribe(TextChangedEvent, text_changed_handler)
        event_bus.subscribe(CursorMovedEvent, cursor_moved_handler)
        event_bus.subscribe(SelectionChangedEvent, selection_changed_handler)
        
        editor = EditorComponent(event_bus)
        
        # Make changes
        editor.set_content("Hello")
        editor.insert_text(5, " world")
        editor.set_selection(0, 5)
        
        # Verify events were emitted
        assert text_changed_handler.call_count >= 2
        assert selection_changed_handler.call_count >= 1
    
    def test_undo_redo_functionality(self):
        """Test undo/redo with the component."""
        editor = EditorComponent()
        
        # Make changes
        editor.set_content("Hello")
        editor.insert_text(5, " world")
        
        original_content = editor.get_content()
        
        # Undo
        success = editor.undo()
        assert success
        assert editor.get_content() != original_content
        
        # Redo
        success = editor.redo()
        assert success
        assert editor.get_content() == original_content
    
    def test_selection_and_replacement(self):
        """Test selection and text replacement."""
        editor = EditorComponent()
        editor.set_content("Hello world")
        
        # Select "world"
        editor.set_selection(6, 11)
        
        selected = editor.get_selected_text()
        assert selected == "world"
        
        # Replace selection
        editor.replace_selection("universe")
        
        assert editor.get_content() == "Hello universe"
    
    def test_line_operations(self):
        """Test line-based operations."""
        editor = EditorComponent()
        content = "first line\nsecond line\nthird line"
        editor.set_content(content)
        
        assert editor.get_line_count() == 3
        assert editor.get_line_text(1) == "second line"
        
        # Test out of range
        with pytest.raises(IndexError):
            editor.get_line_text(5)
    
    def test_find_functionality(self):
        """Test text finding."""
        editor = EditorComponent()
        editor.set_content("Hello world, hello universe")
        
        # Case sensitive search
        result = editor.find_text("Hello")
        assert result == (0, 5)
        
        # Case insensitive search
        result = editor.find_text("HELLO", case_sensitive=False)
        assert result == (0, 5)
        
        # Search with start position
        result = editor.find_text("hello", start=10, case_sensitive=False)
        assert result == (13, 18)
    
    def test_cursor_position_management(self):
        """Test cursor position tracking."""
        editor = EditorComponent()
        editor.set_content("line1\nline2\nline3")
        
        # Set cursor position
        editor.set_cursor_position(1, 3)
        
        line, column, position = editor.get_cursor_position()
        assert line == 1
        assert column == 3
        
        # Position should be calculated correctly
        assert position == 9  # 6 (line1\n) + 3


if __name__ == "__main__":
    pytest.main([__file__])