"""YAML and JSON configuration file chunkers.

This module provides chunkers for YAML and JSON files using hierarchical
adaptive chunking strategy from the base chunker.
"""

import logging
from pathlib import Path
from typing import Any

from codecontext_core.models import DocumentNode

from .config_base import BaseConfigChunker

logger = logging.getLogger(__name__)


class YAMLConfigChunker(BaseConfigChunker):
    """Chunker for YAML configuration files using hierarchical adaptive strategy."""

    def chunk_yaml(self, data: dict[str, Any], file_path: Path) -> list[DocumentNode]:
        """Chunk YAML data hierarchically.

        Args:
            data: Parsed YAML data as dictionary
            file_path: Path to source file

        Returns:
            List of DocumentNode chunks
        """
        if not isinstance(data, dict):
            logger.warning(f"YAML data is not a dict: {type(data)}")
            return []

        chunks = []

        # Process top-level keys
        for key, value in data.items():
            section_chunks = self._chunk_section(key=key, value=value, depth=1, parent_path=None)
            chunks.extend(section_chunks)

        # Optimize: merge small chunks
        chunks = self._optimize_chunks(chunks)

        # Convert to DocumentNodes
        return self._to_document_nodes(chunks, file_path, "yaml")


class JSONConfigChunker(BaseConfigChunker):
    """Chunker for JSON configuration files using hierarchical adaptive strategy."""

    def chunk_json(self, data: dict[str, Any], file_path: Path) -> list[DocumentNode]:
        """Chunk JSON data hierarchically.

        Args:
            data: Parsed JSON data as dictionary
            file_path: Path to source file

        Returns:
            List of DocumentNode chunks
        """
        if not isinstance(data, dict):
            logger.warning(f"JSON data is not a dict: {type(data)}")
            return []

        chunks = []

        # Process top-level keys (same as YAML)
        for key, value in data.items():
            section_chunks = self._chunk_section(key=key, value=value, depth=1, parent_path=None)
            chunks.extend(section_chunks)

        # Optimize: merge small chunks
        chunks = self._optimize_chunks(chunks)

        # Convert to DocumentNodes
        return self._to_document_nodes(chunks, file_path, "json")
