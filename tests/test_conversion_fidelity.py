# Copyright (c) 2025 Francis Bain
# SPDX-License-Identifier: Apache-2.0

"""Conversion fidelity tests for CMD-44: Basic conversion fidelity tests.

This mod        markdown = '```python\ndef test():\n    pass\n```'
        result = self.converter.convert(markdown)e contains automated tests that validate Markdown → Confluence
conversion fidelity for MVP. Tests ensure supported elements are converted
correctly and measure conversion accuracy against golden corpus.
"""

from pathlib import Path
from typing import NamedTuple

import pytest

from confluence_markdown import MarkdownToConfluenceConverter


class ConversionTest(NamedTuple):
    """Test case for conversion fidelity."""

    name: str
    input_file: str
    expected_file: str
    required_elements: list[str]


class TestConversionFidelity:
    """Test suite for Markdown → Confluence conversion fidelity."""

    # Test cases constant to avoid duplication
    TEST_CASES = [
        ConversionTest(
            name="headings_levels_1_to_3",
            input_file="headings.md",
            expected_file="headings.html",
            required_elements=["<h1>", "<h2>", "<h3>"],
        ),
        ConversionTest(
            name="unordered_lists",
            input_file="lists.md",
            expected_file="lists.html",
            required_elements=["<ul>", "<li>"],
        ),
        ConversionTest(
            name="fenced_code_blocks",
            input_file="code_blocks.md",
            expected_file="code_blocks.html",
            required_elements=[
                '<ac:structured-macro ac:name="code"',
                'ac:parameter ac:name="language">python',
                "<![CDATA[",
                "]]>",
            ],
        ),
        ConversionTest(
            name="tables_with_headers",
            input_file="tables.md",
            expected_file="tables.html",
            required_elements=["Header 1", "Cell 1", "Row 2"],  # Content preservation for now
        ),
    ]

    def setup_method(self) -> None:
        """Set up test environment with converter."""
        self.converter = MarkdownToConfluenceConverter()
        self.golden_corpus_dir = Path(__file__).parent / "golden_corpus"
        self.input_dir = self.golden_corpus_dir / "input"
        self.expected_dir = self.golden_corpus_dir / "expected"

    def _load_test_case(self, test_case: ConversionTest) -> tuple[str, str]:
        """Load input and expected output for a test case."""
        input_path = self.input_dir / test_case.input_file
        expected_path = self.expected_dir / test_case.expected_file

        input_content = input_path.read_text(encoding="utf-8")
        expected_content = expected_path.read_text(encoding="utf-8")

        return input_content, expected_content

    def _calculate_fidelity(self, actual: str, expected: str) -> float:
        """Calculate conversion fidelity as percentage match."""
        # Normalize whitespace for comparison
        actual_normalized = " ".join(actual.split())
        expected_normalized = " ".join(expected.split())

        if not expected_normalized:
            return 100.0 if not actual_normalized else 0.0

        # Simple character-based similarity
        matches = sum(1 for a, e in zip(actual_normalized, expected_normalized) if a == e)
        total_chars = max(len(actual_normalized), len(expected_normalized))

        return (matches / total_chars) * 100.0 if total_chars > 0 else 100.0

    def _check_required_elements(self, content: str, required_elements: list[str]) -> list[str]:
        """Check if all required elements are present in the content."""
        missing_elements = []
        for element in required_elements:
            if element not in content:
                missing_elements.append(element)
        return missing_elements

    # Test Cases for CMD-44 Acceptance Criteria

    @pytest.mark.parametrize("test_case", TEST_CASES)
    def test_conversion_fidelity(self, test_case: ConversionTest) -> None:
        """Test conversion fidelity for each supported element type."""
        # Load test data
        input_content, expected_content = self._load_test_case(test_case)

        # Perform conversion
        actual_content = self.converter.convert(input_content)

        # Check required elements are present
        missing_elements = self._check_required_elements(
            actual_content, test_case.required_elements
        )
        assert (
            not missing_elements
        ), f"Missing required elements in {test_case.name}: {missing_elements}"

        # Calculate fidelity
        fidelity = self._calculate_fidelity(actual_content, expected_content)

        # Ensure fidelity meets 95% requirement (CMD-44 acceptance criteria)
        assert fidelity >= 95.0, (
            f"Conversion fidelity for {test_case.name} is {fidelity:.1f}%, "
            f"below required 95%.\n"
            f"Expected:\n{expected_content}\n\n"
            f"Actual:\n{actual_content}"
        )

    def test_headings_hierarchy_preservation(self) -> None:
        """Test that heading hierarchy (levels 1-3) is preserved correctly."""
        markdown = "# H1\n## H2\n### H3"
        result = self.converter.convert(markdown)

        # Check that heading tags appear in correct order
        assert result.find("<h1>") < result.find("<h2>") < result.find("<h3>")
        assert "<h1>H1</h1>" in result
        assert "<h2>H2</h2>" in result
        assert "<h3>H3</h3>" in result

    def test_ordered_lists_conversion(self) -> None:
        """Test ordered list conversion (currently limited support)."""
        markdown = "1. First item\n2. Second item\n3. Third item"
        result = self.converter.convert(markdown)

        # Verify content preservation even if not proper HTML lists
        assert "First item" in result
        assert "Second item" in result
        assert "Third item" in result

    def test_fenced_code_blocks_with_language_tags(self) -> None:
        """Test fenced code blocks preserve language information."""
        markdown = "```python\ndef test():\n    pass\n```"
        result = self.converter.convert(markdown)

        # Check Confluence code macro structure
        assert '<ac:structured-macro ac:name="code"' in result
        assert 'ac:parameter ac:name="language">python' in result
        assert "<![CDATA[def test():\n    pass]]>" in result

    def test_tables_content_preservation(self) -> None:
        """Test that table content is preserved (even if not proper HTML tables)."""
        markdown = "| Header | Value |\n|--------|-------|\n| Test | 123 |"
        result = self.converter.convert(markdown)

        # Ensure content is preserved
        assert "Header" in result
        assert "Value" in result
        assert "Test" in result
        assert "123" in result

    def test_mixed_content_integration(self) -> None:
        """Test conversion of mixed content with multiple element types."""
        markdown = """# Integration Test

## Code Example

```python
print("hello")
```

## List Items

- Item 1 with **bold**
- Item 2 with `code`

### Summary

This tests multiple elements together."""

        result = self.converter.convert(markdown)

        # Check all elements are present
        assert "<h1>Integration Test</h1>" in result
        assert "<h2>Code Example</h2>" in result
        assert "<h3>Summary</h3>" in result
        assert '<ac:structured-macro ac:name="code"' in result
        assert 'language">python' in result
        assert "<li>" in result
        assert "<strong>bold</strong>" in result
        assert "<code>code</code>" in result

    def test_overall_corpus_fidelity(self) -> None:
        """Test overall fidelity across entire golden corpus meets 95% requirement."""
        total_fidelity = 0.0
        test_count = 0

        for test_case in self.TEST_CASES:
            try:
                input_content, expected_content = self._load_test_case(test_case)
                actual_content = self.converter.convert(input_content)
                fidelity = self._calculate_fidelity(actual_content, expected_content)
                total_fidelity += fidelity
                test_count += 1
            except FileNotFoundError:
                # Skip missing test files
                continue

        # Ensure we actually executed test cases
        assert (
            test_count > 0
        ), "No valid test cases were executed. Check that golden corpus files exist."

        average_fidelity = total_fidelity / test_count
        assert (
            average_fidelity >= 95.0
        ), f"Overall corpus fidelity is {average_fidelity:.1f}%, below required 95% threshold"


if __name__ == "__main__":
    # Quick validation
    print("Conversion fidelity test suite loaded successfully")
    print("Run with: poetry run pytest tests/test_conversion_fidelity.py -v")
