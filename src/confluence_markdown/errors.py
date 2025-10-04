# Copyright (c) 2025 Francis Bain
# SPDX-License-Identifier: Apache-2.0

"""Error handling classes and constants for push pipeline implementation.

This module defines exit codes and error classes for the push pipeline
to provide actionable feedback to users.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Exit codes for push pipeline
EXIT_SUCCESS = 0
EXIT_CONVERSION_ERROR = 1  # Markdown conversion failures
EXIT_API_ERROR = 2  # Confluence API failures (4xx/5xx)
EXIT_CONFIG_ERROR = 3  # Configuration/authentication issues


class PushError(Exception):
    """Base class for push pipeline errors."""

    def __init__(self, message: str, *, exit_code: int, context: Optional[dict] = None):
        super().__init__(message)
        self.exit_code = exit_code
        self.context = context or {}

    def log_error(self) -> None:
        """Log the error with context information."""
        logger.error(
            self.args[0],
            extra={
                "error_type": type(self).__name__,
                "exit_code": self.exit_code,
                **self.context,
            },
        )


class ConversionError(PushError):
    """Error during markdown conversion process."""

    def __init__(
        self, message: str, *, file_path: Optional[str] = None, context: Optional[dict] = None
    ):
        ctx = context or {}
        if file_path:
            ctx["file_path"] = file_path
        super().__init__(message, exit_code=EXIT_CONVERSION_ERROR, context=ctx)


class APIError(PushError):
    """Error during Confluence API operations."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        page_id: Optional[str] = None,
        file_path: Optional[str] = None,
        context: Optional[dict] = None,
    ):
        ctx = context or {}
        if status_code:
            ctx["status_code"] = status_code
        if page_id:
            ctx["page_id"] = page_id
        if file_path:
            ctx["file_path"] = file_path
        super().__init__(message, exit_code=EXIT_API_ERROR, context=ctx)


class ConfigError(PushError):
    """Configuration or authentication error."""

    def __init__(self, message: str, *, context: Optional[dict] = None):
        super().__init__(message, exit_code=EXIT_CONFIG_ERROR, context=context)


class AuthenticationError(ConfigError):
    """Authentication failure with Confluence API."""

    def __init__(
        self,
        message: str = "Invalid or missing Confluence API token.",
        *,
        context: Optional[dict] = None,
    ):
        super().__init__(message, context=context)


class VersionConflictError(APIError):
    """Version conflict during page update."""

    def __init__(
        self,
        message: str = "Detected mismatched Confluence version - aborting push to prevent data loss.",
        *,
        page_id: Optional[str] = None,
        expected_version: Optional[int] = None,
        actual_version: Optional[int] = None,
        context: Optional[dict] = None,
    ):
        ctx = context or {}
        if expected_version is not None:
            ctx["expected_version"] = expected_version
        if actual_version is not None:
            ctx["actual_version"] = actual_version
        super().__init__(message, page_id=page_id, context=ctx)
