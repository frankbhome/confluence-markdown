"""Bulk publish Markdown documents to Confluence.

This utility reads the repository's mapping store and pushes the requested Markdown
files to Confluence using :class:`confluence_markdown.confluence_api.ConfluenceClient`.
It is designed for CI/CD usage and developer productivity, supporting dry runs and
clear reporting of successes, skips, and failures.

Usage examples
--------------

Dry run the default mapped documents::

    poetry run python scripts/bulk_publish_docs.py --dry-run

Publish a specific subset::

    poetry run python scripts/bulk_publish_docs.py docs/overview.md docs/api.md
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Iterable, Sequence

from confluence_markdown.mapping_store import MappingStore
from scripts.common import (
    PublishOutcome,
    configure_logging,
    default_markdown_paths,
    publish_documents,
)


def _summarise(outcomes: Sequence[PublishOutcome]) -> str:
    """Return a human-readable summary line for the run."""

    total = len(outcomes)
    successes = sum(1 for outcome in outcomes if outcome.status == "success")
    failures = sum(1 for outcome in outcomes if outcome.status == "failure")
    skipped = sum(1 for outcome in outcomes if outcome.status == "skipped")
    return f"Processed {total} document(s): {successes} succeeded, {failures} failed, {skipped} skipped"


def _render_outcome(outcome: PublishOutcome) -> str:
    """Return a friendly string describing a single outcome."""

    base = f"{outcome.path}: {outcome.action} ({outcome.status})"
    if outcome.detail:
        return f"{base} - {outcome.detail}"
    return base


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description="Bulk publish Markdown documents to Confluence")
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional list of Markdown files to publish. Defaults to all mapped documents.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform all conversions but do not call the Confluence API.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase logging verbosity (can be supplied multiple times).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the bulk publishing workflow."""

    args = parse_args(argv)
    configure_logging(args.verbose)
    logger = logging.getLogger("scripts.bulk_publish")

    mapping_store = MappingStore()

    if args.paths:
        targets: Iterable[Path] = (Path(path) for path in args.paths)
    else:
        targets = default_markdown_paths(mapping_store)

    targets = list(targets)
    if not targets:
        logger.error("No documents supplied and no mappings found. Nothing to publish.")
        return 1

    outcomes = publish_documents(targets, mapping_store=mapping_store, dry_run=args.dry_run)

    for outcome in outcomes:
        logger.info(_render_outcome(outcome))

    logger.info(_summarise(outcomes))

    failures = [outcome for outcome in outcomes if outcome.status == "failure"]
    return 1 if failures else 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
