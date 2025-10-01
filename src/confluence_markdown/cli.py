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
from typing import Optional

from .mapping_store import MappingStore


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration.

    Args:
        verbose: If True, set DEBUG level; otherwise INFO level
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def cmd_map_add(args: argparse.Namespace) -> int:
    """Handle the 'map add' command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    logger = logging.getLogger(__name__)

    try:
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
            # Direct page ID mapping
            result = mapping_store.add_mapping(
                path=str(path), page_id=args.page_id, space_key=args.space if args.space else None
            )
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


def main(argv: Optional[list[str]] = None) -> int:
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
    if args.command == "map":
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
