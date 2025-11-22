"""Memory-bounded chunking for indexing."""

import gc
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncGenerator

from codecontext_core.device import cleanup_all_devices

logger = logging.getLogger(__name__)


@dataclass
class ChunkStats:
    chunk_index: int
    files_processed: int
    objects_count: int
    relationships_count: int
    embeddings_generated: int
    embeddings_reused: int = 0


@dataclass
class ProcessingStats:
    total_chunks: int = 0
    total_files: int = 0
    total_objects: int = 0
    total_relationships: int = 0
    total_embeddings_generated: int = 0
    total_embeddings_reused: int = 0

    def add_chunk(self, chunk_stats: ChunkStats) -> None:
        self.total_files += chunk_stats.files_processed
        self.total_objects += chunk_stats.objects_count
        self.total_relationships += chunk_stats.relationships_count
        self.total_embeddings_generated += chunk_stats.embeddings_generated
        self.total_embeddings_reused += chunk_stats.embeddings_reused

    def to_dict(self) -> dict[str, int]:
        return {
            "total_objects": self.total_objects,
            "total_relationships": self.total_relationships,
            "embeddings_generated": self.total_embeddings_generated,
            "embeddings_reused": self.total_embeddings_reused,
        }


class MemoryManager:
    def __init__(self, config: Any) -> None:
        self.config = config

    def cleanup(self, force: bool = False) -> None:
        mem_config = self.config.indexing.memory_management

        if force or mem_config.force_gc_after_chunk:
            gc.collect()
            gc.collect()

        if mem_config.clear_gpu_cache:
            cleanup_all_devices()

    def create_memory_barrier(self) -> None:
        gc.collect()
        cleanup_all_devices()


async def chunk_files(
    file_paths: list[Path], chunk_size: int
) -> AsyncGenerator[tuple[int, list[Path]], None]:
    for i in range(0, len(file_paths), chunk_size):
        chunk_index = i // chunk_size
        chunk_files = file_paths[i : i + chunk_size]
        yield chunk_index, chunk_files
