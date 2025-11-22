"""Markdown document chunking using hybrid approach.

This module provides intelligent chunking for markdown documents using a hybrid
strategy that combines heading-based splitting with recursive text splitting
for optimal chunk sizes.

Hybrid chunking (heading + recursive) provides the best balance of semantic
coherence and chunk size control.
"""

from pathlib import Path
from typing import Any

from codecontext_core.models import DocumentNode, NodeType

from codecontext.indexer.document_indexer import DocumentIndexer
from codecontext.parsers.common.text_splitters import MarkdownHeaderSplitter, RecursiveTextSplitter
from codecontext.utils.checksum import calculate_content_checksum

# Note: This file doesn't use logging, no changes needed


class MarkdownChunker:
    """Chunks markdown documents using hybrid heading + recursive strategy.

    This chunker implements a hybrid approach:
    1. Split by markdown headings to maintain semantic structure
    2. Apply recursive splitting on large sections to ensure size limits
    3. Generate DocumentNode instances with proper metadata
    """

    def __init__(
        self,
        chunk_size: int = 4096,
        chunk_overlap: int = 400,
        max_heading_level: int = 3,
    ) -> None:
        """Initialize markdown chunker.

        Args:
            chunk_size: Target chunk size in characters (default: 4096, ≈1638 tokens @ 2.5 chars/token)
            chunk_overlap: Overlap between chunks in characters (default: 400, ≈10% overlap)
            max_heading_level: Maximum heading level to split on (default: 3)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_heading_level = max_heading_level

        self.headers_to_split_on = [("#" * i, f"h{i}") for i in range(1, max_heading_level + 1)]

        self.heading_splitter = MarkdownHeaderSplitter(
            headers_to_split_on=self.headers_to_split_on,
            strip_headers=False,
        )

        self.recursive_splitter = RecursiveTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

        self.doc_indexer = DocumentIndexer()

    def chunk_file(self, file_path: Path) -> list[DocumentNode]:
        """Chunk a markdown file into DocumentNode instances.

        Args:
            file_path: Path to markdown file

        Returns:
            List of DocumentNode instances representing chunks

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a markdown file
        """
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)

        if file_path.suffix.lower() not in [".md", ".markdown"]:
            msg = f"Not a markdown file: {file_path}"
            raise ValueError(msg)

        content = file_path.read_text(encoding="utf-8")

        file_title = self._extract_file_title(content)
        chunks = self.chunk_text(content)

        # Calculate relative path from cwd
        try:
            relative_path = str(file_path.relative_to(Path.cwd()))
        except ValueError:
            relative_path = str(file_path)

        document_nodes = []
        for i, (chunk_text, metadata, start_line, end_line) in enumerate(chunks):
            related_code = self.doc_indexer.extract_code_references(chunk_text)

            node = DocumentNode(
                file_path=str(file_path.absolute()),
                relative_path=relative_path,
                node_type=NodeType.MARKDOWN,
                content=chunk_text,
                checksum=calculate_content_checksum(chunk_text),
                chunk_index=i,
                total_chunks=len(chunks),
                parent_doc_id=str(file_path),
                title=metadata.get("title", metadata.get("h1", metadata.get("h2", file_title))),
                start_line=start_line,
                end_line=end_line,
                related_code=related_code if related_code else None,
            )
            document_nodes.append(node)

        return document_nodes

    def _extract_file_title(self, content: str) -> str:
        """Extract file title from first h1 header."""
        lines = content.split("\n", 10)
        for line in lines:
            if line.startswith("# "):
                return line[2:].strip()
        return ""

    def chunk_text(self, text: str) -> list[tuple[str, dict[str, Any], int, int]]:
        """Chunk markdown text using hybrid approach.

        Args:
            text: Markdown text content

        Returns:
            List of (chunk_text, metadata, start_line, end_line) tuples
        """
        heading_chunks = self.heading_splitter.split_text(text)

        final_chunks = []
        for doc in heading_chunks:
            chunk_text = doc.page_content
            metadata = doc.metadata

            if len(chunk_text) > self.chunk_size:
                sub_chunks = self.recursive_splitter.split_text(chunk_text)
                for sub_chunk in sub_chunks:
                    start_line, end_line = self._find_chunk_lines(text, sub_chunk)
                    final_chunks.append((sub_chunk, metadata, start_line, end_line))
            else:
                start_line, end_line = self._find_chunk_lines(text, chunk_text)
                final_chunks.append((chunk_text, metadata, start_line, end_line))

        return final_chunks

    def _find_chunk_lines(self, full_text: str, chunk_text: str) -> tuple[int, int]:
        """Find line numbers for a chunk in the full text.

        Args:
            full_text: Original markdown content
            chunk_text: Chunk content

        Returns:
            Tuple of (start_line, end_line) 1-indexed
        """
        chunk_start = full_text.find(chunk_text)
        if chunk_start == -1:
            return 1, 1

        start_line = full_text[:chunk_start].count("\n") + 1
        end_line = start_line + chunk_text.count("\n")

        return start_line, end_line


def chunk_markdown_file(file_path: Path, chunk_size: int = 4096) -> list[DocumentNode]:
    """Convenience function to chunk a markdown file.

    Args:
        file_path: Path to markdown file
        chunk_size: Target chunk size in characters (default: 4096, ≈1638 tokens)

    Returns:
        List of DocumentNode instances
    """
    chunker = MarkdownChunker(chunk_size=chunk_size)
    return chunker.chunk_file(file_path)
