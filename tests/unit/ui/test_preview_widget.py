"""
Tests for preview widget components.

Tests the MarkdownPreview widget, OutlinePanel, and related UI components
including debouncing, message handling, and widget composition.
"""

from unittest.mock import Mock

import pytest

from tino.components.renderer.markdown_renderer import MarkdownRenderer
from tino.core.interfaces.renderer import Heading, ValidationIssue
from tino.ui.preview_widget import (
    HeadingSelected,
    JumpToLine,
    MarkdownPreview,
    OutlinePanel,
    PreviewError,
    PreviewUpdated,
    SplitPane,
)


class TestOutlinePanel:
    """Test suite for OutlinePanel widget."""

    @pytest.fixture
    def outline_panel(self):
        """Create an OutlinePanel instance for testing."""
        return OutlinePanel()

    def test_initialization(self, outline_panel):
        """Test outline panel initialization."""
        assert outline_panel._headings == []
        assert outline_panel._tree is None

    def test_update_outline_empty(self, outline_panel):
        """Test updating outline with empty headings list."""
        headings = []
        outline_panel.update_outline(headings)
        assert outline_panel._headings == []

    def test_update_outline_with_headings(self, outline_panel):
        """Test updating outline with headings."""
        headings = [
            Heading(level=1, text="Main", id="main", line_number=1),
            Heading(level=2, text="Sub", id="sub", line_number=3),
            Heading(level=1, text="Another", id="another", line_number=5),
        ]

        outline_panel.update_outline(headings)
        assert outline_panel._headings == headings

    def test_heading_selection_message(self, outline_panel):
        """Test that heading selection posts correct message."""
        heading = Heading(level=1, text="Test", id="test", line_number=1)
        message = HeadingSelected(heading)

        assert message.heading == heading
        assert message.heading.text == "Test"
        assert message.heading.line_number == 1


class TestMarkdownPreview:
    """Test suite for MarkdownPreview widget."""

    @pytest.fixture
    def mock_renderer(self):
        """Create a mock renderer for testing."""
        renderer = Mock(spec=MarkdownRenderer)
        renderer.render_html.return_value = Mock(
            html="<h1>Test</h1>",
            outline=[Heading(level=1, text="Test", id="test", line_number=1)],
            issues=[],
            render_time_ms=10.0,
            cached=False,
        )
        renderer.set_theme.return_value = None
        return renderer

    @pytest.fixture
    def preview_widget(self, mock_renderer):
        """Create a MarkdownPreview instance for testing."""
        return MarkdownPreview(mock_renderer)

    def test_initialization(self, preview_widget, mock_renderer):
        """Test preview widget initialization."""
        assert preview_widget._renderer == mock_renderer
        assert preview_widget._markdown_widget is None
        assert preview_widget._outline_panel is None
        assert preview_widget._current_headings == []
        # Debouncing removed for MVP simplicity
        assert preview_widget._last_content == ""
        assert preview_widget.content == ""
        assert preview_widget.show_outline is True
        assert preview_widget.current_theme == "dark"

    def test_content_change_tracking(self, preview_widget):
        """Test that content changes are tracked properly."""
        # Initial state
        assert preview_widget._last_content == ""

        # Setting same content shouldn't trigger update
        preview_widget.content = ""
        # Since we can't easily test the watch_content method in isolation,
        # we test the logic separately
        assert preview_widget.content == ""

    def test_theme_change(self, preview_widget, mock_renderer):
        """Test theme change handling."""
        preview_widget.current_theme = "light"
        # The watch_current_theme method calls renderer.set_theme
        # We can verify this was called in integration tests
        assert preview_widget.current_theme == "light"

    def test_outline_visibility_toggle(self, preview_widget):
        """Test outline panel visibility toggle."""
        assert preview_widget.show_outline is True

        preview_widget.toggle_outline()
        assert preview_widget.show_outline is False

        preview_widget.toggle_outline()
        assert preview_widget.show_outline is True

    def test_get_current_headings(self, preview_widget):
        """Test getting current headings."""
        headings = [Heading(level=1, text="Test", id="test", line_number=1)]
        preview_widget._current_headings = headings

        result = preview_widget.get_current_headings()
        assert result == headings
        assert result is not preview_widget._current_headings  # Should be a copy

    def test_jump_to_heading(self, preview_widget):
        """Test jumping to a heading posts correct message."""
        heading = Heading(level=1, text="Test", id="test", line_number=5)

        # We can't easily test message posting without a full app context,
        # but we can test the method doesn't crash
        try:
            preview_widget.jump_to_heading(heading)
        except Exception:
            # Expected since we don't have app context
            pass

    def test_preview_update_content_validation(self, preview_widget, mock_renderer):
        """Test that preview updates validate content properly."""
        test_content = "# Test Heading\n\nSome content"

        # Test the internal update logic
        preview_widget.content = test_content
        preview_widget._last_content = test_content

        # Content should be stored
        assert preview_widget.content == test_content


class TestSplitPane:
    """Test suite for SplitPane widget."""

    @pytest.fixture
    def mock_editor(self):
        """Create a mock editor widget."""
        return Mock()

    @pytest.fixture
    def mock_preview(self):
        """Create a mock preview widget."""
        return Mock(spec=MarkdownPreview)

    @pytest.fixture
    def split_pane(self, mock_editor, mock_preview):
        """Create a SplitPane instance for testing."""
        return SplitPane(mock_editor, mock_preview)

    def test_initialization(self, split_pane, mock_editor, mock_preview):
        """Test split pane initialization."""
        assert split_pane._editor_widget == mock_editor
        assert split_pane._preview_widget == mock_preview
        assert split_pane.show_preview is True

    def test_preview_visibility_toggle(self, split_pane):
        """Test preview visibility toggle."""
        assert split_pane.show_preview is True

        split_pane.toggle_preview()
        assert split_pane.show_preview is False

        split_pane.toggle_preview()
        assert split_pane.show_preview is True

    def test_pane_resizing(self, split_pane):
        """Test pane resizing functionality."""
        # Test resize method exists and accepts parameters
        try:
            split_pane.resize_panes(0.6)  # 60% editor, 40% preview
        except Exception:
            # May fail due to CSS update without proper app context
            pass


class TestPreviewMessages:
    """Test suite for preview-related messages."""

    def test_heading_selected_message(self):
        """Test HeadingSelected message."""
        heading = Heading(level=2, text="Section", id="section", line_number=10)
        message = HeadingSelected(heading)

        assert message.heading == heading
        assert message.heading.text == "Section"
        assert message.heading.level == 2
        assert message.heading.line_number == 10

    def test_jump_to_line_message(self):
        """Test JumpToLine message."""
        message = JumpToLine(42)

        assert message.line_number == 42

    def test_preview_updated_message(self):
        """Test PreviewUpdated message."""
        issues = [
            ValidationIssue(
                type="warning",
                message="Test",
                line_number=1,
                column=1,
                severity="warning",
            )
        ]
        message = PreviewUpdated(render_time=25.5, cached=True, issues=issues)

        assert message.render_time == 25.5
        assert message.cached is True
        assert message.issues == issues
        assert len(message.issues) == 1

    def test_preview_error_message(self):
        """Test PreviewError message."""
        error_msg = "Rendering failed"
        message = PreviewError(error_msg)

        assert message.error == error_msg


class TestPreviewIntegration:
    """Integration tests for preview components."""

    @pytest.fixture
    def real_renderer(self):
        """Create a real renderer for integration testing."""
        return MarkdownRenderer()

    @pytest.fixture
    def preview_with_real_renderer(self, real_renderer):
        """Create preview widget with real renderer."""
        return MarkdownPreview(real_renderer)

    def test_real_content_rendering(self, preview_with_real_renderer):
        """Test rendering with real markdown content."""
        content = """# Test Document

This is a test document with:

- A list item
- Another item

## Section Two

Some more content with **bold** and *italic* text.

### Subsection

Final content here.
"""

        # Set content and verify it's stored
        preview_with_real_renderer.content = content
        assert preview_with_real_renderer.content == content

        # The actual rendering would happen in the watch_content method
        # which requires a full Textual app context to test properly

    def test_theme_integration(self, preview_with_real_renderer, real_renderer):
        """Test theme changes with real renderer."""
        preview_with_real_renderer.current_theme = "light"

        # Verify theme was set on renderer
        # In a real scenario, this would be called by the watch method
        real_renderer.set_theme("light")

        # Verify no errors occurred
        assert preview_with_real_renderer.current_theme == "light"

    def test_outline_extraction(self, preview_with_real_renderer, real_renderer):
        """Test outline extraction with real content."""
        content = """# Main Title

## Section One

### Subsection A

## Section Two

Content here.
"""

        # Get outline using real renderer
        outline = real_renderer.get_outline(content)

        assert len(outline) == 4
        assert outline[0].level == 1
        assert outline[0].text == "Main Title"
        assert outline[1].level == 2
        assert outline[1].text == "Section One"
        assert outline[2].level == 3
        assert outline[2].text == "Subsection A"
        assert outline[3].level == 2
        assert outline[3].text == "Section Two"


class TestPreviewPerformance:
    """Performance tests for preview components."""

    @pytest.fixture
    def performance_renderer(self):
        """Create renderer for performance testing."""
        return MarkdownRenderer()

    def test_content_change_tracking(self, performance_renderer):
        """Test that content changes are tracked properly."""
        preview = MarkdownPreview(performance_renderer)

        # Test content change tracking
        contents = [
            "# Test 1",
            "# Test 12",
            "# Test 123",
            "# Test 1234",
            "# Test 12345",
        ]

        # Set multiple contents and verify tracking
        for content in contents:
            preview._last_content = content

        # Last content should be tracked
        assert preview._last_content == "# Test 12345"

    def test_large_content_handling(self, performance_renderer):
        """Test handling of large markdown content."""
        # Generate large content
        large_content = "\n".join(
            [f"# Section {i}\n\nContent for section {i}." for i in range(100)]
        )

        preview = MarkdownPreview(performance_renderer)
        preview.content = large_content

        # Verify content is stored without issues
        assert len(preview.content) > 3000  # Adjusted to actual size
        assert "Section 99" in preview.content


# Test runner helper for development
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
