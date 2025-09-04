"""
Markdown renderer implementation using mistune.

Provides markdown parsing, HTML rendering, outline extraction, and link validation
with performance optimizations and caching.
"""

import re
import time
from typing import Any, Dict, List, Optional

import mistune
from textual.widgets import Markdown
from textual.widget import Widget

from tino.core.interfaces.renderer import (
    IRenderer, 
    RenderResult, 
    Heading, 
    ValidationIssue
)
from .outline_extractor import OutlineExtractor
from .link_validator import LinkValidator
from .cache import RenderCache


class MarkdownRenderer(IRenderer):
    """
    Markdown renderer using mistune 3.x for parsing and rendering.
    
    Supports CommonMark + GitHub Flavored Markdown with tables, provides
    caching for performance, and includes link validation.
    """
    
    def __init__(self) -> None:
        """Initialize the markdown renderer."""
        # Configure mistune with CommonMark + GFM features
        self._markdown = mistune.create_markdown(
            escape=False,
            plugins=['strikethrough', 'footnotes', 'table', 'task_lists', 'def_list']
        )
        
        # Initialize components
        self._cache = RenderCache(max_size=100, max_age_seconds=300.0)
        self._outline_extractor = OutlineExtractor()
        self._link_validator = LinkValidator()
        
        # Current theme
        self._theme = "dark"
        
        # Supported formats
        self._supported_formats = [".md", ".markdown", ".mdown", ".mkd", ".mkdown"]
        
        # Available themes
        self._available_themes = ["dark", "light"]
        
        # CSS templates for different themes
        self._css_templates = {
            "dark": self._get_dark_theme_css(),
            "light": self._get_light_theme_css()
        }
    
    def render_html(self, content: str, file_path: Optional[str] = None) -> RenderResult:
        """Render markdown content to HTML with caching."""
        start_time = time.perf_counter()
        
        # Check cache first
        cached_result = self._cache.get(content, file_path, self._theme)
        if cached_result:
            return cached_result
        
        # Parse and render
        html = self._markdown(content)
        
        # Extract outline using outline extractor
        outline = self._outline_extractor.extract_headings(content)
        
        # Validate content
        issues = self.validate(content, file_path)
        
        # Calculate render time
        render_time = (time.perf_counter() - start_time) * 1000
        
        # Create result
        result = RenderResult(
            html=html,
            outline=outline,
            issues=issues,
            render_time_ms=render_time,
            cached=False
        )
        
        # Cache the result
        self._cache.put(content, result, file_path, self._theme)
        
        return result
    
    def render_preview(self, content: str, file_path: Optional[str] = None) -> Widget:
        """Render markdown content for preview display using Textual Markdown widget."""
        # Use Textual's Markdown widget for TUI display
        return Markdown(content)
    
    def get_outline(self, content: str) -> List[Heading]:
        """Extract document outline from markdown headings."""
        return self._outline_extractor.extract_headings(content)
    
    def validate(self, content: str, file_path: Optional[str] = None) -> List[ValidationIssue]:
        """Validate markdown content for issues."""
        return self._link_validator.validate_links(content, file_path)
    
    def supports_format(self, file_extension: str) -> bool:
        """Check if the renderer supports the given file format."""
        return file_extension.lower() in self._supported_formats
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats."""
        return self._supported_formats.copy()
    
    def set_theme(self, theme_name: str) -> None:
        """Set the rendering theme."""
        if theme_name in self._available_themes:
            self._theme = theme_name
            # Clear cache when theme changes
            self._cache.clear()
    
    def get_available_themes(self) -> List[str]:
        """Get list of available themes."""
        return self._available_themes.copy()
    
    def clear_cache(self) -> None:
        """Clear the rendering cache."""
        self._cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._cache.get_stats()
    
    def export_html(
        self, 
        content: str, 
        output_path: str,
        standalone: bool = True,
        include_css: bool = True
    ) -> bool:
        """Export markdown content as HTML file."""
        try:
            render_result = self.render_html(content)
            html_content = render_result.html
            
            if standalone:
                html_content = self._create_standalone_html(
                    html_content, 
                    include_css=include_css
                )
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return True
            
        except Exception:
            return False
    
    def get_word_count(self, content: str) -> Dict[str, int]:
        """Get word count statistics for markdown content."""
        # Remove markdown syntax for accurate word count
        plain_text = self._strip_markdown_syntax(content)
        
        words = len(plain_text.split())
        characters = len(plain_text)
        characters_with_spaces = len(content)
        paragraphs = len([p for p in content.split('\n\n') if p.strip()])
        lines = len(content.split('\n'))
        
        return {
            "words": words,
            "characters": characters,
            "characters_with_spaces": characters_with_spaces,
            "paragraphs": paragraphs,
            "lines": lines
        }
    
    def find_links(self, content: str) -> List[Dict[str, Any]]:
        """Find all links in markdown content."""
        return self._link_validator.find_all_links(content)
    
    def validate_links(self, content: str, file_path: Optional[str] = None) -> List[ValidationIssue]:
        """Validate all links in markdown content."""
        return self._link_validator.validate_links(content, file_path)
    
    # Private helper methods
    
    def _strip_markdown_syntax(self, content: str) -> str:
        """Strip markdown syntax for plain text word counting."""
        # Remove headers
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        
        # Remove bold/italic
        content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)
        content = re.sub(r'\*([^*]+)\*', r'\1', content)
        content = re.sub(r'__([^_]+)__', r'\1', content)
        content = re.sub(r'_([^_]+)_', r'\1', content)
        
        # Remove links but keep text
        content = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', content)
        
        # Remove inline code
        content = re.sub(r'`([^`]+)`', r'\1', content)
        
        # Remove code blocks
        content = re.sub(r'```[^`]*```', '', content, flags=re.DOTALL)
        
        return content
    
    def _create_standalone_html(self, html_content: str, include_css: bool = True) -> str:
        """Create a standalone HTML document."""
        css = self._css_templates[self._theme] if include_css else ""
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document</title>
    {f'<style>{css}</style>' if css else ''}
</head>
<body>
    {html_content}
</body>
</html>"""
    
    def _get_dark_theme_css(self) -> str:
        """Get CSS for dark theme."""
        return """
        body {
            background-color: #1e1e1e;
            color: #d4d4d4;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        h1, h2, h3, h4, h5, h6 {
            color: #ffffff;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }
        
        h1 { border-bottom: 2px solid #404040; padding-bottom: 0.5rem; }
        h2 { border-bottom: 1px solid #404040; padding-bottom: 0.3rem; }
        
        code {
            background-color: #2d2d30;
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', monospace;
        }
        
        pre {
            background-color: #2d2d30;
            padding: 1rem;
            border-radius: 5px;
            overflow-x: auto;
        }
        
        blockquote {
            border-left: 4px solid #007acc;
            margin: 0;
            padding-left: 1rem;
            color: #b3b3b3;
        }
        
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 1rem 0;
        }
        
        th, td {
            border: 1px solid #404040;
            padding: 0.5rem;
            text-align: left;
        }
        
        th {
            background-color: #2d2d30;
            font-weight: bold;
        }
        
        a {
            color: #007acc;
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }
        """
    
    def _get_light_theme_css(self) -> str:
        """Get CSS for light theme."""
        return """
        body {
            background-color: #ffffff;
            color: #333333;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        h1, h2, h3, h4, h5, h6 {
            color: #000000;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }
        
        h1 { border-bottom: 2px solid #e0e0e0; padding-bottom: 0.5rem; }
        h2 { border-bottom: 1px solid #e0e0e0; padding-bottom: 0.3rem; }
        
        code {
            background-color: #f8f8f8;
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', monospace;
            border: 1px solid #e0e0e0;
        }
        
        pre {
            background-color: #f8f8f8;
            padding: 1rem;
            border-radius: 5px;
            overflow-x: auto;
            border: 1px solid #e0e0e0;
        }
        
        blockquote {
            border-left: 4px solid #007acc;
            margin: 0;
            padding-left: 1rem;
            color: #666666;
        }
        
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 1rem 0;
        }
        
        th, td {
            border: 1px solid #e0e0e0;
            padding: 0.5rem;
            text-align: left;
        }
        
        th {
            background-color: #f8f8f8;
            font-weight: bold;
        }
        
        a {
            color: #007acc;
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }
        """