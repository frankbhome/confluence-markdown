"""Shared helpers for development scripts.

This module centralises the plumbing for the development utilities that ship with
confluence-markdown. It handles logging configuration, Confluence client creation,
Markdown conversion, and publication workflows so each script can focus on its
own CLI experience.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Sequence

from confluence_markdown.confluence_api import ConfluenceAPIError, ConfluenceClient
from confluence_markdown.converter import MarkdownToConfluenceConverter
from confluence_markdown.mapping_store import MappingEntry, MappingStore

__all__ = [
    "PublishOutcome",
    "configure_logging",
    "find_repository_root",
    "default_markdown_paths",
    "publish_documents",
    "load_markdown",
    "create_page_title",
]


@dataclass
class PublishOutcome:
    """Summary of a single document publication attempt."""

    path: Path
    action: Literal["created", "updated", "dry-run", "skipped"]
    status: Literal["success", "skipped", "failure"]
    detail: str | None = None


def configure_logging(verbosity: int = 0) -> None:
    """Initialise root logging with a consistent format.

    Args:
        verbosity: Count of ``-v`` flags provided by the user. ``0`` keeps log output
            at ``INFO`` level, while anything higher enables ``DEBUG``.
    """

    level = logging.INFO if verbosity == 0 else logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )


def find_repository_root(start: Path | None = None) -> Path:
    """Locate the repository root by walking upwards until a ``.git`` directory is found."""

    current = start or Path.cwd()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return start or Path.cwd()


def default_markdown_paths(mapping_store: MappingStore) -> List[Path]:
    """Return the set of Markdown paths known to the mapping store as absolute ``Path`` objects."""

    repo_root = find_repository_root()
    return [repo_root / Path(rel_path) for rel_path in mapping_store.list_mappings().keys()]


def load_markdown(path: Path) -> str:
    """Load a Markdown file, normalising newlines."""

    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def create_page_title(path: Path, *, repo_root: Path | None = None) -> str:
    """Derive a human-friendly Confluence page title from ``path``.

    Args:
        path: The Markdown file to derive a title for.
        repo_root: Optional repository root to compute a relative path from. If omitted
            the root is discovered automatically.
    """

    repo_root = repo_root or find_repository_root(path.parent)

    try:
        relative_path = path.resolve().relative_to(repo_root)
    except Exception:
        relative_path = Path(path.name)

    parts = relative_path.parts
    stem = relative_path.stem

    if len(parts) == 1:
        if stem.upper() == stem:
            return stem
        return stem.replace("-", " ").replace("_", " ").title()

    directory_context = " / ".join(parts[:-1])
    title_component = stem.replace("-", " ").replace("_", " ").title()
    return f"{directory_context} / {title_component}"


def _normalise_key(path: Path) -> str:
    """Produce a repository-relative key compatible with :class:`MappingStore`."""

    try:
        repo_root = find_repository_root()
        relative = path.resolve().relative_to(repo_root)
        return relative.as_posix()
    except Exception:
        return path.as_posix().lstrip("./")


def _resolve_mapping(mapping_store: MappingStore, path: Path) -> MappingEntry | None:
    """Look up the mapping entry for ``path`` using multiple canonicalisations."""

    as_posix = path.as_posix()
    mapping = mapping_store.get_mapping(as_posix)
    if mapping:
        return mapping

    resolved_key = _normalise_key(path)
    mapping = mapping_store.get_mapping(resolved_key)
    if mapping:
        return mapping

    # Final attempt with absolute path string – MappingStore handles normalisation internally.
    return mapping_store.get_mapping(str(path.resolve()))


def _publish_single(
    *,
    path: Path,
    mapping: MappingEntry,
    client: ConfluenceClient,
    converter: MarkdownToConfluenceConverter,
    dry_run: bool,
    logger: logging.Logger,
) -> PublishOutcome:
    """Publish a single Markdown document to Confluence."""

    content = load_markdown(path)
    html = converter.convert(content)

    if dry_run:
        logger.info("Dry run: would publish %s", path)
        return PublishOutcome(path=path, action="dry-run", status="success")

    try:
        if mapping.get("page_id"):
            page_id = mapping["page_id"]
            logger.info("Updating page %s from %s", page_id, path)
            client.update_page(page_id=page_id, html_storage=html, title=mapping.get("title"))
            return PublishOutcome(path=path, action="updated", status="success")

        space_key = mapping.get("space_key")
        title = mapping.get("title")
        if not space_key or not title:
            message = "Mapping requires either page_id or (space_key + title)"
            logger.error("%s for %s", message, path)
            return PublishOutcome(path=path, action="skipped", status="failure", detail=message)

        logger.info("Publishing %s to space=%s title=%s", path, space_key, title)
        existing = client.get_page_by_title(space_key=space_key, title=title)
        if existing:
            client.update_page(page_id=existing.id, html_storage=html, title=title)
            return PublishOutcome(path=path, action="updated", status="success")

        client.create_page(space_key=space_key, title=title, html_storage=html)
        return PublishOutcome(path=path, action="created", status="success")

    except ConfluenceAPIError as exc:  # pragma: no cover - defensive logging
        logger.error("Confluence API error for %s: %s", path, exc)
        return PublishOutcome(path=path, action="skipped", status="failure", detail=str(exc))
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Unexpected failure publishing %s", path)
        return PublishOutcome(path=path, action="skipped", status="failure", detail=str(exc))


def publish_documents(
    paths: Sequence[Path | str],
    *,
    mapping_store: MappingStore | None = None,
    client: ConfluenceClient | None = None,
    converter: MarkdownToConfluenceConverter | None = None,
    dry_run: bool = False,
) -> List[PublishOutcome]:
    """Publish the given Markdown documents to Confluence.

    Args:
        paths: Iterable of filesystem paths to Markdown files.
        mapping_store: Optional custom mapping store (useful for testing).
        client: Optional Confluence client instance.
        converter: Optional converter instance.
        dry_run: If ``True`` the script will simulate publishing without API calls.

    Returns:
        List of :class:`PublishOutcome` entries describing the processing results.
    """

    logger = logging.getLogger("scripts.publish")
    mapping_store = mapping_store or MappingStore()
    client = client or ConfluenceClient.from_env()
    converter = converter or MarkdownToConfluenceConverter()

    outcomes: List[PublishOutcome] = []

    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            logger.warning("Skipping %s: file does not exist", path)
            outcomes.append(
                PublishOutcome(
                    path=path,
                    action="skipped",
                    status="skipped",
                    detail="File does not exist",
                )
            )
            continue

        mapping = _resolve_mapping(mapping_store, path)
        if not mapping:
            message = "No mapping found"
            logger.warning("%s for %s", message, path)
            outcomes.append(
                PublishOutcome(path=path, action="skipped", status="skipped", detail=message)
            )
            continue

        outcomes.append(
            _publish_single(
                path=path,
                mapping=mapping,
                client=client,
                converter=converter,
                dry_run=dry_run,
                logger=logger,
            )
        )

    return outcomes
