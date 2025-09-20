#!/usr/bin/env python3
"""Tests for Confluence Publisher functionality."""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.publish_release import ConfluencePublisher


class TestMarkdownConversion:
    """Test markdown to Confluence conversion functionality."""

    def setup_method(self) -> None:
        """
        Prepare a test ConfluencePublisher with required environment variables.

        Patches decouple.config to provide fake Confluence and GitHub settings and
        instantiates self.publisher as a ConfluencePublisher ready for use in the tests.
        """
        config_values = {
            "CONFLUENCE_URL": "https://test.atlassian.net/wiki",
            "CONFLUENCE_USER": "test@example.com",
            "CONFLUENCE_TOKEN": "test_token",
            "CONFLUENCE_SPACE": "TEST",
            "CONFLUENCE_PARENT_PAGE": "Release Notes",
            "GITHUB_REPOSITORY": "test/repo",
        }

        with patch("scripts.publish_release.config", side_effect=lambda key, default="": config_values.get(key, default)):
            self.publisher = ConfluencePublisher()

    def test_convert_headers(self) -> None:
        """Test header conversion."""
        markdown = """# Main Header
## Sub Header
### Sub Sub Header"""

        # Use a public method to test conversion by calling create_confluence_content
        result = self.publisher.create_confluence_content("Test", "v1.0.0", markdown)

        assert "<h1>Main Header</h1>" in result
        assert "<h2>Sub Header</h2>" in result
        assert "<h3>Sub Sub Header</h3>" in result

    def test_convert_fenced_code_blocks(self) -> None:
        """
        Verify that fenced code blocks are converted into Confluence code macros.

        Checks that:
        - A Python fenced block becomes an <ac:structured-macro ac:name="code"> with language "python" and the code wrapped in a CDATA section.
        - A Bash fenced block is converted similarly with language "bash" and its code in CDATA.
        """
        markdown = """Here's some code:

```python
def hello():
    print("Hello, World!")
```

And some bash:

```bash
echo "Hello"
```"""

        result = self.publisher.create_confluence_content("Test", "v1.0.0", markdown)

        # Check for Confluence code macro with Python
        assert '<ac:structured-macro ac:name="code" ac:schema-version="1">' in result
        assert '<ac:parameter ac:name="language">python</ac:parameter>' in result
        assert '<![CDATA[def hello():\n    print("Hello, World!")]]>' in result

        # Check for bash code block
        assert '<ac:parameter ac:name="language">bash</ac:parameter>' in result
        assert '<![CDATA[echo "Hello"]]>' in result

    def test_convert_inline_code(self) -> None:
        """Test inline code conversion."""
        markdown = "Use the `publish_release.py` script to publish."

        result = self.publisher.create_confluence_content("Test", "v1.0.0", markdown)

        assert "<code>publish_release.py</code>" in result

    def test_convert_lists(self) -> None:
        """Test list conversion."""
        markdown = """- First item
- Second item
- Third item"""

        result = self.publisher.create_confluence_content("Test", "v1.0.0", markdown)

        assert "<ul>" in result
        assert "<li>First item</li>" in result
        assert "<li>Second item</li>" in result
        assert "<li>Third item</li>" in result
        assert "</ul>" in result

    def test_convert_bold_and_italic(self) -> None:
        """Test bold and italic conversion."""
        markdown = "This is **bold** and this is *italic* text."

        result = self.publisher.create_confluence_content("Test", "v1.0.0", markdown)

        assert "<strong>bold</strong>" in result
        assert "<em>italic</em>" in result

    def test_convert_links(self) -> None:
        """Test link conversion."""
        markdown = "Check out [GitHub](https://github.com) for more info."

        result = self.publisher.create_confluence_content("Test", "v1.0.0", markdown)

        assert '<a href="https://github.com">GitHub</a>' in result

    def test_convert_complex_markdown(self) -> None:
        """Test complex markdown with multiple elements."""
        markdown = """# Release v1.0.0

## Features Added

- **API Integration**: New `publish_release.py` script
- Support for code blocks:

```python
def publish():
    return True
```

Visit [our docs](https://example.com) for more info.

Use `pip install` to install the package."""

        result = self.publisher.create_confluence_content("Test", "v1.0.0", markdown)

        # Check multiple conversions work together
        assert "<h1>Release v1.0.0</h1>" in result
        assert "<h2>Features Added</h2>" in result
        assert "<strong>API Integration</strong>" in result
        assert "<code>publish_release.py</code>" in result
        assert '<ac:parameter ac:name="language">python</ac:parameter>' in result
        assert '<a href="https://example.com">our docs</a>' in result
        assert "<code>pip install</code>" in result


class TestConfluencePublisher:
    """Test Confluence Publisher main functionality."""

    def test_page_exists_method(self) -> None:
        """Test page_exists method."""
        config_values = {
            "CONFLUENCE_URL": "https://test.atlassian.net/wiki",
            "CONFLUENCE_USER": "test@example.com",
            "CONFLUENCE_TOKEN": "test_token",
            "CONFLUENCE_SPACE": "TEST",
        }

        with patch("scripts.publish_release.config", side_effect=lambda key, default="": config_values.get(key, default)):
            publisher = ConfluencePublisher()

            # Mock the _find_existing_page method
            with patch.object(publisher, "_find_existing_page") as mock_find:
                # Test when page exists
                mock_find.return_value = {"id": "12345"}
                assert publisher.page_exists("v1.0.0") is True

                # Test when page doesn't exist
                mock_find.return_value = None
                assert publisher.page_exists("v1.0.0") is False

                # Verify correct title format
                mock_find.assert_called_with("Release v1.0.0 - confluence-markdown")

    def test_create_confluence_content(self) -> None:
        """Test Confluence content creation."""
        config_values = {
            "CONFLUENCE_URL": "https://test.atlassian.net/wiki",
            "CONFLUENCE_USER": "test@example.com",
            "CONFLUENCE_TOKEN": "test_token",
            "CONFLUENCE_SPACE": "TEST",
            "GITHUB_REPOSITORY": "test/repo",
        }

        with patch("scripts.publish_release.config", side_effect=lambda key, default="": config_values.get(key, default)):
            publisher = ConfluencePublisher()

            title = "Release v1.0.0 - confluence-markdown"
            version = "v1.0.0"
            release_notes = "Initial release with basic features."

            result = publisher.create_confluence_content(title, version, release_notes)

            assert f"<h1>Release {version}</h1>" in result
            assert "https://github.com/test/repo/releases/tag/v1.0.0" in result
            assert "Initial release with basic features." in result
            assert "pip install confluence-markdown==1.0.0" in result

    @patch("scripts.publish_release.requests.Session")
    def test_find_parent_page_id(self, mock_session_class: Mock) -> None:
        """Test finding parent page ID."""
        config_values = {
            "CONFLUENCE_URL": "https://test.atlassian.net/wiki",
            "CONFLUENCE_USER": "test@example.com",
            "CONFLUENCE_TOKEN": "test_token",
            "CONFLUENCE_SPACE": "TEST",
            "CONFLUENCE_PARENT_PAGE": "Release Notes",
        }

        with patch("scripts.publish_release.config", side_effect=lambda key, default="": config_values.get(key, default)):
            publisher = ConfluencePublisher()

            # Mock session and its methods
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # Mock successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"results": [{"id": "parent123"}]}
            mock_session.get.return_value = mock_response

            result = publisher.find_parent_page_id()

            assert result == "parent123"
            assert mock_session.get.called

    def test_configuration_validation(self) -> None:
        """Test configuration validation."""
        # Test missing required configuration
        empty_config_values = {}

        with patch("scripts.publish_release.config", side_effect=lambda key, default="": empty_config_values.get(key, default)):
            with pytest.raises(
                ValueError, match="Missing required Confluence configuration"
            ):
                ConfluencePublisher()

        # Test partial configuration
        partial_config_values = {
            "CONFLUENCE_URL": "https://test.atlassian.net/wiki",
            "CONFLUENCE_USER": "test@example.com",
            # Missing TOKEN and SPACE
        }

        with patch("scripts.publish_release.config", side_effect=lambda key, default="": partial_config_values.get(key, default)):
            with pytest.raises(
                ValueError, match="Missing required Confluence configuration"
            ):
                ConfluencePublisher()


class TestEndToEndPublishing:
    """Test end-to-end publishing scenarios."""

    @patch("scripts.publish_release.requests.Session")
    def test_successful_page_creation(self, mock_session_class: Mock) -> None:
        """Test successful new page creation."""
        config_values = {
            "CONFLUENCE_URL": "https://test.atlassian.net/wiki",
            "CONFLUENCE_USER": "test@example.com",
            "CONFLUENCE_TOKEN": "test_token",
            "CONFLUENCE_SPACE": "TEST",
        }

        with patch("scripts.publish_release.config", side_effect=lambda key, default="": config_values.get(key, default)):
            publisher = ConfluencePublisher()

            # Mock session and its methods
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # Mock responses
            mock_get_response = Mock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = {"results": []}  # Page doesn't exist

            mock_post_response = Mock()
            mock_post_response.status_code = 200
            mock_post_response.json.return_value = {"id": "12345"}

            # Configure session methods
            mock_session.get.return_value = mock_get_response
            mock_session.post.return_value = mock_post_response

            result = publisher.publish_release_notes("v1.0.0", "Test release notes")

            assert result is True
            assert mock_session.get.called
            assert mock_session.post.called

    @patch("scripts.publish_release.requests.Session")
    def test_successful_page_update(self, mock_session_class: Mock) -> None:
        """Test successful page update when page exists."""
        config_values = {
            "CONFLUENCE_URL": "https://test.atlassian.net/wiki",
            "CONFLUENCE_USER": "test@example.com",
            "CONFLUENCE_TOKEN": "test_token",
            "CONFLUENCE_SPACE": "TEST",
        }

        with patch("scripts.publish_release.config", side_effect=lambda key, default="": config_values.get(key, default)):
            publisher = ConfluencePublisher()

            # Mock session and its methods
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # Mock responses for page exists check
            mock_get_response = Mock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = {
                "results": [{"id": "12345", "version": {"number": 1}}]
            }

            # Mock successful page update
            mock_put_response = Mock()
            mock_put_response.status_code = 200
            mock_put_response.json.return_value = {"id": "12345"}

            # Configure session methods
            mock_session.get.return_value = mock_get_response
            mock_session.put.return_value = mock_put_response

            result = publisher.publish_release_notes("v1.0.0", "Updated release notes")

            assert result is True
            assert mock_session.get.called
            assert mock_session.put.called

    @patch("scripts.publish_release.requests.Session")
    def test_failed_authentication(self, mock_session_class: Mock) -> None:
        """Test authentication failure handling."""
        config_values = {
            "CONFLUENCE_URL": "https://test.atlassian.net/wiki",
            "CONFLUENCE_USER": "test@example.com",
            "CONFLUENCE_TOKEN": "invalid_token",
            "CONFLUENCE_SPACE": "TEST",
        }

        with patch("scripts.publish_release.config", side_effect=lambda key, default="": config_values.get(key, default)):
            publisher = ConfluencePublisher()

            # Mock session and its methods
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # Mock 401 Unauthorized response
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"

            mock_session.get.return_value = mock_response

            result = publisher.publish_release_notes("v1.0.0", "Test release notes")

            assert result is False
            assert mock_session.get.called
