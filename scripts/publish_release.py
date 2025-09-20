#!/usr/bin/env python3
"""Confluence Release Notes Publisher.

This script automatically publishes release notes to Confluence
when a new GitHub release is created.
"""

import re
import sys
import json
import requests
from typing import Dict, Optional, Any
from decouple import config  # type: ignore


class ConfluencePublisher:
    """Publishes release notes to Confluence."""

    def __init__(self) -> None:
        """Initialize the Confluence publisher with configuration."""
        self.confluence_url = str(config("CONFLUENCE_URL", default=""))  # type: ignore
        self.confluence_user = str(config("CONFLUENCE_USER", default=""))  # type: ignore
        self.confluence_token = str(config("CONFLUENCE_TOKEN", default=""))  # type: ignore
        self.confluence_space = str(config("CONFLUENCE_SPACE", default=""))  # type: ignore
        self.confluence_parent_page = str(config("CONFLUENCE_PARENT_PAGE", default=""))  # type: ignore
        self.github_repository = str(config("GITHUB_REPOSITORY", default=""))  # type: ignore

        if not all(
            [
                self.confluence_url,
                self.confluence_user,
                self.confluence_token,
                self.confluence_space,
            ]
        ):
            raise ValueError(
                "Missing required Confluence configuration (URL, user, token, and space are required)"
            )

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for Confluence API."""
        import base64

        auth_string = f"{self.confluence_user}:{self.confluence_token}"
        auth_bytes = auth_string.encode("ascii")
        auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

        return {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def create_confluence_content(
        self, title: str, version: str, release_notes: str
    ) -> str:
        """Create Confluence-formatted content from release notes.

        Args:
            title: The page title
            version: The release version
            release_notes: The GitHub release notes content

        Returns:
            Confluence-formatted content
        """
        # Convert markdown to Confluence storage format
        github_url = (
            f"https://github.com/{self.github_repository}/releases/tag/{version}"
            if self.github_repository
            else ""
        )
        confluence_content = f"""
<h1>Release {version}</h1>
<p><strong>Release Date:</strong> {self._get_current_date()}</p>
{f'<p><strong>GitHub Tag:</strong> <a href="{github_url}">{version}</a></p>' if github_url else ''}

<h2>Release Notes</h2>
{self._convert_markdown_to_confluence(release_notes)}

<h2>Installation</h2>
<ac:structured-macro ac:name="code" ac:schema-version="1">
<ac:parameter ac:name="language">bash</ac:parameter>
<ac:plain-text-body><![CDATA[
pip install confluence-markdown=={version.lstrip('v')}
]]></ac:plain-text-body>
</ac:structured-macro>

<p><em>This release note was automatically generated from GitHub release.</em></p>
"""
        return confluence_content.strip()

    def _convert_markdown_to_confluence(self, markdown: str) -> str:
        """Convert basic markdown to Confluence storage format."""
        # Store code blocks temporarily to protect them during processing
        code_blocks: list[str] = []

        def store_code_block(match: re.Match[str]) -> str:
            code_blocks.append(match.group(0))
            return f"__CODE_BLOCK_{len(code_blocks) - 1}__"

        # Extract and store fenced code blocks
        markdown = re.sub(
            r"```(\w+)?\n(.*?)\n```",
            store_code_block,
            markdown,
            flags=re.DOTALL,
        )

        # Convert inline code blocks
        markdown = re.sub(r"`([^`]+)`", r"<code>\1</code>", markdown)

        # Convert headers
        markdown = re.sub(r"^### (.*)", r"<h3>\1</h3>", markdown, flags=re.MULTILINE)
        markdown = re.sub(r"^## (.*)", r"<h2>\1</h2>", markdown, flags=re.MULTILINE)
        markdown = re.sub(r"^# (.*)", r"<h1>\1</h1>", markdown, flags=re.MULTILINE)

        # Convert lists
        markdown = re.sub(r"^- (.*)", r"<li>\1</li>", markdown, flags=re.MULTILINE)
        markdown = re.sub(
            r"(<li>.*</li>\n)+", r"<ul>\g<0></ul>", markdown, flags=re.DOTALL
        )

        # Convert bold
        markdown = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", markdown)

        # Convert italic
        markdown = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", markdown)

        # Convert links
        markdown = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', markdown)

        # Convert paragraphs (but skip lines that are already HTML or empty)
        lines = markdown.split("\n")
        result: list[str] = []

        for line in lines:
            line = line.strip()

            # Only wrap in paragraphs if not already HTML and not a placeholder
            if line and not line.startswith("<") and not line.startswith("__CODE_BLOCK_"):
                line = f"<p>{line}</p>"
            result.append(line)

        # Restore code blocks with proper Confluence format
        final_result = "\n".join(result)
        for i, code_block in enumerate(code_blocks):
            # Parse the original code block to extract language and content
            match = re.match(r"```(\w+)?\n(.*?)\n```", code_block, re.DOTALL)
            if match:
                language = match.group(1) or "text"
                content = match.group(2)
                confluence_code = (
                    f'<ac:structured-macro ac:name="code" ac:schema-version="1">'
                    f'<ac:parameter ac:name="language">{language}</ac:parameter>'
                    f'<ac:plain-text-body><![CDATA[{content}]]></ac:plain-text-body>'
                    f'</ac:structured-macro>'
                )
                final_result = final_result.replace(f"__CODE_BLOCK_{i}__", confluence_code)

        return final_result

    def _get_current_date(self) -> str:
        """Get current date in readable format."""
        from datetime import datetime

        return datetime.now().strftime("%B %d, %Y")

    def find_parent_page_id(self) -> Optional[str]:
        """Find the parent page ID for release notes."""
        if not self.confluence_parent_page:
            return None

        url = f"{self.confluence_url}/rest/api/content"
        params = {
            "title": self.confluence_parent_page,
            "spaceKey": self.confluence_space,
            "expand": "version",
        }

        response = requests.get(url, headers=self.get_auth_headers(), params=params)

        if response.status_code == 200:
            data = response.json()
            if data["results"]:
                return str(data["results"][0]["id"])

        return None

    def page_exists(self, version: str) -> bool:
        """Check if a release page already exists in Confluence.

        Args:
            version: The release version (e.g., 'v1.0.0')

        Returns:
            True if page exists, False otherwise
        """
        title = f"Release {version} - confluence-markdown"
        existing_page = self._find_existing_page(title)
        return existing_page is not None

    def publish_release_notes(self, version: str, release_notes: str) -> bool:
        """Publish release notes to Confluence.

        Args:
            version: The release version (e.g., 'v1.0.0')
            release_notes: The release notes content

        Returns:
            True if successful, False otherwise
        """
        try:
            title = f"Release {version} - confluence-markdown"
            content = self.create_confluence_content(title, version, release_notes)

            # Check if page already exists
            existing_page = self._find_existing_page(title)

            if existing_page:
                # Update existing page
                return self._update_page(
                    existing_page["id"],
                    title,
                    content,
                    existing_page["version"]["number"],
                )
            else:
                # Create new page
                return self._create_page(title, content)

        except Exception as e:
            print(f"Error publishing to Confluence: {e}")
            return False

    def _find_existing_page(self, title: str) -> Optional[Dict[str, Any]]:
        """Find existing Confluence page by title."""
        url = f"{self.confluence_url}/rest/api/content"
        params = {
            "title": title,
            "spaceKey": self.confluence_space,
            "expand": "version",
        }

        response = requests.get(url, headers=self.get_auth_headers(), params=params)

        if response.status_code == 200:
            data = response.json()
            if data["results"]:
                return dict(data["results"][0])

        return None

    def _create_page(self, title: str, content: str) -> bool:
        """Create a new Confluence page."""
        url = f"{self.confluence_url}/rest/api/content"

        page_data: Dict[str, Any] = {
            "type": "page",
            "title": title,
            "space": {"key": self.confluence_space},
            "body": {"storage": {"value": content, "representation": "storage"}},
        }

        # Add parent page if specified
        parent_id = self.find_parent_page_id()
        if parent_id:
            page_data["ancestors"] = [{"id": parent_id}]  # type: ignore

        response = requests.post(
            url, headers=self.get_auth_headers(), data=json.dumps(page_data)
        )

        if response.status_code == 200:
            page_info = response.json()
            page_url = (
                f"{self.confluence_url}/pages/viewpage.action?pageId={page_info['id']}"
            )
            print(f"✅ Created Confluence page: {page_url}")
            return True
        else:
            print(f"❌ Failed to create page: {response.status_code} - {response.text}")
            return False

    def _update_page(
        self, page_id: str, title: str, content: str, current_version: int
    ) -> bool:
        """Update existing Confluence page."""
        url = f"{self.confluence_url}/rest/api/content/{page_id}"

        page_data: Dict[str, Any] = {
            "version": {"number": current_version + 1},
            "title": title,
            "type": "page",
            "body": {"storage": {"value": content, "representation": "storage"}},
        }

        response = requests.put(
            url, headers=self.get_auth_headers(), data=json.dumps(page_data)
        )

        if response.status_code == 200:
            page_url = f"{self.confluence_url}/pages/viewpage.action?pageId={page_id}"
            print(f"✅ Updated Confluence page: {page_url}")
            return True
        else:
            print(f"❌ Failed to update page: {response.status_code} - {response.text}")
            return False


def main() -> None:
    """Main entry point for the script."""
    if len(sys.argv) != 3:
        print("Usage: publish_release.py <version> <release_notes>")
        print(
            "Example: publish_release.py v1.0.0 'Initial release with awesome features'"
        )
        sys.exit(1)

    version = sys.argv[1]
    release_notes = sys.argv[2]

    try:
        publisher = ConfluencePublisher()
        success = publisher.publish_release_notes(version, release_notes)

        if success:
            print(
                f"🎉 Successfully published release notes for {version} to Confluence!"
            )
            sys.exit(0)
        else:
            print(f"❌ Failed to publish release notes for {version}")
            sys.exit(1)

    except ValueError as e:
        print(f"Configuration error: {e}")
        print("\nRequired environment variables:")
        print("- CONFLUENCE_URL: Your Confluence instance URL")
        print("- CONFLUENCE_USER: Your Confluence username/email")
        print("- CONFLUENCE_TOKEN: Your Confluence API token")
        print("- CONFLUENCE_SPACE: Confluence space key")
        print("- CONFLUENCE_PARENT_PAGE: Parent page title (optional)")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
