"""
Link validation utilities for markdown content.

Provides functionality to find, parse, and validate links in markdown documents,
including local file links, fragments, and basic URL validation.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from tino.core.interfaces.renderer import ValidationIssue, Heading


class LinkValidator:
    """Validates links in markdown content."""
    
    def __init__(self) -> None:
        """Initialize the link validator."""
        self._link_patterns = {
            'markdown': r'\[([^\]]*)\]\(([^)]+)\)',
            'reference': r'\[([^\]]*)\]\[([^\]]*)\]',
            'autolink': r'<(https?://[^>]+)>',
            'reference_definition': r'^\s*\[([^\]]+)\]:\s*([^\s]+)(?:\s+["\']([^"\']*)["\'])?$'
        }
    
    def find_all_links(self, content: str) -> List[Dict[str, Any]]:
        """
        Find all links in markdown content.
        
        Args:
            content: Markdown content to search
            
        Returns:
            List of dictionaries with link information
        """
        links = []
        lines = content.split('\n')
        
        # Find reference definitions first
        reference_definitions = self._find_reference_definitions(content)
        
        for line_num, line in enumerate(lines, 1):
            # Find markdown links [text](url)
            for match in re.finditer(self._link_patterns['markdown'], line):
                links.append({
                    "text": match.group(1),
                    "url": match.group(2),
                    "type": "markdown",
                    "line": line_num,
                    "column": match.start() + 1,
                    "raw": match.group(0)
                })
            
            # Find reference links [text][ref]
            for match in re.finditer(self._link_patterns['reference'], line):
                ref_key = match.group(2) or match.group(1)  # Use text as ref if ref is empty
                ref_url = reference_definitions.get(ref_key.lower(), "")
                
                links.append({
                    "text": match.group(1),
                    "reference": ref_key,
                    "url": ref_url,
                    "type": "reference",
                    "line": line_num,
                    "column": match.start() + 1,
                    "raw": match.group(0)
                })
            
            # Find autolinks <url>
            for match in re.finditer(self._link_patterns['autolink'], line):
                url = match.group(1)
                links.append({
                    "text": url,
                    "url": url,
                    "type": "autolink",
                    "line": line_num,
                    "column": match.start() + 1,
                    "raw": match.group(0)
                })
        
        return links
    
    def validate_links(
        self, 
        content: str, 
        file_path: Optional[str] = None,
        check_external: bool = False
    ) -> List[ValidationIssue]:
        """
        Validate all links in markdown content.
        
        Args:
            content: Content to validate
            file_path: Optional path for resolving relative links
            check_external: Whether to check external URLs (requires network)
            
        Returns:
            List of validation issues found
        """
        issues: List[ValidationIssue] = []
        links = self.find_all_links(content)
        
        base_path = Path(file_path).parent if file_path else Path.cwd()
        headings = self._extract_headings_for_validation(content)
        
        for link in links:
            issues.extend(self._validate_single_link(
                link, base_path, headings, check_external
            ))
        
        return issues
    
    def validate_link_url(self, url: str, base_path: Path) -> List[str]:
        """
        Validate a single URL.
        
        Args:
            url: URL to validate
            base_path: Base path for resolving relative URLs
            
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if not url.strip():
            errors.append("Empty URL")
            return errors
        
        parsed = urlparse(url)
        
        if parsed.scheme in ('http', 'https'):
            # External URL - basic validation
            if not parsed.netloc:
                errors.append("Invalid URL format")
        elif parsed.scheme == 'mailto':
            # Email link - basic validation
            if not '@' in url:
                errors.append("Invalid email format")
        elif parsed.scheme == '':
            # Local link
            if url.startswith('#'):
                # Fragment only - cannot validate without headings context
                pass
            else:
                # File path
                try:
                    link_path = base_path / url
                    if not link_path.exists():
                        errors.append(f"File not found: {url}")
                    elif link_path.is_dir():
                        errors.append(f"Link points to directory: {url}")
                except (OSError, ValueError) as e:
                    errors.append(f"Invalid path: {str(e)}")
        else:
            # Unknown scheme
            errors.append(f"Unsupported URL scheme: {parsed.scheme}")
        
        return errors
    
    def check_fragment_exists(self, fragment: str, headings: List[Heading]) -> bool:
        """
        Check if a fragment link exists in the document headings.
        
        Args:
            fragment: Fragment identifier (without #)
            headings: List of headings to check against
            
        Returns:
            True if fragment matches a heading ID
        """
        target_id = fragment.lstrip('#').lower()
        if not target_id:
            return False
        
        return any(heading.id.lower() == target_id for heading in headings)
    
    def suggest_fragment_corrections(
        self, 
        fragment: str, 
        headings: List[Heading]
    ) -> List[str]:
        """
        Suggest corrections for a broken fragment link.
        
        Args:
            fragment: Broken fragment identifier
            headings: Available headings
            
        Returns:
            List of suggested corrections
        """
        target = fragment.lstrip('#').lower()
        suggestions = []
        
        for heading in headings:
            heading_id = heading.id.lower()
            # Simple fuzzy matching - check if target is substring or similar
            if target in heading_id or heading_id in target:
                suggestions.append(f"#{heading.id}")
            elif self._similar_strings(target, heading_id):
                suggestions.append(f"#{heading.id}")
        
        return suggestions[:3]  # Return top 3 suggestions
    
    def _find_reference_definitions(self, content: str) -> Dict[str, str]:
        """Find all reference link definitions in content."""
        definitions = {}
        lines = content.split('\n')
        
        for line in lines:
            match = re.match(self._link_patterns['reference_definition'], line)
            if match:
                key = match.group(1).lower()
                url = match.group(2)
                definitions[key] = url
        
        return definitions
    
    def _validate_single_link(
        self,
        link: Dict[str, Any],
        base_path: Path,
        headings: List[Heading],
        check_external: bool
    ) -> List[ValidationIssue]:
        """Validate a single link and return issues."""
        issues = []
        url = link.get("url", "")
        
        if not url:
            if link["type"] == "reference":
                issues.append(ValidationIssue(
                    type="broken_reference",
                    message=f"Undefined reference: {link['reference']}",
                    line_number=link["line"],
                    column=link["column"],
                    severity="error"
                ))
            return issues
        
        parsed = urlparse(url)
        
        if parsed.scheme in ('http', 'https'):
            if check_external:
                # Would need network request to validate - placeholder for now
                pass
        elif parsed.scheme == '':
            # Local link
            if url.startswith('#'):
                # Fragment link
                fragment = url[1:]  # Remove #
                if not self.check_fragment_exists(fragment, headings):
                    suggestions = self.suggest_fragment_corrections(fragment, headings)
                    suggestion_text = ""
                    if suggestions:
                        suggestion_text = f" Did you mean: {', '.join(suggestions[:2])}?"
                    
                    issues.append(ValidationIssue(
                        type="broken_fragment",
                        message=f"Fragment link '#{fragment}' does not match any heading{suggestion_text}",
                        line_number=link["line"],
                        column=link["column"],
                        severity="warning"
                    ))
            else:
                # File link
                errors = self.validate_link_url(url, base_path)
                for error in errors:
                    issues.append(ValidationIssue(
                        type="broken_link",
                        message=error,
                        line_number=link["line"],
                        column=link["column"],
                        severity="error"
                    ))
        
        return issues
    
    def _extract_headings_for_validation(self, content: str) -> List[Heading]:
        """Extract headings for link validation (simplified version)."""
        headings = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # ATX headings only (for simplicity)
            atx_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if atx_match:
                level = len(atx_match.group(1))
                text = atx_match.group(2).strip()
                text = re.sub(r'\s*#+\s*$', '', text)  # Remove trailing #
                heading_id = self._generate_heading_id(text)
                
                headings.append(Heading(
                    level=level,
                    text=text,
                    id=heading_id,
                    line_number=line_num
                ))
        
        return headings
    
    def _generate_heading_id(self, text: str) -> str:
        """Generate heading ID for link validation."""
        # Convert to lowercase
        heading_id = text.lower()
        
        # Remove markdown formatting
        heading_id = re.sub(r'\*\*([^*]+)\*\*', r'\1', heading_id)  # Bold
        heading_id = re.sub(r'\*([^*]+)\*', r'\1', heading_id)      # Italic
        heading_id = re.sub(r'`([^`]+)`', r'\1', heading_id)        # Code
        heading_id = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', heading_id)  # Links
        
        # Replace spaces and special characters with hyphens
        heading_id = re.sub(r'[^\w\s-]', '', heading_id)
        heading_id = re.sub(r'[\s_-]+', '-', heading_id)
        heading_id = heading_id.strip('-')
        
        return heading_id or "heading"
    
    def _similar_strings(self, a: str, b: str, threshold: float = 0.6) -> bool:
        """Check if two strings are similar (simple implementation)."""
        if not a or not b:
            return False
        
        # Simple character overlap check
        set_a = set(a.lower())
        set_b = set(b.lower())
        
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        
        return union > 0 and intersection / union >= threshold