"""Base chunker for configuration files with shared logic.

This module provides the base class for configuration file chunking with shared
methods for adaptive splitting, optimization, and metadata extraction.
"""

import logging
from pathlib import Path
from typing import Any

from codecontext_core.models import DocumentNode, NodeType

from codecontext.parsers.common.chunkers.config_metadata import (
    extract_config_metadata,
    flatten_keys,
)
from codecontext.utils.checksum import calculate_content_checksum

logger = logging.getLogger(__name__)


def _merge_chunks(chunks: list[dict[str, Any]], token_to_char_ratio: int) -> dict[str, Any]:
    """Merge multiple chunks into one."""
    if len(chunks) == 1:
        return chunks[0]

    merged_content = "\n\n".join(c["content"] for c in chunks)

    all_keys = []
    for c in chunks:
        if "all_keys" in c.get("metadata", {}):
            all_keys.extend(c["metadata"]["all_keys"])

    all_env_refs = []
    for c in chunks:
        env_refs = c.get("metadata", {}).get("env_references")
        if env_refs:
            all_env_refs.extend(env_refs)

    merged = chunks[0].copy()
    merged.update(
        {
            "content": merged_content,
            "size_tokens": len(merged_content) // token_to_char_ratio,
            "path": " + ".join(str(c["path"]) for c in chunks),
            "key": " + ".join(str(c["key"]) for c in chunks),
            "metadata": {
                "all_keys": list(set(all_keys)),
                "env_references": list(set(all_env_refs)) if all_env_refs else None,
                "merged": True,
                "merged_count": len(chunks),
            },
        }
    )

    return merged


class BaseConfigChunker:
    """Base class for configuration file chunking with shared methods.

    This chunker implements hierarchical adaptive chunking strategy:
    - Section-based splitting maintains semantic coherence
    - Adaptive sub-section splitting for size control
    - Smart merging prevents tiny chunks
    """

    # Size thresholds (aligned with markdown chunker)
    TARGET_CHUNK_SIZE = 512  # tokens
    MIN_CHUNK_SIZE = 100  # tokens
    MAX_CHUNK_SIZE = 1024  # tokens
    SPLIT_THRESHOLD = 512  # trigger splitting
    TOKEN_TO_CHAR_RATIO = 4  # rough estimate: 1 token ≈ 4 chars

    def __init__(
        self,
        chunk_size: int = 512,
        min_chunk_size: int = 100,
        max_depth: int = 4,
    ) -> None:
        """Initialize config chunker.

        Args:
            chunk_size: Target chunk size in tokens (default: 512)
            min_chunk_size: Minimum chunk size to prevent tiny chunks (default: 100)
            max_depth: Maximum nesting depth (default: 4)
        """
        self.chunk_size = chunk_size
        self.min_chunk_size = min_chunk_size
        self.max_depth = max_depth
        self.token_to_char_ratio = self.TOKEN_TO_CHAR_RATIO

    def _chunk_section(
        self, key: str, value: object, depth: int, parent_path: str | None = None
    ) -> list[dict[str, Any]]:
        """Recursively chunk a section with adaptive splitting.

        Algorithm:
        1. Estimate section size
        2. If size <= TARGET → return as-is
        3. If size > TARGET and has subsections → split by subsections
        4. If size > TARGET but no subsections → return as-is (warn if > MAX)

        Args:
            key: Section key name
            value: Section value (dict, list, or scalar)
            depth: Current nesting depth
            parent_path: Parent section path (e.g., "spring.datasource")

        Returns:
            List of chunk dictionaries
        """
        # Build current path
        current_path = f"{parent_path}.{key}" if parent_path else key

        # Format section content
        content = self._format_section_content(key, value)
        size_tokens = len(content) // self.token_to_char_ratio

        # Extract metadata
        metadata = extract_config_metadata(key, value)

        # Case 1: Optimal size → return as-is
        if size_tokens <= self.chunk_size:
            return [
                {
                    "path": current_path,
                    "key": key,
                    "content": content,
                    "depth": depth,
                    "size_tokens": size_tokens,
                    "metadata": metadata,
                }
            ]

        # Case 2: Too large with subsections and within depth limit → recursive split
        if isinstance(value, dict) and depth < self.max_depth:
            sub_chunks = []
            for sub_key, sub_value in value.items():
                sub_chunks.extend(self._chunk_section(sub_key, sub_value, depth + 1, current_path))

            # Only return sub-chunks if meaningful split occurred
            if len(sub_chunks) > 1:
                return sub_chunks

        # Case 3: Too large but cannot split → return with warning
        if size_tokens > self.MAX_CHUNK_SIZE:
            logger.warning(
                f"Large config section '{current_path}' ({size_tokens} tokens) "
                f"cannot be split further (depth={depth}, type={type(value).__name__})"
            )

        return [
            {
                "path": current_path,
                "key": key,
                "content": content,
                "depth": depth,
                "size_tokens": size_tokens,
                "metadata": metadata,
                "oversized": size_tokens > self.MAX_CHUNK_SIZE,
            }
        ]

    def _format_section_content(self, key: str, value: object) -> str:
        """Format section as searchable text.

        Args:
            key: Section key
            value: Section value

        Returns:
            Formatted section content
        """
        import yaml

        lines = [f"Configuration: {key}", ""]

        if isinstance(value, dict):
            # YAML format (more readable)
            yaml_content = yaml.dump({key: value}, default_flow_style=False, allow_unicode=True)
            lines.append(yaml_content)

            # Add key list for search optimization
            all_keys = flatten_keys(value, key)
            if all_keys:
                lines.extend(["", f"Available settings: {', '.join(all_keys)}"])
        elif isinstance(value, list):
            # List value
            lines.append(f"{key}:")
            if len(value) <= 10:
                # Small list: show all items
                for item in value:
                    lines.append(f"  - {item}")
            else:
                # Large list: show summary
                lines.append(f"  [{len(value)} items]")
                lines.append(f"  First items: {', '.join(str(x) for x in value[:3])}")
        else:
            # Scalar value
            lines.append(f"{key}: {value}")

        return "\n".join(lines)

    def _optimize_chunks(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Merge small chunks to meet MIN_CHUNK_SIZE."""
        if not chunks:
            return []

        optimized = []
        buffer = []
        buffer_size = 0

        for chunk in chunks:
            size = chunk["size_tokens"]

            if size < self.min_chunk_size:
                buffer.append(chunk)
                buffer_size += size

                if buffer_size >= self.min_chunk_size:
                    optimized.append(_merge_chunks(buffer, self.token_to_char_ratio))
                    buffer = []
                    buffer_size = 0
            else:
                if buffer:
                    optimized.append(_merge_chunks(buffer, self.token_to_char_ratio))
                    buffer = []
                    buffer_size = 0
                optimized.append(chunk)

        if buffer:
            if optimized and optimized[-1]["size_tokens"] + buffer_size < self.MAX_CHUNK_SIZE:
                last = optimized.pop()
                buffer.insert(0, last)
            optimized.append(_merge_chunks(buffer, self.token_to_char_ratio))

        return optimized

    def _to_document_nodes(
        self, chunks: list[dict[str, Any]], file_path: Path, config_format: str
    ) -> list[DocumentNode]:
        """Convert chunk dictionaries to DocumentNode instances.

        Args:
            chunks: List of chunk dictionaries
            file_path: Source file path
            config_format: Configuration format (yaml, json, properties)

        Returns:
            List of DocumentNode instances
        """
        file_content = file_path.read_text(encoding="utf-8")

        # Calculate relative path from cwd
        try:
            relative_path = str(file_path.relative_to(Path.cwd()))
        except ValueError:
            relative_path = str(file_path)

        document_nodes = []

        for i, chunk in enumerate(chunks):
            metadata = chunk.get("metadata", {})
            start_line, end_line = self._find_chunk_lines(file_content, chunk["content"])

            node = DocumentNode(
                file_path=str(file_path.absolute()),
                relative_path=relative_path,
                node_type=NodeType.CONFIG,
                content=chunk["content"],
                checksum=calculate_content_checksum(chunk["content"]),
                chunk_index=i,
                total_chunks=len(chunks),
                parent_doc_id=str(file_path),
                title=chunk["path"],
                start_line=start_line,
                end_line=end_line,
                config_keys=metadata.get("all_keys"),
                config_format=config_format,
                env_references=metadata.get("env_references"),
                section_depth=chunk.get("depth", 1),
            )
            document_nodes.append(node)

        return document_nodes

    def _find_chunk_lines(self, full_text: str, chunk_text: str) -> tuple[int, int]:
        """Find line numbers for a chunk in the full text.

        Args:
            full_text: Original file content
            chunk_text: Chunk content

        Returns:
            Tuple of (start_line, end_line) 1-indexed
        """
        chunk_start = full_text.find(chunk_text.strip())
        if chunk_start == -1:
            return 1, 1

        start_line = full_text[:chunk_start].count("\n") + 1
        end_line = start_line + chunk_text.count("\n")

        return start_line, end_line
