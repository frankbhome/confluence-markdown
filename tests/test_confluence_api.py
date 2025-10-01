# Copyright (c) 2025 Francis Bain
# SPDX-License-Identifier: Apache-2.0

"""Comprehensive tests for Confluence API adapter implementation (CMD-43)."""

import json
from unittest.mock import patch

import pytest

from confluence_markdown.confluence_api import (
    AuthError,
    ConflictError,
    ConfluenceClient,
    NotFoundError,
    Page,
    PageVersion,
    RateLimitError,
    ServerError,
)


class MockResponse:
    """Mock response object for testing."""

    def __init__(self, status_code=200, json_body=None, text=""):
        self.status_code = status_code
        self._json = json_body or {}
        self.ok = 200 <= status_code < 300
        self.text = text or json.dumps(self._json)

    def json(self):
        return self._json


class TestConfluenceClient:
    """Test suite for ConfluenceClient covering CMD-43 acceptance criteria."""

    def test_client_initialization_with_token(self):
        """Test client initializes correctly with personal access token."""
        client = ConfluenceClient(base_url="https://example.atlassian.net/wiki", token="test_token")
        assert client.base_url == "https://example.atlassian.net/wiki"
        assert "Bearer test_token" in client.session.headers["Authorization"]

    def test_client_initialization_with_email_and_token(self):
        """Test client initializes correctly with email and token (Basic auth)."""
        client = ConfluenceClient(
            base_url="https://example.atlassian.net/wiki",
            email="test@example.com",
            token="test_token",
        )
        # Should use Basic auth when both email and token provided
        auth_header = client.session.headers["Authorization"]
        assert auth_header.startswith("Basic ")

    def test_from_env_loads_configuration(self, monkeypatch):
        """Test from_env classmethod loads configuration from environment variables."""
        monkeypatch.setenv("CMT_CONF_BASE_URL", "https://test.atlassian.net/wiki")
        monkeypatch.setenv("CMT_CONF_EMAIL", "test@example.com")
        monkeypatch.setenv("CMT_CONF_TOKEN", "secret_token")

        client = ConfluenceClient.from_env()
        assert client.base_url == "https://test.atlassian.net/wiki"

    def test_invalid_base_url_raises_error(self):
        """Test that empty base URL raises ValueError."""
        with pytest.raises(ValueError, match="base_url is required"):
            ConfluenceClient(base_url="", token="test")

    @patch("requests.Session.get")
    def test_get_page_by_id_success(self, mock_get):
        """Test successful page retrieval by ID with comprehensive logging."""
        # Arrange
        client = ConfluenceClient(base_url="https://example.atlassian.net/wiki", token="test")
        mock_response = MockResponse(
            200,
            {
                "id": "123456",
                "title": "Test Page",
                "space": {"key": "TEST"},
                "version": {"number": 5},
                "body": {"storage": {"representation": "storage", "value": "<p>Test content</p>"}},
            },
        )
        mock_get.return_value = mock_response

        # Act
        with patch("confluence_markdown.confluence_api.logger") as mock_logger:
            page = client.get_page_by_id("123456")

        # Assert
        assert page.id == "123456"
        assert page.title == "Test Page"
        assert page.space_key == "TEST"
        assert page.version.number == 5
        assert page.body_storage == "<p>Test content</p>"

        # Verify logging calls
        mock_logger.info.assert_called()
        # Check that appropriate log messages were called
        call_args_list = mock_logger.info.call_args_list
        assert len(call_args_list) >= 3  # Should have at least 3 log calls

    @patch("requests.Session.get")
    def test_get_page_not_found(self, mock_get):
        """Test 404 error handling for getPage method."""
        client = ConfluenceClient(base_url="https://example.atlassian.net/wiki", token="test")
        mock_get.return_value = MockResponse(404, {"message": "Page not found"})

        with pytest.raises(NotFoundError) as exc_info:
            client.getPage("nonexistent")

        assert exc_info.value.status == 404

    @patch("requests.Session.post")
    def test_create_page_success(self, mock_post):
        """Test successful page creation with logging."""
        client = ConfluenceClient(base_url="https://example.atlassian.net/wiki", token="test")
        mock_response = MockResponse(
            200,
            {
                "id": "789012",
                "title": "New Test Page",
                "space": {"key": "TEST"},
                "version": {"number": 1},
            },
        )
        mock_post.return_value = mock_response

        with patch("confluence_markdown.confluence_api.logger") as mock_logger:
            page = client.create_page(
                space_key="TEST", title="New Test Page", html_storage="<p>New content</p>"
            )

        assert page.id == "789012"
        assert page.title == "New Test Page"
        assert page.version.number == 1

        # Verify API call was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        payload = json.loads(call_args[1]["data"])
        assert payload["title"] == "New Test Page"
        assert payload["space"]["key"] == "TEST"
        assert payload["body"]["storage"]["value"] == "<p>New content</p>"

        # Verify logging
        mock_logger.info.assert_called()

    @patch("requests.Session.post")
    def test_create_page_conflict_error(self, mock_post):
        """Test 409 conflict error when page already exists."""
        client = ConfluenceClient(base_url="https://example.atlassian.net/wiki", token="test")
        mock_post.return_value = MockResponse(409, {"message": "Page with title already exists"})

        with pytest.raises(ConflictError) as exc_info:
            client.createPage(
                space_key="TEST", title="Existing Page", html_storage="<p>Content</p>"
            )

        assert exc_info.value.status == 409

    @patch("requests.Session.put")
    @patch.object(ConfluenceClient, "get_page_by_id")
    def test_update_page_with_optimistic_locking(self, mock_get_page, mock_put):
        """Test page update with optimistic concurrency control."""
        client = ConfluenceClient(base_url="https://example.atlassian.net/wiki", token="test")

        # Mock current page fetch for version control
        current_page = Page(
            id="123", title="Current Title", space_key="TEST", version=PageVersion(number=3)
        )
        mock_get_page.return_value = current_page

        # Mock successful update
        updated_response = MockResponse(
            200,
            {
                "id": "123",
                "title": "Updated Title",
                "space": {"key": "TEST"},
                "version": {"number": 4},
            },
        )
        mock_put.return_value = updated_response

        with patch("confluence_markdown.confluence_api.logger") as mock_logger:
            result = client.update_page(
                page_id="123", html_storage="<p>Updated content</p>", title="Updated Title"
            )

        assert result.id == "123"
        assert result.title == "Updated Title"
        assert result.version.number == 4

        # Verify version was incremented correctly
        call_args = mock_put.call_args
        payload = json.loads(call_args[1]["data"])
        assert payload["version"]["number"] == 4  # Should be current + 1

        # Verify logging includes version information
        mock_logger.info.assert_called()

    @patch("requests.Session.put")
    @patch.object(ConfluenceClient, "get_page_by_id")
    def test_update_page_version_conflict(self, mock_get_page, mock_put):
        """Test 409 conflict error on version mismatch (optimistic locking failure)."""
        client = ConfluenceClient(base_url="https://example.atlassian.net/wiki", token="test")

        # Mock get_page_by_id call that happens when title is not provided
        mock_get_page.return_value = Page(
            id="123", title="Existing Title", space_key="TEST", version=PageVersion(number=5)
        )

        mock_put.return_value = MockResponse(
            409, {"message": "Version mismatch - page was updated by another user"}
        )

        with pytest.raises(ConflictError) as exc_info:
            client.updatePage(
                page_id="123",
                html_storage="<p>Content</p>",
                expected_version=5,  # Outdated version
            )

        assert exc_info.value.status == 409

    @patch("requests.Session.get")
    def test_authentication_error_handling(self, mock_get):
        """Test 401/403 authentication error handling."""
        client = ConfluenceClient(base_url="https://example.atlassian.net/wiki", token="invalid")
        mock_get.return_value = MockResponse(401, {"message": "Invalid token"})

        with pytest.raises(AuthError) as exc_info:
            client.get_page_by_id("123")

        assert exc_info.value.status == 401

    @patch("requests.Session.get")
    def test_rate_limit_error_handling(self, mock_get):
        """Test 429 rate limit error handling."""
        client = ConfluenceClient(base_url="https://example.atlassian.net/wiki", token="test")
        mock_get.return_value = MockResponse(429, {"message": "Too many requests"})

        with pytest.raises(RateLimitError) as exc_info:
            client.get_page_by_id("123")

        assert exc_info.value.status == 429

    @patch("requests.Session.get")
    def test_server_error_handling(self, mock_get):
        """Test 5xx server error handling."""
        client = ConfluenceClient(base_url="https://example.atlassian.net/wiki", token="test")
        mock_get.return_value = MockResponse(500, {"message": "Internal server error"})

        with pytest.raises(ServerError) as exc_info:
            client.get_page_by_id("123")

        assert exc_info.value.status == 500

    def test_retry_configuration(self):
        """Test that retry logic is properly configured."""
        client = ConfluenceClient(
            base_url="https://example.atlassian.net/wiki",
            token="test",
            max_retries=3,
            backoff_factor=0.5,
        )

        # Check that retry adapter is configured
        adapter = client.session.get_adapter("https://example.atlassian.net")
        assert adapter.max_retries.total == 3
        assert adapter.max_retries.backoff_factor == 0.5
        assert 429 in adapter.max_retries.status_forcelist
        assert 500 in adapter.max_retries.status_forcelist

    def test_cmd43_method_aliases_exist(self):
        """Test that CMD-43 specified method names exist and work."""
        client = ConfluenceClient(base_url="https://example.atlassian.net/wiki", token="test")

        # Verify the CMD-43 acceptance criteria method names exist
        assert hasattr(client, "getPage")
        assert hasattr(client, "createPage")
        assert hasattr(client, "updatePage")

        # Verify they are callable
        assert callable(client.getPage)
        assert callable(client.createPage)
        assert callable(client.updatePage)

    def test_page_from_json_parsing(self):
        """Test page JSON parsing handles various response formats."""
        client = ConfluenceClient(base_url="https://example.atlassian.net/wiki", token="test")

        # Test complete page data
        data = {
            "id": "123456",
            "title": "Test Page",
            "space": {"key": "TEST"},
            "version": {"number": 2},
            "body": {"storage": {"representation": "storage", "value": "<h1>Hello</h1>"}},
        }
        page = client._page_from_json(data)

        assert page.id == "123456"
        assert page.title == "Test Page"
        assert page.space_key == "TEST"
        assert page.version.number == 2
        assert page.body_storage == "<h1>Hello</h1>"

    def test_page_from_json_minimal_data(self):
        """Test page parsing with minimal data (handles missing fields gracefully)."""
        client = ConfluenceClient(base_url="https://example.atlassian.net/wiki", token="test")

        # Test minimal page data
        data = {"id": "123"}
        page = client._page_from_json(data)

        assert page.id == "123"
        assert page.title == ""
        assert page.space_key == ""
        assert page.version.number == 1
        assert page.body_storage is None

    @patch("requests.Session.get")
    def test_get_page_by_title_logging(self, mock_get):
        """Test that get_page_by_title includes proper logging like get_page_by_id."""
        client = ConfluenceClient(base_url="https://example.atlassian.net/wiki", token="test")

        # Test when page is found
        mock_response = MockResponse(
            200,
            {
                "results": [
                    {
                        "id": "789012",
                        "title": "Found Page",
                        "space": {"key": "TEST"},
                        "version": {"number": 3},
                    }
                ]
            },
        )
        mock_get.return_value = mock_response

        with patch("confluence_markdown.confluence_api.logger") as mock_logger:
            result = client.get_page_by_title(space_key="TEST", title="Found Page")

        # Verify page was found
        assert result is not None
        assert result.id == "789012"
        assert result.title == "Found Page"

        # Verify comprehensive logging was called
        mock_logger.info.assert_called()
        call_args_list = mock_logger.info.call_args_list
        assert (
            len(call_args_list) >= 3
        )  # Should have operation start, API completion, and result logs

    @patch("requests.Session.get")
    def test_get_page_by_title_not_found_logging(self, mock_get):
        """Test that get_page_by_title logs when page is not found."""
        client = ConfluenceClient(base_url="https://example.atlassian.net/wiki", token="test")

        # Test when page is not found
        mock_response = MockResponse(200, {"results": []})
        mock_get.return_value = mock_response

        with patch("confluence_markdown.confluence_api.logger") as mock_logger:
            result = client.get_page_by_title(space_key="TEST", title="Missing Page")

        # Verify no page was found
        assert result is None

        # Verify logging was called including "not found" message
        mock_logger.info.assert_called()
        call_args_list = mock_logger.info.call_args_list
        assert (
            len(call_args_list) >= 3
        )  # Should have operation start, API completion, and not found logs
