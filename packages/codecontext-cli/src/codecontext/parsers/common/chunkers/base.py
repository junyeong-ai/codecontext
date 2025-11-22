"""Base interfaces for code chunking strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from codecontext_core.models.cast_chunk import CASTChunk
from tree_sitter import Node


class ChunkingStrategy(Enum):
    """Available chunking strategies."""

    CAST = "cast"
    """cAST-style semantic chunking that preserves structure."""

    LINE_BASED = "line_based"
    """Simple line-based chunking (fallback for malformed files)."""


@dataclass
class ChunkingConfig:
    """Configuration for chunking behavior."""

    strategy: ChunkingStrategy = ChunkingStrategy.CAST
    """Chunking strategy to use."""

    max_tokens: int = 512
    """Maximum tokens per chunk."""

    min_tokens: int = 50
    """Minimum tokens per chunk (avoid too small chunks)."""

    include_context: bool = True
    """Whether to include context (imports, parent definitions)."""

    preserve_structure: bool = True
    """Whether to preserve semantic structure (no mid-function splits)."""

    overlap_tokens: int = 0
    """Number of tokens to overlap between chunks (for context)."""

    language_specific: bool = True
    """Whether to use language-specific optimizations."""


class BaseChunker(ABC):
    """Abstract base class for code chunking implementations."""

    def __init__(self, config: ChunkingConfig | None = None) -> None:
        """Initialize chunker with configuration.

        Args:
            config: Chunking configuration. Uses defaults if not provided.
        """
        self.config = config or ChunkingConfig()

    @abstractmethod
    def chunk_file(self, file_path: Path, source_code: str, language: str) -> list[CASTChunk]:
        """Chunk an entire file into semantic units.

        Args:
            file_path: Path to the source file
            source_code: Complete source code content
            language: Programming language

        Returns:
            List of CASTChunk objects representing the file

        Raises:
            ValueError: If the file cannot be chunked
        """
        pass

    @abstractmethod
    def chunk_ast_node(
        self,
        node: Node,
        source_bytes: bytes,
        file_path: Path,
        language: str,
        parent_chunk_id: str | None = None,
    ) -> list[CASTChunk]:
        """Chunk a specific AST node and its children.

        Args:
            node: Tree-sitter AST node to chunk
            source_bytes: Original source code as bytes
            file_path: Path to the source file
            language: Programming language
            parent_chunk_id: ID of parent chunk if this is nested

        Returns:
            List of CASTChunk objects for this node and its children

        Raises:
            ValueError: If the node cannot be chunked
        """
        pass

    def estimate_tokens(self, text: str) -> int:
        """Estimate the number of tokens in text.

        Default implementation uses simple character-based estimation.
        Override for more accurate language-specific estimation.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        # Rough estimate: 1 token ≈ 4 characters
        return len(text) // 4

    def should_split_node(self, node: Node, source_bytes: bytes) -> bool:
        """Determine if a node should be split into smaller chunks.

        Args:
            node: Tree-sitter AST node
            source_bytes: Original source code

        Returns:
            True if the node should be split
        """
        node_text = source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
        estimated_tokens = self.estimate_tokens(node_text)
        return estimated_tokens > self.config.max_tokens

    def generate_chunk_id(self, file_path: Path, start_byte: int, end_byte: int) -> str:
        """Generate a deterministic ID for a chunk.

        Args:
            file_path: Path to the source file
            start_byte: Starting byte offset
            end_byte: Ending byte offset

        Returns:
            Deterministic chunk ID
        """
        import hashlib

        # Create deterministic ID from file path and location
        id_string = f"{file_path}:{start_byte}:{end_byte}"
        return hashlib.sha256(id_string.encode()).hexdigest()[:16]

    def extract_line_info(
        self, source_bytes: bytes, start_byte: int, end_byte: int
    ) -> tuple[int, int]:
        """Extract line number information for a byte range.

        Args:
            source_bytes: Original source code
            start_byte: Starting byte offset
            end_byte: Ending byte offset

        Returns:
            Tuple of (start_line, end_line) numbers (1-indexed)
        """
        # Count newlines up to start_byte
        start_line = source_bytes[:start_byte].count(b"\n") + 1

        # Count newlines up to end_byte
        end_line = source_bytes[:end_byte].count(b"\n") + 1

        return start_line, end_line

    def validate_chunk(self, chunk: CASTChunk) -> bool:
        """Validate that a chunk meets requirements.

        Args:
            chunk: Chunk to validate

        Returns:
            True if the chunk is valid
        """
        # Check minimum size
        if chunk.token_count < self.config.min_tokens:
            return False

        # Check maximum size
        if chunk.token_count > self.config.max_tokens * 1.5:  # Allow some overflow
            return False

        # Check that content includes raw_content
        return not (chunk.raw_content and chunk.raw_content not in chunk.content)


class FallbackChunker(BaseChunker):
    """Simple fallback chunker for when AST parsing fails."""

    def chunk_file(self, file_path: Path, source_code: str, language: str) -> list[CASTChunk]:
        """Chunk file using simple line-based splitting."""
        lines = source_code.split("\n")
        chunks = []

        current_chunk_lines: list[str] = []
        current_tokens = 0
        start_line = 1

        for i, line in enumerate(lines, 1):
            line_tokens = self.estimate_tokens(line)

            if current_tokens + line_tokens > self.config.max_tokens and current_chunk_lines:
                # Create chunk from accumulated lines
                chunk_content = "\n".join(current_chunk_lines)
                chunk = CASTChunk(
                    deterministic_id=self.generate_chunk_id(file_path, start_line, i - 1),
                    file_path=file_path,
                    language=language,
                    content=chunk_content,
                    raw_content=chunk_content,
                    start_line=start_line,
                    end_line=i - 1,
                    token_count=current_tokens,
                    node_type="lines",
                    name=f"Lines {start_line}-{i - 1}",
                )
                chunks.append(chunk)

                # Reset for next chunk
                current_chunk_lines = [line]
                current_tokens = line_tokens
                start_line = i
            else:
                current_chunk_lines.append(line)
                current_tokens += line_tokens

        # Don't forget the last chunk
        if current_chunk_lines:
            chunk_content = "\n".join(current_chunk_lines)
            chunk = CASTChunk(
                deterministic_id=self.generate_chunk_id(file_path, start_line, len(lines)),
                file_path=file_path,
                language=language,
                content=chunk_content,
                raw_content=chunk_content,
                start_line=start_line,
                end_line=len(lines),
                token_count=current_tokens,
                node_type="lines",
                name=f"Lines {start_line}-{len(lines)}",
            )
            chunks.append(chunk)

        return chunks

    def chunk_ast_node(
        self,
        node: Node,
        source_bytes: bytes,
        file_path: Path,
        language: str,
        parent_chunk_id: str | None = None,
    ) -> list[CASTChunk]:
        """Fallback: Convert node to simple chunk."""
        node_text = source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
        start_line, end_line = self.extract_line_info(source_bytes, node.start_byte, node.end_byte)

        chunk = CASTChunk(
            deterministic_id=self.generate_chunk_id(file_path, node.start_byte, node.end_byte),
            file_path=file_path,
            language=language,
            content=node_text,
            raw_content=node_text,
            start_line=start_line,
            end_line=end_line,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            token_count=self.estimate_tokens(node_text),
            node_type=node.type,
            parent_chunk_id=parent_chunk_id,
        )

        return [chunk]
