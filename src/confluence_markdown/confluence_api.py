# Copyright (c) 2025 Francis Bain
# SPDX-License-Identifier: Apache-2.0

"""Confluence API adapter implementation using atlassian-python-api.

This module provides a stable interface for all Markdown → Confluence push operations.
Encapsulates Confluence operations using the upstream atlassian-python-api library
while maintaining backward compatibility with the existing interface.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from atlassian import Confluence
from requests.exceptions import HTTPError, RequestException

logger = logging.getLogger("confluence_api")
logger.addHandler(logging.NullHandler())


@dataclass
class PageVersion:
    number: int


@dataclass
class Page:
    id: str
    title: str
    space_key: str
    version: PageVersion
    body_storage: str | None = None


class ConfluenceAPIError(Exception):
    def __init__(self, message: str, *, status: int | None = None, payload: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.payload = payload


class AuthError(ConfluenceAPIError): ...


class NotFoundError(ConfluenceAPIError): ...


class ConflictError(ConfluenceAPIError): ...


class RateLimitError(ConfluenceAPIError): ...


class ServerError(ConfluenceAPIError): ...


class ConfluenceClient:
    """Confluence API client using atlassian-python-api library.

    This class maintains the same interface as the previous custom implementation
    but delegates to the upstream atlassian-python-api library for all operations.
    """

    def __init__(
        self,
        base_url: str,
        *,
        email: str | None = None,
        token: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 5,
        backoff_factor: float = 0.3,
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required")

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        # Initialize the atlassian-python-api Confluence client
        if email and token:
            # Basic auth with email and API token
            self.confluence = Confluence(
                url=base_url,
                username=email,
                password=token,
                timeout=timeout,
            )
        elif token:
            # Bearer token auth (less common for Confluence Cloud)
            self.confluence = Confluence(
                url=base_url,
                token=token,
                timeout=timeout,
            )
        else:
            logger.warning(
                "ConfluenceClient initialized without credentials; calls will fail with AuthError"
            )
            self.confluence = Confluence(url=base_url, timeout=timeout)

        # Backward compatibility: expose session for testing
        self.session = self.confluence._session

    @classmethod
    def from_env(cls) -> ConfluenceClient:
        """Create client from environment variables.

        Expected environment variables:
        - CMT_CONF_BASE_URL: Confluence base URL
        - CMT_CONF_EMAIL: User email (optional for bearer token auth)
        - CMT_CONF_TOKEN: API token or bearer token
        """
        base_url = os.getenv("CMT_CONF_BASE_URL", "").strip()
        email = os.getenv("CMT_CONF_EMAIL", "").strip() or None
        token = os.getenv("CMT_CONF_TOKEN", "").strip() or None
        return cls(base_url=base_url, email=email, token=token)

    def _handle_exception(self, e: Exception, context: str) -> None:
        """Map library exceptions to our error model."""
        if isinstance(e, HTTPError):
            status = e.response.status_code
            try:
                payload = e.response.json()
            except Exception:
                payload = e.response.text

            if status in (401, 403):
                raise AuthError(f"Auth failed during {context}", status=status, payload=payload)
            if status == 404:
                raise NotFoundError(
                    f"Resource not found during {context}", status=status, payload=payload
                )
            if status == 409:
                raise ConflictError(
                    f"Version conflict during {context}", status=status, payload=payload
                )
            if status == 429:
                raise RateLimitError(
                    f"Rate limited during {context}", status=status, payload=payload
                )
            if 500 <= status < 600:
                raise ServerError(
                    f"Server error {status} during {context}", status=status, payload=payload
                )
            raise ConfluenceAPIError(
                f"HTTP error {status} during {context}", status=status, payload=payload
            )
        elif isinstance(e, RequestException):
            raise ConfluenceAPIError(f"Request failed during {context}: {e}")
        else:
            raise ConfluenceAPIError(f"Unexpected error during {context}: {e}")

    def _resolve_version_and_title(
        self, page_id: str, expected_version: int | None, title: str | None
    ) -> tuple[int, str]:
        """Resolve target version and title for page updates.

        Args:
            page_id: Confluence page ID
            expected_version: Expected current version for optimistic locking (if None, fetches current)
            title: New title (if None or falsy, fetches current title)

        Returns:
            Tuple of (target_version, resolved_title) where target_version is ready for API call
        """
        if expected_version is None:
            logger.info(
                "Fetching current page version for optimistic locking",
                extra={"operation": "update_page", "page_id": page_id},
            )
            current = self.get_page_by_id(page_id, expand=("version",))
            target_version = current.version.number + 1
            resolved_title = title or current.title
        else:
            target_version = expected_version + 1  # Confluence expects next version
            if not title:
                logger.info(
                    "Fetching current page title",
                    extra={"operation": "update_page", "page_id": page_id},
                )
                resolved_title = self.get_page_by_id(page_id).title
            else:
                resolved_title = title

        return target_version, resolved_title

    def get_page_by_id(self, page_id: str, *, expand: tuple[str, ...] = ("version",)) -> Page:
        """Get page by ID with comprehensive logging.

        Args:
            page_id: Confluence page ID
            expand: Additional properties to expand (version, body.storage, etc.)

        Returns:
            Page object with metadata and content

        Raises:
            NotFoundError: If page doesn't exist
            AuthError: If authentication fails
            ConfluenceAPIError: For other API errors
        """
        start_time = time.time()
        expand_str = ",".join(expand) if expand else ""

        logger.info(
            "Getting page by ID",
            extra={"page_id": page_id, "expand": list(expand), "operation": "get_page_by_id"},
        )

        try:
            # Use atlassian-python-api to get page by ID
            page_data = self.confluence.get_page_by_id(
                page_id=page_id, expand=expand_str, status=None, version=None
            )

            duration = time.time() - start_time
            logger.info(
                "Successfully retrieved page by ID",
                extra={
                    "page_id": page_id,
                    "title": page_data.get("title", ""),
                    "operation": "get_page_by_id",
                    "duration_seconds": round(duration, 3),
                },
            )

            return self._page_from_json(page_data)

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Failed to get page by ID",
                extra={
                    "page_id": page_id,
                    "operation": "get_page_by_id",
                    "duration_seconds": round(duration, 3),
                    "error": str(e),
                },
            )
            self._handle_exception(e, f"get_page_by_id(page_id={page_id})")

    def get_page_by_title(
        self,
        space_key: str,
        title: str,
        *,
        expand: tuple[str, ...] = ("version",),
    ) -> Page:
        """Get page by space and title with comprehensive logging.

        Args:
            space_key: Confluence space key (e.g., 'PROJ')
            title: Page title to search for
            expand: Additional properties to expand

        Returns:
            Page object with metadata and content

        Raises:
            NotFoundError: If page doesn't exist in the space
            AuthError: If authentication fails
            ConfluenceAPIError: For other API errors
        """
        start_time = time.time()
        expand_str = ",".join(expand) if expand else ""

        logger.info(
            "Getting page by title",
            extra={
                "space_key": space_key,
                "title": title,
                "expand": list(expand),
                "operation": "get_page_by_title",
            },
        )

        try:
            # Use atlassian-python-api to get page by title
            page_data = self.confluence.get_page_by_title(
                space=space_key, title=title, expand=expand_str
            )

            if not page_data:
                raise NotFoundError(f"Page '{title}' not found in space '{space_key}'", status=404)

            duration = time.time() - start_time
            logger.info(
                "Successfully retrieved page by title",
                extra={
                    "space_key": space_key,
                    "title": title,
                    "page_id": page_data.get("id", ""),
                    "operation": "get_page_by_title",
                    "duration_seconds": round(duration, 3),
                },
            )

            return self._page_from_json(page_data)

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Failed to get page by title",
                extra={
                    "space_key": space_key,
                    "title": title,
                    "operation": "get_page_by_title",
                    "duration_seconds": round(duration, 3),
                    "error": str(e),
                },
            )
            self._handle_exception(e, f"get_page_by_title(space={space_key}, title={title})")

    def create_page(
        self,
        *,
        space_key: str,
        title: str,
        html_storage: str,
        parent_id: str | None = None,
        labels: Iterable[str] | None = None,
    ) -> Page:
        """Create a new Confluence page with comprehensive logging.

        Args:
            space_key: Target Confluence space key
            title: Page title
            html_storage: Page content in Confluence storage format (XHTML)
            parent_id: Optional parent page ID
            labels: Optional labels to add to the page

        Returns:
            Created page object with ID and version

        Raises:
            ConflictError: If page with same title exists in space
            AuthError: If authentication fails
            ConfluenceAPIError: For other API errors
        """
        start_time = time.time()

        logger.info(
            "Creating Confluence page",
            extra={
                "space_key": space_key,
                "title": title,
                "parent_id": parent_id,
                "has_labels": labels is not None,
                "content_length": len(html_storage),
                "operation": "create_page",
            },
        )

        try:
            # Create the page using atlassian-python-api
            page_data = self.confluence.create_page(
                space=space_key,
                title=title,
                body=html_storage,
                parent_id=parent_id,
                type="page",
                representation="storage",
            )

            page_id = page_data["id"]

            # Add labels if provided
            if labels:
                labels_list = list(labels)
                logger.info(
                    "Adding labels to created page",
                    extra={
                        "page_id": page_id,
                        "labels": labels_list,
                        "operation": "create_page",
                    },
                )
                self.add_labels(page_id, labels_list)

            duration = time.time() - start_time
            logger.info(
                "Successfully created Confluence page",
                extra={
                    "page_id": page_id,
                    "space_key": space_key,
                    "title": title,
                    "operation": "create_page",
                    "duration_seconds": round(duration, 3),
                },
            )

            return self._page_from_json(page_data)

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Failed to create Confluence page",
                extra={
                    "space_key": space_key,
                    "title": title,
                    "operation": "create_page",
                    "duration_seconds": round(duration, 3),
                    "error": str(e),
                },
            )
            self._handle_exception(e, f"create_page(space={space_key}, title={title})")

    def update_page(
        self,
        *,
        page_id: str,
        html_storage: str,
        title: str | None = None,
        expected_version: int | None = None,
        labels: Iterable[str] | None = None,
    ) -> Page:
        """Update existing Confluence page with version control.

        Args:
            page_id: Confluence page ID to update
            html_storage: New content in Confluence storage format (XHTML)
            title: Optional new title (if None, keeps current title)
            expected_version: Expected current version for optimistic locking (if None, fetches current)
            labels: Optional labels to add to the page

        Returns:
            Updated page object with new version

        Raises:
            NotFoundError: If page doesn't exist
            ConflictError: If version conflict occurs (409)
            AuthError: If authentication fails
            ConfluenceAPIError: For other API errors
        """
        start_time = time.time()

        logger.info(
            "Updating Confluence page",
            extra={
                "page_id": page_id,
                "title": title,
                "expected_version": expected_version,
                "has_labels": labels is not None,
                "content_length": len(html_storage),
                "operation": "update_page",
            },
        )

        try:
            # Resolve version and title
            target_version, resolved_title = self._resolve_version_and_title(
                page_id, expected_version, title
            )

            # Update the page using atlassian-python-api
            page_data = self.confluence.update_page(
                page_id=page_id,
                title=resolved_title,
                body=html_storage,
                version=target_version,
                representation="storage",
            )

            # Add labels if provided
            if labels:
                labels_list = list(labels)
                logger.info(
                    "Adding labels to updated page",
                    extra={
                        "page_id": page_id,
                        "labels": labels_list,
                        "operation": "update_page",
                    },
                )
                self.add_labels(page_id, labels_list)

            duration = time.time() - start_time
            logger.info(
                "Successfully updated Confluence page",
                extra={
                    "page_id": page_id,
                    "title": resolved_title,
                    "version": target_version,
                    "operation": "update_page",
                    "duration_seconds": round(duration, 3),
                },
            )

            return self._page_from_json(page_data)

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Failed to update Confluence page",
                extra={
                    "page_id": page_id,
                    "title": title,
                    "expected_version": expected_version,
                    "operation": "update_page",
                    "duration_seconds": round(duration, 3),
                    "error": str(e),
                },
            )
            self._handle_exception(e, f"update_page(page_id={page_id})")

    def add_labels(self, page_id: str, labels: Iterable[str]) -> None:
        """Add labels to a Confluence page.

        Args:
            page_id: Confluence page ID
            labels: Iterable of label names to add

        Raises:
            NotFoundError: If page doesn't exist
            AuthError: If authentication fails
            ConfluenceAPIError: For other API errors
        """
        labels_list = list(labels)
        if not labels_list:
            return

        logger.info(
            "Adding labels to page",
            extra={"page_id": page_id, "labels": labels_list, "operation": "add_labels"},
        )

        try:
            # Add each label using atlassian-python-api
            for label in labels_list:
                self.confluence.set_page_label(page_id, label)

            logger.info(
                "Successfully added labels to page",
                extra={"page_id": page_id, "labels": labels_list, "operation": "add_labels"},
            )

        except Exception as e:
            logger.error(
                "Failed to add labels to page",
                extra={
                    "page_id": page_id,
                    "labels": labels_list,
                    "operation": "add_labels",
                    "error": str(e),
                },
            )
            self._handle_exception(e, f"add_labels(page_id={page_id})")

    # Alternative naming convention methods for API compatibility
    # These methods use camelCase naming to match Confluence's REST API convention.
    # Use these if you prefer API-style naming; otherwise use the snake_case methods.

    def getPage(self, page_id: str, *, expand: tuple[str, ...] = ("version",)) -> Page:
        """Alias for get_page_by_id with alternative naming convention.

        This method uses camelCase naming for consistency with Confluence REST API.
        Functionally identical to get_page_by_id().
        """
        return self.get_page_by_id(page_id, expand=expand)

    def createPage(
        self,
        *,
        space_key: str,
        title: str,
        html_storage: str,
        parent_id: str | None = None,
        labels: Iterable[str] | None = None,
    ) -> Page:
        """Alias for create_page with alternative naming convention.

        This method uses camelCase naming for consistency with Confluence REST API.
        Functionally identical to create_page().
        """
        return self.create_page(
            space_key=space_key,
            title=title,
            html_storage=html_storage,
            parent_id=parent_id,
            labels=labels,
        )

    def updatePage(
        self,
        *,
        page_id: str,
        html_storage: str,
        title: str | None = None,
        expected_version: int | None = None,
    ) -> Page:
        """Alias for update_page with alternative naming convention.

        This method uses camelCase naming for consistency with Confluence REST API.
        Functionally identical to update_page().
        """
        return self.update_page(
            page_id=page_id,
            html_storage=html_storage,
            title=title,
            expected_version=expected_version,
        )

    @staticmethod
    def _page_from_json(data: dict[str, Any]) -> Page:
        """Convert JSON response to Page object."""
        page_id = data.get("id") or (data.get("content") or {}).get("id")
        title = data.get("title", "")
        space_key = (data.get("space") or {}).get("key") or ""
        version_num = (data.get("version") or {}).get("number") or 1

        # Extract storage content if available
        body_storage = None
        body = data.get("body", {})
        storage = body.get("storage", {})
        if storage:
            body_storage = storage.get("value", "")

        return Page(
            id=page_id,
            title=title,
            space_key=space_key,
            version=PageVersion(number=version_num),
            body_storage=body_storage,
        )
