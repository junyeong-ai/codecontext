"""Full indexing strategy with memory-bounded chunked processing."""

import logging
from datetime import UTC, datetime
from pathlib import Path

from codecontext_core.models import IndexState, IndexStatus

from codecontext.indexer.strategy import AsyncIndexStrategy
from codecontext.indexer.sync.discovery import FileScanner
from codecontext.utils.git_ops import GitOperations

logger = logging.getLogger(__name__)


class FullIndexStrategy(AsyncIndexStrategy):
    """Full indexing with memory-bounded chunked processing."""

    async def index(self, repository_path: Path, show_progress: bool = True) -> IndexState:
        """Perform full indexing with chunked processing.

        Args:
            repository_path: Repository path
            show_progress: Show progress

        Returns:
            Index state

        Raises:
            IndexingError: If indexing fails
        """
        logger.info(f"Starting full indexing: {repository_path}")

        # Scan files
        scanner = FileScanner(repository_path, self.config)
        code_files = scanner.scan_code_files()
        document_files = scanner.scan_document_files()

        logger.info(
            f"Found {len(code_files)} code files, {len(document_files)} documents "
            f"(chunk_size={self.config.indexing.file_chunk_size})"
        )

        # Process code files in chunks
        code_stats = await self.process_code_files(
            file_paths=code_files,
            show_progress=show_progress,
            reuse_embeddings=False,
        )

        # Process documents in chunks
        total_documents = await self.process_documents(
            file_paths=document_files,
            show_progress=show_progress,
        )

        # Get current commit
        current_commit = ""
        try:
            git_ops = GitOperations(repository_path)
            current_commit = git_ops.get_current_commit()
        except Exception as e:
            logger.warning(f"Not a git repository: {e}")

        # Create state with absolute paths and proper project identification
        from codecontext.utils.project import get_project_id

        abs_repo_path = repository_path.resolve()

        state = IndexState(
            project_id=get_project_id(abs_repo_path),
            project_name=abs_repo_path.name,
            repository_path=str(abs_repo_path),
            last_commit_hash=current_commit,
            last_indexed_at=datetime.now(UTC),
            total_files=len(code_files) + len(document_files),
            total_objects=code_stats.total_objects,
            total_documents=total_documents,
            languages=self.config.indexing.languages,
            index_version="0.3.0",
            status=IndexStatus.IDLE,
        )

        self.storage.update_index_state(state)

        logger.info("Full indexing completed")
        return state
