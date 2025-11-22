"""Lightweight text splitters without external dependencies.

Zero-dependency implementation of markdown and recursive text splitting,
eliminating the need for langchain-text-splitters.
"""

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class Document:
    """Document with content and metadata."""

    page_content: str
    metadata: dict[str, Any]


class MarkdownHeaderSplitter:
    """Split markdown by headers, maintaining semantic structure."""

    def __init__(
        self,
        headers_to_split_on: list[tuple[str, str]],
        strip_headers: bool = False,
    ) -> None:
        """Initialize markdown header splitter.

        Args:
            headers_to_split_on: List of (header_pattern, metadata_key) tuples
                Example: [("#", "h1"), ("##", "h2"), ("###", "h3")]
            strip_headers: Whether to remove header lines from content
        """
        self.headers_to_split_on = sorted(
            headers_to_split_on, key=lambda x: len(x[0]), reverse=True
        )
        self.strip_headers = strip_headers

    def split_text(self, text: str) -> list[Document]:
        """Split markdown text by headers.

        Args:
            text: Markdown text content

        Returns:
            List of Document instances with header metadata
        """
        lines = text.split("\n")
        chunks: list[Document] = []
        current_chunk: list[str] = []
        current_metadata: dict[str, Any] = {}

        for line in lines:
            header_match = self._match_header(line)

            if header_match:
                # Save previous chunk
                if current_chunk:
                    content = "\n".join(current_chunk)
                    if content.strip():
                        chunks.append(
                            Document(page_content=content, metadata=current_metadata.copy())
                        )

                # Start new chunk
                header_level, header_text = header_match
                current_metadata = {header_level: header_text}
                current_chunk = [] if self.strip_headers else [line]
            else:
                current_chunk.append(line)

        # Save final chunk
        if current_chunk:
            content = "\n".join(current_chunk)
            if content.strip():
                chunks.append(Document(page_content=content, metadata=current_metadata.copy()))

        return chunks if chunks else [Document(page_content=text, metadata={})]

    def _match_header(self, line: str) -> tuple[str, str] | None:
        """Match header pattern and extract level and text.

        Args:
            line: Single line of text

        Returns:
            Tuple of (header_level, header_text) or None
        """
        for header_pattern, metadata_key in self.headers_to_split_on:
            # Match "# Header", "## Header", etc.
            pattern = f"^{re.escape(header_pattern)}\\s+(.+)$"
            match = re.match(pattern, line.strip())
            if match:
                return metadata_key, match.group(1).strip()
        return None


class RecursiveTextSplitter:
    """Recursively split text using separators."""

    def __init__(
        self,
        chunk_size: int = 4096,
        chunk_overlap: int = 400,
        separators: list[str] | None = None,
    ) -> None:
        """Initialize recursive text splitter.

        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks in characters
            separators: List of separators to try (in order)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", " ", ""]

    def split_text(self, text: str) -> list[str]:
        """Split text recursively using separators.

        Args:
            text: Text to split

        Returns:
            List of text chunks
        """
        return self._split_text_recursive(text, self.separators)

    def _split_text_recursive(self, text: str, separators: list[str]) -> list[str]:
        """Recursively split text using separator hierarchy.

        Args:
            text: Text to split
            separators: Remaining separators to try

        Returns:
            List of text chunks
        """
        if len(text) <= self.chunk_size:
            return [text] if text else []

        if not separators:
            # Last resort: split by character at chunk_size
            return self._split_by_size(text)

        separator = separators[0]
        remaining_separators = separators[1:]

        # Try splitting with current separator
        splits = text.split(separator) if separator else list(text)

        chunks: list[str] = []
        current_chunk: list[str] = []
        current_size = 0

        for split in splits:
            split_size = len(split) + (len(separator) if separator else 0)

            # If single split is too large, recurse with next separator
            if split_size > self.chunk_size:
                # Save current chunk first
                if current_chunk:
                    chunks.append(separator.join(current_chunk))
                    current_chunk = []
                    current_size = 0

                # Recurse on large split
                sub_chunks = self._split_text_recursive(split, remaining_separators)
                chunks.extend(sub_chunks)
                continue

            # Check if adding split exceeds chunk_size
            if current_size + split_size > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append(separator.join(current_chunk))

                # Start new chunk with overlap
                overlap_chunk = self._create_overlap_chunk(current_chunk, separator)
                current_chunk = overlap_chunk
                current_size = sum(len(s) for s in current_chunk) + len(separator) * (
                    len(current_chunk) - 1
                )

            current_chunk.append(split)
            current_size += split_size

        # Save final chunk
        if current_chunk:
            chunks.append(separator.join(current_chunk))

        return chunks

    def _create_overlap_chunk(self, chunks: list[str], separator: str) -> list[str]:
        """Create overlap chunk from end of previous chunks.

        Args:
            chunks: Previous chunks
            separator: Separator used

        Returns:
            Overlap chunks
        """
        if self.chunk_overlap == 0 or not chunks:
            return []

        overlap: list[str] = []
        overlap_size = 0

        # Take from end of chunks
        for chunk in reversed(chunks):
            chunk_size = len(chunk) + len(separator)
            if overlap_size + chunk_size > self.chunk_overlap:
                break
            overlap.insert(0, chunk)
            overlap_size += chunk_size

        return overlap

    def _split_by_size(self, text: str) -> list[str]:
        """Split text by character count (last resort).

        Args:
            text: Text to split

        Returns:
            List of chunks split at chunk_size boundaries
        """
        chunks: list[str] = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            start = end - self.chunk_overlap if self.chunk_overlap > 0 else end

        return chunks
