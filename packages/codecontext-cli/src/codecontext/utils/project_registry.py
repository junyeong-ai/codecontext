"""Project registry for name-to-ID resolution and project discovery."""

from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from codecontext.config.settings import get_data_dir, get_settings
from codecontext.utils.metadata import list_all_projects


@dataclass
class ProjectInfo:
    """Project information combining metadata and index state."""

    collection_id: str
    name: str
    repository_path: str
    git_origin: str | None = None
    last_indexed: str | None = None
    total_files: int = 0
    total_objects: int = 0

    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        return f"{self.name} ({self.collection_id})"


class ProjectRegistry:
    """Centralized registry for project name <-> collection ID mapping.

    Provides:
    - Name to collection ID resolution
    - Collection ID to name resolution
    - Fuzzy matching for similar project suggestions
    - Unified project listing
    """

    def __init__(self) -> None:
        self._cache: dict[str, ProjectInfo] | None = None

    def _load_projects(self) -> dict[str, ProjectInfo]:
        """Load all projects from metadata and storage."""
        if self._cache is not None:
            return self._cache

        projects: dict[str, ProjectInfo] = {}
        metadata_projects = list_all_projects()

        for collection_id, metadata in metadata_projects.items():
            # Project name comes from source_path (canonical source)
            source_path = metadata.get("source_path", "")
            name = Path(source_path).name if source_path else collection_id

            projects[collection_id] = ProjectInfo(
                collection_id=collection_id,
                name=name,
                repository_path=source_path,
                git_origin=metadata.get("git_origin"),
                last_indexed=metadata.get("indexed_at"),
            )

        # Enrich with index state data from storage
        self._enrich_from_storage(projects)

        self._cache = projects
        return projects

    def _enrich_from_storage(self, projects: dict[str, ProjectInfo]) -> None:
        """Enrich project info from Qdrant index state."""
        settings = get_settings()
        config = settings.load()

        if config.storage.provider != "qdrant":
            return

        # For remote mode, check collections
        if config.storage.qdrant.mode != "embedded":
            try:
                from qdrant_client import QdrantClient

                client = QdrantClient(
                    url=config.storage.qdrant.url, api_key=config.storage.qdrant.api_key
                )
                collections = client.get_collections().collections

                for collection in collections:
                    collection_id = collection.name

                    try:
                        from codecontext.storage.factory import create_storage_provider

                        storage = create_storage_provider(config, collection_id)
                        storage.set_client(client)
                        state = storage.get_index_state()

                        if state:
                            if collection_id in projects:
                                # Enrich existing project with index state data
                                projects[collection_id].total_files = state.total_files
                                projects[collection_id].total_objects = state.total_objects
                                if state.project_name:
                                    projects[collection_id].name = state.project_name
                            else:
                                # Create new project entry
                                projects[collection_id] = ProjectInfo(
                                    collection_id=collection_id,
                                    name=state.project_name or collection_id,
                                    repository_path=state.repository_path,
                                    last_indexed=state.last_indexed_at.isoformat(),
                                    total_files=state.total_files,
                                    total_objects=state.total_objects,
                                )
                    except Exception:
                        pass
                client.close()
            except Exception:
                pass
        else:
            # Embedded mode: scan directories
            data_dir = get_data_dir()
            if not data_dir.exists():
                return

            for project_dir in data_dir.iterdir():
                if not project_dir.is_dir():
                    continue

                collection_id = project_dir.name

                try:
                    from codecontext.storage.factory import create_storage_provider

                    storage = create_storage_provider(config, collection_id)
                    storage.initialize()
                    state = storage.get_index_state()
                    storage.close()

                    if state:
                        if collection_id in projects:
                            # Enrich existing project with index state data
                            projects[collection_id].total_files = state.total_files
                            projects[collection_id].total_objects = state.total_objects
                            if state.project_name:
                                projects[collection_id].name = state.project_name
                        else:
                            # Create new project entry
                            projects[collection_id] = ProjectInfo(
                                collection_id=collection_id,
                                name=state.project_name or collection_id,
                                repository_path=state.repository_path,
                                last_indexed=state.last_indexed_at.isoformat(),
                                total_files=state.total_files,
                                total_objects=state.total_objects,
                            )
                except Exception:
                    pass

    def resolve_project_id(self, project: str) -> str | None:
        """Resolve project name or ID to collection ID.

        Args:
            project: Project name or collection ID

        Returns:
            Collection ID if found, None otherwise

        Resolution order:
        1. Exact collection ID match
        2. Exact project name match (case-insensitive)
           - If multiple matches, prefer the one with most objects
        3. None if not found
        """
        projects = self._load_projects()

        # 1. Exact collection ID match
        if project in projects:
            return project

        # 2. Exact project name match (case-insensitive)
        # Collect all matches and prefer the one with most objects
        project_lower = project.lower()
        matches: list[tuple[str, ProjectInfo]] = []

        for collection_id, info in projects.items():
            if info.name.lower() == project_lower:
                matches.append((collection_id, info))

        if matches:
            # Sort by total_objects descending, then by last_indexed descending
            matches.sort(key=lambda x: (x[1].total_objects, x[1].last_indexed or ""), reverse=True)
            return matches[0][0]

        return None

    def get_project(self, project: str) -> ProjectInfo | None:
        """Get project info by name or ID.

        Args:
            project: Project name or collection ID

        Returns:
            ProjectInfo if found, None otherwise
        """
        collection_id = self.resolve_project_id(project)
        if collection_id:
            return self._load_projects().get(collection_id)
        return None

    def list_projects(self) -> list[ProjectInfo]:
        """List all registered projects.

        Returns:
            List of ProjectInfo sorted by name
        """
        projects = self._load_projects()
        return sorted(projects.values(), key=lambda p: p.name.lower())

    def find_similar_projects(self, query: str, threshold: float = 0.6) -> list[ProjectInfo]:
        """Find projects with similar names using fuzzy matching.

        Args:
            query: Search query (project name or partial name)
            threshold: Minimum similarity ratio (0.0 to 1.0)

        Returns:
            List of similar projects sorted by similarity (descending)
        """
        projects = self._load_projects()
        query_lower = query.lower()

        matches: list[tuple[float, ProjectInfo]] = []

        for info in projects.values():
            # Check name similarity
            name_ratio = SequenceMatcher(None, query_lower, info.name.lower()).ratio()

            # Check collection ID similarity
            id_ratio = SequenceMatcher(None, query_lower, info.collection_id.lower()).ratio()

            # Use best match
            best_ratio = max(name_ratio, id_ratio)

            # Also check if query is substring
            if query_lower in info.name.lower() or query_lower in info.collection_id.lower():
                best_ratio = max(best_ratio, 0.8)

            if best_ratio >= threshold:
                matches.append((best_ratio, info))

        # Sort by similarity (descending)
        matches.sort(key=lambda x: x[0], reverse=True)

        return [info for _, info in matches]

    def invalidate_cache(self) -> None:
        """Invalidate the project cache."""
        self._cache = None


# Global registry instance
_registry: ProjectRegistry | None = None


def get_project_registry() -> ProjectRegistry:
    """Get the global project registry instance."""
    global _registry
    if _registry is None:
        _registry = ProjectRegistry()
    return _registry


def reset_project_registry() -> None:
    """Reset the global project registry (useful for testing)."""
    global _registry
    _registry = None
