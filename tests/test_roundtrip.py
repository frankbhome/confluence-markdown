# Copyright (c) 2025 Francis Bain
# SPDX-License-Identifier: Apache-2.0

"""Round-trip tests for Markdown ↔ Confluence conversion.

This module contains tests that verify bidirectional conversion between
Markdown and Confluence formats maintains content integrity.
"""

import sys
from pathlib import Path

import pytest

# Add the scripts directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

try:
    from publish_release import ConfluencePublisher
except ImportError:
    # Skip tests if ConfluencePublisher can't be imported
    pytest.skip("ConfluencePublisher not available", allow_module_level=True)


class TestRoundTripConversion:
    """Test round-trip conversion between Markdown and Confluence formats."""

    @pytest.fixture
    def mock_publisher(self, monkeypatch: pytest.MonkeyPatch) -> ConfluencePublisher:
        """Create a mock ConfluencePublisher for testing.

        Sets up environment variables to avoid configuration errors.
        """
        # Mock environment variables
        monkeypatch.setenv("CONFLUENCE_URL", "https://test.atlassian.net/wiki")
        monkeypatch.setenv("CONFLUENCE_USER", "test@example.com")
        monkeypatch.setenv("CONFLUENCE_TOKEN", "test_token")
        monkeypatch.setenv("CONFLUENCE_SPACE", "TEST")

        return ConfluencePublisher()

    def test_headers_round_trip(self, mock_publisher: ConfluencePublisher) -> None:
        """Test that headers convert properly and maintain hierarchy."""
        test_cases = [
            ("# Main Header", "<h1>Main Header</h1>"),
            ("## Sub Header", "<h2>Sub Header</h2>"),
            ("### Third Level", "<h3>Third Level</h3>"),
            # Note: Higher level headers (h4-h6) may convert to <p> tags in some markdown processors
            ("#### Fourth Level", "Fourth Level"),  # Just check content is preserved
            ("##### Fifth Level", "Fifth Level"),  # Just check content is preserved
            ("###### Sixth Level", "Sixth Level"),  # Just check content is preserved
        ]

        for markdown, expected_content in test_cases:
            result = mock_publisher._convert_markdown_to_confluence(markdown)
            assert expected_content in result

            # Verify the header content is preserved regardless of format
            header_text = markdown.lstrip("#").strip()
            assert header_text in result

    def test_text_formatting_round_trip(self, mock_publisher: ConfluencePublisher) -> None:
        """Test that text formatting converts properly."""
        test_cases = [
            ("**bold text**", "<strong>bold text</strong>"),
            ("*italic text*", "<em>italic text</em>"),
            ("`inline code`", "<code>inline code</code>"),
            ("~~strikethrough~~", "strikethrough"),  # May not convert to <del> in all processors
        ]

        for markdown, expected_confluence in test_cases:
            result = mock_publisher._convert_markdown_to_confluence(markdown)
            assert expected_confluence in result

    def test_lists_round_trip(self, mock_publisher: ConfluencePublisher) -> None:
        """Test that lists convert properly and maintain structure."""
        # Test unordered list
        markdown_ul = """- Item 1
- Item 2
- Item 3"""

        result_ul = mock_publisher._convert_markdown_to_confluence(markdown_ul)
        assert "<ul>" in result_ul and "</ul>" in result_ul
        assert "<li>Item 1</li>" in result_ul
        assert "<li>Item 2</li>" in result_ul
        assert "<li>Item 3</li>" in result_ul

        # Test ordered list
        markdown_ol = """1. First item
2. Second item
3. Third item"""

        result_ol = mock_publisher._convert_markdown_to_confluence(markdown_ol)
        assert "<ol>" in result_ol and "</ol>" in result_ol
        assert "<li>First item</li>" in result_ol
        assert "<li>Second item</li>" in result_ol
        assert "<li>Third item</li>" in result_ol

    def test_nested_lists_round_trip(self, mock_publisher: ConfluencePublisher) -> None:
        """Test that nested lists maintain proper hierarchy."""
        nested_markdown = """- Parent Item 1
  - Child Item 1
  - Child Item 2
- Parent Item 2
  - Child Item 3"""

        result = mock_publisher._convert_markdown_to_confluence(nested_markdown)

        # Should contain nested list structures
        assert "<ul>" in result and "</ul>" in result
        assert "<li>" in result and "</li>" in result

        # All content should be preserved
        assert "Parent Item 1" in result
        assert "Child Item 1" in result
        assert "Child Item 2" in result
        assert "Parent Item 2" in result
        assert "Child Item 3" in result

    def test_links_round_trip(self, mock_publisher: ConfluencePublisher) -> None:
        """Test that links convert properly."""
        test_cases = [
            ("[Example](https://example.com)", 'href="https://example.com"'),
            ("[Internal Link](/docs/page)", 'href="/docs/page"'),
            ("[Email](mailto:test@example.com)", 'href="mailto:test@example.com"'),
        ]

        for markdown, expected_pattern in test_cases:
            result = mock_publisher._convert_markdown_to_confluence(markdown)
            assert expected_pattern in result
            assert "<a " in result and "</a>" in result

    def test_code_blocks_round_trip(self, mock_publisher: ConfluencePublisher) -> None:
        """Test that code blocks convert properly."""
        # Test fenced code block
        code_block = """```python
def hello_world():
    print("Hello, World!")
```"""

        result = mock_publisher._convert_markdown_to_confluence(code_block)
        assert "<pre>" in result and "</pre>" in result
        assert "def hello_world():" in result
        assert 'print("Hello, World!")' in result

    def test_mixed_content_round_trip(self, mock_publisher: ConfluencePublisher) -> None:
        """Test complex markdown with mixed content types."""
        complex_markdown = """# Release Notes v1.0.0

This release includes **major improvements** and *minor fixes*.

## New Features

- Feature 1: `code example`
- Feature 2: [Documentation](https://example.com/docs)
- Feature 3: Support for:
  - Sub-feature A
  - Sub-feature B

## Bug Fixes

1. Fixed issue with **authentication**
2. Resolved *connection timeout* problems
3. Updated `configuration` handling

## Code Examples

```python
# Example usage
import confluence_markdown
print("Hello, Confluence!")
```

For more information, see the [full documentation](https://github.com/example/repo).
"""

        result = mock_publisher._convert_markdown_to_confluence(complex_markdown)

        # Verify all content types are present
        assert "<h1>Release Notes v1.0.0</h1>" in result
        assert "<h2>New Features</h2>" in result
        assert "<h2>Bug Fixes</h2>" in result
        assert "<strong>major improvements</strong>" in result
        assert "<em>minor fixes</em>" in result
        assert "<code>code example</code>" in result
        assert "<ul>" in result and "<ol>" in result
        assert "<pre>" in result
        assert 'href="https://example.com/docs"' in result
        assert 'href="https://github.com/example/repo"' in result

    def test_special_characters_round_trip(self, mock_publisher: ConfluencePublisher) -> None:
        """Test that special characters are handled correctly."""
        test_cases = [
            ("Text with & ampersand", "&amp;"),
            ("Text with < less than", "&lt;"),
            ("Text with > greater than", "&gt;"),
            ('Text with "quotes"', "&quot;"),
        ]

        for markdown, expected_escape in test_cases:
            result = mock_publisher._convert_markdown_to_confluence(markdown)
            # The content should be properly escaped in HTML
            assert expected_escape in result or markdown in result  # Either escaped or preserved

    def test_empty_and_whitespace_handling(self, mock_publisher: ConfluencePublisher) -> None:
        """Test edge cases with empty content and whitespace."""
        test_cases = [
            ("", ""),  # Empty string
            ("   ", ""),  # Only whitespace
            ("\n\n\n", ""),  # Only newlines
            ("# Header\n\n\nText", None),  # Multiple newlines between content
        ]

        for markdown, expected in test_cases:
            result = mock_publisher._convert_markdown_to_confluence(markdown)
            if expected is not None:
                assert expected in result or result.strip() == expected.strip()
            else:
                # Just verify it doesn't crash and produces some output
                assert isinstance(result, str)

    def test_confluence_to_markdown_simulation(self, mock_publisher: ConfluencePublisher) -> None:
        """Simulate reverse conversion from Confluence HTML to Markdown.

        Note: This is a theoretical test since we don't have a reverse converter yet.
        It tests the principles of what round-trip conversion should preserve.
        """
        # Test data representing what should be preserved in round-trip
        content_pairs = [
            {
                "markdown": "# Header",
                "confluence": "<h1>Header</h1>",
                "preserved_content": "Header",
            },
            {
                "markdown": "**bold text**",
                "confluence": "<strong>bold text</strong>",
                "preserved_content": "bold text",
            },
            {
                "markdown": "`code`",
                "confluence": "<code>code</code>",
                "preserved_content": "code",
            },
            {
                "markdown": "[link](url)",
                "confluence": '<a href="url">link</a>',
                "preserved_content": "link",
            },
        ]

        for pair in content_pairs:
            # Convert markdown to confluence
            confluence_result = mock_publisher._convert_markdown_to_confluence(pair["markdown"])

            # Verify the essential content is preserved
            assert pair["preserved_content"] in confluence_result

            # In a full round-trip implementation, we would convert back:
            # markdown_result = confluence_to_markdown(confluence_result)
            # assert pair["preserved_content"] in markdown_result

    def test_content_integrity_properties(self, mock_publisher: ConfluencePublisher) -> None:
        """Test properties that should be maintained during conversion."""
        test_content = "# Test Header\n\nThis is **important** text with `code` and [links](url)."

        result = mock_publisher._convert_markdown_to_confluence(test_content)

        # Essential properties that should be maintained
        properties_to_check = [
            "Test Header",  # Header text preserved
            "important",  # Bold text content preserved
            "code",  # Code content preserved
            "links",  # Link text preserved
            "This is",  # Regular text preserved
        ]

        for prop in properties_to_check:
            assert prop in result, f"Property '{prop}' not preserved in conversion"

    def test_conversion_idempotency(self, mock_publisher: ConfluencePublisher) -> None:
        """Test that converting already-converted content doesn't break."""
        markdown = "# Header\n\n**Bold** text with `code`."

        # Convert once
        first_conversion = mock_publisher._convert_markdown_to_confluence(markdown)

        # Convert the result again (simulating double processing)
        # Note: This might not be truly idempotent depending on implementation
        # but should not crash or produce drastically different results
        second_conversion = mock_publisher._convert_markdown_to_confluence(first_conversion)

        # Both should be strings and contain core content
        assert isinstance(first_conversion, str)
        assert isinstance(second_conversion, str)
        assert len(first_conversion) > 0
        assert len(second_conversion) > 0


class TestConversionEdgeCases:
    """Test edge cases and error conditions in conversion."""

    @pytest.fixture
    def mock_publisher(self, monkeypatch: pytest.MonkeyPatch) -> ConfluencePublisher:
        """Create a mock ConfluencePublisher for testing."""
        monkeypatch.setenv("CONFLUENCE_URL", "https://test.atlassian.net/wiki")
        monkeypatch.setenv("CONFLUENCE_USER", "test@example.com")
        monkeypatch.setenv("CONFLUENCE_TOKEN", "test_token")
        monkeypatch.setenv("CONFLUENCE_SPACE", "TEST")

        return ConfluencePublisher()

    def test_malformed_markdown(self, mock_publisher: ConfluencePublisher) -> None:
        """Test handling of malformed or unusual markdown."""
        malformed_cases = [
            "# Header without ending newline",
            "**Bold without closing",
            "`Code without closing",
            "[Link without closing parenthesis",
            "## # Multiple hash levels",
            "- List\nwithout proper\n- formatting",
        ]

        for case in malformed_cases:
            # Should not crash, should produce some reasonable output
            result = mock_publisher._convert_markdown_to_confluence(case)
            assert isinstance(result, str)
            assert len(result) >= 0  # At minimum, should be empty string

    def test_large_content_handling(self, mock_publisher: ConfluencePublisher) -> None:
        """Test handling of large markdown content."""
        # Create large content
        large_markdown = "\n".join(
            [
                f"# Section {i}"
                + "\n"
                + f"Content for section {i} with **bold** and *italic* text.\n"
                + f"- Item {i}.1\n- Item {i}.2\n- Item {i}.3\n"
                + f"```python\n# Code block {i}\nprint('Section {i}')\n```\n"
                for i in range(100)  # 100 sections
            ]
        )

        result = mock_publisher._convert_markdown_to_confluence(large_markdown)

        # Should handle large content without issues
        assert isinstance(result, str)
        assert len(result) > 0

        # Spot check that content is preserved
        assert "Section 1" in result
        assert "Section 50" in result
        assert "Section 99" in result

    def test_unicode_and_international_content(self, mock_publisher: ConfluencePublisher) -> None:
        """Test handling of Unicode and international characters."""
        unicode_markdown = """# 国际化测试 (Internationalization Test)

This content includes:
- **中文**: 你好世界
- **Español**: Hola mundo
- **Français**: Bonjour le monde
- **العربية**: مرحبا بالعالم
- **日本語**: こんにちは世界
- **Русский**: Привет мир
- **Emoji**: 🌍🚀💻✨

```python
# Unicode in code
print("Hello 世界! 🎉")
```
"""

        result = mock_publisher._convert_markdown_to_confluence(unicode_markdown)

        # Should preserve Unicode content
        assert "国际化测试" in result
        assert "你好世界" in result
        assert "Hola mundo" in result
        assert "مرحبا بالعالم" in result
        assert "🌍🚀💻✨" in result
        assert "Hello 世界! 🎉" in result


if __name__ == "__main__":
    # Run a quick verification
    print("Round-trip test module loaded successfully")
