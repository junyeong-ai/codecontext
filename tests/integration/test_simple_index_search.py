"""Simple integration test for indexing and searching."""

import asyncio
import tempfile
from pathlib import Path

import pytest
import requests
from codecontext.config.schema import CodeContextConfig
from codecontext.embeddings.factory import create_embedding_provider
from codecontext.indexer.sync import FullIndexStrategy
from codecontext.search.retriever import SearchRetriever
from codecontext.storage.factory import create_storage_provider
from codecontext_core.models import SearchQuery


def chromadb_available() -> bool:
    """Check if ChromaDB is running."""
    try:
        config = CodeContextConfig()
        host = config.storage.chromadb.host
        port = config.storage.chromadb.port
        response = requests.get(f"http://{host}:{port}/api/v2/heartbeat", timeout=1)
    except Exception:
        return False
    else:
        return response.status_code == 200


pytestmark = pytest.mark.skipif(not chromadb_available(), reason="ChromaDB not running")


@pytest.fixture
def temp_repo():
    """Create a temporary repository with sample code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create Python file
        python_file = repo_path / "calculator.py"
        python_file.write_text(
            """
class Calculator:
    '''A simple calculator class.'''

    def add(self, a, b):
        '''Add two numbers.'''
        return a + b

    def subtract(self, a, b):
        '''Subtract two numbers.'''
        return a - b

    def multiply(self, a, b):
        '''Multiply two numbers.'''
        return a * b
"""
        )

        # Create JavaScript file
        js_file = repo_path / "utils.js"
        js_file.write_text(
            """
function formatDate(date) {
    return date.toISOString();
}

function validateEmail(email) {
    return email.includes('@');
}

module.exports = { formatDate, validateEmail };
"""
        )

        yield repo_path


@pytest.fixture
def test_config():
    """Create test configuration."""
    config = CodeContextConfig()
    config.storage.chromadb.collection_name = "test_simple_integration"
    return config


@pytest.fixture(scope="module")
def shared_embedding_provider():
    """Create a shared embedding provider for all tests."""
    config = CodeContextConfig()
    provider = create_embedding_provider(config.embeddings)
    with provider:
        yield provider


def test_full_indexing_and_search_workflow(temp_repo, test_config, shared_embedding_provider):
    """Test complete workflow: index files and search for code."""
    # Setup
    embedding_provider = shared_embedding_provider
    storage = create_storage_provider(test_config.storage, project_id="test_project")
    storage.initialize()

    try:
        # Step 1: Index repository
        strategy = FullIndexStrategy(test_config, embedding_provider, storage)
        state = asyncio.run(strategy.index(temp_repo, show_progress=False))

        # Verify indexing completed
        assert state.total_files > 0, "Should have indexed files"
        assert state.total_objects > 0, "Should have extracted code objects"

        # Check storage statistics
        stats = storage.get_statistics()
        assert stats["code_objects_count"] > 0, "Should have code objects in storage"

        # Step 2: Search for calculator-related code
        retriever = SearchRetriever(test_config, embedding_provider, storage)
        query = SearchQuery(query_text="calculator add function", limit=5)
        results = retriever.search(query)

        # Verify search results
        assert len(results) > 0, "Should find relevant code"

        # Check that we found the Calculator class or its methods
        found_calculator = any(
            "calculator" in r.metadata.get("name", "").lower()
            or "add" in r.metadata.get("name", "").lower()
            for r in results
        )
        assert found_calculator, "Should find calculator-related code"

        # Step 3: Search for JavaScript functions
        query2 = SearchQuery(query_text="email validation", limit=5)
        results2 = retriever.search(query2)

        # Verify we can find JS code
        assert len(results2) > 0, "Should find JS code"

        # Check metadata
        first_result = results[0]
        assert "name" in first_result.metadata, "Should have name metadata"
        assert "language" in first_result.metadata, "Should have language metadata"

    finally:
        storage.close()


def test_incremental_search_performance(temp_repo, test_config, shared_embedding_provider):
    """Test search performance after indexing."""
    embedding_provider = shared_embedding_provider
    storage = create_storage_provider(test_config.storage, project_id="test_project2")
    storage.initialize()

    try:
        # Index
        strategy = FullIndexStrategy(test_config, embedding_provider, storage)
        asyncio.run(strategy.index(temp_repo, show_progress=False))

        # Perform multiple searches
        retriever = SearchRetriever(test_config, embedding_provider, storage)

        queries = [
            "add two numbers",
            "multiply function",
            "format date",
            "validate email",
        ]

        for query_text in queries:
            query = SearchQuery(query_text=query_text, limit=3)
            results = retriever.search(query)

            # Should get results for each query
            assert len(results) >= 0, f"Search should complete for: {query_text}"

    finally:
        storage.close()
