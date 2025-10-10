"""Validate Markdown to Confluence formatting against the golden corpus."""

from __future__ import annotations

import argparse
import difflib
import logging
from pathlib import Path
from typing import Sequence

from confluence_markdown.converter import MarkdownToConfluenceConverter
from scripts.common import configure_logging, find_repository_root

LOGGER = logging.getLogger("scripts.test_formatting")


def _golden_directories(repo_root: Path) -> tuple[Path, Path]:
    base = repo_root / "tests" / "golden_corpus"
    return base / "input", base / "expected"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        help="Directory containing source Markdown fixtures (defaults to tests/golden_corpus/input).",
    )
    parser.add_argument(
        "--expected-dir",
        type=Path,
        help="Directory containing expected Confluence HTML fixtures (defaults to tests/golden_corpus/expected).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase logging verbosity (can be supplied multiple times).",
    )
    return parser.parse_args(argv)


def _load(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").strip()


def _render_diff(expected: str, actual: str) -> str:
    lines = difflib.unified_diff(
        expected.splitlines(),
        actual.splitlines(),
        fromfile="expected",
        tofile="actual",
        lineterm="",
    )
    return "\n".join(lines)


def _validate_pair(converter: MarkdownToConfluenceConverter, source: Path, expected: Path) -> bool:
    markdown = _load(source)
    actual_html = converter.convert(markdown).strip()
    expected_html = _load(expected)

    if actual_html == expected_html:
        LOGGER.info("✔ %s", source.name)
        return True

    diff = _render_diff(expected_html, actual_html)
    LOGGER.error("✖ %s\n%s", source.name, diff)
    return False


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    configure_logging(args.verbose)

    repo_root = find_repository_root()
    input_dir, expected_dir = _golden_directories(repo_root)

    if args.input_dir:
        input_dir = args.input_dir
    if args.expected_dir:
        expected_dir = args.expected_dir

    if not input_dir.exists() or not expected_dir.exists():
        LOGGER.error(
            "Input directory %s or expected directory %s does not exist", input_dir, expected_dir
        )
        return 1

    converter = MarkdownToConfluenceConverter()
    failures = 0
    processed = 0

    for source in sorted(input_dir.glob("*.md")):
        expected = expected_dir / f"{source.stem}.html"
        if not expected.exists():
            LOGGER.error("Missing expected fixture for %s", source.name)
            failures += 1
            continue

        processed += 1
        if not _validate_pair(converter, source, expected):
            failures += 1

    if processed == 0:
        LOGGER.error("No Markdown fixtures discovered in %s", input_dir)
        return 1

    LOGGER.info("Formatting validation complete: %s checked, %s failed", processed, failures)
    return 0 if failures == 0 else 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
