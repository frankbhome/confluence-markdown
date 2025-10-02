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

    def test_cli_unknown_map_command(self, capsys):
        """Test that unknown map commands show error."""
        # argparse will catch unknown subcommands and raise SystemExit
        with pytest.raises(SystemExit) as exc_info:
            main(["map", "unknown"])
        assert exc_info.value.code == 2  # argparse error

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

    def test_cli_updated_existing_mapping(self):
        """Test CLI updating an existing mapping."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            with patch("confluence_markdown.cli.MappingStore") as mock_store_class:
                mock_store = mock_store_class.return_value
                mock_store.add_mapping.return_value = {
                    "created": False,
                    "mapping": {"page_id": "PAGE123"},
                }

                # Create test file
                test_file = temp_path / "test.md"
                test_file.write_text("# Test")

                exit_code = main(["map", "add", "--page", "PAGE123", "--path", str(test_file)])
                assert exit_code == 0

    def test_cli_page_with_title_conflict(self, caplog):
        """Test CLI rejects --page with --title combination."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test file
            test_file = temp_path / "test.md"
            test_file.write_text("# Test")

            exit_code = main(
                [
                    "map",
                    "add",
                    "--page",
                    "PAGE123",
                    "--title",
                    "Test Page",
                    "--path",
                    str(test_file),
                ]
            )
            assert exit_code == 1
            assert "Cannot use --page with --title" in caplog.text

    def test_cli_map_add_exception_handling(self, capsys):
        """Test map add exception handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a test markdown file
            test_file = temp_path / "test.md"
            test_file.write_text("# Test Content")

            with patch("confluence_markdown.cli.MappingStore") as mock_store_class:
                mock_store = mock_store_class.return_value
                mock_store.add_mapping.side_effect = Exception("Test error")

                exit_code = main(["map", "add", "--path", str(test_file), "--page", "123456"])
                assert exit_code == 1

                # Verify the mapping store was called
                mock_store.add_mapping.assert_called_once()

    def test_cli_missing_path_parameter(self, capsys):
        """Test CLI with missing --path parameter (caught by argparse)."""
        # argparse handles this validation, so expect SystemExit
        with pytest.raises(SystemExit):
            main(["map", "add", "--page", "PAGE123"])

    def test_cli_empty_path_parameter(self, caplog):
        """Test CLI with empty --path parameter."""
        # This will test our validation logic in cmd_map_add (line 47-48)
        exit_code = main(["map", "add", "--page", "PAGE123", "--path", ""])
        assert exit_code == 1
        # Check log output instead of stderr
        assert "--path is required" in caplog.text

    def test_cli_no_command_specified(self, capsys):
        """Test CLI with no command specified."""
        exit_code = main([])
        assert exit_code == 1

    def test_cli_unknown_map_command_fallback(self):
        """Test unknown map command fallback (lines 133-135)."""
        # Mock the parser to simulate reaching the unknown command branch
        from unittest.mock import MagicMock

        with patch("confluence_markdown.cli.create_parser") as mock_create:
            mock_parser = MagicMock()
            mock_create.return_value = mock_parser

            # Create args that would reach the unknown map command branch
            mock_args = MagicMock()
            mock_args.verbose = False
            mock_args.command = "map"
            mock_args.map_command = "unknown_command"  # Not "add"
            mock_parser.parse_args.return_value = mock_args

            result = main(["map", "unknown_command"])
            assert result == 1
            mock_parser.print_help.assert_called_once()

    def test_main_module_direct_execution(self):
        """Test __main__ module execution (line 145)."""
        # Test the __name__ == "__main__" block in cli.py
        import subprocess
        import sys

        # Execute the cli module directly as __main__
        # This will test line 145: if __name__ == "__main__":
        result = subprocess.run(
            [sys.executable, "-m", "confluence_markdown.cli", "--help"],
            capture_output=True,
            text=True,
        )

        # Should exit with 0 for help
        assert result.returncode == 0
        assert "conmd" in result.stdout


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

    def test_mapping_store_no_git_directory(self):
        """Test mapping store initialization when no .git directory is found (line 40)."""
        with patch("pathlib.Path.cwd") as mock_cwd:
            # Set up a fake current working directory
            fake_cwd = Path("/no/git/anywhere")
            mock_cwd.return_value = fake_cwd

            # Mock exists to always return False (no .git directories)
            with patch.object(Path, "exists", return_value=False):
                store = MappingStore()
                # Should fall back to current directory (lines 47-48 are executed)
                normalized_path = str(store.mapping_file).replace("\\", "/")
                assert normalized_path.endswith(".cmt/map.json")
                # The path should be based on the fake current directory
                assert str(fake_cwd).replace("\\", "/") in normalized_path
                # Verify the repo root fallback was set (covers line 48)
                assert store._repo_root == fake_cwd

    def test_load_mappings_invalid_json(self):
        """Test loading mappings with invalid JSON format (lines 71-72)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "map.json"
            # Create invalid JSON file
            mapping_file.write_text("invalid json content", encoding="utf-8")

            store = MappingStore(mapping_file=mapping_file)
            # Should start with empty mappings due to JSON decode error
            mappings = store.list_mappings()
            assert len(mappings) == 0

    def test_load_mappings_invalid_format(self):
        """Test loading mappings with non-dict format (lines 76-78)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "map.json"
            # Create JSON that's not a dict
            mapping_file.write_text('["not", "a", "dict"]', encoding="utf-8")

            store = MappingStore(mapping_file=mapping_file)
            # Should start with empty mappings due to invalid format
            mappings = store.list_mappings()
            assert len(mappings) == 0

    def test_save_mappings_file_error(self):
        """Test save mappings with file system error (lines 92-93)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "map.json"
            store = MappingStore(mapping_file=mapping_file)

            # Mock open to raise an OSError
            with patch("builtins.open", side_effect=OSError("Permission denied")):
                with pytest.raises(RuntimeError, match="Failed to save mappings"):
                    store.add_mapping(path="test.md", page_id="123456")

    def test_add_mapping_page_id_conflict(self):
        """Test adding mapping with conflicting page ID."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "map.json"
            store = MappingStore(mapping_file=mapping_file)

            # Add first mapping
            store.add_mapping(path="docs/test1.md", page_id="CONFLICT123")

            # Try to add second mapping with same page ID
            with pytest.raises(ValueError, match="Page ID 'CONFLICT123' is already mapped"):
                store.add_mapping(path="docs/test2.md", page_id="CONFLICT123")

    def test_add_mapping_space_title_conflict(self):
        """Test adding mapping with conflicting space+title."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "map.json"
            store = MappingStore(mapping_file=mapping_file)

            # Add first mapping
            store.add_mapping(path="docs/test1.md", space_key="TEST", title="Conflict Page")

            # Try to add second mapping with same space+title
            with pytest.raises(
                ValueError, match="Space 'TEST' \\+ title 'Conflict Page' is already mapped"
            ):
                store.add_mapping(path="docs/test2.md", space_key="TEST", title="Conflict Page")

    def test_add_mapping_update_existing(self):
        """Test updating an existing mapping (tests 'skip self' logic line 145)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "map.json"
            store = MappingStore(mapping_file=mapping_file)

            # Add first mapping
            result1 = store.add_mapping(path="docs/test.md", page_id="123456")
            assert result1["created"] is True

            # Update the same mapping (should skip self in conflict check)
            result2 = store.add_mapping(path="docs/test.md", page_id="654321")
            assert result2["created"] is False  # Not created, updated
            assert result2["mapping"]["page_id"] == "654321"

    def test_path_normalization_comprehensive(self):
        """Test comprehensive path normalization with dot segments and different formats."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "map.json"
            store = MappingStore(mapping_file=mapping_file)

            # Test various equivalent path formats
            equivalent_paths = [
                "docs/test.md",
                "./docs/test.md",
                "docs/./test.md",
                "docs/../docs/test.md",
                "docs\\test.md",  # Windows backslashes
            ]

            # Add mapping with first path format
            store.add_mapping(path=equivalent_paths[0], page_id="123456")

            # Test that all equivalent paths resolve to the same normalized key
            # by checking that get_mapping returns the same result for all variants
            for path_variant in equivalent_paths:
                mapping = store.get_mapping(path_variant)
                assert mapping is not None, f"Path variant {path_variant} not found"
                assert (
                    mapping["page_id"] == "123456"
                ), f"Path variant {path_variant} has wrong page_id"

            # Verify only one mapping exists in storage
            mappings = store.list_mappings()
            assert len(mappings) == 1

            # Verify the normalized key doesn't have leading "./" or duplicated segments
            normalized_key = list(mappings.keys())[0]
            assert not normalized_key.startswith("./")
            assert not normalized_key.startswith("/")
            assert "/./" not in normalized_key
            assert "/../" not in normalized_key

            # Test that we can update the mapping using any equivalent path
            result = store.add_mapping(path="./docs/test.md", page_id="654321")
            assert result["created"] is False  # Should be an update
            assert result["mapping"]["page_id"] == "654321"

            # Verify all paths still resolve to the updated mapping
            for path_variant in equivalent_paths:
                mapping = store.get_mapping(path_variant)
                assert mapping["page_id"] == "654321"

    def test_path_resolution_error_handling(self):
        """Test error handling in path resolution methods."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "map.json"
            store = MappingStore(mapping_file=mapping_file)

            # Test path normalization with various edge cases that might trigger error paths
            from unittest.mock import patch

            # Test the fallback normalization when main logic fails
            with patch.object(Path, "resolve", side_effect=OSError("Mock resolve error")):
                # This should trigger the resolve(strict=False) fallback path
                normalized = store._normalize_path("docs/test.md")
                assert isinstance(normalized, str)
                assert "test.md" in normalized

            # Test TypeError path (Python 3.9 compatibility)
            with patch("os.path.realpath") as mock_realpath:
                mock_realpath.return_value = "/resolved/path/docs/test.md"

                # Create a mock that first raises OSError, then TypeError on resolve
                def mock_resolve(*args, **kwargs):
                    if "strict" in kwargs:
                        raise TypeError("No strict parameter")
                    else:
                        raise OSError("Mock resolve error")

                with patch.object(Path, "resolve", side_effect=mock_resolve):
                    # This should trigger the TypeError -> realpath fallback
                    normalized = store._normalize_path("docs/test.md")
                    assert isinstance(normalized, str)
                    mock_realpath.assert_called()

            # Test repository root caching when no custom mapping file is used
            store_default = MappingStore()
            root1 = store_default._get_repository_root()
            root2 = store_default._get_repository_root()
            assert root1 == root2  # Should use cached value
            assert store_default._repo_root is not None

            # Test fallback exception handling in _normalize_path
            with patch.object(store, "_get_repository_root", side_effect=Exception("Mock error")):
                # This should trigger the fallback normalization
                normalized = store._normalize_path("docs\\test.md")
                assert isinstance(normalized, str)
                assert normalized == "docs/test.md"

    def test_advanced_path_resolution_coverage(self):
        """Test advanced path resolution scenarios for complete coverage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "map.json"
            store = MappingStore(mapping_file=mapping_file)

            from unittest.mock import patch

            # Test OSError in second resolve attempt (line 130)
            def mock_resolve(*args, **kwargs):
                if "strict" in kwargs:
                    raise OSError("Mock OSError in resolve(strict=False)")
                else:
                    raise OSError("Mock OSError in resolve()")

            with patch.object(Path, "resolve", side_effect=mock_resolve):
                with patch("os.path.realpath") as mock_realpath:
                    mock_realpath.return_value = "/some/path/docs/test.md"
                    normalized = store._normalize_path("docs/test.md")
                    assert isinstance(normalized, str)
                    mock_realpath.assert_called()

            # Test absolute path outside repository scenario (line 150)
            abs_path = "/completely/different/location/test.md"
            with patch.object(Path, "is_absolute", return_value=True):
                normalized = store._normalize_path(abs_path)
                assert isinstance(normalized, str)

            # Test repository root traversal fallback (lines 179-183)
            with patch("pathlib.Path.cwd") as mock_cwd:
                fake_root = Path("/fake/root")
                mock_cwd.return_value = fake_root

                # Mock a directory structure where we need to traverse up
                def mock_exists(*args, **kwargs):
                    # Simulate that no .git directory exists anywhere in the path
                    return False

                with patch.object(Path, "exists", side_effect=mock_exists):
                    # Create store that will need to traverse and then fallback
                    store_no_git = MappingStore()

                    # Clear cached repo root to force traversal
                    store_no_git._repo_root = None

                    # This should traverse up directories and then fallback (lines 179-183)
                    root = store_no_git._get_repository_root()
                    assert root == fake_root
                    assert store_no_git._repo_root == fake_root

    def test_cli_main_module_execution(self):
        """Test CLI main module execution to cover __name__ == '__main__' block."""
        import subprocess
        import sys

        # Execute the CLI module directly to test the main block
        result = subprocess.run(
            [sys.executable, "-m", "confluence_markdown.cli", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        # Should exit with 0 for help
        assert result.returncode == 0
        assert "usage: conmd" in result.stdout


def test_cli_main_block():
    """Test the if __name__ == '__main__' execution block."""
    import subprocess
    import sys

    # Test running the CLI module directly
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from src.confluence_markdown.cli import main; import sys; sys.exit(main(['--help']))",
        ],
        capture_output=True,
        text=True,
    )

    # Should exit with code 0 for help and contain usage info
    assert result.returncode == 0
    assert "usage: conmd" in result.stdout
