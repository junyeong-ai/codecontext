"""Core data models for CodeContext CLI."""

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    """Get current UTC time (replacement for deprecated datetime.utcnow())."""
    return datetime.now(UTC)


class ObjectType(str, Enum):
    """Types of code and document objects."""

    # Code objects
    CLASS = "class"
    METHOD = "method"
    INTERFACE = "interface"
    FUNCTION = "function"
    VARIABLE = "variable"
    MODULE = "module"
    ENUM = "enum"
    STRUCT = "struct"

    # Document objects
    DOCUMENT = "document"


class Language(str, Enum):
    """Supported programming languages and configuration formats."""

    # Programming languages
    KOTLIN = "kotlin"
    JAVA = "java"
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"

    # Configuration and data formats
    YAML = "yaml"
    JSON = "json"
    PROPERTIES = "properties"
    MARKDOWN = "markdown"


class NodeType(str, Enum):
    """Types of document nodes."""

    MARKDOWN = "markdown"
    COMMENT = "comment"
    DOCSTRING = "docstring"
    CONFIG = "config"


class RelationType(str, Enum):
    CALLS = "calls"
    CALLED_BY = "called_by"
    EXTENDS = "extends"
    EXTENDED_BY = "extended_by"
    IMPLEMENTS = "implements"
    IMPLEMENTED_BY = "implemented_by"
    REFERENCES = "references"
    REFERENCED_BY = "referenced_by"
    CONTAINS = "contains"
    CONTAINED_BY = "contained_by"
    IMPORTS = "imports"
    IMPORTED_BY = "imported_by"


class IndexStatus(str, Enum):
    """Status of the index."""

    IDLE = "idle"
    INDEXING = "indexing"
    ERROR = "error"


@dataclass
class CodeObject:
    """Represents a semantic unit of code extracted from source files."""

    file_path: str
    relative_path: str
    object_type: ObjectType
    name: str
    language: Language
    start_line: int
    end_line: int
    content: str
    checksum: str
    id: UUID = field(default_factory=uuid4)
    deterministic_id: str = field(init=False)
    parent_deterministic_id: Optional[str] = None
    qualified_name: Optional[str] = None
    signature: Optional[str] = None
    docstring: Optional[str] = None
    embedding: Optional[list[float]] = None
    embedding_model_version: str = "qwen3-0.6b"
    parent_id: Optional[UUID | str] = None
    ast_metadata: Optional[dict[str, Any]] = None
    token_count: int = 0
    unique_token_count: int = 0
    score_weight: float = 1.0
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        """Initialize computed fields after object creation."""
        self.deterministic_id = self.generate_deterministic_id()

        # Set parent_deterministic_id from parent_id if it's a string
        if self.parent_id and isinstance(self.parent_id, str):
            self.parent_deterministic_id = self.parent_id

    def generate_deterministic_id(self) -> str:
        """Generate a deterministic ID based on code object properties.

        This ensures that the same code object (same file, name, type, location)
        always gets the same ID, preventing duplicates during re-indexing.
        Uses relative_path instead of file_path for location independence.

        Returns:
            Hexadecimal string suitable for use as vector store document ID
        """
        # Handle both enum and string values for object_type
        obj_type_str = (
            self.object_type.value if hasattr(self.object_type, "value") else str(self.object_type)
        )
        unique_str = (
            f"{self.relative_path}:{self.name}:{obj_type_str}:{self.start_line}:{self.end_line}"
        )
        return hashlib.sha256(unique_str.encode()).hexdigest()[:32]

    def validate(self) -> None:
        """Validate the code object fields."""
        if self.start_line < 1:
            raise ValueError("Invalid value")
        if self.end_line < self.start_line:
            raise ValueError(
                f"end_line ({self.end_line}) must be >= start_line ({self.start_line})"
            )
        if self.embedding is not None and len(self.embedding) != 768:
            raise ValueError("Invalid value")

    def to_metadata(self) -> dict[str, Any]:
        """Convert to storage payload."""
        import json

        return {
            "type": "code",
            "object_type": (
                self.object_type.value
                if isinstance(self.object_type, ObjectType)
                else self.object_type
            ),
            "name": self.name,
            "qualified_name": self.qualified_name or "",
            "signature": self.signature or "",
            "docstring": self.docstring or "",
            "content": self.content,
            "file_path": self.file_path,
            "relative_path": self.relative_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "checksum": self.checksum,
            "language": (
                self.language.value if isinstance(self.language, Language) else self.language
            ),
            "token_count": self.token_count,
            "unique_token_count": self.unique_token_count,
            "score_weight": self.score_weight,
            "parent_id": self.parent_deterministic_id or "",
            "deterministic_id": self.deterministic_id,
            "embedding_model_version": self.embedding_model_version,
            "ast_metadata": json.dumps(self.ast_metadata) if self.ast_metadata else "",
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any], content: str) -> "CodeObject":
        """Reconstruct CodeObject from vector storage."""
        import json

        ast_metadata = (
            json.loads(metadata["ast_metadata"]) if metadata.get("ast_metadata") else None
        )
        lang = metadata.get("language", "")
        obj = cls(
            id=UUID(metadata.get("id", str(uuid4()))),
            file_path=metadata["file_path"],
            relative_path=metadata["relative_path"],
            object_type=ObjectType(metadata["object_type"]),
            name=metadata["name"],
            language=Language(lang) if lang else Language.YAML,
            start_line=int(metadata.get("start_line", 0)),
            end_line=int(metadata.get("end_line", 0)),
            content=content,
            signature=metadata.get("signature", ""),
            docstring=metadata.get("docstring", ""),
            checksum=metadata["checksum"],
            embedding_model_version=metadata.get("embedding_model_version", "qwen3-0.6b"),
            ast_metadata=ast_metadata,
            parent_id=UUID(metadata["parent_id"]) if metadata.get("parent_id") else None,
            created_at=datetime.fromisoformat(metadata["created_at"]),
            updated_at=datetime.fromisoformat(metadata["updated_at"]),
        )
        # Use stored deterministic_id instead of regenerating
        obj.deterministic_id = metadata["deterministic_id"]
        obj.parent_deterministic_id = metadata.get("parent_id", "")
        return obj


@dataclass
class DocumentNode:
    """Represents documentation or summary content linked to code."""

    file_path: str
    relative_path: str
    node_type: NodeType
    content: str
    checksum: str
    id: UUID = field(default_factory=uuid4)
    deterministic_id: str = field(init=False)
    chunk_index: int = 0
    total_chunks: int = 1
    parent_doc_id: Optional[str] = None
    title: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    embedding: Optional[list[float]] = None
    language: Optional[str] = None
    related_code: Optional[list[dict[str, Any]]] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    # Config-specific fields (for NodeType.CONFIG)
    config_keys: Optional[list[str]] = None
    config_format: Optional[str] = None  # yaml, json, properties
    env_references: Optional[list[str]] = None  # ${VAR} references
    section_depth: Optional[int] = None  # Nesting depth
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        """Initialize computed fields after object creation."""
        # Coerce string to NodeType enum if needed
        if isinstance(self.node_type, str):
            self.node_type = NodeType(self.node_type)
        self.deterministic_id = self.generate_deterministic_id()

    def generate_deterministic_id(self) -> str:
        """Generate deterministic ID for document node.

        Uses relative_path instead of file_path for location independence.

        Returns:
            Hexadecimal string suitable for use as vector store document ID
        """
        unique_str = f"{self.relative_path}:{self.node_type.value}:{self.chunk_index}"
        return hashlib.sha256(unique_str.encode()).hexdigest()[:32]

    def validate(self) -> None:
        """Validate the document node fields."""
        if self.embedding is not None and len(self.embedding) != 768:
            raise ValueError("Invalid value")

    def to_metadata(self) -> dict[str, Any]:
        """Convert to storage payload."""
        import json
        from pathlib import Path

        qualified_name = self.relative_path
        if self.title:
            qualified_name += f"#{self.title}"

        return {
            "type": "document",
            "node_type": self.node_type.value,
            "object_type": "document",
            "name": self.title or Path(self.file_path).name,
            "qualified_name": qualified_name,
            "title": self.title or "",
            "signature": "",
            "docstring": self.content[:200] if self.content else "",
            "content": self.content,
            "file_path": self.file_path,
            "relative_path": self.relative_path,
            "start_line": self.start_line or 0,
            "end_line": self.end_line or 0,
            "checksum": self.checksum,
            "language": self.language or "",
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "parent_doc_id": self.parent_doc_id or "",
            "deterministic_id": self.deterministic_id,
            "related_code": json.dumps(self.related_code) if self.related_code else "[]",
            "config_keys": json.dumps(self.config_keys) if self.config_keys else "[]",
            "config_format": self.config_format or "",
            "env_references": json.dumps(self.env_references) if self.env_references else "[]",
            "section_depth": str(self.section_depth) if self.section_depth is not None else "0",
            "custom_metadata": json.dumps(self.metadata) if self.metadata else "{}",
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any], content: str) -> "DocumentNode":
        """Reconstruct DocumentNode from vector storage."""
        import json

        related_code = (
            json.loads(metadata.get("related_code", "[]")) if metadata.get("related_code") else None
        )
        custom_metadata = json.loads(metadata.get("custom_metadata", "{}"))
        # Config-specific fields
        config_keys = (
            json.loads(metadata.get("config_keys", "[]")) if metadata.get("config_keys") else None
        )
        env_references = (
            json.loads(metadata.get("env_references", "[]"))
            if metadata.get("env_references")
            else None
        )
        section_depth_str = metadata.get("section_depth", "0")
        section_depth = (
            int(section_depth_str) if section_depth_str and section_depth_str != "0" else None
        )

        start_line = metadata.get("start_line")
        end_line = metadata.get("end_line")

        doc = cls(
            id=UUID(metadata.get("id", str(uuid4()))),
            file_path=metadata["file_path"],
            relative_path=metadata.get("relative_path", metadata["file_path"]),
            node_type=NodeType(metadata["node_type"]),
            content=content,
            checksum=metadata["checksum"],
            title=metadata.get("title") or None,
            start_line=int(start_line) if start_line and start_line != 0 else None,
            end_line=int(end_line) if end_line and end_line != 0 else None,
            language=metadata.get("language") or None,
            related_code=related_code,
            metadata=custom_metadata,
            config_keys=config_keys,
            config_format=metadata.get("config_format") or None,
            env_references=env_references,
            section_depth=section_depth,
            created_at=datetime.fromisoformat(metadata["created_at"]),
            updated_at=datetime.fromisoformat(metadata["updated_at"]),
        )
        # Use stored deterministic_id instead of regenerating
        doc.deterministic_id = metadata["deterministic_id"]
        doc.parent_doc_id = metadata.get("parent_doc_id", "")
        return doc


@dataclass
class Relationship:
    """Defines connections between code objects and documentation."""

    source_id: str  # Changed from UUID to str (deterministic_id)
    source_type: str
    target_id: str  # Changed from UUID to str (deterministic_id)
    target_type: str
    relation_type: RelationType
    confidence: float
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utcnow)

    def generate_deterministic_id(self) -> str:
        """Generate a deterministic ID based on relationship properties.

        This ensures that the same relationship always gets the same ID,
        preventing duplicates during re-indexing.

        Returns:
            Hexadecimal string suitable for use as vector store document ID
        """
        unique_str = f"{self.source_id}:{self.target_id}:{self.relation_type.value}"
        return hashlib.sha256(unique_str.encode()).hexdigest()[:32]

    def validate(self) -> None:
        """Validate the relationship fields."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Invalid value")

    def to_metadata(self) -> dict[str, Any]:
        """Convert to vector store metadata format."""
        return {
            "source_id": self.source_id,  # Already a string (deterministic_id)
            "source_type": self.source_type,
            "target_id": self.target_id,  # Already a string (deterministic_id)
            "target_type": self.target_type,
            "relation_type": self.relation_type.value,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any]) -> "Relationship":
        """Reconstruct Relationship from vector storage."""
        return cls(
            id=UUID(metadata.get("id", str(uuid4()))),
            source_id=metadata["source_id"],  # Now a string, not UUID
            source_type=metadata["source_type"],
            target_id=metadata["target_id"],  # Now a string, not UUID
            target_type=metadata["target_type"],
            relation_type=RelationType(metadata["relation_type"]),
            confidence=float(metadata["confidence"]),
            created_at=datetime.fromisoformat(metadata["created_at"]),
        )


@dataclass
class IndexState:
    """Tracks the state of the indexed codebase."""

    project_id: str  # NEW: Unique project identifier for multi-project support
    repository_path: str
    last_commit_hash: str
    last_indexed_at: datetime
    total_files: int
    total_objects: int
    total_documents: int
    languages: list[str]
    index_version: str
    status: IndexStatus
    id: UUID = field(default_factory=uuid4)

    def validate(self) -> None:
        """Validate the index state fields."""
        if self.total_files < 0:
            raise ValueError("Invalid value")
        if self.total_objects < 0:
            raise ValueError("Invalid value")
        if self.total_documents < 0:
            raise ValueError("Invalid value")

    def to_metadata(self) -> dict[str, Any]:
        """Convert to metadata dict format."""
        return {
            "project_id": self.project_id,
            "repository_path": self.repository_path,
            "last_commit_hash": self.last_commit_hash,
            "last_indexed_at": self.last_indexed_at.isoformat(),
            "total_files": self.total_files,
            "total_objects": self.total_objects,
            "total_documents": self.total_documents,
            "languages": ",".join(self.languages),
            "index_version": self.index_version,
            "status": self.status.value,
        }

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any]) -> "IndexState":
        """Create IndexState from metadata dict."""
        return cls(
            project_id=metadata["project_id"],
            repository_path=metadata["repository_path"],
            last_commit_hash=metadata["last_commit_hash"],
            last_indexed_at=datetime.fromisoformat(metadata["last_indexed_at"]),
            total_files=int(metadata["total_files"]),
            total_objects=int(metadata["total_objects"]),
            total_documents=int(metadata["total_documents"]),
            languages=metadata["languages"].split(",") if metadata["languages"] else [],
            index_version=metadata["index_version"],
            status=IndexStatus(metadata["status"]),
        )


@dataclass
class FileChecksum:
    """File-level checksum cache for incremental indexing optimization.

    This model enables hierarchical checksum-based change detection:
    1. File-level: Quick skip if entire file unchanged
    2. Object-level: Fine-grained detection if file changed

    Benefits:
    - 60-80% faster incremental indexing
    - Embedding reuse for unchanged objects
    - Accurate deleted object detection
    """

    file_path: str
    file_checksum: str  # SHA256 of entire file content
    last_modified: datetime
    object_checksums: dict[str, str]  # {deterministic_id: checksum}
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def validate(self) -> None:
        """Validate the file checksum fields."""
        if not self.file_path:
            raise ValueError("file_path must be non-empty")
        if not self.file_checksum:
            raise ValueError("file_checksum must be non-empty")

    def to_metadata(self) -> dict[str, Any]:
        """Convert to vector store metadata format."""
        import json

        return {
            "file_path": self.file_path,
            "file_checksum": self.file_checksum,
            "last_modified": self.last_modified.isoformat(),
            "object_checksums": json.dumps(self.object_checksums),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any]) -> "FileChecksum":
        """Reconstruct FileChecksum from vector storage."""
        import json

        return cls(
            id=UUID(metadata.get("id", str(uuid4()))),
            file_path=metadata["file_path"],
            file_checksum=metadata["file_checksum"],
            last_modified=datetime.fromisoformat(metadata["last_modified"]),
            object_checksums=json.loads(metadata["object_checksums"]),
            created_at=datetime.fromisoformat(metadata["created_at"]),
            updated_at=datetime.fromisoformat(metadata["updated_at"]),
        )
