# Copyright (c) 2025 Francis Bain
# SPDX-License-Identifier: Apache-2.0

"""Confluence API adapter implementation.

This module provides a stable interface for all Markdown → Confluence push operations.
Encapsulates REST API calls for retrieving, creating, and updating Confluence pages
while handling authentication, version control, and retry/backoff logic.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

logger = logging.getLogger("confluence_api")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s confluence_api %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)


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
        self.session = requests.Session()
        retry = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "PUT", "POST", "DELETE"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        if email and token:
            b = base64.b64encode(f"{email}:{token}".encode()).decode()
            self.session.headers["Authorization"] = f"Basic {b}"
        elif token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        else:
            logger.warning(
                "ConfluenceClient initialized without credentials; calls will fail with AuthError"
            )

        self.session.headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )

    @classmethod
    def from_env(cls) -> ConfluenceClient:
        base_url = os.getenv("CMT_CONF_BASE_URL", "").strip()
        email = os.getenv("CMT_CONF_EMAIL", "").strip() or None
        token = os.getenv("CMT_CONF_TOKEN", "").strip() or None
        return cls(base_url=base_url, email=email, token=token)

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _handle_error(self, resp: requests.Response, context: str) -> None:
        status = resp.status_code
        try:
            payload = resp.json()
        except Exception:
            payload = resp.text

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
            raise RateLimitError(f"Rate limited during {context}", status=status, payload=payload)
        if 500 <= status < 600:
            raise ServerError(
                f"Server error {status} during {context}", status=status, payload=payload
            )
        raise ConfluenceAPIError(
            f"Unexpected status {status} during {context}", status=status, payload=payload
        )

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
        params = {"expand": ",".join(expand)} if expand else None

        logger.info(
            "Getting page by ID",
            extra={"page_id": page_id, "expand": list(expand), "operation": "get_page_by_id"},
        )

        try:
            resp = self.session.get(
                self._url(f"/rest/api/content/{page_id}"), params=params, timeout=self.timeout
            )
            duration = time.time() - start_time

            logger.info(
                "API call completed",
                extra={
                    "operation": "get_page_by_id",
                    "page_id": page_id,
                    "status_code": resp.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "success": resp.ok,
                },
            )

            if not resp.ok:
                self._handle_error(resp, f"get_page_by_id(page_id={page_id})")

            page = self._page_from_json(resp.json())

            logger.info(
                "Page retrieved successfully",
                extra={
                    "operation": "get_page_by_id",
                    "page_id": page_id,
                    "page_title": page.title,
                    "version": page.version.number,
                    "space_key": page.space_key,
                },
            )

            return page

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "API call failed",
                extra={
                    "operation": "get_page_by_id",
                    "page_id": page_id,
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    def get_page_by_title(
        self, *, space_key: str, title: str, expand: tuple[str, ...] = ("version",)
    ) -> Page | None:
        params = {"title": title, "spaceKey": space_key, "expand": ",".join(expand), "limit": 1}
        resp = self.session.get(self._url("/rest/api/content"), params=params, timeout=self.timeout)
        if not resp.ok:
            self._handle_error(resp, f"get_page_by_title(space={space_key}, title={title})")
        results = resp.json().get("results", [])
        return self._page_from_json(results[0]) if results else None

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
            space_key: Confluence space key
            title: Page title
            html_storage: HTML content in Confluence storage format
            parent_id: Optional parent page ID
            labels: Optional labels to add to the page

        Returns:
            Created Page object

        Raises:
            ConflictError: If page with same title already exists
            AuthError: If insufficient permissions
            ConfluenceAPIError: For other API errors
        """
        start_time = time.time()

        logger.info(
            "Creating new page",
            extra={
                "operation": "create_page",
                "space_key": space_key,
                "title": title,
                "parent_id": parent_id,
                "has_labels": labels is not None,
                "content_size": len(html_storage),
            },
        )

        try:
            payload = {
                "type": "page",
                "title": title,
                "space": {"key": space_key},
                "body": {"storage": {"value": html_storage, "representation": "storage"}},
            }
            if parent_id:
                payload["ancestors"] = [{"id": parent_id}]

            resp = self.session.post(
                self._url("/rest/api/content"), data=json.dumps(payload), timeout=self.timeout
            )
            duration = time.time() - start_time

            logger.info(
                "Create page API call completed",
                extra={
                    "operation": "create_page",
                    "space_key": space_key,
                    "title": title,
                    "status_code": resp.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "success": resp.ok,
                },
            )

            if not resp.ok:
                self._handle_error(resp, f"create_page(space={space_key}, title={title})")

            page = self._page_from_json(resp.json())

            # Add labels if provided
            if labels:
                try:
                    self.add_labels(page.id, labels)
                    logger.info(
                        "Labels added successfully",
                        extra={
                            "operation": "create_page",
                            "page_id": page.id,
                            "labels": list(labels),
                        },
                    )
                except ConfluenceAPIError as e:
                    logger.warning(
                        "Failed to add labels to page",
                        extra={"operation": "create_page", "page_id": page.id, "error": str(e)},
                    )

            logger.info(
                "Page created successfully",
                extra={
                    "operation": "create_page",
                    "page_id": page.id,
                    "page_title": page.title,
                    "space_key": page.space_key,
                    "version": page.version.number,
                },
            )

            return page

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Create page failed",
                extra={
                    "operation": "create_page",
                    "space_key": space_key,
                    "title": title,
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    def update_page(
        self,
        *,
        page_id: str,
        html_storage: str,
        title: str | None = None,
        expected_version: int | None = None,
    ) -> Page:
        """Update an existing Confluence page with optimistic concurrency control.

        Args:
            page_id: Confluence page ID
            html_storage: Updated HTML content in Confluence storage format
            title: Optional new title (if None, keeps existing title)
            expected_version: Expected current version for optimistic locking
                            (if None, fetches current version)

        Returns:
            Updated Page object

        Raises:
            ConflictError: If version conflict occurs (optimistic locking failure)
            NotFoundError: If page doesn't exist
            AuthError: If insufficient permissions
            ConfluenceAPIError: For other API errors
        """
        start_time = time.time()

        logger.info(
            "Updating page",
            extra={
                "operation": "update_page",
                "page_id": page_id,
                "expected_version": expected_version,
                "has_title_update": title is not None,
                "content_size": len(html_storage),
            },
        )

        try:
            # Handle version control and title resolution
            if expected_version is None:
                logger.info(
                    "Fetching current page version for optimistic locking",
                    extra={"operation": "update_page", "page_id": page_id},
                )
                current = self.get_page_by_id(page_id, expand=("version",))
                expected_version = current.version.number + 1
                title = title or current.title
            else:
                expected_version = expected_version + 1  # Confluence expects next version
                if not title:
                    logger.info(
                        "Fetching current page title",
                        extra={"operation": "update_page", "page_id": page_id},
                    )
                    title = self.get_page_by_id(page_id).title

            logger.info(
                "Prepared update payload",
                extra={
                    "operation": "update_page",
                    "page_id": page_id,
                    "title": title,
                    "target_version": expected_version,
                },
            )

            payload = {
                "id": page_id,
                "type": "page",
                "title": title,
                "version": {"number": expected_version},
                "body": {"storage": {"value": html_storage, "representation": "storage"}},
            }

            resp = self.session.put(
                self._url(f"/rest/api/content/{page_id}"),
                data=json.dumps(payload),
                timeout=self.timeout,
            )
            duration = time.time() - start_time

            logger.info(
                "Update page API call completed",
                extra={
                    "operation": "update_page",
                    "page_id": page_id,
                    "target_version": expected_version,
                    "status_code": resp.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "success": resp.ok,
                },
            )

            if not resp.ok:
                self._handle_error(resp, f"update_page(page_id={page_id})")

            updated_page = self._page_from_json(resp.json())

            logger.info(
                "Page updated successfully",
                extra={
                    "operation": "update_page",
                    "page_id": page_id,
                    "page_title": updated_page.title,
                    "old_version": expected_version - 1,
                    "new_version": updated_page.version.number,
                    "space_key": updated_page.space_key,
                },
            )

            return updated_page

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Update page failed",
                extra={
                    "operation": "update_page",
                    "page_id": page_id,
                    "expected_version": expected_version,
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    def add_labels(self, page_id: str, labels: Iterable[str]) -> None:
        items = [{"prefix": "global", "name": label} for label in labels]
        resp = self.session.post(
            self._url(f"/rest/api/content/{page_id}/label"),
            data=json.dumps(items),
            timeout=self.timeout,
        )
        if not resp.ok:
            self._handle_error(resp, f"add_labels(page_id={page_id})")

    # Convenience methods matching CMD-43 acceptance criteria naming
    def getPage(self, page_id: str, *, expand: tuple[str, ...] = ("version",)) -> Page:
        """Alias for get_page_by_id following CMD-43 naming convention."""
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
        """Alias for create_page following CMD-43 naming convention."""
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
        """Alias for update_page following CMD-43 naming convention."""
        return self.update_page(
            page_id=page_id,
            html_storage=html_storage,
            title=title,
            expected_version=expected_version,
        )

    @staticmethod
    def _page_from_json(data: dict[str, Any]) -> Page:
        page_id = data.get("id") or (data.get("content") or {}).get("id")
        title = data.get("title", "")
        space_key = (data.get("space") or {}).get("key") or ""
        version_num = (data.get("version") or {}).get("number") or 1
        storage = (data.get("body") or {}).get("storage") or {}
        body_storage = storage.get("value") if storage.get("representation") == "storage" else None
        return Page(
            id=str(page_id),
            title=title,
            space_key=str(space_key),
            version=PageVersion(number=int(version_num)),
            body_storage=body_storage,
        )
