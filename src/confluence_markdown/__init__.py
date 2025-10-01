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

__all__ = [
    "ConfluenceClient",
    "ConfluenceAPIError",
    "AuthError",
    "NotFoundError",
    "ConflictError",
    "RateLimitError",
    "ServerError",
    "MarkdownToConfluenceConverter",
]
