"""Incremental indexing strategy with memory-bounded chunked processing."""

import logging
from datetime import UTC, datetime
from pathlib import Path

from typing import Any

from codecontext_core.models import IndexState, IndexStatus

from codecontext.indexer.strategy import AsyncIndexStrategy
from codecontext.indexer.sync.checksum import ChecksumOptimizer
from codecontext.indexer.sync.discovery import FileScanner
from codecontext.utils.git_ops import GitOperations

logger = logging.getLogger(__name__)


class IncrementalIndexStrategy(AsyncIndexStrategy):
    """Incremental indexing with memory-bounded chunked processing."""

    def __init__(
        self, config: Any, embedding_provider: Any, storage: Any, translation_provider: Any = None
    ) -> None:
        """Initialize incremental strategy.

        Args:
            config: Configuration
            embedding_provider: Embedding provider
            storage: Vector storage
            translation_provider: Optional translation provider
        """
        super().__init__(config, embedding_provider, storage, translation_provider)
        self.checksum_optimizer = ChecksumOptimizer(storage)

    async def index(self, repository_path: Path, show_progress: bool = True) -> IndexState:
        """Perform incremental indexing with chunked processing.

        Args:
            repository_path: Repository path
            show_progress: Show progress

        Returns:
            Updated index state
        """
        logger.info(f"Starting incremental indexing: {repository_path}")

        # Load existing state
        state = self.storage.get_index_state()
        if not state:
            logger.warning("No existing index, falling back to full indexing")
            from codecontext.indexer.sync.full import FullIndexStrategy

            full_strategy = FullIndexStrategy(self.config, self.embedding_provider, self.storage)
            return await full_strategy.index(repository_path, show_progress)

        # Detect changes
        changed_code_files, changed_doc_files = await self._detect_changes(repository_path)

        total_changed = len(changed_code_files) + len(changed_doc_files)
        if total_changed == 0:
            logger.info("No changes detected")
            return state  # type: ignore[no-any-return]

        logger.info(
            f"Detected {len(changed_code_files)} code files, "
            f"{len(changed_doc_files)} documents changed"
        )

        # Process code files with embedding reuse
        code_stats = await self.process_code_files(
            file_paths=changed_code_files,
            show_progress=show_progress,
            reuse_embeddings=True,
        )

        # Process documents
        total_documents = await self.process_documents(
            file_paths=changed_doc_files,
            show_progress=show_progress,
        )

        # Get current commit
        current_commit = ""
        try:
            git_ops = GitOperations(repository_path)
            current_commit = git_ops.get_current_commit()
        except (ValueError, OSError) as e:
            logger.warning(f"Not a git repository: {e}")

        # Update languages with newly indexed languages
        # Merge existing languages with new ones
        existing_languages = set(state.languages) if state.languages else set()
        new_languages = set(code_stats.get_languages_list())
        merged_languages = sorted(existing_languages | new_languages)

        # Update state
        state.last_commit_hash = current_commit
        state.last_indexed_at = datetime.now(UTC)
        state.total_files = total_changed
        state.total_objects = code_stats.total_objects
        state.total_documents = total_documents
        state.languages = merged_languages
        state.index_version = "0.3.0"
        state.status = IndexStatus.IDLE

        self.storage.update_index_state(state)

        logger.info("Incremental indexing completed")
        return state  # type: ignore[no-any-return]

    async def _detect_changes(self, repository_path: Path) -> tuple[list[Path], list[Path]]:
        """Detect changed files using checksums.

        Args:
            repository_path: Repository path

        Returns:
            (changed_code_files, changed_document_files)
        """
        from codecontext.utils.checksum import calculate_file_checksum

        scanner = FileScanner(repository_path, self.config)
        all_code_files = scanner.scan_code_files()
        all_doc_files = scanner.scan_document_files()

        # Detect changed code files using batch checksum comparison
        changed_code, _ = self.checksum_optimizer.should_skip_files_batch(all_code_files)

        # Detect changed document files
        changed_docs = []
        for doc_file in all_doc_files:
            current_checksum = calculate_file_checksum(doc_file)
            stored_checksum_obj = self.storage.get_file_checksum(str(doc_file))
            stored_checksum = stored_checksum_obj.file_checksum if stored_checksum_obj else None

            if current_checksum != stored_checksum:
                changed_docs.append(doc_file)

        return changed_code, changed_docs
