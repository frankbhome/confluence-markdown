#!/usr/bin/env python3
"""Tests for Confluence Publisher functionality."""

import os
import sys
from unittest.mock import Mock, patch

import pytest

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

        with patch(
            "scripts.publish_release.config",
            side_effect=lambda key, default="": config_values.get(key, default),
        ):
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

        with patch(
            "scripts.publish_release.config",
            side_effect=lambda key, default="": config_values.get(key, default),
        ):
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

        with patch(
            "scripts.publish_release.config",
            side_effect=lambda key, default="": config_values.get(key, default),
        ):
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

        with patch(
            "scripts.publish_release.config",
            side_effect=lambda key, default="": config_values.get(key, default),
        ):
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

        with patch(
            "scripts.publish_release.config",
            side_effect=lambda key, default="": empty_config_values.get(key, default),
        ):
            with pytest.raises(ValueError, match="Missing required Confluence configuration"):
                ConfluencePublisher()

        # Test partial configuration
        partial_config_values = {
            "CONFLUENCE_URL": "https://test.atlassian.net/wiki",
            "CONFLUENCE_USER": "test@example.com",
            # Missing TOKEN and SPACE
        }

        with patch(
            "scripts.publish_release.config",
            side_effect=lambda key, default="": partial_config_values.get(key, default),
        ):
            with pytest.raises(ValueError, match="Missing required Confluence configuration"):
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

        with patch(
            "scripts.publish_release.config",
            side_effect=lambda key, default="": config_values.get(key, default),
        ):
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

        with patch(
            "scripts.publish_release.config",
            side_effect=lambda key, default="": config_values.get(key, default),
        ):
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

        with patch(
            "scripts.publish_release.config",
            side_effect=lambda key, default="": config_values.get(key, default),
        ):
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


class TestParentPageHandling:
    """Test parent page functionality."""

    @patch("scripts.publish_release.requests.Session")
    def test_find_parent_page_id_no_parent_configured(self, mock_session_class: Mock) -> None:
        """Test finding parent page ID when no parent is configured."""
        config_values = {
            "CONFLUENCE_URL": "https://test.atlassian.net/wiki",
            "CONFLUENCE_USER": "test@example.com",
            "CONFLUENCE_TOKEN": "test_token",
            "CONFLUENCE_SPACE": "TEST",
            "CONFLUENCE_PARENT_PAGE": "",  # No parent page configured
        }

        with patch(
            "scripts.publish_release.config",
            side_effect=lambda key, default="": config_values.get(key, default),
        ):
            publisher = ConfluencePublisher()
            result = publisher.find_parent_page_id()

            assert result is None

    @patch("scripts.publish_release.requests.Session")
    def test_find_parent_page_id_no_results(self, mock_session_class: Mock) -> None:
        """Test finding parent page ID when API returns no results."""
        config_values = {
            "CONFLUENCE_URL": "https://test.atlassian.net/wiki",
            "CONFLUENCE_USER": "test@example.com",
            "CONFLUENCE_TOKEN": "test_token",
            "CONFLUENCE_SPACE": "TEST",
            "CONFLUENCE_PARENT_PAGE": "Non-existent Page",
        }

        with patch(
            "scripts.publish_release.config",
            side_effect=lambda key, default="": config_values.get(key, default),
        ):
            publisher = ConfluencePublisher()

            # Mock session and response
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"results": []}  # No results
            mock_session.get.return_value = mock_response

            result = publisher.find_parent_page_id()

            assert result is None


class TestPageCreationAndUpdateFailures:
    """Test error handling in page creation and updates."""

    @patch("scripts.publish_release.requests.Session")
    def test_create_page_failure(self, mock_session_class: Mock) -> None:
        """Test page creation failure handling."""
        config_values = {
            "CONFLUENCE_URL": "https://test.atlassian.net/wiki",
            "CONFLUENCE_USER": "test@example.com",
            "CONFLUENCE_TOKEN": "test_token",
            "CONFLUENCE_SPACE": "TEST",
        }

        with patch(
            "scripts.publish_release.config",
            side_effect=lambda key, default="": config_values.get(key, default),
        ):
            publisher = ConfluencePublisher()

            # Mock session
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # Mock GET request (page doesn't exist)
            mock_get_response = Mock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = {"results": []}
            mock_session.get.return_value = mock_get_response

            # Mock POST request (creation fails)
            mock_post_response = Mock()
            mock_post_response.status_code = 400
            mock_post_response.text = "Bad Request"
            mock_session.post.return_value = mock_post_response

            result = publisher.publish_release_notes("v1.0.0", "Test release notes")

            assert result is False
            assert mock_session.get.called
            assert mock_session.post.called

    @patch("scripts.publish_release.requests.Session")
    def test_update_page_failure(self, mock_session_class: Mock) -> None:
        """Test page update failure handling."""
        config_values = {
            "CONFLUENCE_URL": "https://test.atlassian.net/wiki",
            "CONFLUENCE_USER": "test@example.com",
            "CONFLUENCE_TOKEN": "test_token",
            "CONFLUENCE_SPACE": "TEST",
        }

        with patch(
            "scripts.publish_release.config",
            side_effect=lambda key, default="": config_values.get(key, default),
        ):
            publisher = ConfluencePublisher()

            # Mock session
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # Mock GET request (page exists)
            mock_get_response = Mock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = {
                "results": [{"id": "123", "version": {"number": 1}}]
            }
            mock_session.get.return_value = mock_get_response

            # Mock PUT request (update fails)
            mock_put_response = Mock()
            mock_put_response.status_code = 403
            mock_put_response.text = "Forbidden"
            mock_session.put.return_value = mock_put_response

            result = publisher.publish_release_notes("v1.0.0", "Updated release notes")

            assert result is False
            assert mock_session.get.called
            assert mock_session.put.called

    @patch("scripts.publish_release.requests.Session")
    def test_create_page_with_parent(self, mock_session_class: Mock) -> None:
        """Test page creation with parent page configured."""
        config_values = {
            "CONFLUENCE_URL": "https://test.atlassian.net/wiki",
            "CONFLUENCE_USER": "test@example.com",
            "CONFLUENCE_TOKEN": "test_token",
            "CONFLUENCE_SPACE": "TEST",
            "CONFLUENCE_PARENT_PAGE": "Release Notes",
        }

        with patch(
            "scripts.publish_release.config",
            side_effect=lambda key, default="": config_values.get(key, default),
        ):
            publisher = ConfluencePublisher()

            # Mock session
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # Mock GET requests
            # First call: check if release page exists (it doesn't)
            # Second call: find parent page
            get_responses = [
                Mock(status_code=200, **{"json.return_value": {"results": []}}),  # No release page
                Mock(
                    status_code=200, **{"json.return_value": {"results": [{"id": "parent123"}]}}
                ),  # Parent exists
            ]
            mock_session.get.side_effect = get_responses

            # Mock POST request (creation succeeds)
            mock_post_response = Mock()
            mock_post_response.status_code = 201
            mock_post_response.json.return_value = {"id": "new123"}
            mock_session.post.return_value = mock_post_response

            result = publisher.publish_release_notes("v1.0.0", "Test release notes")

            assert result is True
            assert mock_session.get.call_count == 2  # Check page exists + find parent
            assert mock_session.post.called


class TestMainFunction:
    """Test the main CLI function."""

    def test_main_incorrect_usage(self) -> None:
        """Test main function with incorrect number of arguments."""
        with patch("sys.argv", ["publish_release.py"]):
            with patch("sys.exit") as mock_exit:
                # Make sys.exit raise SystemExit to stop execution
                mock_exit.side_effect = SystemExit(1)
                with patch("builtins.print") as mock_print:
                    from scripts.publish_release import main

                    with pytest.raises(SystemExit):
                        main()
                    mock_exit.assert_called_with(1)
                    mock_print.assert_any_call(
                        "Usage: publish_release.py <version> <release_notes>"
                    )

    def test_main_correct_usage_success(self) -> None:
        """Test main function with correct arguments and successful publishing."""
        test_args = ["publish_release.py", "v1.0.0", "Test release notes"]

        with patch("sys.argv", test_args):
            with patch("sys.exit") as mock_exit:
                mock_exit.side_effect = SystemExit(0)
                with patch("scripts.publish_release.ConfluencePublisher") as mock_publisher_class:
                    mock_publisher = Mock()
                    mock_publisher.publish_release_notes.return_value = True
                    mock_publisher_class.return_value = mock_publisher

                    from scripts.publish_release import main

                    with pytest.raises(SystemExit):
                        main()

                    mock_publisher.publish_release_notes.assert_called_with(
                        "v1.0.0", "Test release notes"
                    )
                    mock_exit.assert_called_with(0)

    def test_main_correct_usage_failure(self) -> None:
        """Test main function with correct arguments but publishing failure."""
        test_args = ["publish_release.py", "v1.0.0", "Test release notes"]

        with patch("sys.argv", test_args):
            with patch("sys.exit") as mock_exit:
                mock_exit.side_effect = SystemExit(1)
                with patch("scripts.publish_release.ConfluencePublisher") as mock_publisher_class:
                    mock_publisher = Mock()
                    mock_publisher.publish_release_notes.return_value = False
                    mock_publisher_class.return_value = mock_publisher

                    from scripts.publish_release import main

                    with pytest.raises(SystemExit):
                        main()

                    mock_publisher.publish_release_notes.assert_called_with(
                        "v1.0.0", "Test release notes"
                    )
                    mock_exit.assert_called_with(1)

    def test_main_configuration_error(self) -> None:
        """Test main function with configuration error."""
        test_args = ["publish_release.py", "v1.0.0", "Test release notes"]

        with patch("sys.argv", test_args):
            with patch("sys.exit") as mock_exit:
                mock_exit.side_effect = SystemExit(1)
                with patch("scripts.publish_release.ConfluencePublisher") as mock_publisher_class:
                    mock_publisher_class.side_effect = ValueError("Missing configuration")

                    from scripts.publish_release import main

                    with pytest.raises(SystemExit):
                        main()

                    mock_exit.assert_called_with(1)

    def test_main_unexpected_error(self) -> None:
        """Test main function with unexpected error."""
        test_args = ["publish_release.py", "v1.0.0", "Test release notes"]

        with patch("sys.argv", test_args):
            with patch("sys.exit") as mock_exit:
                mock_exit.side_effect = SystemExit(1)
                with patch("scripts.publish_release.ConfluencePublisher") as mock_publisher_class:
                    mock_publisher_class.side_effect = RuntimeError("Unexpected error")

                    from scripts.publish_release import main

                    with pytest.raises(SystemExit):
                        main()

                    mock_exit.assert_called_with(1)


class TestModuleExecution:
    """Test module execution."""

    def test_name_main_execution(self) -> None:
        """Test that the module can be executed directly."""
        import os
        import subprocess
        import sys

        # Get the path to the script
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "scripts",
            "publish_release.py",
        )

        # Run the script with no arguments to trigger usage message
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)

        # Should exit with code 1 due to incorrect usage
        assert result.returncode == 1
        assert "Usage:" in result.stdout
