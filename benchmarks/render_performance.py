"""
Performance benchmarks for MarkdownRenderer component.

Tests rendering performance to ensure <50ms update times as specified
in the requirements, and provides detailed performance analysis.
"""

import statistics
import time
from pathlib import Path
from typing import List, Dict, Any

from tino.components.renderer.markdown_renderer import MarkdownRenderer


class RenderPerformanceBenchmark:
    """Benchmark suite for markdown rendering performance."""
    
    def __init__(self) -> None:
        """Initialize the benchmark suite."""
        self.renderer = MarkdownRenderer()
        self.results: List[Dict[str, Any]] = []
    
    def generate_test_content(self, size: str = "medium") -> str:
        """
        Generate test markdown content of various sizes.
        
        Args:
            size: Size category ("small", "medium", "large", "xlarge")
            
        Returns:
            Generated markdown content
        """
        if size == "small":
            return self._generate_small_content()
        elif size == "medium":
            return self._generate_medium_content()
        elif size == "large":
            return self._generate_large_content()
        elif size == "xlarge":
            return self._generate_xlarge_content()
        else:
            raise ValueError(f"Unknown size: {size}")
    
    def _generate_small_content(self) -> str:
        """Generate small test content (~1KB)."""
        return """# Small Test Document

This is a small markdown document for performance testing.

## Introduction

Here's some **bold text** and *italic text* with a [link](example.md).

### Features

- List item one
- List item two
- List item three

```python
def hello():
    print("Hello, World!")
```

That's it!
"""
    
    def _generate_medium_content(self) -> str:
        """Generate medium test content (~10KB)."""
        sections = []
        
        sections.append("# Medium Test Document")
        sections.append("")
        sections.append("This is a medium-sized markdown document for performance testing.")
        sections.append("")
        
        for i in range(10):
            sections.extend([
                f"## Section {i + 1}",
                "",
                f"This is section {i + 1} with various markdown elements.",
                "",
                f"### Subsection {i + 1}.1",
                "",
                "Here's a paragraph with **bold**, *italic*, and `inline code`.",
                f"Also includes [a link](section-{i}.md) and [internal link](#section-{i + 1}).",
                "",
                "#### Lists",
                "",
                "Unordered list:",
                "- Item A",
                "- Item B", 
                "- Item C",
                "",
                "Ordered list:",
                "1. First item",
                "2. Second item",
                "3. Third item",
                "",
                "#### Code Block",
                "",
                "```python",
                f"def function_{i}():",
                f'    """Function number {i}."""',
                f'    return "Result {i}"',
                "```",
                "",
                "#### Table",
                "",
                "| Column 1 | Column 2 | Column 3 |",
                "|----------|----------|----------|",
                f"| Row {i}.1 | Data A | Data B |",
                f"| Row {i}.2 | Data C | Data D |",
                ""
            ])
        
        return "\n".join(sections)
    
    def _generate_large_content(self) -> str:
        """Generate large test content (~50KB)."""
        sections = []
        
        sections.append("# Large Test Document")
        sections.append("")
        sections.append("This is a large markdown document for performance testing.")
        sections.append("")
        
        for i in range(50):
            sections.extend([
                f"## Chapter {i + 1}: Topic {i + 1}",
                "",
                f"This chapter covers topic {i + 1} in detail.",
                "",
                f"### Section {i + 1}.1: Introduction",
                "",
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 5,
                "",
                f"Here's a [link to chapter {i}](chapter-{i}.md) and " +
                f"[internal reference](#chapter-{i + 1}-topic-{i + 1}).",
                "",
                f"### Section {i + 1}.2: Implementation",
                "",
                "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. " * 3,
                "",
                "#### Code Example",
                "",
                "```python",
                f"class Topic{i}:",
                f'    """Implementation for topic {i}."""',
                "",
                "    def __init__(self):",
                f'        self.name = "Topic {i}"',
                f"        self.id = {i}",
                "",
                "    def process(self):",
                f'        print(f"Processing {{self.name}}")',
                f"        return self.id * 2",
                "```",
                "",
                "#### Data Table",
                "",
                "| ID | Name | Value | Status |",
                "|----|----- |-------|--------|",
                f"| {i} | Topic {i} | {i * 10} | Active |",
                f"| {i + 100} | Related {i} | {i * 20} | Pending |",
                "",
                f"### Section {i + 1}.3: Examples",
                "",
                "Multiple examples with various formatting:",
                "",
                f"1. **Example {i}.1**: Using *emphasis* and `code`",
                f"2. **Example {i}.2**: With [external link](https://example{i}.com)",
                f"3. **Example {i}.3**: Featuring ~~strikethrough~~ text",
                "",
                "> This is a blockquote in section " + str(i + 1),
                "> It spans multiple lines",
                "> And provides additional context",
                ""
            ])
        
        return "\n".join(sections)
    
    def _generate_xlarge_content(self) -> str:
        """Generate extra large test content (~200KB)."""
        sections = []
        
        sections.append("# Extra Large Test Document")
        sections.append("")
        sections.append("This is an extra large markdown document for stress testing.")
        sections.append("")
        
        # Generate massive content
        for i in range(200):
            sections.extend([
                f"## Chapter {i + 1}",
                "",
                f"Content for chapter {i + 1}. " + "Lorem ipsum dolor sit amet. " * 20,
                "",
                f"### Section {i + 1}.1",
                "",
                f"Detailed content. " + "Consectetur adipiscing elit. " * 15,
                "",
                f"### Section {i + 1}.2",
                "",
                f"More content. " + "Sed do eiusmod tempor incididunt. " * 10,
                "",
                "#### Code",
                "",
                "```python",
                f"# Code block {i + 1}",
                f"def function_{i}():",
                f"    return {i} * 2",
                "```",
                "",
                "#### List",
                "",
                f"- Item {i}.1",
                f"- Item {i}.2", 
                f"- Item {i}.3",
                ""
            ])
        
        return "\n".join(sections)
    
    def benchmark_render_times(self, iterations: int = 10) -> Dict[str, Any]:
        """
        Benchmark rendering times for different content sizes.
        
        Args:
            iterations: Number of iterations to run for each test
            
        Returns:
            Dictionary with benchmark results
        """
        results = {}
        
        sizes = ["small", "medium", "large", "xlarge"]
        
        for size in sizes:
            print(f"Benchmarking {size} content...")
            
            content = self.generate_test_content(size)
            times = []
            
            # Warm up
            self.renderer.render_html(content)
            self.renderer.clear_cache()  # Clear cache for fair timing
            
            # Run benchmark
            for i in range(iterations):
                start_time = time.perf_counter()
                result = self.renderer.render_html(content)
                end_time = time.perf_counter()
                
                render_time_ms = (end_time - start_time) * 1000
                times.append(render_time_ms)
                
                # Clear cache between iterations for fair comparison
                self.renderer.clear_cache()
            
            # Calculate statistics
            results[size] = {
                "content_size_kb": len(content.encode('utf-8')) / 1024,
                "iterations": iterations,
                "times_ms": times,
                "min_ms": min(times),
                "max_ms": max(times),
                "mean_ms": statistics.mean(times),
                "median_ms": statistics.median(times),
                "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
                "meets_requirement": max(times) < 50.0  # Must be under 50ms
            }
            
            print(f"  Size: {results[size]['content_size_kb']:.1f} KB")
            print(f"  Mean: {results[size]['mean_ms']:.2f} ms")
            print(f"  Max:  {results[size]['max_ms']:.2f} ms")
            print(f"  Requirement (<50ms): {'✓' if results[size]['meets_requirement'] else '✗'}")
            print()
        
        return results
    
    def benchmark_cache_performance(self, iterations: int = 100) -> Dict[str, Any]:
        """
        Benchmark cache performance.
        
        Args:
            iterations: Number of cache operations to test
            
        Returns:
            Dictionary with cache benchmark results
        """
        print("Benchmarking cache performance...")
        
        content = self.generate_test_content("medium")
        
        # First render (cache miss)
        start_time = time.perf_counter()
        result1 = self.renderer.render_html(content)
        first_render_time = (time.perf_counter() - start_time) * 1000
        
        # Subsequent renders (cache hits)
        cache_times = []
        for _ in range(iterations):
            start_time = time.perf_counter()
            result2 = self.renderer.render_html(content)
            cache_time = (time.perf_counter() - start_time) * 1000
            cache_times.append(cache_time)
        
        speedup_factor = first_render_time / statistics.mean(cache_times)
        
        results = {
            "first_render_ms": first_render_time,
            "cache_times_ms": cache_times,
            "cache_mean_ms": statistics.mean(cache_times),
            "cache_max_ms": max(cache_times),
            "speedup_factor": speedup_factor,
            "cache_efficiency": speedup_factor > 5.0  # Should be much faster
        }
        
        print(f"  First render: {results['first_render_ms']:.2f} ms")
        print(f"  Cache mean:   {results['cache_mean_ms']:.4f} ms")
        print(f"  Speedup:      {results['speedup_factor']:.1f}x")
        print(f"  Efficient:    {'✓' if results['cache_efficiency'] else '✗'}")
        print()
        
        return results
    
    def benchmark_outline_extraction(self, iterations: int = 50) -> Dict[str, Any]:
        """
        Benchmark outline extraction performance.
        
        Args:
            iterations: Number of iterations
            
        Returns:
            Dictionary with outline benchmark results
        """
        print("Benchmarking outline extraction...")
        
        content = self.generate_test_content("large")
        times = []
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            outline = self.renderer.get_outline(content)
            end_time = time.perf_counter()
            
            extraction_time = (end_time - start_time) * 1000
            times.append(extraction_time)
        
        results = {
            "content_size_kb": len(content.encode('utf-8')) / 1024,
            "heading_count": len(self.renderer.get_outline(content)),
            "iterations": iterations,
            "times_ms": times,
            "mean_ms": statistics.mean(times),
            "max_ms": max(times),
            "fast_enough": max(times) < 10.0  # Should be very fast
        }
        
        print(f"  Content size: {results['content_size_kb']:.1f} KB")
        print(f"  Headings:     {results['heading_count']}")
        print(f"  Mean time:    {results['mean_ms']:.2f} ms")
        print(f"  Max time:     {results['max_ms']:.2f} ms")
        print(f"  Fast enough:  {'✓' if results['fast_enough'] else '✗'}")
        print()
        
        return results
    
    def benchmark_link_validation(self, iterations: int = 20) -> Dict[str, Any]:
        """
        Benchmark link validation performance.
        
        Args:
            iterations: Number of iterations
            
        Returns:
            Dictionary with validation benchmark results
        """
        print("Benchmarking link validation...")
        
        # Generate content with many links
        content_parts = []
        content_parts.append("# Link Validation Test")
        
        for i in range(100):
            content_parts.extend([
                f"## Section {i}",
                f"Link to [file {i}](file{i}.md) and [section {i}](#section-{i}).",
                f"Reference [link {i}][ref{i}] here.",
                ""
            ])
        
        # Add reference definitions
        for i in range(100):
            content_parts.append(f"[ref{i}]: http://example{i}.com")
        
        content = "\n".join(content_parts)
        times = []
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            issues = self.renderer.validate_links(content)
            end_time = time.perf_counter()
            
            validation_time = (end_time - start_time) * 1000
            times.append(validation_time)
        
        results = {
            "content_size_kb": len(content.encode('utf-8')) / 1024,
            "link_count": len(self.renderer.find_links(content)),
            "iterations": iterations,
            "times_ms": times,
            "mean_ms": statistics.mean(times),
            "max_ms": max(times),
            "acceptable_speed": max(times) < 100.0  # Should validate quickly
        }
        
        print(f"  Content size: {results['content_size_kb']:.1f} KB")
        print(f"  Links:        {results['link_count']}")
        print(f"  Mean time:    {results['mean_ms']:.2f} ms")
        print(f"  Max time:     {results['max_ms']:.2f} ms")
        print(f"  Acceptable:   {'✓' if results['acceptable_speed'] else '✗'}")
        print()
        
        return results
    
    def run_full_benchmark(self) -> Dict[str, Any]:
        """
        Run complete benchmark suite.
        
        Returns:
            Complete benchmark results
        """
        print("=" * 60)
        print("TINO MARKDOWN RENDERER PERFORMANCE BENCHMARK")
        print("=" * 60)
        print()
        
        results = {
            "timestamp": time.time(),
            "renderer_version": "1.0.0",
            "render_performance": self.benchmark_render_times(),
            "cache_performance": self.benchmark_cache_performance(),
            "outline_performance": self.benchmark_outline_extraction(),
            "validation_performance": self.benchmark_link_validation()
        }
        
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        
        # Check if 50ms requirement is met
        render_results = results["render_performance"]
        all_meet_requirement = all(
            size_results["meets_requirement"] 
            for size_results in render_results.values()
        )
        
        print(f"50ms Requirement Met: {'✓' if all_meet_requirement else '✗'}")
        
        if not all_meet_requirement:
            print("\nSizes that exceed 50ms:")
            for size, size_results in render_results.items():
                if not size_results["meets_requirement"]:
                    print(f"  {size}: {size_results['max_ms']:.2f} ms")
        
        print(f"\nCache Performance: {'✓' if results['cache_performance']['cache_efficiency'] else '✗'}")
        print(f"Outline Extraction: {'✓' if results['outline_performance']['fast_enough'] else '✗'}")
        print(f"Link Validation: {'✓' if results['validation_performance']['acceptable_speed'] else '✗'}")
        
        return results
    
    def save_results(self, results: Dict[str, Any], filename: str = "benchmark_results.json") -> None:
        """
        Save benchmark results to file.
        
        Args:
            results: Benchmark results to save
            filename: Output filename
        """
        import json
        
        output_path = Path("benchmarks") / filename
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"Results saved to: {output_path}")


def main() -> None:
    """Run the benchmark suite."""
    benchmark = RenderPerformanceBenchmark()
    results = benchmark.run_full_benchmark()
    benchmark.save_results(results)


if __name__ == "__main__":
    main()