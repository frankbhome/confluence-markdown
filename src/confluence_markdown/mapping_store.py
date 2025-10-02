# Copyright (c) 2025 Francis Bain
# SPDX-License-Identifier: Apache-2.0

"""Mapping store for confluence-markdown tool.

This module manages the storage and retrieval of mappings between Markdown files
and Confluence pages using a JSON file store at .cmt/map.json.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, TypedDict


class MappingEntry(TypedDict, total=False):
    """Type definition for a mapping entry."""

    page_id: str
    space_key: str
    title: str


class MappingStore:
    """Manages mappings between Markdown files and Confluence pages."""

    def __init__(self, mapping_file: Optional[Path] = None):
        """Initialize the mapping store.

        Args:
            mapping_file: Path to the mapping file (defaults to .cmt/map.json)
        """
        self.logger = logging.getLogger(__name__)

        if mapping_file is None:
            # Find the repository root by looking for .git directory
            current_dir = Path.cwd()
            while current_dir != current_dir.parent:
                if (current_dir / ".git").exists():
                    break
                current_dir = current_dir.parent
            else:
                # Fallback to current directory if no .git found
                current_dir = Path.cwd()

            self.mapping_file = current_dir / ".cmt" / "map.json"
        else:
            self.mapping_file = mapping_file

        self.logger.debug(f"Using mapping file: {self.mapping_file}")

    def _ensure_directory_exists(self) -> None:
        """Ensure the .cmt directory exists."""
        self.mapping_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_mappings(self) -> Dict[str, MappingEntry]:
        """Load mappings from the JSON file.

        Returns:
            Dictionary of path -> mapping entry
        """
        if not self.mapping_file.exists():
            return {}

        try:
            with open(self.mapping_file, encoding="utf-8") as f:
                data = json.load(f)

            # Validate the loaded data
            if not isinstance(data, dict):
                self.logger.warning("Invalid mapping file format, starting fresh")
                return {}

            return data

        except (json.JSONDecodeError, OSError) as e:
            self.logger.warning(f"Failed to load mappings: {e}, starting fresh")
            return {}

    def _save_mappings(self, mappings: Dict[str, MappingEntry]) -> None:
        """Save mappings to the JSON file.

        Args:
            mappings: Dictionary of mappings to save
        """
        self._ensure_directory_exists()

        try:
            with open(self.mapping_file, "w", encoding="utf-8") as f:
                json.dump(mappings, f, indent=2, ensure_ascii=False)

        except OSError as e:
            raise RuntimeError(f"Failed to save mappings: {e}") from e

    def _normalize_path(self, path: str) -> str:
        """Normalize a path to canonical repository-relative form.

        Resolves dot segments, makes paths repository-relative, converts to forward slashes,
        and strips leading "./" or "/" to ensure consistent path keys.

        Args:
            path: The path to normalize

        Returns:
            Canonical repository-relative path string
        """
        try:
            # Convert to Path object and resolve dot segments
            path_obj = Path(path)

            # Try to resolve the path (may not exist yet)
            try:
                resolved_path = path_obj.resolve()
            except (OSError, RuntimeError):
                # If resolve fails, fall back to absolute path
                # Python 3.9 doesn't support resolve(strict=False)
                resolved_path = path_obj.absolute()

            # Get repository root (where .git directory is or current working directory)
            repo_root = self._get_repository_root()

            # Make path relative to repository root
            try:
                relative_path = resolved_path.relative_to(repo_root)
            except ValueError:
                # Path is outside repo, use as-is but still normalize
                relative_path = path_obj

            # Convert to POSIX (forward slashes) and strip leading "./" or "/"
            normalized = relative_path.as_posix()
            normalized = normalized.lstrip("./")
            normalized = normalized.lstrip("/")

            return normalized

        except Exception:
            # Fallback to simple normalization if anything fails
            return str(Path(path)).replace("\\", "/").lstrip("./").lstrip("/")

    def _get_repository_root(self) -> Path:
        """Get the repository root directory.

        Returns:
            Path to the repository root (where .git exists) or current directory
        """
        current_dir = Path.cwd()
        while current_dir != current_dir.parent:
            if (current_dir / ".git").exists():
                return current_dir
            current_dir = current_dir.parent
        # Fallback to current directory if no .git found
        return Path.cwd()

    def add_mapping(
        self,
        path: str,
        page_id: Optional[str] = None,
        space_key: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add or update a mapping between a file and Confluence page.

        Args:
            path: Path to the Markdown file
            page_id: Confluence page ID (optional)
            space_key: Confluence space key (optional)
            title: Page title (optional)

        Returns:
            Dictionary with 'created' boolean and 'mapping' entry

        Raises:
            ValueError: If invalid parameters are provided
        """
        # Validate parameters
        if not page_id and not (space_key and title):
            raise ValueError("Either page_id or both space_key and title must be provided")

        if page_id and title:
            raise ValueError("Cannot provide both page_id and title")

        # Normalize path to canonical repository-relative form
        normalized_path = self._normalize_path(path)

        # Load current mappings
        mappings = self._load_mappings()

        # Check if this path already exists
        existing_entry = mappings.get(normalized_path)
        created = existing_entry is None

        # Create the new mapping entry
        entry: MappingEntry = {}
        if page_id:
            entry["page_id"] = page_id
        if space_key:
            entry["space_key"] = space_key
        if title:
            entry["title"] = title

        # Check for conflicts with existing mappings
        for existing_path, existing_mapping in mappings.items():
            if existing_path == normalized_path:
                continue  # Skip self

            # Check for page_id conflicts
            if page_id and existing_mapping.get("page_id") == page_id:
                raise ValueError(f"Page ID '{page_id}' is already mapped to '{existing_path}'")

            # Check for space+title conflicts
            if (
                space_key
                and title
                and existing_mapping.get("space_key") == space_key
                and existing_mapping.get("title") == title
            ):
                raise ValueError(
                    f"Space '{space_key}' + title '{title}' is already mapped to '{existing_path}'"
                )

        # Update mappings
        mappings[normalized_path] = entry

        # Save to file
        self._save_mappings(mappings)

        self.logger.info(f"{'Created' if created else 'Updated'} mapping: {normalized_path}")

        return {"created": created, "mapping": entry}

    def get_mapping(self, path: str) -> Optional[MappingEntry]:
        """Get the mapping for a specific file path.

        Args:
            path: Path to the Markdown file

        Returns:
            Mapping entry if found, None otherwise
        """
        normalized_path = self._normalize_path(path)
        mappings = self._load_mappings()
        return mappings.get(normalized_path)

    def list_mappings(self) -> Dict[str, MappingEntry]:
        """List all current mappings.

        Returns:
            Dictionary of all mappings
        """
        return self._load_mappings()

    def remove_mapping(self, path: str) -> bool:
        """Remove a mapping for a specific file path.

        Args:
            path: Path to the Markdown file

        Returns:
            True if mapping was removed, False if it didn't exist
        """
        normalized_path = self._normalize_path(path)
        mappings = self._load_mappings()

        if normalized_path in mappings:
            del mappings[normalized_path]
            self._save_mappings(mappings)
            self.logger.info(f"Removed mapping: {normalized_path}")
            return True

        return False
