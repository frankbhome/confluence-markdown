"""Smoke tests for the confluence-markdown package.

This module contains smoke tests to verify that the package
is properly installed and core functionality works correctly.
"""

import subprocess
import sys
import os
from unittest.mock import patch


def test_smoke():
    """Basic smoke test that always passes.

    This test serves as a minimal validation that the testing
    framework is working correctly and the package structure
    is intact.
    """
    assert True


def test_package_main_entry_point():
    """Test that the package main module can be executed."""
    # Test by running the module directly via subprocess
    src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")

    result = subprocess.run(
        [sys.executable, "-m", "confluence_markdown"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": src_path},
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

    # Should exit successfully and print the expected message
    assert result.returncode == 0
    assert "confluence-markdown OK" in result.stdout


def test_cli_help_message():
    """Test that the CLI script shows help when called incorrectly."""
    script_path = os.path.join("scripts", "publish_release.py")

    # Test with no arguments (should show usage and exit with code 1)
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
        if key.startswith('CONFLUENCE_'):
            del env[key]

    result = subprocess.run(
        [sys.executable, script_path, "v1.0.0", "Test release notes"],
        capture_output=True,
        text=True,
        env=env,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

    assert result.returncode == 1
    assert "Configuration error" in result.stdout
    assert "Required environment variables" in result.stdout
    assert "CONFLUENCE_URL" in result.stdout


def test_confluence_publisher_import():
    """Test that ConfluencePublisher can be imported and basic functionality works."""
    # Add the scripts directory to path for import
    import sys
    import os
    scripts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
    sys.path.insert(0, scripts_path)

    try:
        # Import using importlib to avoid static analysis issues
        import importlib.util
        spec = importlib.util.spec_from_file_location("publish_release",
                                                     os.path.join(scripts_path, "publish_release.py"))
        if spec is None or spec.loader is None:
            assert False, "Could not load publish_release module"

        publish_release = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(publish_release)

        ConfluencePublisher = publish_release.ConfluencePublisher

        # Test that we can import the class
        assert ConfluencePublisher is not None

        # Test markdown conversion functionality without requiring Confluence config
        with patch.dict(os.environ, {
            'CONFLUENCE_URL': 'https://test.atlassian.net/wiki',
            'CONFLUENCE_USER': 'test@example.com',
            'CONFLUENCE_TOKEN': 'test_token',
            'CONFLUENCE_SPACE': 'TEST'
        }):
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
        assert False, f"ConfluencePublisher basic functionality failed: {e}"
    finally:
        # Clean up path
        if scripts_path in sys.path:
            sys.path.remove(scripts_path)
