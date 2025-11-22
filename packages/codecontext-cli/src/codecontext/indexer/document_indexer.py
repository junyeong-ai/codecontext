"""Document indexer for markdown section extraction."""

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class MarkdownSection:
    """Represents a markdown section split by headers."""

    title: str
    content: str
    start_line: int
    end_line: int
    depth: int
    parent_title: str | None = None


class DocumentIndexer:
    """Indexes markdown documents by splitting into sections."""

    def split_by_headers(self, content: str, _file_path: str) -> list[MarkdownSection]:
        """Split markdown by ATX headers (##, ###)."""
        sections = []
        lines = content.split("\n")

        current_section = None
        current_content = []

        for i, line in enumerate(lines):
            header_match = re.match(r"^(#{2,6})\s+(.+)$", line)

            if header_match:
                if current_section:
                    current_section.content = "\n".join(current_content)
                    current_section.end_line = i
                    sections.append(current_section)

                depth = len(header_match.group(1))
                title = header_match.group(2).strip()

                current_section = MarkdownSection(
                    title=title, content="", start_line=i + 1, end_line=i + 1, depth=depth
                )
                current_content = [line]
            elif current_section:
                current_content.append(line)

        if current_section:
            current_section.content = "\n".join(current_content)
            current_section.end_line = len(lines)
            sections.append(current_section)

        return sections

    def extract_code_references(self, content: str) -> list[dict[str, Any]]:
        """Extract code references from markdown content.

        Identifies potential code references using two patterns:
        1. Backtick references: `ClassName.method` or `ClassName`
        2. File path references: path/to/file.py, Driver.kt, etc.

        This enables document-to-code linking in search results.

        Args:
            content: Markdown content to extract references from

        Returns:
            List of dictionaries with 'name', 'type', and 'match_reason' keys
        """
        references = []

        backtick_pattern = r"`([A-Z][a-zA-Z0-9.]+)`"
        for match in re.finditer(backtick_pattern, content):
            references.append(
                {"name": match.group(1), "type": "code_ref", "match_reason": "backtick reference"}
            )

        file_pattern = r"([a-zA-Z_/]+\.(py|kt|java|ts|js|tsx|jsx))"
        for match in re.finditer(file_pattern, content):
            references.append(
                {"name": match.group(1), "type": "file_ref", "match_reason": "file reference"}
            )

        return references
