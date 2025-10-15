"""Interactive publisher for Confluence Markdown documents."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Iterable, List, Sequence

from confluence_markdown.mapping_store import MappingEntry, MappingStore
from scripts.common import (
    configure_logging,
    find_repository_root,
    publish_documents,
)

LOGGER = logging.getLogger("scripts.interactive_publish")


def _format_mapping(path: Path, mapping: MappingEntry) -> str:
    """Return a friendly description of the Confluence target for ``path``."""

    if mapping.get("page_id"):
        target = f"page_id={mapping['page_id']}"
    else:
        target = f"space={mapping.get('space_key')} title={mapping.get('title')}"
    return f"{path} -> {target}"


def _prepare_options(mapping_store: MappingStore) -> List[tuple[Path, MappingEntry]]:
    """Collect mappings with repository-absolute paths for selection."""

    repo_root = find_repository_root()
    options: List[tuple[Path, MappingEntry]] = []
    for rel_path, mapping in mapping_store.list_mappings().items():
        options.append((repo_root / Path(rel_path), mapping))
    return sorted(options, key=lambda item: item[0].as_posix())


def _prompt_selection(count: int, input_func=input) -> List[int]:
    """Prompt the user to choose one or more documents by menu index."""

    while True:
        try:
            raw = input_func("Select documents (comma separated), 'a' for all, or 'q' to quit: ")
        except EOFError:
            # User triggered EOF (Ctrl+D/Ctrl+Z); treat as quit
            return []

        choice = raw.strip().lower()
        if not choice:
            print("No selection made; choose at least one entry or 'q' to quit.")
            continue
        if choice in {"q", "quit"}:
            return []
        if choice in {"a", "all"}:
            return list(range(1, count + 1))

        try:
            indices = {int(part) for part in choice.split(",")}
        except ValueError:
            print("Invalid selection. Use comma separated numbers, 'a', or 'q'.")
            continue

        if not indices:
            print("No selection made; choose at least one entry or 'q' to quit.")
            continue

        if any(index < 1 or index > count for index in indices):
            print(f"Selections must be between 1 and {count}.")
            continue

        return sorted(indices)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line options."""

    parser = argparse.ArgumentParser(
        description="Interactively publish Markdown files to Confluence"
    )
    parser.add_argument(
        "paths", nargs="*", help="Optional explicit files to publish; skips the prompt."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Convert but do not call the Confluence API."
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase logging verbosity (repeat for more detail).",
    )
    return parser.parse_args(argv)


def _resolve_selection(
    options: Sequence[tuple[Path, MappingEntry]], selections: Sequence[int]
) -> List[Path]:
    """Translate menu selections into concrete paths."""

    lookup = {index: option[0] for index, option in enumerate(options, start=1)}
    return [lookup[index] for index in selections if index in lookup]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the interactive publishing workflow."""

    args = parse_args(argv)
    configure_logging(args.verbose)

    mapping_store = MappingStore()

    if args.paths:
        targets: Iterable[Path] = (Path(path) for path in args.paths)
    else:
        options = _prepare_options(mapping_store)
        if not options:
            LOGGER.error("No mappings found. Add entries to .cmt/map.json before publishing.")
            return 1

        for index, (path, mapping) in enumerate(options, start=1):
            print(f"[{index}] {_format_mapping(path, mapping)}")

        selections = _prompt_selection(len(options))
        if not selections:
            LOGGER.info("No documents selected; nothing to publish.")
            return 0

        targets = _resolve_selection(options, selections)

    outcomes = publish_documents(targets, mapping_store=mapping_store, dry_run=args.dry_run)

    for outcome in outcomes:
        LOGGER.info("%s -> %s (%s)", outcome.path, outcome.action, outcome.status)

    return 1 if any(outcome.status == "failure" for outcome in outcomes) else 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
