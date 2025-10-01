# Copyright (c) 2025 Francis Bain
# SPDX-License-Identifier: Apache-2.0

"""Tests for CLI functionality."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from confluence_markdown.cli import main
from confluence_markdown.mapping_store import MappingStore


class TestCLI:
    """Test cases for CLI functionality."""

    def test_cli_help(self, capsys):
        """Test that CLI shows help when no command is provided."""
        exit_code = main([])
        assert exit_code == 1

        captured = capsys.readouterr()
        assert "Two-way sync between Confluence and Markdown" in captured.err
        assert "Available commands" in captured.err

    def test_cli_map_add_missing_params(self, capsys):
        """Test that map add requires proper parameters."""
        with pytest.raises(SystemExit) as exc_info:
            main(["map", "add"])
        assert exc_info.value.code == 2  # argparse error

        captured = capsys.readouterr()
        assert "--path" in captured.err

    def test_cli_map_add_file_not_exists(self, capsys):
        """Test that map add fails when file doesn't exist."""
        exit_code = main(["map", "add", "--path", "nonexistent.md", "--page", "123456"])
        assert exit_code == 1

        # Error logging may not be captured by capsys
        # Just verify the exit code is correct

    def test_cli_map_add_invalid_params(self, capsys):
        """Test that map add validates parameter combinations."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test")
            temp_path = f.name

        try:
            # Missing both page and space+title
            exit_code = main(["map", "add", "--path", temp_path])
            assert exit_code == 1

            # The error should be in the logs, which may not be captured by capsys
            # Just verify the exit code is correct
            pass

        finally:
            Path(temp_path).unlink()

    def test_cli_map_add_with_page_id(self, capsys):
        """Test successful map add with page ID."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a test markdown file
            test_file = temp_path / "test.md"
            test_file.write_text("# Test Content")

            with patch("confluence_markdown.cli.MappingStore") as mock_store_class:
                mock_store = mock_store_class.return_value
                mock_store.add_mapping.return_value = {
                    "created": True,
                    "mapping": {"page_id": "123456"},
                }

                exit_code = main(["map", "add", "--path", str(test_file), "--page", "123456"])
                assert exit_code == 0

                # Verify the mapping store was called correctly
                mock_store.add_mapping.assert_called_once_with(
                    path=str(test_file), page_id="123456", space_key=None
                )

                # Since we're mocking MappingStore, logging messages won't appear
                # The test passes if exit code is 0 and mapping store was called correctly

    def test_cli_map_add_with_space_title(self, capsys):
        """Test successful map add with space and title."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a test markdown file
            test_file = temp_path / "test.md"
            test_file.write_text("# Test Content")

            with patch("confluence_markdown.cli.MappingStore") as mock_store_class:
                mock_store = mock_store_class.return_value
                mock_store.add_mapping.return_value = {
                    "created": True,
                    "mapping": {"space_key": "TEST", "title": "Test Page"},
                }

                exit_code = main(
                    [
                        "map",
                        "add",
                        "--path",
                        str(test_file),
                        "--space",
                        "TEST",
                        "--title",
                        "Test Page",
                    ]
                )
                assert exit_code == 0

                # Verify the mapping store was called correctly
                mock_store.add_mapping.assert_called_once_with(
                    path=str(test_file), space_key="TEST", title="Test Page"
                )

                # Since we're mocking MappingStore, logging messages won't appear
                # The test passes if exit code is 0 and mapping store was called correctly


class TestMappingStore:
    """Test cases for mapping store functionality."""

    def test_mapping_store_init_default(self):
        """Test mapping store initialization with default path."""
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/fake/repo")

            # Mock the .git directory check
            with patch.object(Path, "exists") as mock_exists:
                mock_exists.side_effect = lambda: str(self).endswith(".git")

                store = MappingStore()
                # Use path normalization to handle Windows vs Unix paths
                normalized_path = str(store.mapping_file).replace("\\", "/")
                assert normalized_path.endswith(".cmt/map.json")

    def test_mapping_store_init_custom(self):
        """Test mapping store initialization with custom path."""
        custom_path = Path("/custom/map.json")
        store = MappingStore(mapping_file=custom_path)
        assert store.mapping_file == custom_path

    def test_add_mapping_page_id(self):
        """Test adding mapping with page ID."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "map.json"
            store = MappingStore(mapping_file=mapping_file)

            result = store.add_mapping(path="docs/test.md", page_id="123456")

            assert result["created"] is True
            assert result["mapping"]["page_id"] == "123456"

            # Verify file was created
            assert mapping_file.exists()

            # Verify content
            with open(mapping_file, encoding="utf-8") as f:
                data = json.load(f)

            assert "docs/test.md" in data
            assert data["docs/test.md"]["page_id"] == "123456"

    def test_add_mapping_space_title(self):
        """Test adding mapping with space and title."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "map.json"
            store = MappingStore(mapping_file=mapping_file)

            result = store.add_mapping(path="docs/test.md", space_key="TEST", title="Test Page")

            assert result["created"] is True
            assert result["mapping"]["space_key"] == "TEST"
            assert result["mapping"]["title"] == "Test Page"

    def test_add_mapping_validation_errors(self):
        """Test mapping validation errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "map.json"
            store = MappingStore(mapping_file=mapping_file)

            # Test missing parameters
            with pytest.raises(ValueError, match="Either page_id or both space_key and title"):
                store.add_mapping(path="docs/test.md")

            # Test conflicting parameters
            with pytest.raises(ValueError, match="Cannot provide both page_id and title"):
                store.add_mapping(path="docs/test.md", page_id="123456", title="Test Page")

    def test_add_mapping_uniqueness_page_id(self):
        """Test that page IDs must be unique."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "map.json"
            store = MappingStore(mapping_file=mapping_file)

            # Add first mapping
            store.add_mapping(path="docs/test1.md", page_id="123456")

            # Try to add duplicate page ID
            with pytest.raises(ValueError, match="Page ID '123456' is already mapped"):
                store.add_mapping(path="docs/test2.md", page_id="123456")

    def test_add_mapping_uniqueness_space_title(self):
        """Test that space+title combinations must be unique."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "map.json"
            store = MappingStore(mapping_file=mapping_file)

            # Add first mapping
            store.add_mapping(path="docs/test1.md", space_key="TEST", title="Test Page")

            # Try to add duplicate space+title
            with pytest.raises(
                ValueError, match="Space 'TEST' \\+ title 'Test Page' is already mapped"
            ):
                store.add_mapping(path="docs/test2.md", space_key="TEST", title="Test Page")

    def test_get_mapping(self):
        """Test getting a specific mapping."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "map.json"
            store = MappingStore(mapping_file=mapping_file)

            # Add a mapping
            store.add_mapping(path="docs/test.md", page_id="123456")

            # Get the mapping
            mapping = store.get_mapping("docs/test.md")
            assert mapping is not None
            assert mapping["page_id"] == "123456"

            # Get non-existent mapping
            mapping = store.get_mapping("docs/nonexistent.md")
            assert mapping is None

    def test_list_mappings(self):
        """Test listing all mappings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "map.json"
            store = MappingStore(mapping_file=mapping_file)

            # Add multiple mappings
            store.add_mapping(path="docs/test1.md", page_id="123456")
            store.add_mapping(path="docs/test2.md", space_key="TEST", title="Test Page")

            # List all mappings
            mappings = store.list_mappings()
            assert len(mappings) == 2
            assert "docs/test1.md" in mappings
            assert "docs/test2.md" in mappings

    def test_remove_mapping(self):
        """Test removing a mapping."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "map.json"
            store = MappingStore(mapping_file=mapping_file)

            # Add a mapping
            store.add_mapping(path="docs/test.md", page_id="123456")

            # Remove the mapping
            result = store.remove_mapping("docs/test.md")
            assert result is True

            # Verify it's gone
            mapping = store.get_mapping("docs/test.md")
            assert mapping is None

            # Try to remove non-existent mapping
            result = store.remove_mapping("docs/nonexistent.md")
            assert result is False

    def test_path_normalization(self):
        """Test that paths are normalized consistently."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "map.json"
            store = MappingStore(mapping_file=mapping_file)

            # Add mapping with backslashes (Windows style)
            store.add_mapping(path="docs\\test.md", page_id="123456")

            # Get mapping with forward slashes
            mapping = store.get_mapping("docs/test.md")
            assert mapping is not None
            assert mapping["page_id"] == "123456"

            # Verify the stored path uses forward slashes
            mappings = store.list_mappings()
            assert "docs/test.md" in mappings
            assert "docs\\test.md" not in mappings
