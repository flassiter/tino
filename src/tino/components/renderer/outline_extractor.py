"""
Document outline extraction utilities.

Provides functionality to extract and organize document structure from markdown
content, including heading hierarchy and table of contents generation.
"""

import re
from typing import List, Dict, Any

from tino.core.interfaces.renderer import Heading


class OutlineExtractor:
    """Extracts document outline and generates table of contents from markdown."""
    
    def __init__(self) -> None:
        """Initialize the outline extractor."""
        pass
    
    def extract_headings(self, content: str) -> List[Heading]:
        """
        Extract all headings from markdown content.
        
        Args:
            content: Markdown content to analyze
            
        Returns:
            List of Heading objects in document order
        """
        headings = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            line_num = i + 1
            
            # ATX headings (# ## ###)
            atx_match = re.match(r'^(#{1,6})\s*(.*)$', line)
            if atx_match:
                level = len(atx_match.group(1))
                text = atx_match.group(2).strip()
                # Remove trailing #
                text = re.sub(r'\s*#+\s*$', '', text)
                # Handle empty headings
                if not text:
                    text = "heading"
                heading_id = self._generate_heading_id(text)
                
                headings.append(Heading(
                    level=level,
                    text=text,
                    id=heading_id,
                    line_number=line_num
                ))
            
            # Setext headings (underlined with = or -)
            elif line and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # Require underline to be at least 2 characters (most parsers are lenient)
                if re.match(r'^=+$', next_line) and len(next_line) >= 2:
                    # H1 (underlined with =)
                    heading_id = self._generate_heading_id(line)
                    headings.append(Heading(
                        level=1,
                        text=line,
                        id=heading_id,
                        line_number=line_num
                    ))
                    i += 1  # Skip the underline
                elif re.match(r'^-+$', next_line) and len(next_line) >= 2:
                    # H2 (underlined with -)
                    heading_id = self._generate_heading_id(line)
                    headings.append(Heading(
                        level=2,
                        text=line,
                        id=heading_id,
                        line_number=line_num
                    ))
                    i += 1  # Skip the underline
            
            i += 1
        
        return headings
    
    def generate_toc(self, headings: List[Heading], max_level: int = 6) -> str:
        """
        Generate a table of contents from headings.
        
        Args:
            headings: List of Heading objects
            max_level: Maximum heading level to include in TOC
            
        Returns:
            Markdown-formatted table of contents
        """
        if not headings:
            return ""
        
        toc_lines = ["# Table of Contents\n"]
        
        for heading in headings:
            if heading.level <= max_level:
                indent = "  " * (heading.level - 1)
                link = f"#{heading.id}"
                toc_line = f"{indent}- [{heading.text}]({link})"
                toc_lines.append(toc_line)
        
        return "\n".join(toc_lines)
    
    def get_heading_hierarchy(self, headings: List[Heading]) -> List[Dict[str, Any]]:
        """
        Convert flat heading list to hierarchical structure.
        
        Args:
            headings: List of Heading objects
            
        Returns:
            Nested dictionary representing heading hierarchy
        """
        if not headings:
            return []
        
        hierarchy = []
        stack = []  # Stack to track parent headings
        
        for heading in headings:
            heading_dict = {
                "level": heading.level,
                "text": heading.text,
                "id": heading.id,
                "line_number": heading.line_number,
                "children": []
            }
            
            # Find the correct parent in the stack
            while stack and stack[-1]["level"] >= heading.level:
                stack.pop()
            
            if stack:
                # Add as child to the last item in stack
                stack[-1]["children"].append(heading_dict)
            else:
                # Add as top-level heading
                hierarchy.append(heading_dict)
            
            # Add to stack for potential children
            stack.append(heading_dict)
        
        return hierarchy
    
    def find_heading_by_id(self, headings: List[Heading], heading_id: str) -> Heading | None:
        """
        Find a heading by its ID.
        
        Args:
            headings: List of Heading objects to search
            heading_id: ID to search for
            
        Returns:
            Heading object if found, None otherwise
        """
        for heading in headings:
            if heading.id == heading_id:
                return heading
        return None
    
    def get_next_heading(self, headings: List[Heading], current_line: int) -> Heading | None:
        """
        Get the next heading after the given line number.
        
        Args:
            headings: List of Heading objects
            current_line: Current line number
            
        Returns:
            Next Heading object if found, None otherwise
        """
        for heading in headings:
            if heading.line_number > current_line:
                return heading
        return None
    
    def get_previous_heading(self, headings: List[Heading], current_line: int) -> Heading | None:
        """
        Get the previous heading before the given line number.
        
        Args:
            headings: List of Heading objects
            current_line: Current line number
            
        Returns:
            Previous Heading object if found, None otherwise
        """
        previous = None
        for heading in headings:
            if heading.line_number >= current_line:
                break
            previous = heading
        return previous
    
    def get_section_range(
        self, 
        headings: List[Heading], 
        heading: Heading
    ) -> tuple[int, int]:
        """
        Get the line range of a section (from heading to next heading of same or higher level).
        
        Args:
            headings: List of all headings
            heading: Heading to get range for
            
        Returns:
            Tuple of (start_line, end_line)
        """
        start_line = heading.line_number
        end_line = float('inf')
        
        # Find the index of the current heading
        current_index = -1
        for i, h in enumerate(headings):
            if h.id == heading.id and h.line_number == heading.line_number:
                current_index = i
                break
        
        if current_index == -1:
            return (start_line, start_line)
        
        # Look for next heading at same or higher level
        for i in range(current_index + 1, len(headings)):
            next_heading = headings[i]
            if next_heading.level <= heading.level:
                end_line = next_heading.line_number - 1
                break
        
        return (start_line, int(end_line) if end_line != float('inf') else start_line)
    
    def _generate_heading_id(self, text: str) -> str:
        """
        Generate a URL-safe ID for a heading.
        
        Args:
            text: Heading text
            
        Returns:
            URL-safe ID string
        """
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