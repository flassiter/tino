"""
Renderer interface for document rendering operations.

Defines the contract for renderer components that convert markdown and other
document formats to HTML, extract document structure, and validate content.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from textual.widget import Widget


@dataclass
class Heading:
    """Represents a heading in a document."""

    level: int  # 1-6 for H1-H6
    text: str
    id: str  # For linking
    line_number: int  # Line in source document


@dataclass
class ValidationIssue:
    """Represents a validation issue found in content."""

    type: str  # "broken_link", "invalid_syntax", etc.
    message: str
    line_number: int
    column: int
    severity: str  # "error", "warning", "info"


@dataclass
class RenderResult:
    """Result of a rendering operation."""

    html: str
    outline: list[Heading]
    issues: list[ValidationIssue]
    render_time_ms: float
    cached: bool = False


class IRenderer(ABC):
    """
    Interface for document renderer components.

    Handles conversion of markdown and other formats to HTML, extraction of
    document structure, content validation, and preview generation.
    """

    @abstractmethod
    def render_html(
        self, content: str, file_path: str | None = None
    ) -> RenderResult:
        """
        Render content to HTML.

        Args:
            content: Source content to render
            file_path: Optional path for resolving relative links

        Returns:
            RenderResult containing HTML and metadata
        """
        pass

    @abstractmethod
    def render_preview(self, content: str, file_path: str | None = None) -> Widget:
        """
        Render content for preview display.

        Args:
            content: Source content to render
            file_path: Optional path for resolving relative links

        Returns:
            Widget suitable for display in TUI
        """
        pass

    @abstractmethod
    def get_outline(self, content: str) -> list[Heading]:
        """
        Extract document outline from content.

        Args:
            content: Source content to analyze

        Returns:
            List of headings in document order
        """
        pass

    @abstractmethod
    def validate(
        self, content: str, file_path: str | None = None
    ) -> list[ValidationIssue]:
        """
        Validate content for issues.

        Args:
            content: Source content to validate
            file_path: Optional path for resolving relative links

        Returns:
            List of validation issues found
        """
        pass

    @abstractmethod
    def supports_format(self, file_extension: str) -> bool:
        """
        Check if renderer supports a file format.

        Args:
            file_extension: File extension (e.g., ".md", ".rst")

        Returns:
            True if format is supported
        """
        pass

    @abstractmethod
    def get_supported_formats(self) -> list[str]:
        """
        Get list of supported file formats.

        Returns:
            List of supported file extensions
        """
        pass

    @abstractmethod
    def set_theme(self, theme_name: str) -> None:
        """
        Set the rendering theme.

        Args:
            theme_name: Name of theme to use ("dark", "light", etc.)
        """
        pass

    @abstractmethod
    def get_available_themes(self) -> list[str]:
        """
        Get list of available themes.

        Returns:
            List of available theme names
        """
        pass

    @abstractmethod
    def clear_cache(self) -> None:
        """Clear any cached rendering results."""
        pass

    @abstractmethod
    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        pass

    @abstractmethod
    def export_html(
        self,
        content: str,
        output_path: str,
        standalone: bool = True,
        include_css: bool = True,
    ) -> bool:
        """
        Export content as HTML file.

        Args:
            content: Source content to export
            output_path: Path where to save HTML file
            standalone: Whether to create standalone HTML
            include_css: Whether to include CSS styling

        Returns:
            True if export was successful
        """
        pass

    @abstractmethod
    def get_word_count(self, content: str) -> dict[str, int]:
        """
        Get word count statistics.

        Args:
            content: Content to analyze

        Returns:
            Dictionary with statistics (words, characters, paragraphs, etc.)
        """
        pass

    @abstractmethod
    def find_links(self, content: str) -> list[dict[str, Any]]:
        """
        Find all links in content.

        Args:
            content: Content to search

        Returns:
            List of dictionaries with link information
        """
        pass

    @abstractmethod
    def validate_links(
        self, content: str, file_path: str | None = None
    ) -> list[ValidationIssue]:
        """
        Validate all links in content.

        Args:
            content: Content to validate
            file_path: Optional path for resolving relative links

        Returns:
            List of link validation issues
        """
        pass
