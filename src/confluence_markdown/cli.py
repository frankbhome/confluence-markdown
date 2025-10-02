# Copyright (c) 2025 Francis Bain
# SPDX-License-Identifier: Apache-2.0

"""CLI interface for confluence-markdown tool.

This module provides the command-line interface for the confluence-markdown tool,
supporting various operations like mapping management, push/pull operations, etc.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from .confluence_api import AuthError, ConflictError, ConfluenceAPIError, ConfluenceClient
from .converter import MarkdownToConfluenceConverter
from .errors import (
    EXIT_API_ERROR,
    EXIT_CONFIG_ERROR,
    EXIT_SUCCESS,
    APIError,
    AuthenticationError,
    ConfigError,
    ConversionError,
    VersionConflictError,
)
from .mapping_store import MappingEntry, MappingStore


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration.

    Args:
        verbose: If True, set DEBUG level; otherwise INFO level
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def cmd_push(args: argparse.Namespace) -> int:
    """Handle the 'push' command.

    Args:
        args: Parsed command line arguments containing file path and options

    Returns:
        Exit code (0 for success, 1-3 for various error types)
    """
    logger = logging.getLogger(__name__)

    try:
        # Validate required parameters
        if not args.file:
            logger.error("--file is required for push command")
            return EXIT_CONFIG_ERROR

        file_path = Path(args.file)

        # Validate file exists
        if not file_path.exists():
            logger.error(f"File does not exist: {file_path}")
            return EXIT_CONFIG_ERROR

        # Initialize mapping store to find confluence target
        mapping_store = MappingStore()
        mapping = mapping_store.get_mapping(str(file_path))

        if not mapping:
            logger.error(f"No mapping found for file: {file_path}")
            logger.info("Use 'cmt map add' to create a mapping first")
            return EXIT_CONFIG_ERROR

        # Configure Confluence client with error handling
        try:
            client = _get_confluence_client()
        except AuthenticationError as e:
            e.log_error()
            return e.exit_code
        except ConfigError as e:
            e.log_error()
            return e.exit_code

        # Read and convert markdown
        try:
            with open(file_path, encoding="utf-8") as f:
                markdown_content = f.read()

            converter = MarkdownToConfluenceConverter()
            html_content = converter.convert(markdown_content)

        except Exception as e:
            conversion_error = ConversionError(
                f"Failed to convert markdown file: {e}", file_path=str(file_path)
            )
            conversion_error.log_error()
            return conversion_error.exit_code

        # Push to Confluence with comprehensive error handling
        try:
            _push_to_confluence(client, mapping, html_content, str(file_path))
            logger.info(
                "Successfully pushed file to Confluence",
                extra={
                    "file_path": str(file_path),
                    "page_id": mapping.get("page_id", "N/A"),
                },
            )
            return EXIT_SUCCESS

        except AuthenticationError as e:
            e.log_error()
            return e.exit_code
        except VersionConflictError as e:
            e.log_error()
            return e.exit_code
        except APIError as e:
            e.log_error()
            return e.exit_code
        except Exception as e:
            api_error = APIError(
                f"Unexpected error during push: {e}",
                file_path=str(file_path),
                page_id=mapping.get("page_id"),
            )
            api_error.log_error()
            return api_error.exit_code

    except Exception as e:
        logger.error(f"Unexpected error in push command: {e}")
        return EXIT_API_ERROR


def _get_confluence_client() -> ConfluenceClient:
    """Get configured Confluence client with authentication validation.

    Returns:
        Configured ConfluenceClient

    Raises:
        AuthenticationError: If authentication credentials are invalid/missing
        ConfigError: If configuration is invalid
    """
    import os

    # Check for required environment variables
    base_url = os.getenv("CMT_CONF_BASE_URL", "").strip()
    email = os.getenv("CMT_CONF_EMAIL", "").strip() or None
    token = os.getenv("CMT_CONF_TOKEN", "").strip() or None

    if not base_url:
        raise ConfigError("Missing CMT_CONF_BASE_URL environment variable")

    if not token:
        raise AuthenticationError("Invalid or missing Confluence API token.")

    try:
        return ConfluenceClient(base_url=base_url, email=email, token=token)
    except Exception as e:
        raise ConfigError(f"Failed to initialize Confluence client: {e}") from e


def _push_to_confluence(
    client: ConfluenceClient, mapping: MappingEntry, html_content: str, file_path: str
) -> bool:
    """Push content to Confluence with error handling.

    Args:
        client: Configured Confluence client
        mapping: File-to-page mapping from mapping store
        html_content: Converted HTML content
        file_path: Original file path for logging

    Returns:
        True if successful, False otherwise

    Raises:
        AuthenticationError: If API returns 401/403
        VersionConflictError: If API returns 409 (version conflict)
        APIError: For other API errors
    """
    logger = logging.getLogger(__name__)

    try:
        page_id = mapping.get("page_id")
        space_key = mapping.get("space_key")
        title = mapping.get("title")

        if page_id:
            # Update existing page by ID
            logger.info(f"Updating page {page_id} from {file_path}")
            try:
                result = client.update_page(page_id=page_id, html_storage=html_content)
                logger.info(
                    f"Page updated successfully: {result.id} (version {result.version.number})"
                )
                return True

            except AuthError as e:
                raise AuthenticationError(
                    context={
                        "page_id": page_id,
                        "file_path": file_path,
                        "error_code": getattr(e, "status", None),
                    }
                ) from e
            except ConflictError as e:
                raise VersionConflictError(page_id=page_id, context={"file_path": file_path}) from e
            except ConfluenceAPIError as e:
                raise APIError(
                    f"API error during page update: {e}",
                    status_code=getattr(e, "status", None),
                    page_id=page_id,
                    file_path=file_path,
                ) from e

        elif space_key and title:
            # Create or update page by space + title
            logger.info(f"Creating/updating page '{title}' in space {space_key} from {file_path}")
            try:
                # First try to find existing page
                existing_page = client.get_page_by_title(space_key=space_key, title=title)

                if existing_page:
                    # Update existing page
                    result = client.update_page(
                        page_id=existing_page.id, html_storage=html_content, title=title
                    )
                    logger.info(
                        f"Page updated successfully: {result.id} (version {result.version.number})"
                    )
                else:
                    # Create new page
                    result = client.create_page(
                        space_key=space_key, title=title, html_storage=html_content
                    )
                    logger.info(
                        f"Page created successfully: {result.id} (version {result.version.number})"
                    )

                return True

            except AuthError as e:
                raise AuthenticationError(
                    context={
                        "file_path": file_path,
                        "space_key": space_key,
                        "title": title,
                        "error_code": getattr(e, "status", None),
                    }
                ) from e
            except ConflictError as e:
                raise VersionConflictError(
                    context={"file_path": file_path, "space_key": space_key, "title": title}
                ) from e
            except ConfluenceAPIError as e:
                raise APIError(
                    f"API error during page creation/update: {e}",
                    status_code=getattr(e, "status", None),
                    file_path=file_path,
                    context={"space_key": space_key, "title": title},
                ) from e
        else:
            raise ConfigError(f"Invalid mapping configuration: {mapping}")

    except Exception as e:
        if isinstance(e, (AuthenticationError, VersionConflictError, APIError, ConfigError)):
            raise
        else:
            raise APIError(
                f"Unexpected error during Confluence operation: {e}", file_path=file_path
            ) from e


def cmd_map_add(args: argparse.Namespace) -> int:
    """Handle the 'map add' command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    logger = logging.getLogger(__name__)

    try:
        # Validate parameter combinations - fail fast with user-friendly messages
        if args.page_id and args.title:
            logger.error(
                "Cannot use --page with --title; provide either --page or --space and --title"
            )
            return 1

        # Validate required parameters
        if not args.page_id and not (args.space and args.title):
            logger.error("Either --page or both --space and --title must be provided")
            return 1

        if not args.path:
            logger.error("--path is required")
            return 1

        # Validate path exists
        path = Path(args.path)
        if not path.exists():
            logger.error(f"File does not exist: {path}")
            return 1

        # Initialize mapping store
        mapping_store = MappingStore()

        # Create the mapping entry
        if args.page_id:
            # Direct page ID mapping - only pass space_key if provided
            if args.space:
                result = mapping_store.add_mapping(
                    path=str(path), page_id=args.page_id, space_key=args.space
                )
            else:
                result = mapping_store.add_mapping(path=str(path), page_id=args.page_id)
        else:
            # Space + title mapping
            result = mapping_store.add_mapping(
                path=str(path), space_key=args.space, title=args.title
            )

        if result.get("created"):
            logger.info(f"Created new mapping: {path} -> {result['mapping']}")
        else:
            logger.info(f"Updated existing mapping: {path} -> {result['mapping']}")

        return 0

    except Exception as e:
        logger.error(f"Failed to add mapping: {e}")
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create the command line argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="conmd", description="Two-way sync between Confluence and Markdown (Git)"
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Push command
    push_parser = subparsers.add_parser("push", help="Push markdown file to Confluence")
    push_parser.add_argument("--file", required=True, help="Path to the Markdown file to push")

    # Map command
    map_parser = subparsers.add_parser("map", help="Mapping management commands")
    map_subparsers = map_parser.add_subparsers(dest="map_command", help="Map operations")

    # Map add command
    add_parser = map_subparsers.add_parser("add", help="Add a file-to-page mapping")
    add_parser.add_argument("--page", dest="page_id", help="Confluence page ID")
    add_parser.add_argument(
        "--path", required=True, help="Path to the Markdown file (relative to repository root)"
    )
    add_parser.add_argument("--space", help="Confluence space key")
    add_parser.add_argument("--title", help="Page title (used with --space for page creation)")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entry point.

    Args:
        argv: Command line arguments (defaults to sys.argv)

    Returns:
        Exit code
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Handle commands
    if args.command == "push":
        return cmd_push(args)
    elif args.command == "map":
        if args.map_command == "add":
            return cmd_map_add(args)
        else:
            logger.error("Unknown map command")
            parser.print_help(file=sys.stderr)
            return 1
    else:
        # No command specified or unknown command
        if not args.command:
            logger.info("confluence-markdown CLI - no command specified")
        parser.print_help(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
