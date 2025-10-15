# Copyright (c) 2025 Francis Bain
# SPDX-License-Identifier: Apache-2.0

"""Smoke tests for the confluence-markdown package.

This module contains smoke tests to verify that the package
is properly installed and core functionality works correctly.
"""

import os
import subprocess
import sys
from unittest.mock import patch


def test_smoke():
    """Basic smoke test that always passes.

    This test serves as a minimal validation that the testing
    framework is working correctly and the package structure
    is intact.
    """
    assert True


def test_main_function_direct_call():
    """Test that the main function can be called directly and shows help."""
    import sys
    from io import StringIO
    from unittest.mock import patch

    from confluence_markdown.__main__ import main

    # The main function now uses CLI, so it will show help and exit with code 1
    with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
        with patch.object(sys, "argv", ["conmd"]):  # Mock argv to avoid pytest args
            try:
                main()
            except SystemExit as e:
                # CLI exits with code 1 when no command is provided
                assert e.code == 1

            output = mock_stderr.getvalue()

    assert "Two-way sync between Confluence and Markdown" in output


def test_main_module_if_name_main():
    """Test the if __name__ == '__main__' execution path."""
    import runpy
    import sys
    from io import StringIO
    from unittest.mock import patch

    # The CLI now shows help when no command is provided
    with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
        # Mock sys.argv to simulate command line execution
        with patch.object(sys, "argv", ["confluence_markdown.__main__"]):
            # Remove cached module so run_module executes cleanly without runtime warnings.
            sys.modules.pop("confluence_markdown.__main__", None)
            try:
                # Use runpy to execute the module as if it was run with python -m
                runpy.run_module("confluence_markdown.__main__", run_name="__main__")
            except SystemExit:
                # runpy might call sys.exit, which is normal for CLI tools
                pass

        output = mock_stderr.getvalue()

    assert (
        "Two-way sync between Confluence and Markdown" in output or "Available commands" in output
    )


def test_package_main_entry_point():
    """Test that the package main module can be executed."""
    # Test by running the module directly via subprocess
    src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")

    result = subprocess.run(
        [sys.executable, "-m", "confluence_markdown"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": src_path},
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )

    # CLI now exits with code 1 when no command is provided and shows help
    assert result.returncode == 1
    assert (
        "Two-way sync between Confluence and Markdown" in result.stderr
        or "Available commands" in result.stderr
    )


def test_cli_help_message():
    """Test that the CLI script shows help when called incorrectly."""
    script_path = os.path.join("scripts", "publish_release.py")

    # Test with no arguments (should show usage and exit with code 1)
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )

    assert result.returncode == 1
    assert "Usage: publish_release.py <version> <release_notes>" in result.stdout
    assert "Example: publish_release.py v1.0.0" in result.stdout


def test_cli_configuration_validation():
    """Test that CLI validates required configuration."""
    script_path = os.path.join("scripts", "publish_release.py")

    # Test with arguments but no environment configuration
    # Should fail with configuration error
    env = os.environ.copy()
    # Clear confluence environment variables to force configuration error
    for key in list(env.keys()):
        if key.startswith("CONFLUENCE_"):
            del env[key]

    result = subprocess.run(
        [sys.executable, script_path, "v1.0.0", "Test release notes"],
        capture_output=True,
        text=True,
        env=env,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )

    assert result.returncode == 1
    assert "Configuration error" in result.stdout
    assert "Required environment variables" in result.stdout
    assert "CONFLUENCE_URL" in result.stdout


def test_confluence_publisher_import():
    """Test that ConfluencePublisher can be imported and basic functionality works."""
    # Add the scripts directory to path for import
    import os
    import sys

    scripts_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"
    )
    sys.path.insert(0, scripts_path)

    try:
        # Import using importlib to avoid static analysis issues
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "publish_release", os.path.join(scripts_path, "publish_release.py")
        )
        if spec is None or spec.loader is None:
            raise AssertionError("Could not load publish_release module")

        publish_release = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(publish_release)

        ConfluencePublisher = publish_release.ConfluencePublisher

        # Test that we can import the class
        assert ConfluencePublisher is not None

        # Test markdown conversion functionality without requiring Confluence config
        with patch.dict(
            os.environ,
            {
                "CONFLUENCE_URL": "https://test.atlassian.net/wiki",
                "CONFLUENCE_USER": "test@example.com",
                "CONFLUENCE_TOKEN": "test_token",
                "CONFLUENCE_SPACE": "TEST",
            },
        ):
            publisher = ConfluencePublisher()

            # Test basic markdown conversion
            test_markdown = "# Test Header\n\nThis is **bold** text with `code`."
            result = publisher._convert_markdown_to_confluence(test_markdown)

            # Verify basic conversions work
            assert "<h1>Test Header</h1>" in result
            assert "<strong>bold</strong>" in result
            assert "<code>code</code>" in result

        assert True

    except Exception as e:
        raise AssertionError(f"ConfluencePublisher basic functionality failed: {e}") from e
    finally:
        # Clean up path
        if scripts_path in sys.path:
            sys.path.remove(scripts_path)
