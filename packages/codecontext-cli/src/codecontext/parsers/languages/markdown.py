"""Markdown document parser for CodeContext.

This parser handles markdown (.md) files, chunking them into semantic units
and creating DocumentNode instances for indexing and search.
"""

import logging
import re
from pathlib import Path
from typing import Any

from codecontext_core.models import DocumentNode, Language

from codecontext.parsers.common.markdown_chunker import MarkdownChunker
from codecontext.parsers.interfaces import DocumentParser

logger = logging.getLogger(__name__)


class MarkdownParser(DocumentParser):
    """Parser for markdown documentation files.

    This parser uses the MarkdownChunker to split markdown files into
    semantic chunks based on heading structure, then creates DocumentNode
    instances suitable for vector indexing.

    Features:
    - Heading-based chunking for semantic coherence
    - Recursive splitting for size control
    - Metadata preservation (titles, heading levels)
    - Chunk linking (parent_doc_id)
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50) -> None:
        """Initialize markdown parser.

        Args:
            chunk_size: Target chunk size in tokens (default: 512)
            chunk_overlap: Overlap between chunks in tokens (default: 50)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunker = MarkdownChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            max_heading_level=3,
        )
        logger.debug(
            f"Initialized MarkdownParser with chunk_size={chunk_size}, overlap={chunk_overlap}"
        )

    def parse_file(self, file_path: Path) -> list[DocumentNode]:
        """Parse a markdown file into DocumentNode instances.

        Args:
            file_path: Path to markdown file

        Returns:
            List of DocumentNode instances representing chunks

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a markdown file
        """
        logger.info(f"Parsing markdown file: {file_path}")

        # Validate file
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)

        if file_path.suffix.lower() not in [".md", ".markdown"]:
            msg = f"Not a markdown file: {file_path}"
            raise ValueError(msg)

        # Chunk the file
        try:
            document_nodes = self.chunker.chunk_file(file_path)
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}", exc_info=True)
            raise
        else:
            logger.info(f"Successfully parsed {file_path}: {len(document_nodes)} chunks")
            return document_nodes

    def is_supported(self, file_path: Path) -> bool:
        """Check if a file is a supported markdown file.

        Args:
            file_path: Path to check

        Returns:
            True if file is a markdown file, False otherwise
        """
        return file_path.suffix.lower() in [".md", ".markdown"]

    # DocumentParser interface methods

    def get_language(self) -> Language:
        """Get the language this parser handles."""
        return Language.MARKDOWN

    def supports_file(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        return self.is_supported(file_path)

    def get_file_extensions(self) -> list[str]:
        """Get list[Any] of supported file extensions."""
        return [".md", ".markdown"]

    def extract_code_references(self, content: str) -> list[dict[str, Any]]:
        """Extract references to code from markdown content.

        Extracts:
        - Inline code references: `code`
        - Code blocks: ```language ... ```
        - Links to code files

        Args:
            content: Markdown content

        Returns:
            List of code references with context
        """
        references = []

        # Extract inline code references
        inline_code_pattern = r"`([^`]+)`"
        for match in re.finditer(inline_code_pattern, content):
            code_ref = match.group(1)
            references.append(
                {
                    "type": "inline_code",
                    "ref": code_ref,
                    "context": content[max(0, match.start() - 50) : match.end() + 50],
                }
            )

        # Extract code blocks with language
        code_block_pattern = r"```(\w+)?\n(.*?)\n```"
        for match in re.finditer(code_block_pattern, content, re.DOTALL):
            language = match.group(1) or "unknown"
            code = match.group(2)
            references.append(
                {
                    "type": "code_block",
                    "language": language,
                    "code": code[:200],  # Limit to first 200 chars
                }
            )

        # Extract markdown links that might reference code files
        link_pattern = r"\[([^\]]+)\]\(([^\)]+\.(?:py|js|ts|java|kt|go|rs|cpp|c|h))\)"
        for match in re.finditer(link_pattern, content):
            link_text = match.group(1)
            file_path = match.group(2)
            references.append(
                {
                    "type": "file_reference",
                    "text": link_text,
                    "file": file_path,
                }
            )

        return references

    def chunk_document(
        self, content: str, max_chunk_size: int = 1500
    ) -> list[tuple[str, int, int]]:
        """Split large markdown documents into chunks for embedding.

        Uses heading-based chunking for semantic coherence.

        Args:
            content: Markdown content
            max_chunk_size: Maximum characters per chunk

        Returns:
            List of (chunk_content, start_index, end_index) tuples
        """
        chunks = []

        # Split by headings
        heading_pattern = r"^#+\s+.+$"
        lines = content.split("\n")

        current_chunk: list[str] = []
        current_start = 0
        current_pos = 0

        for _i, line in enumerate(lines):
            if re.match(heading_pattern, line) and len("\n".join(current_chunk)) > max_chunk_size:
                # Save current chunk
                chunk_content = "\n".join(current_chunk)
                chunks.append((chunk_content, current_start, current_pos))

                # Start new chunk
                current_chunk = [line]
                current_start = current_pos
            else:
                current_chunk.append(line)

            current_pos += len(line) + 1  # +1 for newline

        # Add final chunk
        if current_chunk:
            chunk_content = "\n".join(current_chunk)
            chunks.append((chunk_content, current_start, len(content)))

        return chunks if chunks else [(content, 0, len(content))]


def parse_markdown_file(file_path: Path) -> list[DocumentNode]:
    """Convenience function to parse a markdown file.

    Args:
        file_path: Path to markdown file

    Returns:
        List of DocumentNode instances
    """
    parser = MarkdownParser()
    return parser.parse_file(file_path)
