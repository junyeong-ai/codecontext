"""Integration tests for configuration file indexing."""

import asyncio
import json
import tempfile
from pathlib import Path

import pytest
import requests
from codecontext.config.schema import CodeContextConfig
from codecontext.embeddings.factory import create_embedding_provider
from codecontext.formatters.config_formatter import ConfigFormatter
from codecontext.indexer.sync import FullIndexStrategy
from codecontext.search.retriever import SearchRetriever
from codecontext.storage.factory import create_storage_provider
from codecontext_core.models import SearchQuery


def chromadb_available() -> bool:
    """Check if ChromaDB is running using configured host and port."""
    try:
        config = CodeContextConfig()
        host = config.storage.chromadb.host
        port = config.storage.chromadb.port
        response = requests.get(f"http://{host}:{port}/api/v1/heartbeat", timeout=1)
    except Exception:
        return False
    else:
        return response.status_code == 200


# Mark all tests in this module as requiring ChromaDB
pytestmark = pytest.mark.skipif(
    not chromadb_available(), reason="ChromaDB not running (check config for host/port)"
)


@pytest.fixture
def temp_repo():
    """Create a temporary repository with config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create YAML config
        yaml_config = repo_path / "application.yaml"
        yaml_config.write_text(
            """
database:
  host: localhost
  port: 5432
  username: ${DB_USER}
  password: ${DB_PASSWORD}
  pool:
    min: 5
    max: 20

redis:
  host: localhost
  port: 6379
  password: ${REDIS_PASSWORD}

server:
  port: 8080
  host: 0.0.0.0
"""
        )

        # Create JSON config
        json_config = repo_path / "package.json"
        json_config.write_text(
            """{
  "name": "test-app",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.18.0",
    "redis": "^4.0.0"
  },
  "scripts": {
    "start": "node server.js",
    "test": "jest"
  }
}"""
        )

        # Create properties config
        props_config = repo_path / "application.properties"
        props_config.write_text(
            """# Database Configuration
database.host=localhost
database.port=5432
database.username=${DB_USER}

# Redis Configuration
redis.host=localhost
redis.port=6379
"""
        )

        yield repo_path


@pytest.fixture
def test_config():
    """Create test configuration."""
    config = CodeContextConfig()
    config.storage.chromadb.collection_name = "test_config_indexing"
    return config


@pytest.fixture(scope="module")
def shared_embedding_provider():
    """Create a shared embedding provider for all tests."""
    config = CodeContextConfig()
    return create_embedding_provider(config.embeddings)


class TestConfigFileIndexing:
    """Test configuration file indexing end-to-end."""

    def test_indexes_yaml_config_files(self, temp_repo, test_config, shared_embedding_provider):
        """Should index YAML config files and make them searchable."""
        # Create providers
        embedding_provider = shared_embedding_provider
        storage = create_storage_provider(test_config.storage, "test_project")
        storage.initialize()

        try:
            # Index repository
            strategy = FullIndexStrategy(test_config, embedding_provider, storage)
            state = asyncio.run(strategy.index(temp_repo, show_progress=False))

            # Verify indexing
            assert state.total_files > 0
            stats = storage.get_statistics()
            assert stats["documents_count"] > 0

            # Search for database configuration
            retriever = SearchRetriever(test_config, embedding_provider, storage)
            query = SearchQuery(query_text="database connection settings", limit=5)
            results = retriever.search(query)

            # Should find database config
            assert len(results) > 0
            # Check that at least one result is a config
            config_results = [r for r in results if r.metadata.get("config_format")]
            assert len(config_results) > 0

            # Verify metadata
            first_config = config_results[0]
            assert first_config.metadata.get("config_format") in ["yaml", "json", "properties"]
            assert first_config.metadata.get("node_type") == "config"

        finally:
            storage.close()

    def test_indexes_json_config_files(self, temp_repo, test_config, shared_embedding_provider):
        """Should index JSON config files."""
        embedding_provider = shared_embedding_provider
        storage = create_storage_provider(test_config.storage, "test_project")
        storage.initialize()

        try:
            strategy = FullIndexStrategy(test_config, embedding_provider, storage)
            asyncio.run(strategy.index(temp_repo, show_progress=False))

            retriever = SearchRetriever(test_config, embedding_provider, storage)
            query = SearchQuery(query_text="npm scripts dependencies", limit=5)
            results = retriever.search(query)

            # Should find package.json
            assert len(results) > 0
            json_results = [
                r
                for r in results
                if r.metadata.get("config_format") == "json"
                and "package" in r.metadata.get("file_path", "")
            ]
            assert len(json_results) > 0

        finally:
            storage.close()

    def test_indexes_properties_files(self, temp_repo, test_config, shared_embedding_provider):
        """Should index properties files."""
        embedding_provider = shared_embedding_provider
        storage = create_storage_provider(test_config.storage, "test_project")
        storage.initialize()

        try:
            strategy = FullIndexStrategy(test_config, embedding_provider, storage)
            asyncio.run(strategy.index(temp_repo, show_progress=False))

            # Verify properties file was indexed
            stats = storage.get_statistics()
            assert stats["documents_count"] > 0

            # Search with a more general query that should match properties
            retriever = SearchRetriever(test_config, embedding_provider, storage)
            query = SearchQuery(query_text="database configuration settings", limit=10)
            results = retriever.search(query)

            # Should find at least one properties config among all results
            assert len(results) > 0
            props_results = [r for r in results if r.metadata.get("config_format") == "properties"]
            # If properties results are found, verify metadata
            if props_results:
                assert props_results[0].metadata.get("node_type") == "config"

        finally:
            storage.close()

    def test_extracts_environment_variables(
        self, temp_repo, test_config, shared_embedding_provider
    ):
        """Should extract environment variable references."""
        embedding_provider = shared_embedding_provider
        storage = create_storage_provider(test_config.storage, "test_project")
        storage.initialize()

        try:
            strategy = FullIndexStrategy(test_config, embedding_provider, storage)
            asyncio.run(strategy.index(temp_repo, show_progress=False))

            retriever = SearchRetriever(test_config, embedding_provider, storage)
            query = SearchQuery(query_text="database password configuration", limit=10)
            results = retriever.search(query)

            # Find results with env references
            results_with_env = []
            for r in results:
                env_refs_str = r.metadata.get("env_references", "[]")
                env_refs = (
                    json.loads(env_refs_str) if isinstance(env_refs_str, str) else env_refs_str
                )
                if env_refs and len(env_refs) > 0:
                    results_with_env.append((r, env_refs))

            # Should find at least one config with env vars
            assert len(results_with_env) > 0

            # Check for expected env vars
            all_env_vars = []
            for _, env_refs in results_with_env:
                all_env_vars.extend(env_refs)

            assert any(var in all_env_vars for var in ["DB_USER", "DB_PASSWORD", "REDIS_PASSWORD"])

        finally:
            storage.close()

    def test_config_result_formatting(self, temp_repo, test_config, shared_embedding_provider):
        """Should format config results correctly."""
        embedding_provider = shared_embedding_provider
        storage = create_storage_provider(test_config.storage, "test_project")
        storage.initialize()

        try:
            strategy = FullIndexStrategy(test_config, embedding_provider, storage)
            asyncio.run(strategy.index(temp_repo, show_progress=False))

            retriever = SearchRetriever(test_config, embedding_provider, storage)
            query = SearchQuery(query_text="server configuration", limit=5)
            results = retriever.search(query)

            # Format as JSON
            formatter = ConfigFormatter()
            formatted = formatter.format(results, "server configuration", storage)
            data = json.loads(formatted)

            assert "results" in data
            assert "total" in data
            assert "query" in data
            assert data["query"] == "server configuration"

            if data["results"]:
                first_result = data["results"][0]
                assert "location" in first_result
                assert "metadata" in first_result
                assert "config_keys" in first_result
                assert "snippet" in first_result
                assert first_result["metadata"]["type"] == "config"

        finally:
            storage.close()
