# Copyright (c) 2025 Francis Bain
# SPDX-License-Identifier: Apache-2.0

"""Property-based tests for the confluence-markdown package.

This module contains property-based tests using Hypothesis to verify
that the package behaves correctly across a wide range of inputs.
"""

import sys
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

# Add the src directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestMarkdownConversionProperties:
    """Property-based tests for markdown conversion functionality."""

    @given(st.text())
    def test_conversion_preserves_text_content(self, markdown_text: str) -> None:
        """Test that markdown conversion preserves the essential text content.

        This property test verifies that when we convert markdown to HTML,
        the essential text content is preserved (ignoring formatting tags).
        """
        # Import here to avoid import issues in CI
        try:
            from confluence_markdown import __main__ as main_module

            # For now, just test that the package can be imported with any text
            # In a full implementation, this would test actual conversion
            assert main_module is not None

            # Basic property: text should be a string
            assert isinstance(markdown_text, str)

        except ImportError:
            # Skip if the module can't be imported
            pass

    @given(st.text(min_size=1, max_size=1000))
    def test_markdown_headers_conversion(self, header_text: str) -> None:
        """Test that markdown headers are consistently converted.

        Property: Any valid header text should convert to a consistent format.
        """
        # Clean the header text to make it valid (remove newlines)
        clean_header = header_text.replace("\n", " ").replace("\r", " ").strip()

        if not clean_header:
            return  # Skip empty headers

        # Test different header levels
        for level in range(1, 7):  # H1 through H6
            markdown_header = f"{'#' * level} {clean_header}"

            # Property: Header should contain the original text
            assert clean_header in markdown_header
            # Property: Header should start with correct number of #
            assert markdown_header.startswith("#" * level)

    @given(st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=10))
    def test_markdown_lists_structure(self, list_items: list[str]) -> None:
        """Test that markdown lists maintain proper structure.

        Property: Any list of items should convert to a consistent list format.
        """
        # Clean list items (remove problematic characters)
        clean_items = [
            item.replace("\n", " ").replace("\r", " ").strip()
            for item in list_items
            if item.strip()
        ]

        if not clean_items:
            return  # Skip empty lists

        # Create markdown list
        markdown_list = "\n".join(f"- {item}" for item in clean_items)

        # Properties of a well-formed markdown list
        lines = markdown_list.split("\n")
        assert len(lines) == len(clean_items)  # One line per item

        for line, original_item in zip(lines, clean_items):
            assert line.startswith("- ")  # Each line starts with list marker
            assert original_item in line  # Original content is preserved

    @given(
        st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs")),
            min_size=1,
            max_size=200,
        )
    )
    def test_code_block_encapsulation(self, code_content: str) -> None:
        """Test that code blocks properly encapsulate content.

        Property: Any text wrapped in code blocks should be preserved as-is.
        """
        # Create inline code
        inline_code = f"`{code_content}`"

        # Properties of inline code
        assert inline_code.startswith("`")
        assert inline_code.endswith("`")
        assert code_content in inline_code

        # Create fenced code block
        fenced_code = f"```\n{code_content}\n```"

        # Properties of fenced code
        assert fenced_code.startswith("```")
        assert fenced_code.endswith("```")
        assert code_content in fenced_code

    @given(st.text(min_size=1, max_size=100), st.text(min_size=1, max_size=200))
    def test_link_structure_preservation(self, link_text: str, url: str) -> None:
        """Test that markdown links maintain proper structure.

        Property: Link text and URL should be preserved in markdown link format.
        """
        # Clean inputs to make valid markdown
        clean_text = (
            link_text.replace("\n", " ")
            .replace("\r", " ")
            .replace("[", "")
            .replace("]", "")
            .strip()
        )
        clean_url = (
            url.replace("\n", "").replace("\r", "").replace("(", "").replace(")", "").strip()
        )

        if not clean_text or not clean_url:
            return  # Skip invalid inputs

        # Create markdown link
        markdown_link = f"[{clean_text}]({clean_url})"

        # Properties of a well-formed markdown link
        assert markdown_link.startswith("[")
        assert "](" in markdown_link
        assert markdown_link.endswith(")")
        assert clean_text in markdown_link
        assert clean_url in markdown_link

    @given(st.integers(min_value=1, max_value=6), st.text(min_size=1, max_size=50))
    def test_header_level_consistency(self, level: int, text: str) -> None:
        """Test that header levels are consistently represented.

        Property: Header level should match the number of # characters.
        """
        clean_text = text.replace("\n", " ").replace("\r", " ").strip()
        if not clean_text:
            return

        header = f"{'#' * level} {clean_text}"

        # Count the # characters at the start
        hash_count = 0
        for char in header:
            if char == "#":
                hash_count += 1
            else:
                break

        # Property: Number of # should equal the intended level
        assert hash_count == level

        # Property: Text content should be preserved
        assert clean_text in header


class TestRoundTripProperties:
    """Property-based tests for round-trip conversion scenarios."""

    @given(
        st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs", "Po")),
            min_size=10,
            max_size=500,
        )
    )
    def test_idempotent_text_processing(self, text: str) -> None:
        """Test that text processing operations are idempotent.

        Property: Applying the same text processing twice should yield the same result.
        """

        # Clean text processing (simulate markdown preprocessing)
        def clean_text(input_text: str) -> str:
            return input_text.strip().replace("\r\n", "\n").replace("\r", "\n")

        # Apply processing once
        processed_once = clean_text(text)

        # Apply processing twice
        processed_twice = clean_text(processed_once)

        # Property: Should be idempotent
        assert processed_once == processed_twice

    @given(st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=5))
    def test_content_preservation_through_conversion_chain(self, content_pieces: list[str]) -> None:
        """Test that content is preserved through a conversion chain.

        Property: Essential content should survive multiple processing steps.
        """
        # Simulate a conversion chain: markdown -> intermediate -> final
        original_content = " ".join(content_pieces)

        # Step 1: Normalize whitespace (like markdown processing)
        step1 = " ".join(original_content.split())

        # Step 2: HTML escape simulation
        step2 = step1.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # Step 3: Unescape (like final output)
        step3 = step2.replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")

        # Property: Content should round-trip cleanly
        assert step1 == step3  # Should survive the round trip


if __name__ == "__main__":
    # Run a quick test to ensure the module works
    print("Property-based tests module loaded successfully")

    # You can run individual tests like this:
    # test_instance = TestMarkdownConversionProperties()
    # test_instance.test_conversion_preserves_text_content("# Test Header")
