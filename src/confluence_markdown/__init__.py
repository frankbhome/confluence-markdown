# Copyright (c) 2025 Francis Bain
# SPDX-License-Identifier: Apache-2.0

# Makes top-level imports work and documents public API
from .confluence_api import (
    AuthError,
    ConflictError,
    ConfluenceAPIError,
    ConfluenceClient,
    NotFoundError,
    RateLimitError,
    ServerError,
)
from .converter import MarkdownToConfluenceConverter
from .errors import (
    EXIT_API_ERROR,
    EXIT_CONFIG_ERROR,
    EXIT_CONVERSION_ERROR,
    EXIT_SUCCESS,
    APIError,
    AuthenticationError,
    ConfigError,
    ConversionError,
    PushError,
    VersionConflictError,
)

__all__ = [
    "ConfluenceClient",
    "ConfluenceAPIError",
    "AuthError",
    "NotFoundError",
    "ConflictError",
    "RateLimitError",
    "ServerError",
    "MarkdownToConfluenceConverter",
    "APIError",
    "AuthenticationError",
    "ConfigError",
    "ConversionError",
    "PushError",
    "VersionConflictError",
    "EXIT_SUCCESS",
    "EXIT_API_ERROR",
    "EXIT_CONFIG_ERROR",
    "EXIT_CONVERSION_ERROR",
]
