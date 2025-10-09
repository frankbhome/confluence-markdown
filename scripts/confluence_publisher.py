#!/usr/bin/env python3
"""Interactive Confluence Publisher - Enhanced development tool for publishing markdown to Confluence.

This script provides an interactive interface to publish all repository markdown files
to your Confluence space as documentation pages with enhanced error handling and progress tracking.
"""

import argparse
import getpass
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from scripts.common import create_page_title, find_repository_root

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from confluence_markdown.confluence_api import ConfluenceClient, NotFoundError
from confluence_markdown.converter import MarkdownToConfluenceConverter

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ConfluencePublisher:
    """Enhanced Confluence publisher with interactive features and robust error handling."""

    def __init__(self, base_url: str, space_key: str, parent_page_id: str):
        """Initialize the publisher with Confluence connection details."""
        self.base_url = base_url
        self.space_key = space_key
        self.parent_page_id = parent_page_id
        self.client: Optional[ConfluenceClient] = None
        self.converter = MarkdownToConfluenceConverter()
        self.repo_root = find_repository_root(Path(__file__).resolve().parent)

    def setup_credentials(self, email: str = None, token: str = None) -> bool:
        """Setup Confluence credentials either from parameters or interactive input."""
        if not email or not token:
            email, token = self._get_interactive_credentials()

        try:
            self.client = ConfluenceClient(base_url=self.base_url, email=email, token=token)
            return self._test_connection()
        except Exception as e:
            logger.error(f"Failed to setup credentials: {e}")
            return False

    def _get_interactive_credentials(self) -> Tuple[str, str]:
        """Get Confluence credentials from user input."""
        print("🔐 Confluence Credentials Setup")
        print("=" * 50)

        email = input("Enter your Confluence email: ").strip()
        if not email:
            logger.error("Email is required")
            sys.exit(1)

        print("\n📖 API Token Instructions:")
        print("   1. Go to https://id.atlassian.com/manage-profile/security/api-tokens")
        print("   2. Click 'Create API token'")
        print("   3. Give it a label like 'Confluence Markdown'")
        print("   4. Copy the token and paste it below")
        print()

        token = getpass.getpass("Enter your API token (hidden input): ").strip()
        if not token:
            logger.error("API token is required")
            sys.exit(1)

        return email, token

    def _test_connection(self) -> bool:
        """Test the Confluence connection."""
        print("\n🔗 Testing connection...")
        try:
            parent_page = self.client.get_page_by_id(self.parent_page_id)
            print(f"✅ Connected to: {parent_page.title}")
            print(f"   Space: {parent_page.space_key}")
            print(f"   Page ID: {parent_page.id}")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print("Please check your credentials and try again.")
            return False

    def find_markdown_files(self, include_patterns: List[str] = None) -> List[Path]:
        """Find all markdown files in the repository with optional include patterns."""
        repo_root = self.repo_root
        markdown_files = []

        # Default exclude patterns
        exclude_patterns = [
            "tests/golden_corpus/**",  # Test files
            ".git/**",  # Git metadata
            "htmlcov/**",  # Coverage reports
            ".venv/**",  # Virtual environment
            "venv/**",  # Alternative venv name
            ".pytest_cache/**",  # Pytest cache
            "**/.pytest_cache/**",  # Pytest cache in subdirs
            "**/node_modules/**",  # Node modules
            "**/__pycache__/**",  # Python cache
            "**/.tox/**",  # Tox environments
            "**/build/**",  # Build directories
            "**/dist/**",  # Distribution directories
        ]

        for md_file in repo_root.rglob("*.md"):
            relative_path = md_file.relative_to(repo_root)

            # Check exclusion patterns
            should_exclude = any(relative_path.match(pattern) for pattern in exclude_patterns)

            # Check inclusion patterns if specified
            should_include = True
            if include_patterns:
                should_include = any(relative_path.match(pattern) for pattern in include_patterns)

            if not should_exclude and should_include:
                markdown_files.append(md_file)

        return sorted(markdown_files)

    def publish_files(self, markdown_files: List[Path], dry_run: bool = False) -> Tuple[int, int]:
        """Publish markdown files to Confluence."""
        if not self.client:
            raise RuntimeError("Client not initialized. Call setup_credentials() first.")

        success_count = 0
        error_count = 0

        print(f"\n📤 {'Previewing' if dry_run else 'Publishing'} {len(markdown_files)} files...")

        for i, md_file in enumerate(markdown_files, 1):
            try:
                relative_path = md_file.relative_to(self.repo_root)
                print(f"\n[{i}/{len(markdown_files)}] 📝 {relative_path}")

                # Create page title
                page_title = create_page_title(md_file, repo_root=self.repo_root)

                if dry_run:
                    print(f"   📋 Would create/update: '{page_title}'")
                    success_count += 1
                    continue

                # Convert markdown to Confluence format
                with open(md_file, encoding="utf-8") as f:
                    markdown_content = f.read()
                confluence_html = self.converter.convert(markdown_content)

                # Check if page already exists and publish
                try:
                    existing_page = self.client.get_page_by_title(
                        space_key=self.space_key, title=page_title
                    )
                except NotFoundError:
                    existing_page = None
                except Exception as lookup_error:
                    logger.error("Failed to look up page '%s': %s", page_title, lookup_error)
                    raise

                if existing_page:
                    self.client.update_page(
                        page_id=existing_page.id,
                        html_storage=confluence_html,
                        title=page_title,
                    )
                    print(f"   ✅ Updated: {page_title}")
                else:
                    self.client.create_page(
                        space_key=self.space_key,
                        title=page_title,
                        html_storage=confluence_html,
                        parent_id=self.parent_page_id,
                        labels=["documentation", "confluence-markdown", "auto-generated"],
                    )
                    print(f"   ✅ Created: {page_title}")

                success_count += 1

            except Exception as e:
                print(f"   ❌ Failed: {e}")
                logger.exception(f"Failed to process {relative_path}")
                error_count += 1

        return success_count, error_count

    def print_summary(self, success_count: int, error_count: int, dry_run: bool = False):
        """Print publishing summary."""
        print(f"\n🎉 {'Preview' if dry_run else 'Publishing'} complete!")
        print(
            f"✅ Successfully {'would process' if dry_run else 'processed'}: {success_count} files"
        )
        if error_count > 0:
            print(f"❌ Failed: {error_count} files")

        if not dry_run:
            print("\n📖 View your documentation at:")
            print(f"   {self.base_url}/spaces/{self.space_key}/pages/{self.parent_page_id}/")


def setup_argument_parser() -> argparse.ArgumentParser:
    """Setup command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Interactive Confluence Publisher for markdown documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (default)
  python confluence_publisher.py

  # Non-interactive with environment variables
  python confluence_publisher.py --non-interactive

  # Dry run to preview what would be published
  python confluence_publisher.py --dry-run

  # Include only specific file patterns
  python confluence_publisher.py --include "README.md" "docs/**/*.md"

Environment Variables:
  CMT_CONF_BASE_URL    - Confluence base URL
  CMT_CONF_EMAIL       - Confluence email
  CMT_CONF_TOKEN       - Confluence API token
  CMT_CONF_SPACE       - Confluence space key
  CMT_CONF_PARENT_ID   - Parent page ID
        """,
    )

    parser.add_argument(
        "--non-interactive",
        "-n",
        action="store_true",
        help="Use environment variables instead of interactive input",
    )

    parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Preview what would be published without actually publishing",
    )

    parser.add_argument(
        "--include", "-i", nargs="*", help="Include only files matching these glob patterns"
    )

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

    parser.add_argument("--parent-page-id", "-p", required=True, help="Parent page ID (required)")

    return parser


def main():
    """Main function to run the Confluence publisher."""
    parser = setup_argument_parser()
    args = parser.parse_args()

    print("🚀 Confluence-Markdown Documentation Publisher")
    print("=" * 60)

    # Initialize publisher
    publisher = ConfluencePublisher(
        base_url=args.base_url, space_key=args.space_key, parent_page_id=args.parent_page_id
    )

    # Setup credentials
    if args.non_interactive:
        email = os.getenv("CMT_CONF_EMAIL")
        token = os.getenv("CMT_CONF_TOKEN")

        if not email or not token:
            print("❌ Missing required environment variables for non-interactive mode:")
            print("   CMT_CONF_EMAIL and CMT_CONF_TOKEN are required")
            sys.exit(1)

        success = publisher.setup_credentials(email, token)
    else:
        success = publisher.setup_credentials()

    if not success:
        sys.exit(1)

    # Find markdown files
    markdown_files = publisher.find_markdown_files(args.include)

    if not markdown_files:
        print("❌ No markdown files found matching the criteria")
        sys.exit(1)

    print(f"\n📄 Found {len(markdown_files)} markdown files:")
    repo_root = Path(__file__).parent.parent
    for i, md_file in enumerate(markdown_files[:5], 1):
        relative_path = md_file.relative_to(repo_root)
        print(f"   {i}. {relative_path}")
    if len(markdown_files) > 5:
        print(f"   ... and {len(markdown_files) - 5} more")

    # Confirm before proceeding (unless dry run or non-interactive)
    if not args.dry_run and not args.non_interactive:
        print()
        confirm = input("Publish all these files to Confluence? (y/N): ").strip().lower()
        if confirm != "y":
            print("❌ Cancelled by user")
            sys.exit(0)

    # Publish files
    success_count, error_count = publisher.publish_files(markdown_files, args.dry_run)

    # Print summary
    publisher.print_summary(success_count, error_count, args.dry_run)

    # Exit with appropriate code
    sys.exit(0 if error_count == 0 else 1)


if __name__ == "__main__":
    main()
