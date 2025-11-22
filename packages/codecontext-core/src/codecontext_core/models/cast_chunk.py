"""CASTChunk data model for structure-preserving AST chunking."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class CASTChunk:
    """Structure-preserving AST chunk following cAST methodology.

    Represents a semantically complete code unit with preserved context,
    ensuring each chunk can be understood independently while maintaining
    relationships to parent and child chunks.
    """

    # Identity fields
    deterministic_id: str
    """Unique hash-based ID for the chunk."""

    file_path: Path
    """Source file path."""

    language: str
    """Programming language (python, kotlin, java, javascript, typescript)."""

    # Content fields
    content: str
    """Complete chunk content including added context (imports, parent definitions)."""

    raw_content: str
    """Original code without any added context."""

    # Context elements
    imports: list[str] = field(default_factory=list)
    """Relevant import statements included for context."""

    parent_definition: Optional[str] = None
    """Parent class/module definition if chunk is nested."""

    # Location metadata
    start_line: int = 0
    """Starting line number in the source file."""

    end_line: int = 0
    """Ending line number in the source file."""

    start_byte: int = 0
    """Starting byte offset in the source file."""

    end_byte: int = 0
    """Ending byte offset in the source file."""

    token_count: int = 0
    """Estimated token count for the chunk."""

    # Semantic information
    node_type: str = ""
    """AST node type (function_definition, class_definition, etc.)."""

    name: str = ""
    """Name of the code entity (function name, class name, etc.)."""

    signature: Optional[str] = None
    """Function/method signature if applicable."""

    docstring: Optional[str] = None
    """Extracted documentation string if present."""

    # Relationships
    parent_chunk_id: Optional[str] = None
    """ID of the parent chunk for nested structures."""

    child_chunk_ids: list[str] = field(default_factory=list)
    """IDs of child chunks contained within this chunk."""

    # Language-specific metadata
    language_metadata: dict[str, Any] = field(default_factory=dict)
    """Language-specific information (type hints, decorators, annotations, etc.)."""

    # Search optimization
    search_keywords: Optional[list[str]] = None
    """Additional search keywords for improved discoverability."""

    def __post_init__(self) -> None:
        """Validate chunk data after initialization."""
        # Ensure Path object
        if not isinstance(self.file_path, Path):
            self.file_path = Path(self.file_path)

        # Validate content relationship
        if self.raw_content and self.raw_content not in self.content:
            raise ValueError("raw_content must be a substring of content")

        # Validate token count
        if self.token_count < 0:
            raise ValueError("token_count must be non-negative")

        # Validate language
        valid_languages = {"python", "kotlin", "java", "javascript", "typescript"}
        if self.language and self.language.lower() not in valid_languages:
            raise ValueError("Invalid value")

    @property
    def is_nested(self) -> bool:
        """Check if this chunk is nested within another chunk."""
        return self.parent_chunk_id is not None

    @property
    def has_children(self) -> bool:
        """Check if this chunk contains child chunks."""
        return len(self.child_chunk_ids) > 0

    @property
    def context_size(self) -> int:
        """Calculate the size of added context in characters."""
        return len(self.content) - len(self.raw_content)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "deterministic_id": self.deterministic_id,
            "file_path": str(self.file_path),
            "language": self.language,
            "content": self.content,
            "raw_content": self.raw_content,
            "imports": self.imports,
            "parent_definition": self.parent_definition,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "start_byte": self.start_byte,
            "end_byte": self.end_byte,
            "token_count": self.token_count,
            "node_type": self.node_type,
            "name": self.name,
            "signature": self.signature,
            "docstring": self.docstring,
            "parent_chunk_id": self.parent_chunk_id,
            "child_chunk_ids": self.child_chunk_ids,
            "language_metadata": self.language_metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CASTChunk":
        """Create from dictionary representation."""
        return cls(
            deterministic_id=data["deterministic_id"],
            file_path=Path(data["file_path"]),
            language=data["language"],
            content=data["content"],
            raw_content=data["raw_content"],
            imports=data.get("imports", []),
            parent_definition=data.get("parent_definition"),
            start_line=data.get("start_line", 0),
            end_line=data.get("end_line", 0),
            start_byte=data.get("start_byte", 0),
            end_byte=data.get("end_byte", 0),
            token_count=data.get("token_count", 0),
            node_type=data.get("node_type", ""),
            name=data.get("name", ""),
            signature=data.get("signature"),
            docstring=data.get("docstring"),
            parent_chunk_id=data.get("parent_chunk_id"),
            child_chunk_ids=data.get("child_chunk_ids", []),
            language_metadata=data.get("language_metadata", {}),
        )
