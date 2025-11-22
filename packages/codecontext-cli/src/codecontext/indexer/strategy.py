"""Memory-bounded chunked indexing strategy.

All indexing operations use chunked processing with explicit memory management
to ensure O(1) memory usage regardless of repository size.
"""

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from codecontext_core.interfaces import EmbeddingProvider, TranslationProvider
from codecontext_core.models import CodeObject, DocumentNode, Relationship

from codecontext.config.schema import Config

if TYPE_CHECKING:
    from codecontext.indexer.extractor import ImportInfo
import logging

from codecontext_core import VectorStore

from codecontext.indexer.chunking import (
    ChunkStats,
    MemoryManager,
    ProcessingStats,
)
from codecontext.indexer.chunking import (
    chunk_files as iter_chunks,
)
from codecontext.parsers.languages.config import ConfigFileParser
from codecontext.parsers.languages.markdown import MarkdownParser

logger = logging.getLogger(__name__)


class AsyncIndexStrategy:
    """Memory-bounded chunked indexing strategy.

    Processes files in chunks to maintain constant memory usage.
    Supports any embedding provider (HuggingFace, OpenAI, etc.).
    """

    def __init__(
        self,
        config: Config,
        embedding_provider: EmbeddingProvider,
        storage: VectorStore,
        translation_provider: TranslationProvider | None = None,
    ) -> None:
        """Initialize strategy.

        Args:
            config: Configuration
            embedding_provider: Any embedding provider
            storage: Vector storage
            translation_provider: Optional translation provider
        """
        self.config = config
        self.embedding_provider = embedding_provider
        self.storage = storage
        self.translation_provider = translation_provider
        # Initialize document parsers with proper defaults
        self.markdown_parser = MarkdownParser(chunk_size=512, chunk_overlap=50)
        self.config_parser = ConfigFileParser()

        # Initialize language detector if translation is enabled
        from codecontext.utils.language import LanguageDetector

        if self.translation_provider:
            self.language_detector: LanguageDetector | None = LanguageDetector()
        else:
            self.language_detector = None

        # Initialize parser factory and extractor
        from codecontext.indexer.extractor import Extractor
        from codecontext.parsers.factory import ParserFactory

        self.parser_factory = ParserFactory.from_parsing_config(config.indexing.parsing)
        self.extractor = Extractor(self.parser_factory)

        # Memory manager
        self.memory_manager: MemoryManager = MemoryManager(config)

    # ═══════════════════════════════════════════════════════════
    # PUBLIC API: Chunked Processing
    # ═══════════════════════════════════════════════════════════

    async def process_code_files(
        self,
        file_paths: list[Path],
        show_progress: bool = True,
        reuse_embeddings: bool = False,
    ) -> ProcessingStats:
        if not file_paths:
            return ProcessingStats()

        chunk_size = self.config.indexing.file_chunk_size
        stats = ProcessingStats()

        logger.info(
            f"Processing {len(file_paths)} files "
            f"(chunk_size={chunk_size}, reuse={reuse_embeddings})"
        )

        async for chunk_index, chunk_files in iter_chunks(file_paths, chunk_size):
            await self.embedding_provider.cleanup()

            chunk_stats = await self._process_code_chunk(
                chunk_files=chunk_files,
                chunk_index=chunk_index,
                show_progress=show_progress,
                reuse_embeddings=reuse_embeddings,
            )

            stats.add_chunk(chunk_stats)
            stats.total_chunks += 1
            self.memory_manager.create_memory_barrier()

            logger.info(
                f"Chunk {chunk_index + 1}: "
                f"{chunk_stats.objects_count} objects "
                f"(total: {stats.total_objects})"
            )

        logger.info(f"Processing complete: {stats.total_objects} objects")
        return stats

    async def process_documents(
        self,
        file_paths: list[Path],
        show_progress: bool = True,
    ) -> int:
        """Process document files in memory-bounded chunks.

        Args:
            file_paths: Document files
            show_progress: Show progress bars

        Returns:
            Total documents processed
        """
        if not file_paths:
            return 0

        chunk_size = self.config.indexing.file_chunk_size
        total_documents = 0

        logger.info(f"Processing {len(file_paths)} documents (chunk_size={chunk_size})")

        async for chunk_index, chunk_files in iter_chunks(file_paths, chunk_size):
            chunk_docs = await self._process_document_chunk(
                chunk_files=chunk_files,
                chunk_index=chunk_index,
                show_progress=show_progress,
            )

            total_documents += len(chunk_docs)
            self.memory_manager.create_memory_barrier()

        logger.info("=" * 80)
        logger.info("✅ DOCUMENT INDEXING COMPLETE")
        logger.info(f"   Total: {total_documents} documents indexed")
        logger.info("=" * 80)

        return total_documents

    # ═══════════════════════════════════════════════════════════
    # CHUNK PROCESSING
    # ═══════════════════════════════════════════════════════════

    async def _process_code_chunk(
        self,
        chunk_files: list[Path],
        chunk_index: int,
        show_progress: bool,
        reuse_embeddings: bool,
    ) -> ChunkStats:
        """Process single code chunk.

        Args:
            chunk_files: Files in chunk
            chunk_index: Chunk index
            show_progress: Show progress
            reuse_embeddings: Reuse embeddings

        Returns:
            Chunk statistics
        """

        # Extract
        chunk_objects, chunk_relationships = await self._extract_files(chunk_files)

        # Embeddings
        if reuse_embeddings:
            chunk_objects, gen, reused = await self._embed_incremental(chunk_objects, show_progress)
        else:
            chunk_objects = await self._embed(chunk_objects, show_progress)
            gen, reused = len(chunk_objects), 0

        await self._store_objects(chunk_objects, chunk_relationships, show_progress)

        stats = ChunkStats(
            chunk_index=chunk_index,
            files_processed=len(chunk_files),
            objects_count=len(chunk_objects),
            relationships_count=len(chunk_relationships),
            embeddings_generated=gen,
            embeddings_reused=reused,
        )

        del chunk_objects, chunk_relationships
        return stats

    async def _process_document_chunk(
        self,
        chunk_files: list[Path],
        chunk_index: int,
        show_progress: bool,
    ) -> list[DocumentNode]:
        """Process single document chunk.

        Args:
            chunk_files: Files in chunk
            chunk_index: Chunk index
            show_progress: Show progress

        Returns:
            Document nodes
        """
        chunk_documents: list[DocumentNode] = []

        # Parse files
        logger.info(f"Parsing {len(chunk_files)} files in chunk {chunk_index}")
        for file_path in chunk_files:
            try:
                if file_path.suffix.lower() in [".md", ".markdown"]:
                    logger.debug(f"Parsing markdown file: {file_path}")
                    docs = self.markdown_parser.parse_file(file_path)
                    chunk_documents.extend(docs)
                    logger.debug(f"Parsed {len(docs)} chunks from {file_path}")
                elif self.config_parser.is_supported(file_path):
                    logger.debug(f"Parsing config file: {file_path}")
                    docs = self.config_parser.parse_file(file_path)
                    chunk_documents.extend(docs)
                    logger.debug(f"Parsed {len(docs)} chunks from {file_path}")
            except (ValueError, OSError, RuntimeError) as e:
                logger.warning(f"Failed to process {file_path}: {e}")

        logger.info(
            f"Parsed {len(chunk_documents)} total document chunks from {len(chunk_files)} files"
        )

        # Translation (if enabled)
        if chunk_documents and self.translation_provider and self.language_detector:
            logger.info(f"Translating {len(chunk_documents)} document chunks")
            chunk_documents = await self._translate_documents(chunk_documents, show_progress)
            logger.info(f"Translation complete for {len(chunk_documents)} document chunks")

        # Embeddings and storage
        if chunk_documents:
            logger.info(f"Generating embeddings for {len(chunk_documents)} document chunks")
            chunk_documents = await self._embed_documents(chunk_documents, show_progress)
            logger.info(f"Storing {len(chunk_documents)} document chunks")
            await self._store_documents(chunk_documents, show_progress)
            logger.info(f"Successfully stored {len(chunk_documents)} document chunks")
        else:
            logger.warning(
                f"No documents parsed from chunk {chunk_index} - skipping embedding and storage"
            )

        return chunk_documents

    # ═══════════════════════════════════════════════════════════
    # EXTRACTION
    # ═══════════════════════════════════════════════════════════

    async def _extract_files(
        self, file_paths: list[Path]
    ) -> tuple[list[CodeObject], list[Relationship]]:
        """Extract files sequentially with controlled concurrency."""
        from codecontext.indexer.extractor import ExtractionResult

        max_concurrent = self._get_concurrency()
        semaphore = asyncio.Semaphore(max_concurrent)

        async def extract_one(file_path: Path) -> ExtractionResult | None:
            async with semaphore:
                try:
                    return await self.extractor.extract_from_file(str(file_path))
                except Exception as e:
                    logger.warning(f"Extraction failed for {file_path}: {e}")
                    return None

        all_objects = []
        all_relationships = []
        all_imports = []

        tasks = [extract_one(fp) for fp in file_paths]
        results = await asyncio.gather(*tasks)

        for result in results:
            if result:
                all_objects.extend(result.objects)
                all_relationships.extend(result.relationships)
                all_imports.extend(result.imports)

        logger.debug(f"Extracted {len(all_objects)} objects from {len(file_paths)} files")
        self._set_parent_ids(all_objects)

        # Resolve import relationships (cross-file)
        import_relationships = self._resolve_import_relationships(all_imports, all_objects)
        all_relationships.extend(import_relationships)

        logger.debug(
            f"Resolved {len(import_relationships)} IMPORTS relationships "
            f"from {len(all_imports)} import statements"
        )

        # Auto-generate reverse relationships
        from codecontext_core.relationship_utils import create_reverse_relationship

        reverse_relationships = []
        for rel in all_relationships:
            reverse_rel = create_reverse_relationship(rel)
            if reverse_rel:
                reverse_relationships.append(reverse_rel)

        all_relationships.extend(reverse_relationships)
        logger.debug(f"Generated {len(reverse_relationships)} reverse relationships")

        return all_objects, all_relationships

    def _set_parent_ids(self, objects: list[CodeObject]) -> None:
        """Set parent_deterministic_id.

        Args:
            objects: Code objects
        """
        id_map = {obj.id: obj.deterministic_id for obj in objects}
        for obj in objects:
            if obj.parent_id and isinstance(obj.parent_id, UUID) and obj.parent_id in id_map:
                obj.parent_deterministic_id = id_map[obj.parent_id]

    def _resolve_import_relationships(
        self, imports: list["ImportInfo"], objects: list[CodeObject]
    ) -> list[Relationship]:
        from codecontext_core.models import Relationship, RelationType

        if not imports or not objects:
            return []

        name_map: dict[str, list[CodeObject]] = {}
        file_map: dict[str, list[CodeObject]] = {}
        path_index: dict[str, list[CodeObject]] = {}

        for obj in objects:
            if obj.name not in name_map:
                name_map[obj.name] = []
            name_map[obj.name].append(obj)

            if obj.relative_path not in file_map:
                file_map[obj.relative_path] = []
            file_map[obj.relative_path].append(obj)

            normalized_path = obj.relative_path.replace("/", ".").replace(".py", "")
            if normalized_path not in path_index:
                path_index[normalized_path] = []
            path_index[normalized_path].append(obj)

        relationships = []
        for import_info in imports:
            matched = self._match_import_to_objects(import_info.imported_name, name_map, path_index)
            source_objects = file_map.get(import_info.source_file, [])
            if not source_objects:
                continue

            source_obj = source_objects[0]
            for target_obj in matched:
                relationships.append(
                    Relationship(
                        source_id=source_obj.deterministic_id,
                        source_type=source_obj.object_type.value,
                        target_id=target_obj.deterministic_id,
                        target_type=target_obj.object_type.value,
                        relation_type=RelationType.IMPORTS,
                        confidence=0.8,
                    )
                )

        return relationships

    def _match_import_to_objects(
        self,
        imported_name: str,
        name_map: dict[str, list[CodeObject]],
        path_index: dict[str, list[CodeObject]],
    ) -> list[CodeObject]:
        matched = []

        if imported_name in name_map:
            matched.extend(name_map[imported_name])

        if "." in imported_name:
            last_segment = imported_name.split(".")[-1]
            if last_segment in name_map:
                matched.extend(name_map[last_segment])

            if imported_name in path_index:
                matched.extend(path_index[imported_name])

        seen = set()
        unique = []
        for obj in matched:
            if obj.deterministic_id not in seen:
                seen.add(obj.deterministic_id)
                unique.append(obj)

        return unique

    def _get_concurrency(self) -> int:
        """Get extraction concurrency.

        Returns:
            Concurrency level
        """
        import os

        workers = self.config.indexing.parallel_workers
        if workers > 0:
            return workers

        cpu_count = os.cpu_count() or 4
        return min(cpu_count // 2, 8)

    # ═══════════════════════════════════════════════════════════
    # EMBEDDINGS (Provider-agnostic)
    # ═══════════════════════════════════════════════════════════

    async def _embed(
        self, objects: list[CodeObject], show_progress: bool = True
    ) -> list[CodeObject]:
        """Generate embeddings with instruction prefixes.

        Applies appropriate instruction types:
        - Code content: NL2CODE_PASSAGE
        - Docstrings: QA_PASSAGE

        Args:
            objects: Code objects
            show_progress: Show progress

        Returns:
            Objects with embeddings
        """
        if not objects:
            return []

        from codecontext.utils.streaming_progress import SimpleProgress

        batch_size = self.embedding_provider.get_batch_size()
        progress = SimpleProgress(total=len(objects), desc="Embeddings") if show_progress else None

        # Separate objects by embedding type
        code_objects = [obj for obj in objects if not obj.docstring]
        docstring_objects = [obj for obj in objects if obj.docstring]

        # Embed code content (primary content for all objects)
        if code_objects:

            async def code_batch_generator() -> AsyncGenerator[list[str], None]:
                for i in range(0, len(code_objects), batch_size):
                    batch = code_objects[i : i + batch_size]
                    texts = []
                    for obj in batch:
                        instruction = (
                            self.config.embeddings.huggingface.instructions.nl2code_passage
                        )
                        texts.append(instruction + obj.content)
                    yield texts

            batch_index = 0
            async for embeddings in self.embedding_provider.embed_stream(
                code_batch_generator(), progress=progress
            ):
                start_idx = batch_index * batch_size
                end_idx = min(start_idx + batch_size, len(code_objects))

                for i, embedding in enumerate(embeddings):
                    if start_idx + i < end_idx:
                        code_objects[start_idx + i].embedding = embedding

                batch_index += 1

        # Embed docstrings separately (QA task)
        if docstring_objects:

            async def docstring_batch_generator() -> AsyncGenerator[list[str], None]:
                for i in range(0, len(docstring_objects), batch_size):
                    batch = docstring_objects[i : i + batch_size]
                    texts = []
                    for obj in batch:
                        instruction = self.config.embeddings.huggingface.instructions.qa_passage
                        texts.append(instruction + (obj.docstring or ""))
                    yield texts

            batch_index = 0
            async for embeddings in self.embedding_provider.embed_stream(
                docstring_batch_generator(), progress=progress
            ):
                start_idx = batch_index * batch_size
                end_idx = min(start_idx + batch_size, len(docstring_objects))

                for i, embedding in enumerate(embeddings):
                    if start_idx + i < end_idx:
                        docstring_objects[start_idx + i].embedding = embedding

                batch_index += 1

        return objects

    async def _embed_incremental(
        self, objects: list[CodeObject], show_progress: bool = True
    ) -> tuple[list[CodeObject], int, int]:
        """Generate embeddings incrementally with reuse.

        Args:
            objects: Code objects
            show_progress: Show progress

        Returns:
            (objects, generated_count, reused_count)
        """
        if not objects:
            return [], 0, 0

        # Fetch existing
        ids = [obj.deterministic_id for obj in objects]
        existing = self.storage.get_code_objects_batch(ids)
        existing_map = {
            obj.deterministic_id: obj.embedding for obj in existing if obj.embedding is not None
        }

        # Separate
        to_generate = []
        reused = 0

        for obj in objects:
            if obj.deterministic_id in existing_map:
                obj.embedding = existing_map[obj.deterministic_id]
                reused += 1
            else:
                to_generate.append(obj)

        # Generate new
        generated = 0
        if to_generate:
            await self._embed(to_generate, show_progress)
            generated = len(to_generate)

        logger.debug(f"Embeddings: {generated} generated, {reused} reused")
        return objects, generated, reused

    async def _embed_documents(
        self, documents: list[DocumentNode], show_progress: bool = True
    ) -> list[DocumentNode]:
        """Generate document embeddings with QA instruction."""
        if not documents:
            return []

        from codecontext.utils.streaming_progress import SimpleProgress

        batch_size = self.embedding_provider.get_batch_size()
        progress = SimpleProgress(total=len(documents), desc="Documents") if show_progress else None

        async def batch_generator() -> AsyncGenerator[list[str], None]:
            for i in range(0, len(documents), batch_size):
                batch = documents[i : i + batch_size]
                texts = []
                for doc in batch:
                    instruction = self.config.embeddings.huggingface.instructions.qa_passage
                    texts.append(instruction + doc.content)
                yield texts

        batch_index = 0
        async for embeddings in self.embedding_provider.embed_stream(
            batch_generator(), progress=progress
        ):
            start_idx = batch_index * batch_size
            end_idx = min(start_idx + batch_size, len(documents))

            for i, embedding in enumerate(embeddings):
                if start_idx + i < end_idx:
                    documents[start_idx + i].embedding = embedding

            batch_index += 1

        return documents

    async def _translate_documents(
        self, documents: list[DocumentNode], show_progress: bool = True
    ) -> list[DocumentNode]:
        """Translate documents to English if needed.

        Args:
            documents: Document nodes
            show_progress: Show progress

        Returns:
            Documents with translated content
        """
        if not documents or not self.translation_provider or not self.language_detector:
            return documents

        from codecontext.utils.streaming_progress import SimpleProgress

        translated_count = 0
        progress = (
            SimpleProgress(total=len(documents), desc="Translation") if show_progress else None
        )

        for doc in documents:
            if not doc.content or not doc.content.strip():
                continue

            lang = self.language_detector.detect(doc.content)

            if lang != "en":
                try:
                    translated_content = self.translation_provider.translate_text(
                        doc.content, source_lang=lang, target_lang="en"
                    )

                    doc.metadata["original_text"] = doc.content
                    doc.metadata["original_lang"] = lang
                    doc.content = translated_content
                    translated_count += 1

                    logger.debug(f"Translated document from {lang} to en: {doc.id}")
                except Exception as e:
                    logger.warning(f"Translation failed for document {doc.id}: {e}")

            if progress:
                progress.update(1)

        if progress:
            progress.close()

        logger.info(f"Translated {translated_count}/{len(documents)} documents to English")
        return documents

    # ═══════════════════════════════════════════════════════════
    # STORAGE
    # ═══════════════════════════════════════════════════════════

    async def _store_objects(
        self,
        objects: list[CodeObject],
        relationships: list[Relationship],
        show_progress: bool = True,
    ) -> None:
        if not objects:
            return

        batch_size = self.config.indexing.batch_size

        for i in range(0, len(objects), batch_size):
            obj_batch = objects[i : i + batch_size]
            self.storage.add_code_objects(obj_batch, relationships)

    async def _store_documents(
        self, documents: list[DocumentNode], show_progress: bool = True
    ) -> None:
        """Store documents.

        Args:
            documents: Document nodes
            show_progress: Show progress
        """
        if not documents:
            return

        batch_size = self.config.indexing.batch_size

        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            self.storage.add_documents(batch)
