#!/usr/bin/env python3
"""Simple script to push core markdown documentation to Confluence."""

import argparse
import getpass
import logging
import sys
from pathlib import Path

# Add src to path for imports (repo root src, not scripts/src)
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent / "src"))

from confluence_markdown.confluence_api import (  # noqa: E402
    ConfluenceAPIError,
    ConfluenceClient,
    NotFoundError,
)
from confluence_markdown.converter import MarkdownToConfluenceConverter  # noqa: E402
from scripts.common import create_page_title, find_repository_root  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_credentials():
    """Get Confluence credentials from user input."""
    print("🔐 Confluence Credentials Setup")
    print("=" * 50)

    email = input("Enter your Confluence email: ").strip()
    if not email:
        print("❌ Email is required")
        sys.exit(1)

    print("\n📖 API Token Instructions:")
    print("   1. Go to https://id.atlassian.com/manage-profile/security/api-tokens")
    print("   2. Click 'Create API token'")
    print("   3. Give it a label like 'Confluence Markdown'")
    print("   4. Copy the token and paste it below")
    print()

    token = getpass.getpass("Enter your API token (hidden input): ").strip()
    if not token:
        print("❌ API token is required")
        sys.exit(1)

    return email, token


def get_core_markdown_files():
    """Get the core markdown documentation files."""
    repo_root = find_repository_root(SCRIPT_DIR)

    # Define the core documentation files we want to push
    core_files = [
        # Root level documentation
        "README.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "DEVELOPMENT.md",
        "RELEASING.md",
        "SECURITY-PIPELINE.md",
        "PUSH-ERROR-HANDLING-IMPLEMENTATION.md",
        # Documentation in docs/ directory
        "docs/confluence-setup.md",
        "docs/conversion-fidelity-testing.md",
        "docs/CI-CD-AUTOMATION.md",
        "docs/SECURITY-PIPELINE-IMPLEMENTATION.md",
        # Architecture Decision Records
        "docs/adr/ADR-001-adopt-atlassian-python-api.md",
        # Examples
        "docs/examples/basic-page.md",
        "docs/examples/design-page.md",
        "docs/examples/requirements-page.md",
    ]

    # Find existing files from the list
    markdown_files = []
    for file_path in core_files:
        full_path = repo_root / file_path
        if full_path.exists():
            markdown_files.append(full_path)
        else:
            print(f"⚠️  File not found: {file_path}")

    return sorted(markdown_files)


def convert_markdown_to_confluence(md_file_path):
    """Convert a markdown file to Confluence storage format."""
    try:
        with open(md_file_path, encoding="utf-8") as f:
            markdown_content = f.read()
    except FileNotFoundError as e:
        msg = f"Markdown file not found: {md_file_path}"
        logger.error("%s: %s", msg, e)
        # Re-raise with context so callers can handle gracefully
        raise FileNotFoundError(msg) from e
    except PermissionError as e:
        msg = f"Permission denied reading markdown file: {md_file_path}"
        logger.error("%s: %s", msg, e)
        # Re-raise with context so callers can handle gracefully
        raise PermissionError(msg) from e
    except Exception as e:  # pragma: no cover - defensive fallback
        # Log full stack trace and re-raise to be handled by caller
        logger.exception("Unexpected error reading markdown file '%s': %s", md_file_path, e)
        raise

    converter = MarkdownToConfluenceConverter()
    confluence_html = converter.convert(markdown_content)
    return confluence_html


def main():
    """Main function to push core markdown files to Confluence."""
    parser = argparse.ArgumentParser(description="Push core markdown documentation to Confluence.")
    parser.add_argument(
        "--base-url",
        required=True,
        help="Confluence base URL (required)",
    )
    parser.add_argument(
        "--space-key",
        required=True,
        help="Confluence space key (required)",
    )
    parser.add_argument(
        "--parent-page-id",
        required=True,
        help="Parent page ID (required)",
    )
    args = parser.parse_args()

    print("🚀 Confluence-Markdown Documentation Publisher")
    print("=" * 60)
    print()

    # Get credentials
    email, token = get_credentials()

    # Setup Confluence client
    base_url = args.base_url
    space_key = args.space_key
    parent_page_id = args.parent_page_id

    if not base_url:
        print("❌ BASE_URL (or --base-url) is required.")
        sys.exit(1)
    if not space_key:
        print("❌ CONFLUENCE_SPACE_KEY (or --space-key) is required.")
        sys.exit(1)
    if not parent_page_id:
        print("❌ PARENT_PAGE_ID (or --parent-page-id) is required.")
        sys.exit(1)

    client = ConfluenceClient(base_url=base_url, email=email, token=token)

    # Test connection
    print("\n🔗 Testing connection...")
    try:
        parent_page = client.get_page_by_id(parent_page_id)
        print(f"✅ Connected to: {parent_page.title}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("Please check your credentials and try again.")
        sys.exit(1)

    # Find core markdown files
    repo_root = find_repository_root(SCRIPT_DIR)
    markdown_files = get_core_markdown_files()

    print(f"\n📄 Found {len(markdown_files)} core documentation files:")
    for i, md_file in enumerate(markdown_files, 1):
        relative_path = md_file.relative_to(repo_root)
        print(f"   {i}. {relative_path}")

    # Confirm before proceeding
    print()
    print("You can override connection details with environment variables or CLI flags:")
    print("  BASE_URL, CONFLUENCE_SPACE_KEY, PARENT_PAGE_ID")
    print("  --base-url, --space-key, --parent-page-id")
    confirm = input("Push these files to Confluence? (y/N): ").strip().lower()
    if confirm != "y":
        print("❌ Cancelled by user")
        sys.exit(0)

    # Push each file
    print(f"\n📤 Pushing {len(markdown_files)} files...")
    success_count = 0
    error_count = 0

    for i, md_file in enumerate(markdown_files, 1):
        try:
            relative_path = md_file.relative_to(repo_root)
            print(f"\n[{i}/{len(markdown_files)}] 📝 {relative_path}")

            # Convert markdown to Confluence format
            confluence_html = convert_markdown_to_confluence(md_file)

            # Create page title
            page_title = create_page_title(md_file, repo_root=repo_root)

            try:
                existing_page = client.get_page_by_title(space_key=space_key, title=page_title)
            except NotFoundError:
                existing_page = None
            except ConfluenceAPIError as exc:  # pragma: no cover - defensive log path
                logger.exception("Failed to look up page '%s': %s", page_title, exc)
                raise

            if existing_page:
                client.update_page(
                    page_id=existing_page.id,
                    html_storage=confluence_html,
                    title=page_title,
                    parent_id=parent_page_id,
                )
                print(f"   ✅ Updated: {page_title}")
            else:
                client.create_page(
                    space_key=space_key,
                    title=page_title,
                    html_storage=confluence_html,
                    parent_id=parent_page_id,
                    labels=["documentation", "confluence-markdown", "auto-generated"],
                )
                print(f"   ✅ Created: {page_title}")

            success_count += 1

        except Exception as e:
            print(f"   ❌ Failed: {e}")
            logger.exception(f"Failed to process {relative_path}")
            error_count += 1

    # Summary
    print("\n🎉 Push complete!")
    print(f"✅ Successfully pushed: {success_count} files")
    if error_count > 0:
        print(f"❌ Failed: {error_count} files")

    print("\n📖 View your documentation at:")
    print(f"   {base_url}/spaces/{space_key}/pages/{parent_page_id}/")


if __name__ == "__main__":
    main()
