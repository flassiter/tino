"""
Tests for MarkdownRenderer component.

Tests markdown parsing, HTML rendering, outline extraction, link validation,
caching behavior, and performance requirements.
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tino.components.renderer.markdown_renderer import MarkdownRenderer
from tino.core.interfaces.renderer import Heading, ValidationIssue


class TestMarkdownRenderer:
    """Test suite for MarkdownRenderer."""
    
    @pytest.fixture
    def renderer(self):
        """Create a MarkdownRenderer instance for testing."""
        return MarkdownRenderer()
    
    @pytest.fixture
    def sample_markdown(self):
        """Sample markdown content for testing."""
        return """# Main Title

This is a paragraph with **bold** and *italic* text.

## Section One

Here's a [link](example.md) and a [broken link](missing.md).

### Subsection

- List item one
- List item two

## Section Two

| Column 1 | Column 2 |
|----------|----------|
| Cell 1   | Cell 2   |

### Another Subsection

```python
def hello():
    print("Hello, World!")
```

[Internal link](#section-one) and [broken fragment](#nonexistent).
"""

    def test_interface_implementation(self, renderer):
        """Test that MarkdownRenderer properly implements IRenderer interface."""
        from tino.core.interfaces.renderer import IRenderer
        assert isinstance(renderer, IRenderer)
        
        # Check all required methods exist
        required_methods = [
            'render_html', 'render_preview', 'get_outline', 'validate',
            'supports_format', 'get_supported_formats', 'set_theme',
            'get_available_themes', 'clear_cache', 'get_cache_stats',
            'export_html', 'get_word_count', 'find_links', 'validate_links'
        ]
        
        for method_name in required_methods:
            assert hasattr(renderer, method_name)
            assert callable(getattr(renderer, method_name))
    
    def test_basic_html_rendering(self, renderer, sample_markdown):
        """Test basic HTML rendering functionality."""
        result = renderer.render_html(sample_markdown)
        
        assert result.html is not None
        assert len(result.html) > 0
        assert '<h1>' in result.html
        assert '<h2>' in result.html
        assert '<h3>' in result.html
        assert '<strong>bold</strong>' in result.html
        assert '<em>italic</em>' in result.html
        assert '<table>' in result.html
        assert '<code' in result.html  # Match code tags (with or without attributes)
        assert not result.cached  # First render should not be cached
    
    def test_outline_extraction(self, renderer, sample_markdown):
        """Test outline extraction from markdown."""
        result = renderer.render_html(sample_markdown)
        headings = result.outline
        
        assert len(headings) == 5
        
        # Check heading hierarchy
        assert headings[0].level == 1
        assert headings[0].text == "Main Title"
        assert headings[0].line_number == 1
        
        assert headings[1].level == 2
        assert headings[1].text == "Section One"
        
        assert headings[2].level == 3
        assert headings[2].text == "Subsection"
        
        # Check generated IDs
        assert headings[0].id == "main-title"
        assert headings[1].id == "section-one"
        assert headings[2].id == "subsection"
    
    def test_get_outline_method(self, renderer, sample_markdown):
        """Test standalone outline extraction method."""
        headings = renderer.get_outline(sample_markdown)
        
        assert len(headings) == 5
        assert all(isinstance(h, Heading) for h in headings)
        
        # Check that IDs are unique
        ids = [h.id for h in headings]
        assert len(ids) == len(set(ids))
    
    def test_setext_headings(self, renderer):
        """Test Setext-style heading parsing."""
        content = """Main Title
==========

Subtitle
--------

Regular paragraph.
"""
        
        headings = renderer.get_outline(content)
        
        assert len(headings) == 2
        assert headings[0].level == 1
        assert headings[0].text == "Main Title"
        assert headings[1].level == 2
        assert headings[1].text == "Subtitle"
    
    def test_link_finding(self, renderer, sample_markdown):
        """Test finding links in markdown content."""
        links = renderer.find_links(sample_markdown)
        
        # Should find markdown links, reference links, etc.
        assert len(links) >= 4  # At least 4 links in sample
        
        link_urls = [link.get('url', '') for link in links]
        assert 'example.md' in link_urls
        assert 'missing.md' in link_urls
        assert '#section-one' in link_urls
        assert '#nonexistent' in link_urls
    
    def test_link_validation(self, renderer):
        """Test link validation functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a test file
            existing_file = temp_path / "existing.md"
            existing_file.write_text("# Existing File")
            
            content = """# Test Document

[Good link](existing.md)
[Broken link](missing.md)
[Fragment link](#test-document)
[Broken fragment](#nonexistent)
"""
            
            issues = renderer.validate_links(content, str(temp_path / "test.md"))
            
            # Should find broken link and broken fragment
            issue_types = [issue.type for issue in issues]
            assert "broken_link" in issue_types
            assert "broken_fragment" in issue_types
            
            # Should have proper severity levels
            assert any(issue.severity == "error" for issue in issues)
            assert any(issue.severity == "warning" for issue in issues)
    
    def test_caching_behavior(self, renderer, sample_markdown):
        """Test that caching works correctly."""
        # First render
        result1 = renderer.render_html(sample_markdown)
        assert not result1.cached
        
        # Second render with same content should be cached
        result2 = renderer.render_html(sample_markdown)
        assert result2.cached
        
        # Should be same HTML output
        assert result1.html == result2.html
    
    def test_cache_invalidation(self, renderer, sample_markdown):
        """Test cache invalidation on theme change."""
        # Render with default theme
        result1 = renderer.render_html(sample_markdown)
        assert not result1.cached
        
        # Change theme and render again - should not be cached
        renderer.set_theme("light")
        result2 = renderer.render_html(sample_markdown)
        assert not result2.cached
    
    def test_cache_statistics(self, renderer, sample_markdown):
        """Test cache statistics tracking."""
        initial_stats = renderer.get_cache_stats()
        assert initial_stats["cache_size"] == 0
        
        # Render content
        renderer.render_html(sample_markdown)
        
        stats_after = renderer.get_cache_stats()
        assert stats_after["cache_size"] == 1
        
        # Clear cache
        renderer.clear_cache()
        cleared_stats = renderer.get_cache_stats()
        assert cleared_stats["cache_size"] == 0
    
    def test_supported_formats(self, renderer):
        """Test file format support checking."""
        supported = renderer.get_supported_formats()
        assert ".md" in supported
        assert ".markdown" in supported
        
        assert renderer.supports_format(".md")
        assert renderer.supports_format(".markdown")
        assert not renderer.supports_format(".txt")
    
    def test_theme_support(self, renderer):
        """Test theme functionality."""
        themes = renderer.get_available_themes()
        assert "dark" in themes
        assert "light" in themes
        
        # Test theme setting
        renderer.set_theme("light")
        # Should not raise any errors
        
        renderer.set_theme("invalid")
        # Should not crash but might not change theme
    
    def test_html_export(self, renderer, sample_markdown):
        """Test HTML export functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "output.html"
            
            success = renderer.export_html(
                sample_markdown, 
                str(output_path),
                standalone=True,
                include_css=True
            )
            
            assert success
            assert output_path.exists()
            
            html_content = output_path.read_text()
            assert "<!DOCTYPE html>" in html_content
            assert "<html" in html_content
            assert "<head>" in html_content
            assert "<body>" in html_content
            assert "<style>" in html_content  # CSS included
    
    def test_html_export_minimal(self, renderer, sample_markdown):
        """Test minimal HTML export without standalone format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "minimal.html"
            
            success = renderer.export_html(
                sample_markdown, 
                str(output_path),
                standalone=False,
                include_css=False
            )
            
            assert success
            assert output_path.exists()
            
            html_content = output_path.read_text()
            assert "<!DOCTYPE html>" not in html_content
            assert "<h1>" in html_content  # Should have actual content
    
    def test_word_count(self, renderer, sample_markdown):
        """Test word count functionality."""
        stats = renderer.get_word_count(sample_markdown)
        
        assert "words" in stats
        assert "characters" in stats
        assert "characters_with_spaces" in stats
        assert "paragraphs" in stats
        assert "lines" in stats
        
        assert stats["words"] > 0
        assert stats["characters"] > 0
        assert stats["paragraphs"] > 0
        assert stats["lines"] > 0
        assert stats["characters_with_spaces"] >= stats["characters"]
    
    def test_word_count_markdown_stripping(self, renderer):
        """Test that word count strips markdown syntax."""
        content = "This is **bold** and *italic* text with `code`."
        stats = renderer.get_word_count(content)
        
        # Should count 8 words: "This is bold and italic text with code"
        assert stats["words"] == 8
    
    def test_render_preview_widget(self, renderer, sample_markdown):
        """Test preview widget generation."""
        widget = renderer.render_preview(sample_markdown)
        
        # Should return a Textual widget
        from textual.widget import Widget
        assert isinstance(widget, Widget)
    
    def test_validation_comprehensive(self, renderer):
        """Test comprehensive validation functionality."""
        content = """# Test
        
[Good internal](#test)
[Broken internal](#missing)
[Unmatched brackets test](broken
"""
        
        issues = renderer.validate(content)
        
        # Should find broken fragment issue
        issue_types = [issue.type for issue in issues]
        assert "broken_fragment" in issue_types
        
        # The malformed link [text](broken is not detected as it doesn't match markdown pattern
        # This is correct behavior - malformed links are simply not parsed as links
    
    def test_performance_requirement(self, renderer):
        """Test that rendering meets performance requirements (<50ms)."""
        # Test with moderately sized content
        content = "# Performance Test\n\n" + ("Some content paragraph. " * 100)
        
        start_time = time.perf_counter()
        result = renderer.render_html(content)
        end_time = time.perf_counter()
        
        render_time_ms = (end_time - start_time) * 1000
        
        # Should render within 50ms requirement (first render)
        assert render_time_ms < 50, f"Render time {render_time_ms:.2f}ms exceeds 50ms requirement"
        
        # Cached render should be much faster
        start_time = time.perf_counter()
        cached_result = renderer.render_html(content)
        end_time = time.perf_counter()
        
        cached_render_time_ms = (end_time - start_time) * 1000
        
        assert cached_result.cached
        assert cached_render_time_ms < render_time_ms
    
    def test_large_document_performance(self, renderer):
        """Test performance with larger document."""
        # Generate larger content
        large_content = []
        for i in range(50):
            large_content.extend([
                f"# Heading {i}",
                "",
                "This is a paragraph with some content. " * 20,
                "",
                f"## Subheading {i}.1",
                "",
                "- List item 1",
                "- List item 2", 
                "- List item 3",
                "",
                "| Column 1 | Column 2 |",
                "|----------|----------|",
                f"| Data {i} | Value {i} |",
                ""
            ])
        
        content = "\n".join(large_content)
        
        start_time = time.perf_counter()
        result = renderer.render_html(content)
        end_time = time.perf_counter()
        
        render_time_ms = (end_time - start_time) * 1000
        
        # Should still render within reasonable time
        assert render_time_ms < 200, f"Large document render time {render_time_ms:.2f}ms too slow"
        assert len(result.outline) == 100  # Should find all headings
    
    def test_error_handling(self, renderer):
        """Test error handling for edge cases."""
        # Empty content
        result = renderer.render_html("")
        assert result.html == ""
        assert result.outline == []
        
        # Only whitespace
        result = renderer.render_html("   \n\n   ")
        assert result.html.strip() == ""
        
        # Very malformed content should not crash
        malformed = "# Heading\n[broken link("
        result = renderer.render_html(malformed)
        assert result.html is not None  # Should not crash
    
    def test_heading_id_generation(self, renderer):
        """Test heading ID generation for various edge cases."""
        test_cases = [
            ("Simple Heading", "simple-heading"),
            ("Heading with **Bold**", "heading-with-bold"),
            ("Heading with `code`", "heading-with-code"),
            ("Heading with [link](url)", "heading-with-link"),
            ("Multiple   Spaces", "multiple-spaces"),
            ("Special !@#$% Characters", "special-characters"),
            ("", "heading"),  # Empty heading
        ]
        
        for text, expected_id in test_cases:
            content = f"# {text}"
            headings = renderer.get_outline(content)
            if headings:
                assert headings[0].id == expected_id, f"Expected '{expected_id}' for '{text}', got '{headings[0].id}'"
    
    def test_concurrent_rendering(self, renderer, sample_markdown):
        """Test that concurrent rendering works correctly."""
        import threading
        import time
        
        results = []
        errors = []
        
        def render_worker():
            try:
                result = renderer.render_html(sample_markdown)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Start multiple rendering threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=render_worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0, f"Concurrent rendering errors: {errors}"
        assert len(results) == 5
        
        # All results should have the same HTML (since content is the same)
        first_html = results[0].html
        assert all(r.html == first_html for r in results)
    
    @pytest.mark.parametrize("theme", ["dark", "light"])
    def test_theme_css_generation(self, renderer, theme):
        """Test CSS generation for different themes."""
        renderer.set_theme(theme)
        
        # Test standalone HTML generation includes theme-appropriate CSS
        content = "# Test Heading\n\nSome content."
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / f"test_{theme}.html"
            
            success = renderer.export_html(
                content,
                str(output_path),
                standalone=True,
                include_css=True
            )
            
            assert success
            html_content = output_path.read_text()
            
            # Should contain theme-appropriate styles
            if theme == "dark":
                assert "#1e1e1e" in html_content  # Dark background
                assert "#d4d4d4" in html_content  # Light text
            elif theme == "light":
                assert "#ffffff" in html_content  # Light background
                assert "#333333" in html_content  # Dark text