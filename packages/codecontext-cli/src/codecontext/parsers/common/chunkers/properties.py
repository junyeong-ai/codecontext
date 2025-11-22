"""Properties file chunker.

This module provides a chunker for Java properties files using prefix-based grouping.
"""

import logging
from pathlib import Path

from codecontext_core.models import DocumentNode

from .config_base import BaseConfigChunker

logger = logging.getLogger(__name__)


class PropertiesConfigChunker(BaseConfigChunker):
    """Chunker for Java properties files using prefix-based grouping strategy."""

    def chunk_properties(self, file_path: Path) -> list[DocumentNode]:
        """Chunk properties file by prefix-based grouping.

        Args:
            file_path: Path to properties file

        Returns:
            List of DocumentNode chunks
        """
        content = file_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        # Group by prefix
        sections: dict[str, list[str]] = {}
        current_comment_block = []

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Comment line
            if line.startswith("#"):
                current_comment_block.append(line)
                continue

            # Property line
            if "=" in line:
                key = line.split("=")[0].strip()
                # Extract prefix (e.g., "database" from "database.host")
                prefix = key.split(".")[0] if "." in key else key

                if prefix not in sections:
                    sections[prefix] = []
                    # Add accumulated comments
                    if current_comment_block:
                        sections[prefix].extend(current_comment_block)
                        current_comment_block = []

                sections[prefix].append(line)

        # Create chunks from sections
        chunks = []
        for prefix, lines_list in sections.items():
            content = "\n".join(lines_list)
            size_tokens = len(content) // self.token_to_char_ratio

            # Extract all keys
            keys = []
            for line in lines_list:
                if "=" in line and not line.startswith("#"):
                    key = line.split("=")[0].strip()
                    keys.append(key)

            chunk = {
                "path": prefix,
                "key": prefix,
                "content": content,
                "depth": 1,
                "size_tokens": size_tokens,
                "metadata": {
                    "all_keys": keys,
                    "format": "properties",
                },
            }
            chunks.append(chunk)

        # Optimize and convert
        chunks = self._optimize_chunks(chunks)
        return self._to_document_nodes(chunks, file_path, "properties")
