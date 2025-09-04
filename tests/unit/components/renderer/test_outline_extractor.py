"""
Tests for OutlineExtractor component.

Tests heading extraction, TOC generation, hierarchy building, and navigation.
"""

import pytest

from tino.components.renderer.outline_extractor import OutlineExtractor
from tino.core.interfaces.renderer import Heading


class TestOutlineExtractor:
    """Test suite for OutlineExtractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create an OutlineExtractor instance for testing."""
        return OutlineExtractor()
    
    @pytest.fixture
    def sample_markdown(self):
        """Sample markdown with various heading styles."""
        return """# Main Title

Some content here.

## Section One

More content.

### Subsection A

Content under subsection.

### Subsection B

More content.

## Section Two

Different content.

#### Deep Heading

Very deep content.

Main Alt Title
==============

Alt section under setext.

Alt Subsection
--------------

Alt subsection content.

### Back to ATX

Final content.
"""
    
    def test_extract_atx_headings(self, extractor):
        """Test extraction of ATX-style headings (# ## ###)."""
        content = """# Heading 1

## Heading 2

### Heading 3

#### Heading 4

##### Heading 5

###### Heading 6"""
        
        headings = extractor.extract_headings(content)
        
        assert len(headings) == 6
        
        for i, heading in enumerate(headings, 1):
            assert heading.level == i
            assert heading.text == f"Heading {i}"
            assert heading.id == f"heading-{i}"
            assert heading.line_number == i * 2 - 1  # Every other line
    
    def test_extract_setext_headings(self, extractor):
        """Test extraction of Setext-style headings (underlined)."""
        content = """Main Heading
============

Subheading
----------

Regular paragraph.

Another Main
============"""
        
        headings = extractor.extract_headings(content)
        
        assert len(headings) == 3
        
        assert headings[0].level == 1
        assert headings[0].text == "Main Heading"
        assert headings[0].line_number == 1
        
        assert headings[1].level == 2
        assert headings[1].text == "Subheading"
        assert headings[1].line_number == 4
        
        assert headings[2].level == 1
        assert headings[2].text == "Another Main"
        assert headings[2].line_number == 9
    
    def test_extract_mixed_heading_styles(self, extractor, sample_markdown):
        """Test extraction of mixed ATX and Setext headings."""
        headings = extractor.extract_headings(sample_markdown)
        
        # Should find all headings regardless of style
        assert len(headings) == 9
        
        # Check specific headings
        titles = [h.text for h in headings]
        assert "Main Title" in titles
        assert "Section One" in titles
        assert "Main Alt Title" in titles
        assert "Alt Subsection" in titles
    
    def test_heading_id_generation(self, extractor):
        """Test heading ID generation with various text formats."""
        test_cases = [
            ("Simple Title", "simple-title"),
            ("Title with **Bold**", "title-with-bold"),
            ("Title with *Italic*", "title-with-italic"),
            ("Title with `Code`", "title-with-code"),
            ("Title with [Link](url)", "title-with-link"),
            ("Multiple   Spaces", "multiple-spaces"),
            ("Special !@#$% Characters", "special-characters"),
            ("Numbers 123 and More", "numbers-123-and-more"),
            ("Hyphens-and_underscores", "hyphens-and-underscores"),
        ]
        
        for text, expected_id in test_cases:
            content = f"# {text}"
            headings = extractor.extract_headings(content)
            
            assert len(headings) == 1
            assert headings[0].id == expected_id
    
    def test_trailing_hash_removal(self, extractor):
        """Test removal of trailing hashes from ATX headings."""
        content = """# Title One #

## Title Two ##

### Title Three ### 

#### Title Four ####"""
        
        headings = extractor.extract_headings(content)
        
        assert len(headings) == 4
        assert headings[0].text == "Title One"
        assert headings[1].text == "Title Two"
        assert headings[2].text == "Title Three"
        assert headings[3].text == "Title Four"
    
    def test_generate_toc_basic(self, extractor):
        """Test basic TOC generation."""
        headings = [
            Heading(level=1, text="Main Title", id="main-title", line_number=1),
            Heading(level=2, text="Section One", id="section-one", line_number=5),
            Heading(level=2, text="Section Two", id="section-two", line_number=10),
            Heading(level=3, text="Subsection", id="subsection", line_number=15),
        ]
        
        toc = extractor.generate_toc(headings)
        
        assert "# Table of Contents" in toc
        assert "- [Main Title](#main-title)" in toc
        assert "  - [Section One](#section-one)" in toc
        assert "  - [Section Two](#section-two)" in toc
        assert "    - [Subsection](#subsection)" in toc
    
    def test_generate_toc_with_max_level(self, extractor):
        """Test TOC generation with maximum level limit."""
        headings = [
            Heading(level=1, text="Main Title", id="main-title", line_number=1),
            Heading(level=2, text="Section One", id="section-one", line_number=5),
            Heading(level=3, text="Subsection", id="subsection", line_number=10),
            Heading(level=4, text="Deep Section", id="deep-section", line_number=15),
        ]
        
        toc = extractor.generate_toc(headings, max_level=2)
        
        assert "[Main Title](#main-title)" in toc
        assert "[Section One](#section-one)" in toc
        assert "[Subsection](#subsection)" not in toc  # Level 3 excluded
        assert "[Deep Section](#deep-section)" not in toc  # Level 4 excluded
    
    def test_generate_toc_empty_headings(self, extractor):
        """Test TOC generation with no headings."""
        toc = extractor.generate_toc([])
        assert toc == ""
    
    def test_heading_hierarchy(self, extractor):
        """Test hierarchical structure building."""
        headings = [
            Heading(level=1, text="Main", id="main", line_number=1),
            Heading(level=2, text="Sub A", id="sub-a", line_number=5),
            Heading(level=3, text="Sub A.1", id="sub-a-1", line_number=8),
            Heading(level=3, text="Sub A.2", id="sub-a-2", line_number=12),
            Heading(level=2, text="Sub B", id="sub-b", line_number=16),
            Heading(level=1, text="Main 2", id="main-2", line_number=20),
        ]
        
        hierarchy = extractor.get_heading_hierarchy(headings)
        
        assert len(hierarchy) == 2  # Two top-level headings
        
        # Check first main heading
        main1 = hierarchy[0]
        assert main1["text"] == "Main"
        assert len(main1["children"]) == 2  # Sub A and Sub B
        
        # Check Sub A has children
        sub_a = main1["children"][0]
        assert sub_a["text"] == "Sub A"
        assert len(sub_a["children"]) == 2  # Sub A.1 and Sub A.2
        
        # Check Sub B has no children
        sub_b = main1["children"][1]
        assert sub_b["text"] == "Sub B"
        assert len(sub_b["children"]) == 0
        
        # Check second main heading
        main2 = hierarchy[1]
        assert main2["text"] == "Main 2"
        assert len(main2["children"]) == 0
    
    def test_hierarchy_irregular_levels(self, extractor):
        """Test hierarchy with irregular heading levels."""
        headings = [
            Heading(level=1, text="Main", id="main", line_number=1),
            Heading(level=4, text="Deep", id="deep", line_number=5),  # Skip levels 2,3
            Heading(level=2, text="Back to 2", id="back-to-2", line_number=10),
        ]
        
        hierarchy = extractor.get_heading_hierarchy(headings)
        
        assert len(hierarchy) == 1
        main = hierarchy[0]
        assert len(main["children"]) == 2
        
        # Deep heading should be direct child despite level 4
        deep = main["children"][0]
        assert deep["text"] == "Deep"
        assert deep["level"] == 4
    
    def test_find_heading_by_id(self, extractor):
        """Test finding headings by ID."""
        headings = [
            Heading(level=1, text="Main Title", id="main-title", line_number=1),
            Heading(level=2, text="Section One", id="section-one", line_number=5),
            Heading(level=2, text="Section Two", id="section-two", line_number=10),
        ]
        
        # Find existing heading
        found = extractor.find_heading_by_id(headings, "section-one")
        assert found is not None
        assert found.text == "Section One"
        
        # Find non-existent heading
        not_found = extractor.find_heading_by_id(headings, "nonexistent")
        assert not_found is None
    
    def test_get_next_heading(self, extractor):
        """Test finding next heading after a given line."""
        headings = [
            Heading(level=1, text="Title", id="title", line_number=1),
            Heading(level=2, text="Section A", id="section-a", line_number=5),
            Heading(level=2, text="Section B", id="section-b", line_number=10),
        ]
        
        # Find next heading after line 3
        next_heading = extractor.get_next_heading(headings, 3)
        assert next_heading is not None
        assert next_heading.text == "Section A"
        
        # Find next heading after line 7
        next_heading = extractor.get_next_heading(headings, 7)
        assert next_heading is not None
        assert next_heading.text == "Section B"
        
        # No next heading after last one
        next_heading = extractor.get_next_heading(headings, 15)
        assert next_heading is None
    
    def test_get_previous_heading(self, extractor):
        """Test finding previous heading before a given line."""
        headings = [
            Heading(level=1, text="Title", id="title", line_number=1),
            Heading(level=2, text="Section A", id="section-a", line_number=5),
            Heading(level=2, text="Section B", id="section-b", line_number=10),
        ]
        
        # Find previous heading before line 8
        prev_heading = extractor.get_previous_heading(headings, 8)
        assert prev_heading is not None
        assert prev_heading.text == "Section A"
        
        # Find previous heading before line 12
        prev_heading = extractor.get_previous_heading(headings, 12)
        assert prev_heading is not None
        assert prev_heading.text == "Section B"
        
        # No previous heading before first one
        prev_heading = extractor.get_previous_heading(headings, 1)
        assert prev_heading is None
    
    def test_get_section_range(self, extractor):
        """Test getting line range for a section."""
        headings = [
            Heading(level=1, text="Main", id="main", line_number=1),
            Heading(level=2, text="Sub A", id="sub-a", line_number=5),
            Heading(level=3, text="Sub A.1", id="sub-a-1", line_number=8),
            Heading(level=2, text="Sub B", id="sub-b", line_number=15),  # Same level as Sub A
            Heading(level=1, text="Main 2", id="main-2", line_number=20),  # Same level as Main
        ]
        
        # Range for Sub A should end before Sub B (same level)
        start, end = extractor.get_section_range(headings, headings[1])  # Sub A
        assert start == 5
        assert end == 14  # Line before Sub B
        
        # Range for Sub A.1 should end before Sub B (higher level)
        start, end = extractor.get_section_range(headings, headings[2])  # Sub A.1
        assert start == 8
        assert end == 14
        
        # Range for last heading should go to end
        start, end = extractor.get_section_range(headings, headings[4])  # Main 2
        assert start == 20
        assert end == 20  # No next heading at same level
    
    def test_edge_cases(self, extractor):
        """Test edge cases and error conditions."""
        # Empty content
        headings = extractor.extract_headings("")
        assert headings == []
        
        # Content with no headings
        headings = extractor.extract_headings("Just regular text\n\nNo headings here.")
        assert headings == []
        
        # Only whitespace headings
        content = "#   \n##  \n###"
        headings = extractor.extract_headings(content)
        # Should create headings with empty or "heading" text
        assert len(headings) == 3
        
        # Malformed setext
        content = "Title\n==\nNot enough equals\n="
        headings = extractor.extract_headings(content)
        # Should only find properly formatted setext
        assert len(headings) <= 1
    
    def test_unicode_handling(self, extractor):
        """Test handling of Unicode characters in headings."""
        content = """# 中文标题

## Título en Español

### Заголовок на русском

#### العنوان بالعربية

##### Título çom açentos"""
        
        headings = extractor.extract_headings(content)
        
        assert len(headings) == 5
        assert headings[0].text == "中文标题"
        assert headings[1].text == "Título en Español" 
        assert headings[2].text == "Заголовок на русском"
        assert headings[3].text == "العنوان بالعربية"
        assert headings[4].text == "Título çom açentos"
        
        # IDs should be properly generated (may be simplified)
        for heading in headings:
            assert len(heading.id) > 0
            assert heading.id != ""
    
    def test_performance_large_document(self, extractor):
        """Test performance with large document."""
        import time
        
        # Generate large document with many headings
        content_lines = []
        for i in range(1000):
            content_lines.append(f"## Heading {i}")
            content_lines.append("Some content here.")
            content_lines.append("")
        
        content = "\n".join(content_lines)
        
        start_time = time.perf_counter()
        headings = extractor.extract_headings(content)
        end_time = time.perf_counter()
        
        extraction_time = (end_time - start_time) * 1000  # Convert to ms
        
        assert len(headings) == 1000
        assert extraction_time < 100, f"Extraction took {extraction_time:.2f}ms, should be <100ms"
    
    def test_toc_generation_large_hierarchy(self, extractor):
        """Test TOC generation with large hierarchy."""
        # Generate nested headings
        headings = []
        line_num = 1
        
        for i in range(10):  # 10 main sections
            headings.append(Heading(level=1, text=f"Main {i}", id=f"main-{i}", line_number=line_num))
            line_num += 5
            
            for j in range(5):  # 5 subsections each
                headings.append(Heading(level=2, text=f"Sub {i}.{j}", id=f"sub-{i}-{j}", line_number=line_num))
                line_num += 3
                
                for k in range(3):  # 3 sub-subsections each
                    headings.append(Heading(level=3, text=f"SubSub {i}.{j}.{k}", id=f"subsub-{i}-{j}-{k}", line_number=line_num))
                    line_num += 2
        
        toc = extractor.generate_toc(headings)
        
        # Should generate complete TOC
        assert "# Table of Contents" in toc
        assert toc.count("- [Main") == 10
        assert toc.count("  - [Sub ") == 50  # More specific match to avoid SubSub
        assert toc.count("    - [SubSub") == 150