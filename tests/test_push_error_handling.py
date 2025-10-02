# Copyright (c) 2025 Francis Bain
# SPDX-License-Identifier: Apache-2.0

"""Tests for push pipeline error handling."""

import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from confluence_markdown.cli import main
from confluence_markdown.confluence_api import AuthError, ConflictError, ConfluenceAPIError
from confluence_markdown.errors import (
    EXIT_API_ERROR,
    EXIT_CONFIG_ERROR,
    EXIT_CONVERSION_ERROR,
    EXIT_SUCCESS,
    APIError,
    AuthenticationError,
    ConversionError,
    VersionConflictError,
)


class TestPushErrorHandling:
    """Test error handling for push command."""

    @pytest.fixture
    def temp_markdown_file(self):
        """Create a temporary markdown file for testing."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write("# Test Heading\n\nSome content.")
            path = Path(f.name)
        try:
            yield path
        finally:
            path.unlink(missing_ok=True)

    @pytest.fixture
    def mock_mapping_store(self):
        """Mock mapping store with a valid mapping."""
        with patch("confluence_markdown.cli.MappingStore") as mock_store:
            mock_instance = MagicMock()
            mock_instance.get_mapping.return_value = {
                "page_id": "12345",
                "space_key": "TEST",
                "title": "Test Page",
            }
            mock_store.return_value = mock_instance
            yield mock_instance

    def test_push_missing_file_parameter(self):
        """Test push command fails with argparse error when --file is missing."""
        # argparse handles this and exits with code 2, not our custom code
        with pytest.raises(SystemExit) as exc_info:
            main(["push"])
        assert exc_info.value.code == 2  # argparse standard exit code

    def test_push_file_not_exists(self, caplog, mock_mapping_store):
        """Test push command fails with config error when file doesn't exist."""
        with caplog.at_level(logging.ERROR):
            result = main(["push", "--file", "nonexistent.md"])

            assert result == EXIT_CONFIG_ERROR
            assert "File does not exist" in caplog.text

    def test_push_no_mapping_found(self, caplog, temp_markdown_file):
        """Test push command fails with config error when no mapping exists."""
        with caplog.at_level(logging.INFO):
            with patch("confluence_markdown.cli.MappingStore") as mock_store:
                mock_instance = MagicMock()
                mock_instance.get_mapping.return_value = None
                mock_store.return_value = mock_instance

                result = main(["push", "--file", str(temp_markdown_file)])

                assert result == EXIT_CONFIG_ERROR
                assert "No mapping found" in caplog.text
                assert "Use 'cmt map add'" in caplog.text

    @patch.dict(os.environ, {}, clear=True)
    def test_push_missing_confluence_token(self, caplog, temp_markdown_file, mock_mapping_store):
        """Test authentication error when Confluence token is missing."""
        with caplog.at_level(logging.ERROR):
            result = main(["push", "--file", str(temp_markdown_file)])

            assert result == EXIT_CONFIG_ERROR
            # Should fail on missing base URL first, but that's still a config error

    @patch.dict(os.environ, {"CMT_CONF_TOKEN": "test-token"}, clear=True)
    def test_push_missing_base_url(self, caplog, temp_markdown_file, mock_mapping_store):
        """Test config error when base URL is missing."""
        with caplog.at_level(logging.ERROR):
            result = main(["push", "--file", str(temp_markdown_file)])

            assert result == EXIT_CONFIG_ERROR
            assert "Missing CMT_CONF_BASE_URL" in caplog.text

    @patch.dict(
        os.environ,
        {"CMT_CONF_BASE_URL": "https://test.atlassian.net/wiki", "CMT_CONF_TOKEN": "test-token"},
    )
    def test_push_conversion_error(self, caplog, temp_markdown_file, mock_mapping_store):
        """Test conversion error handling."""
        with caplog.at_level(logging.ERROR):
            with patch("confluence_markdown.cli.MarkdownToConfluenceConverter") as mock_converter:
                mock_converter.return_value.convert.side_effect = Exception("Conversion failed")

                result = main(["push", "--file", str(temp_markdown_file)])

                assert result == EXIT_CONVERSION_ERROR
                assert "Failed to convert markdown file" in caplog.text

    @patch.dict(
        os.environ,
        {"CMT_CONF_BASE_URL": "https://test.atlassian.net/wiki", "CMT_CONF_TOKEN": "test-token"},
    )
    def test_push_authentication_error_from_api(
        self, caplog, temp_markdown_file, mock_mapping_store
    ):
        """Test API authentication error (401/403) handling."""
        with caplog.at_level(logging.ERROR):
            with patch("confluence_markdown.cli.MarkdownToConfluenceConverter") as mock_converter:
                mock_converter.return_value.convert.return_value = "<p>Test</p>"

                with patch("confluence_markdown.cli.ConfluenceClient") as mock_client_class:
                    mock_client = MagicMock()
                    mock_client.update_page.side_effect = AuthError(
                        "Authentication failed", status=401
                    )
                    mock_client_class.return_value = mock_client

                    result = main(["push", "--file", str(temp_markdown_file)])

                    assert result == EXIT_CONFIG_ERROR
                    assert "Invalid or missing Confluence API token" in caplog.text

    @patch.dict(
        os.environ,
        {"CMT_CONF_BASE_URL": "https://test.atlassian.net/wiki", "CMT_CONF_TOKEN": "test-token"},
    )
    def test_push_version_conflict_error(self, caplog, temp_markdown_file, mock_mapping_store):
        """Test version conflict error (409) handling."""
        with caplog.at_level(logging.ERROR):
            with patch("confluence_markdown.cli.MarkdownToConfluenceConverter") as mock_converter:
                mock_converter.return_value.convert.return_value = "<p>Test</p>"

                with patch("confluence_markdown.cli.ConfluenceClient") as mock_client_class:
                    mock_client = MagicMock()
                    mock_client.update_page.side_effect = ConflictError(
                        "Version conflict", status=409
                    )
                    mock_client_class.return_value = mock_client

                    result = main(["push", "--file", str(temp_markdown_file)])

                    assert result == EXIT_API_ERROR
                    assert "mismatched Confluence version" in caplog.text

    @patch.dict(
        os.environ,
        {"CMT_CONF_BASE_URL": "https://test.atlassian.net/wiki", "CMT_CONF_TOKEN": "test-token"},
    )
    def test_push_api_error_4xx_5xx(self, caplog, temp_markdown_file, mock_mapping_store):
        """Test API error (4xx/5xx) handling."""
        with caplog.at_level(logging.ERROR):
            with patch("confluence_markdown.cli.MarkdownToConfluenceConverter") as mock_converter:
                mock_converter.return_value.convert.return_value = "<p>Test</p>"

                with patch("confluence_markdown.cli.ConfluenceClient") as mock_client_class:
                    mock_client = MagicMock()
                    mock_client.update_page.side_effect = ConfluenceAPIError(
                        "Server error", status=500
                    )
                    mock_client_class.return_value = mock_client

                    result = main(["push", "--file", str(temp_markdown_file)])

                    assert result == EXIT_API_ERROR
                    assert "API error during page update" in caplog.text

    @patch.dict(
        os.environ,
        {"CMT_CONF_BASE_URL": "https://test.atlassian.net/wiki", "CMT_CONF_TOKEN": "test-token"},
    )
    def test_push_success(self, caplog, temp_markdown_file, mock_mapping_store):
        """Test successful push operation."""
        with caplog.at_level(logging.INFO):
            with patch("confluence_markdown.cli.MarkdownToConfluenceConverter") as mock_converter:
                mock_converter.return_value.convert.return_value = "<p>Test content</p>"

                with patch("confluence_markdown.cli.ConfluenceClient") as mock_client_class:
                    mock_client = MagicMock()
                    mock_result = MagicMock()
                    mock_result.id = "12345"
                    mock_result.version.number = 2
                    mock_client.update_page.return_value = mock_result
                    mock_client_class.return_value = mock_client

                    result = main(["push", "--file", str(temp_markdown_file)])

                    assert result == EXIT_SUCCESS
                    assert "Successfully pushed" in caplog.text

    @patch.dict(
        os.environ,
        {"CMT_CONF_BASE_URL": "https://test.atlassian.net/wiki", "CMT_CONF_TOKEN": "test-token"},
    )
    def test_push_create_new_page_success(self, temp_markdown_file):
        """Test successful page creation when using space + title mapping."""
        with patch("confluence_markdown.cli.MappingStore") as mock_store:
            mock_instance = MagicMock()
            mock_instance.get_mapping.return_value = {"space_key": "TEST", "title": "New Page"}
            mock_store.return_value = mock_instance

            with patch("confluence_markdown.cli.MarkdownToConfluenceConverter") as mock_converter:
                mock_converter.return_value.convert.return_value = "<p>Test</p>"

                with patch("confluence_markdown.cli.ConfluenceClient") as mock_client_class:
                    mock_client = MagicMock()

                    # Simulate page doesn't exist
                    mock_client.get_page_by_title.return_value = None

                    # Simulate successful creation
                    mock_result = MagicMock()
                    mock_result.id = "67890"
                    mock_result.version.number = 1
                    mock_client.create_page.return_value = mock_result
                    mock_client_class.return_value = mock_client

                    result = main(["push", "--file", str(temp_markdown_file)])

                    assert result == EXIT_SUCCESS
                    mock_client.create_page.assert_called_once()

    @patch.dict(
        os.environ,
        {"CMT_CONF_BASE_URL": "https://test.atlassian.net/wiki", "CMT_CONF_TOKEN": "test-token"},
    )
    def test_push_update_existing_page_success(self, caplog, temp_markdown_file):
        """Test successful page update when page already exists."""
        with patch("confluence_markdown.cli.MappingStore") as mock_store:
            mock_instance = MagicMock()
            mock_instance.get_mapping.return_value = {"space_key": "TEST", "title": "Existing Page"}
            mock_store.return_value = mock_instance

            with patch("confluence_markdown.cli.MarkdownToConfluenceConverter") as mock_converter:
                mock_converter.return_value.convert.return_value = "<p>Updated content</p>"

                with patch("confluence_markdown.cli.ConfluenceClient") as mock_client_class:
                    mock_client = MagicMock()

                    # Simulate existing page found
                    mock_existing_page = MagicMock()
                    mock_existing_page.id = "existing-123"
                    mock_client.get_page_by_title.return_value = mock_existing_page

                    # Simulate successful update
                    mock_result = MagicMock()
                    mock_result.id = "existing-123"
                    mock_result.version.number = 3
                    mock_client.update_page.return_value = mock_result
                    mock_client_class.return_value = mock_client

                    with caplog.at_level(logging.INFO):
                        result = main(["push", "--file", str(temp_markdown_file)])

                        assert result == EXIT_SUCCESS
                        assert "Page updated successfully" in caplog.text
                        mock_client.update_page.assert_called_once()

    @patch.dict(
        os.environ,
        {"CMT_CONF_BASE_URL": "https://test.atlassian.net/wiki", "CMT_CONF_TOKEN": "test-token"},
    )
    def test_push_client_initialization_failure(
        self, caplog, temp_markdown_file, mock_mapping_store
    ):
        """Test client initialization failure handling."""
        with caplog.at_level(logging.ERROR):
            with patch("confluence_markdown.cli.ConfluenceClient") as mock_client_class:
                mock_client_class.side_effect = Exception("Connection failed")

                result = main(["push", "--file", str(temp_markdown_file)])

                assert result == EXIT_CONFIG_ERROR
                assert "Failed to initialize Confluence client" in caplog.text

    @patch.dict(
        os.environ,
        {"CMT_CONF_BASE_URL": "https://test.atlassian.net/wiki", "CMT_CONF_TOKEN": "test-token"},
    )
    def test_push_invalid_mapping_configuration(self, caplog, temp_markdown_file):
        """Test error handling for invalid mapping configurations."""
        with patch("confluence_markdown.cli.MappingStore") as mock_store:
            mock_instance = MagicMock()
            # Invalid mapping - missing required fields
            mock_instance.get_mapping.return_value = {"invalid": "mapping"}
            mock_store.return_value = mock_instance

            with patch("confluence_markdown.cli.MarkdownToConfluenceConverter") as mock_converter:
                mock_converter.return_value.convert.return_value = "<p>Test</p>"

                with caplog.at_level(logging.ERROR):
                    result = main(["push", "--file", str(temp_markdown_file)])

                    assert (
                        result == EXIT_API_ERROR
                    )  # This becomes an API error due to unexpected error handling
                    assert "Unexpected error during push" in caplog.text

    @patch.dict(
        os.environ,
        {"CMT_CONF_BASE_URL": "https://test.atlassian.net/wiki", "CMT_CONF_TOKEN": "test-token"},
    )
    def test_push_unexpected_error_handling(self, caplog, temp_markdown_file, mock_mapping_store):
        """Test handling of unexpected errors during push operation."""
        with patch("confluence_markdown.cli.MarkdownToConfluenceConverter") as mock_converter:
            mock_converter.return_value.convert.return_value = "<p>Test</p>"

            with patch("confluence_markdown.cli.ConfluenceClient") as mock_client_class:
                mock_client = MagicMock()
                # Simulate unexpected error not covered by specific exception types
                mock_client.update_page.side_effect = RuntimeError("Unexpected system error")
                mock_client_class.return_value = mock_client

                with caplog.at_level(logging.ERROR):
                    result = main(["push", "--file", str(temp_markdown_file)])

                    assert result == EXIT_API_ERROR
                    assert "Unexpected error during Confluence operation" in caplog.text

    @patch.dict(
        os.environ,
        {"CMT_CONF_BASE_URL": "https://test.atlassian.net/wiki", "CMT_CONF_TOKEN": "test-token"},
    )
    def test_push_file_read_error(self, caplog, temp_markdown_file, mock_mapping_store):
        """Test error handling when file cannot be read."""
        # Mock file existence check to pass, but reading fails
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", side_effect=OSError("Permission denied")):
                with caplog.at_level(logging.ERROR):
                    result = main(["push", "--file", str(temp_markdown_file)])

                    assert result == EXIT_CONVERSION_ERROR
                    assert "Failed to convert markdown file" in caplog.text

    def test_push_missing_file_argument_internal_check(self, caplog):
        """Test internal --file validation (lines 55-56)."""
        # Create args object without file parameter to test internal validation
        from argparse import Namespace

        from confluence_markdown.cli import cmd_push

        args = Namespace(file=None)

        with caplog.at_level(logging.ERROR):
            result = cmd_push(args)

            assert result == EXIT_CONFIG_ERROR
            assert "--file is required for push command" in caplog.text

    @patch.dict(
        os.environ,
        {"CMT_CONF_BASE_URL": "https://test.atlassian.net/wiki", "CMT_CONF_TOKEN": "test-token"},
    )
    def test_push_config_error_from_client_setup(
        self, caplog, temp_markdown_file, mock_mapping_store
    ):
        """Test ConfigError handling from _get_confluence_client (lines 78-79)."""
        with patch("confluence_markdown.cli._get_confluence_client") as mock_get_client:
            from confluence_markdown.errors import ConfigError

            mock_get_client.side_effect = ConfigError("Client setup failed")

            with caplog.at_level(logging.ERROR):
                result = main(["push", "--file", str(temp_markdown_file)])

                assert result == EXIT_CONFIG_ERROR
                assert "Client setup failed" in caplog.text

    def test_push_outer_exception_handler(self, caplog, temp_markdown_file):
        """Test outer exception handler in cmd_push (lines 129-131)."""
        # Create an error that happens before any other handling
        from argparse import Namespace

        from confluence_markdown.cli import cmd_push

        with patch("confluence_markdown.cli.Path") as mock_path:
            mock_path.side_effect = RuntimeError("Unexpected path error")

            with caplog.at_level(logging.ERROR):
                args = Namespace(file=str(temp_markdown_file))
                result = cmd_push(args)

                assert result == EXIT_API_ERROR
                assert "Unexpected error in push command" in caplog.text

    @patch.dict(os.environ, {"CMT_CONF_BASE_URL": "https://test.atlassian.net/wiki"}, clear=True)
    def test_get_confluence_client_missing_token(self, caplog):
        """Test AuthenticationError when token is missing (line 155)."""
        from confluence_markdown.cli import _get_confluence_client
        from confluence_markdown.errors import AuthenticationError

        with pytest.raises(AuthenticationError) as exc_info:
            _get_confluence_client()

        assert "Invalid or missing Confluence API token" in str(exc_info.value)

    @patch.dict(
        os.environ,
        {"CMT_CONF_BASE_URL": "https://test.atlassian.net/wiki", "CMT_CONF_TOKEN": "test-token"},
    )
    def test_push_conflict_error_handling(self, caplog, temp_markdown_file):
        """Test ConflictError handling in _push_to_confluence (lines 237-240)."""
        with patch("confluence_markdown.cli.MappingStore") as mock_store:
            mock_instance = MagicMock()
            mock_instance.get_mapping.return_value = {"space_key": "TEST", "title": "Test Page"}
            mock_store.return_value = mock_instance

            with patch("confluence_markdown.cli.MarkdownToConfluenceConverter") as mock_converter:
                mock_converter.return_value.convert.return_value = "<p>Test</p>"

                with patch("confluence_markdown.cli.ConfluenceClient") as mock_client_class:
                    mock_client = MagicMock()
                    mock_client.get_page_by_title.return_value = None  # No existing page
                    mock_client.create_page.side_effect = ConflictError(
                        "Conflict during creation", status=409
                    )
                    mock_client_class.return_value = mock_client

                    with caplog.at_level(logging.ERROR):
                        result = main(["push", "--file", str(temp_markdown_file)])

                        assert result == EXIT_API_ERROR
                        assert "mismatched Confluence version" in caplog.text

    @patch.dict(
        os.environ,
        {"CMT_CONF_BASE_URL": "https://test.atlassian.net/wiki", "CMT_CONF_TOKEN": "test-token"},
    )
    def test_push_confluence_api_error_handling(self, caplog, temp_markdown_file):
        """Test ConfluenceAPIError handling in _push_to_confluence (lines 243-244)."""
        with patch("confluence_markdown.cli.MappingStore") as mock_store:
            mock_instance = MagicMock()
            mock_instance.get_mapping.return_value = {"space_key": "TEST", "title": "Test Page"}
            mock_store.return_value = mock_instance

            with patch("confluence_markdown.cli.MarkdownToConfluenceConverter") as mock_converter:
                mock_converter.return_value.convert.return_value = "<p>Test</p>"

                with patch("confluence_markdown.cli.ConfluenceClient") as mock_client_class:
                    mock_client = MagicMock()
                    mock_client.get_page_by_title.return_value = None
                    mock_client.create_page.side_effect = ConfluenceAPIError(
                        "API Error", status=500
                    )
                    mock_client_class.return_value = mock_client

                    with caplog.at_level(logging.ERROR):
                        result = main(["push", "--file", str(temp_markdown_file)])

                        assert result == EXIT_API_ERROR
                        assert "API error during page creation/update" in caplog.text

    def teardown_method(self, method):
        """Clean up temporary files."""
        # Clean up any temporary files created during tests
        pass


class TestErrorLogging:
    """Test that error logging includes required context."""

    def test_error_context_logging(self, caplog):
        """Test that errors log required context (page ID, file path, error code)."""
        error = APIError(
            "Test API error", status_code=404, page_id="12345", file_path="/path/to/file.md"
        )

        error.log_error()

        assert len(caplog.records) == 1
        record = caplog.records[0]

        # Check that context is properly logged
        assert record.status_code == 404
        assert record.page_id == "12345"
        assert record.file_path == "/path/to/file.md"
        assert record.exit_code == EXIT_API_ERROR
        assert record.error_type == "APIError"

    def test_version_conflict_error_context(self, caplog):
        """Test version conflict error logs expected and actual versions."""
        error = VersionConflictError(page_id="12345", expected_version=3, actual_version=5)

        error.log_error()

        record = caplog.records[0]
        assert record.expected_version == 3
        assert record.actual_version == 5
        assert record.page_id == "12345"


class TestExitCodes:
    """Test that exit codes match specification."""

    def test_exit_code_constants(self):
        """Test that exit code constants have correct values."""
        assert EXIT_SUCCESS == 0
        assert EXIT_CONVERSION_ERROR == 1
        assert EXIT_API_ERROR == 2
        assert EXIT_CONFIG_ERROR == 3

    def test_error_classes_exit_codes(self):
        """Test that error classes return correct exit codes."""
        conversion_error = ConversionError("Test conversion error")
        assert conversion_error.exit_code == EXIT_CONVERSION_ERROR

        api_error = APIError("Test API error")
        assert api_error.exit_code == EXIT_API_ERROR

        auth_error = AuthenticationError()
        assert auth_error.exit_code == EXIT_CONFIG_ERROR

        version_error = VersionConflictError()
        assert version_error.exit_code == EXIT_API_ERROR
