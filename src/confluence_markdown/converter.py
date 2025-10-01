# Copyright (c) 2025 Francis Bain
# SPDX-License-Identifier: Apache-2.0

"""Markdown to Confluence converter module."""

import html
import re
from urllib.parse import urlparse


class MarkdownToConfluenceConverter:
    """Convert Markdown to Confluence storage format HTML."""

    def convert(self, markdown: str) -> str:
        """
        Convert a subset of Markdown into Confluence storage-format HTML.

        Supports:
        - Fenced code blocks (```lang\ncode\n```) — preserved and replaced with Confluence
          code macro; language parameter is kept when present, otherwise "text".
        - Inline code using backticks -> <code>...</code>.
        - ATX headers (#, ##, ###) -> <h1>, <h2>, <h3>.
        - Unordered lists starting with "- " -> <ul><li>...</li></ul>.
        - Bold (**text**) -> <strong>, italic (*text*) -> <em>.
        - Markdown links [text](url) -> <a href="url">text</a>.
        - Simple paragraph wrapping for non-empty lines that are not already HTML or code placeholders.

        Code blocks are temporarily replaced with placeholders during processing to avoid accidental transformation,
        then restored as Confluence `<ac:structured-macro ac:name="code">` blocks containing the code inside CDATA.

        Parameters:
            markdown (str): Markdown source text to convert.

        Returns:
            str: Converted string in Confluence storage format.
        """
        # Store code blocks temporarily to protect them during processing
        code_blocks: list[str] = []

        def store_code_block(match: re.Match[str]) -> str:
            """
            Store a matched fenced code block and return a placeholder token.

            Parameters:
                match (re.Match[str]): A regex Match object representing a fenced code block. The entire matched text (match.group(0)) is appended to the module-level `code_blocks` list.

            Returns:
                str: A placeholder token of the form "__CODE_BLOCK_{n}__" where n is the index of the stored block in `code_blocks`.

            Side effects:
                Appends the matched code block text to the `code_blocks` list in the enclosing scope.
            """
            code_blocks.append(match.group(0))
            return f"__CODE_BLOCK_{len(code_blocks) - 1}__"

        # Extract and store fenced code blocks first (before HTML escaping)
        markdown = re.sub(
            r"```(\w+)?\n(.*?)\n```",
            store_code_block,
            markdown,
            flags=re.DOTALL,
        )

        # Escape HTML special characters to prevent XSS and format issues
        markdown = html.escape(markdown)

        # Convert inline code blocks (after escaping, since backticks are safe)
        markdown = re.sub(r"`([^`]+)`", r"<code>\1</code>", markdown)

        # Convert headers
        markdown = re.sub(r"^### (.*)", r"<h3>\1</h3>", markdown, flags=re.MULTILINE)
        markdown = re.sub(r"^## (.*)", r"<h2>\1</h2>", markdown, flags=re.MULTILINE)
        markdown = re.sub(r"^# (.*)", r"<h1>\1</h1>", markdown, flags=re.MULTILINE)

        # Convert lists - process them to match expected format exactly
        lines = markdown.split("\n")
        result_lines = []
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            if re.match(r"^- ", line):
                # Unordered list
                list_items = []
                j = i
                while j < len(lines) and re.match(r"^- ", lines[j].strip()):
                    item_content = re.sub(r"^- ", "", lines[j].strip())
                    list_items.append(f"<li>{item_content}</li>")
                    j += 1

                # Add compact list format to match expected output
                if list_items:
                    list_content = "\n".join(list_items)
                    result_lines.append(f"__LIST_START__<ul>{list_content}\n</ul>__LIST_END__")
                i = j

            elif re.match(r"^\d+\. ", line):
                # Ordered list
                list_items = []
                j = i
                while j < len(lines) and re.match(r"^\d+\. ", lines[j].strip()):
                    item_content = re.sub(r"^\d+\. ", "", lines[j].strip())
                    list_items.append(f"<li>{item_content}</li>")
                    j += 1

                # Add compact list format to match expected output
                if list_items:
                    list_content = "\n".join(list_items)
                    result_lines.append(f"__LIST_START__<ol>{list_content}\n</ol>__LIST_END__")
                i = j

            else:
                # Only add non-empty lines to avoid excessive spacing
                if line:
                    result_lines.append(line)
                i += 1

        markdown = "\n".join(result_lines)

        # Convert bold
        markdown = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", markdown)

        # Convert italic
        markdown = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", markdown)

        # Convert links with security filtering
        def secure_link_replacement(match: re.Match[str]) -> str:
            """
            Securely process markdown links, filtering out dangerous schemes.

            Args:
                match: Regex match object with groups (link_text, url)

            Returns:
                str: Safe HTML link or plain text if URL scheme is dangerous
            """
            link_text = match.group(1)
            url = match.group(2).strip()

            # Parse the URL to extract the scheme
            try:
                parsed = urlparse(url)
                scheme = parsed.scheme.lower() if parsed.scheme else ""
            except Exception:
                # If URL parsing fails, treat as plain text
                return html.escape(link_text)

            # Define allowed schemes (case-insensitive)
            allowed_schemes = {"http", "https", "mailto"}

            # Allow local paths (no scheme, starts with /, or starts with #)
            if not scheme or url.startswith("/") or url.startswith("#"):
                # Local path - escape the URL and create link
                escaped_url = html.escape(url, quote=True)
                escaped_text = html.escape(link_text)
                return f'<a href="{escaped_url}">{escaped_text}</a>'

            # Check if scheme is allowed
            if scheme in allowed_schemes:
                # Safe scheme - escape and create link
                escaped_url = html.escape(url, quote=True)
                escaped_text = html.escape(link_text)
                return f'<a href="{escaped_url}">{escaped_text}</a>'
            else:
                # Dangerous scheme - return only the link text (safely escaped)
                return html.escape(link_text)

        markdown = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", secure_link_replacement, markdown)

        # Convert paragraphs (but skip lines that are already HTML or empty)
        lines = markdown.split("\n")
        result: list[str] = []

        for line in lines:
            line = line.strip()

            # Only wrap in paragraphs if not already HTML and not a placeholder
            if (
                line
                and not line.startswith("<")
                and not line.startswith("__CODE_BLOCK_")
                and not line.startswith("__LIST_")
            ):
                line = f"<p>{line}</p>"

            # Only add non-empty lines to avoid excessive whitespace
            if line:
                result.append(line)

        # Join result with proper spacing, but handle lists specially
        final_result = "\n\n".join(result)

        # Fix list spacing - remove extra newlines within lists
        final_result = re.sub(
            r"__LIST_START__(.*?)__LIST_END__", lambda m: m.group(1), final_result, flags=re.DOTALL
        )
        for i, code_block in enumerate(code_blocks):
            # Parse the original code block to extract language and content
            match = re.match(r"```(\w+)?\n(.*?)\n```", code_block, re.DOTALL)
            if match:
                language = match.group(1) or "text"
                content = match.group(2)
                confluence_code = (
                    f'<ac:structured-macro ac:name="code" ac:schema-version="1">'
                    f'<ac:parameter ac:name="language">{language}</ac:parameter>'
                    f"<ac:plain-text-body><![CDATA[{content}]]></ac:plain-text-body>"
                    f"</ac:structured-macro>"
                )
                final_result = final_result.replace(f"__CODE_BLOCK_{i}__", confluence_code)

        return final_result
