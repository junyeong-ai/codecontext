"""
pytest Configuration for Quality Tests

Fixtures use CliRunner to test actual CLI commands:
- codecontext index (indexing performance)
- codecontext search (search quality)

Tests integration of:
- packages/codecontext-cli
- packages/codecontext-embeddings-huggingface
- packages/codecontext-storage-chromadb
"""

import json
import os
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from quality_tests.monitors import ProgressMonitor

# Disable proxy for local testing (must be after import)
# macOS-specific proxy bypass (only set if attribute exists)
if hasattr(urllib.request, "proxy_bypass_macosx_sysconf"):
    urllib.request.proxy_bypass_macosx_sysconf = lambda _: False
# Override the default proxy_bypass with type cast
urllib.request.proxy_bypass = cast(Any, lambda _: False)

# ==============================================================================
# Path Configuration
# ==============================================================================


@pytest.fixture(scope="session")
def quality_tests_dir() -> Path:
    """Root directory of quality tests."""
    return Path(__file__).parent


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def config_path(quality_tests_dir: Path) -> Path:
    """Path to quality tests configuration."""
    return quality_tests_dir / "config.yaml"


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(config_path: Path) -> None:
    """
    Setup test environment before any tests run.

    CRITICAL: This fixture must run BEFORE any code that initializes Settings,
    because Settings uses singleton pattern with caching. Once Settings.load()
    is called, it caches the config and ignores subsequent environment variable changes.

    By using autouse=True and session scope, this ensures CODECONTEXT_CONFIG
    is set before Settings singleton is created during indexing fixture.

    Additionally, this resets the Settings singleton to force re-initialization
    with the correct config.
    """
    # Set environment variable FIRST
    os.environ["CODECONTEXT_CONFIG"] = str(config_path)

    # Force Settings singleton reset to ensure config is reloaded
    # This is critical when --reindex flag is used
    from codecontext.config import settings
    settings._settings = None


@pytest.fixture(scope="session")
def fixtures_dir(quality_tests_dir: Path) -> Path:
    """Fixtures directory with ground truth data."""
    return quality_tests_dir / "fixtures"


@pytest.fixture(scope="session")
def samples_dir(project_root: Path) -> Path:
    """Sample files directory (ecommerce_samples)."""
    return project_root / "tests" / "fixtures" / "ecommerce_samples"


@pytest.fixture(scope="session")
def results_dir(project_root: Path) -> Path:
    """Test results output directory."""
    output_dir = project_root / "tests" / "data" / "quality_results"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


# ==============================================================================
# Configuration
# ==============================================================================


@pytest.fixture(scope="session")
def quality_config(config_path: Path) -> dict[str, Any]:
    """Load quality tests configuration."""
    with config_path.open() as f:
        result = yaml.safe_load(f)
        assert isinstance(result, dict), "Config must be a dictionary"
        return result


# ==============================================================================
# CLI Testing
# ==============================================================================




@pytest.fixture(scope="session")
def detected_project_id(samples_dir: Path) -> str:  # noqa: ARG001
    """
    Return explicit project ID for ecommerce_samples.

    We use an explicit name instead of auto-detection to avoid Git
    parent directory detection issues (ecommerce_samples is inside codecontext repo).

    Returns:
        Normalized project identifier
    """
    from codecontext.utils.project_identifier import ProjectIdentifier

    # Use explicit project name for ecommerce samples
    # This ensures tests use same collections as CLI with --project ecommerce
    project_id = "ecommerce"

    # Normalize for consistency
    normalized = ProjectIdentifier.normalize(project_id)

    return normalized


@pytest.fixture(scope="session", autouse=True)
def verify_chromadb_running() -> None:
    """
    Verify ChromaDB server is running before any tests execute.

    Fails fast with actionable error message if ChromaDB is not accessible.
    """
    try:
        import httpx

        # Test ChromaDB v2 API heartbeat endpoint
        response = httpx.get("http://localhost:8000/api/v2", timeout=2.0)
        response.raise_for_status()
    except (httpx.HTTPError, httpx.ConnectError, httpx.TimeoutException) as e:
        pytest.exit(
            f"\n\n"
            f"❌ ChromaDB server is not running!\n"
            f"   Start it with: ./scripts/chroma-cli.sh start\n"
            f"   Verify with: curl http://localhost:8000/api/v2\n"
            f"   Error: {e}\n",
            returncode=1,
        )


def check_index_exists(
    project_id: str = "default",
) -> dict[str, Any]:
    """
    Check if ChromaDB index exists and has data across all collections.

    Validates all 4 collections:
    - code_objects: Primary collection (code chunks)
    - documents: Document chunks
    - relationships: Code relationships (CALLS, CONTAINS, etc.)
    - state: Indexing state metadata

    Args:
        collection_name: Base collection name
        project_id: Project identifier for collection isolation

    Returns:
        Dict with index status:
        - exists: bool - All required collections exist
        - count: int - Number of code objects (primary metric)
        - empty: bool - Index is empty (no code objects)
        - collections: dict - Individual collection counts
        - complete: bool - All 4 collections present
    """
    try:
        import chromadb

        # Create client
        client = chromadb.HttpClient(host="localhost", port=8000)

        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../packages/codecontext-storage-chromadb/src"))
        from codecontext_storage_chromadb.config import ChromaDBConfig

        config = ChromaDBConfig()

        collection_counts: dict[str, int] = {}
        missing_collections: list[str] = []

        # Check each collection type (2-collection architecture)
        collection_types = ["content", "meta"]
        for col_type in collection_types:
            full_name = config.get_collection_name(project_id, col_type)
            try:
                collection = client.get_collection(name=full_name)
                collection_counts[col_type] = collection.count()
            except (ValueError, KeyError, chromadb.errors.NotFoundError):
                # Collection doesn't exist
                collection_counts[col_type] = 0
                missing_collections.append(col_type)

        # Determine overall status
        code_objects_count = collection_counts.get("code", 0)
        all_exist = len(missing_collections) == 0
        is_empty = code_objects_count == 0
    except (ImportError, ConnectionError, OSError) as _:
        # Client creation failed or other error
        return {
            "exists": False,
            "count": 0,
            "empty": True,
            "collections": {},
            "complete": False,
            "missing": ["code", "docs", "rels", "state"],
        }
    else:
        return {
            "exists": all_exist,
            "count": code_objects_count,
            "empty": is_empty,
            "collections": collection_counts,
            "complete": all_exist,
            "missing": missing_collections,
        }


@pytest.fixture(scope="session")
def indexed_samples(
    samples_dir: Path,
    config_path: Path,
    results_dir: Path,
    request: pytest.FixtureRequest,
    detected_project_id: str,
) -> dict[str, Any]:
    """
    Ensure samples are indexed with conditional re-indexing.

    Uses subprocess to run CLI for real-time output visibility.

    Returns:
        Dict with indexing results (indexed, reused, duration_seconds, count, etc.)
    """
    force_reindex = request.config.getoption("--reindex")
    # Check existing index
    index_status = check_index_exists(project_id=detected_project_id)
    needs_indexing = force_reindex or index_status["empty"]

    if not needs_indexing:
        # Reuse existing index
        collections_info = index_status.get("collections", {})
        print(f"\n{'=' * 80}")
        print("✅ Reusing Existing Index")
        print(f"{'=' * 80}")
        print(f"Code Objects:   {collections_info.get('code_objects', 0):,} chunks")
        print(f"Documents:      {collections_info.get('documents', 0):,} chunks")
        print(f"Relationships:  {collections_info.get('relationships', 0):,} edges")
        print(f"\n💡 Use --reindex to force re-indexing")
        print(f"{'=' * 80}\n")

        return {
            "indexed": False,
            "reused": True,
            "duration_seconds": 0.0,
            "count": index_status["count"],
            "metrics_path": None,
            "collections": collections_info,
        }

    # Perform indexing via subprocess
    reason = "forced by --reindex" if force_reindex else "index not found or empty"
    print(f"\n{'=' * 80}")
    print(f"🔄 Indexing samples ({reason})")
    print(f"{'=' * 80}\n")

    # Setup progress monitoring
    progress_file = results_dir / "indexing_progress.log"
    monitor = ProgressMonitor("Indexing", progress_file=progress_file)
    monitor.start()

    # Prepare environment
    env = os.environ.copy()
    env["CODECONTEXT_CONFIG"] = str(config_path)
    env["PYTHONUNBUFFERED"] = "1"  # Disable stdout/stderr buffering

    # Build command
    import subprocess
    cmd = [
        "codecontext", "index", str(samples_dir),
        "--project", "ecommerce",
        "--force"
    ]

    # Run with real-time output
    start_time = time.time()
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Stream output
    output_lines = []
    with progress_file.open('w') as f:
        for line in process.stdout:
            print(line, end='', flush=True)
            f.write(line)
            f.flush()
            output_lines.append(line)

    exit_code = process.wait()
    duration = time.time() - start_time

    # Finalize
    metrics_path = results_dir / "indexing_metrics.json"
    monitor.finish(metrics_path)

    # Verify success
    if exit_code != 0:
        pytest.fail(
            f"\n❌ Indexing failed (exit code {exit_code})\n"
            f"Check: ./scripts/chroma-cli.sh status\n"
            f"Last 50 lines:\n{''.join(output_lines[-50:])}"
        )

    # Get final count
    final_status = check_index_exists(environment="test", project_id=detected_project_id)

    return {
        "indexed": True,
        "reused": False,
        "duration_seconds": duration,
        "count": final_status["count"],
        "metrics_path": metrics_path,
    }


@pytest.fixture
def search_cli(
    config_path: Path,
    indexed_samples: dict[str, Any],  # noqa: ARG001 - Required for fixture dependency
) -> Callable[[str, int], dict[str, Any]]:
    """Search fixture using subprocess CLI execution."""

    def _search(query: str, limit: int = 20) -> dict[str, Any]:
        """Execute search via CLI and return results."""
        import subprocess

        env = os.environ.copy()
        env["CODECONTEXT_CONFIG"] = str(config_path)

        # Run CLI command with --expand for detailed scoring
        result = subprocess.run(
            [
                "codecontext", "search", query,
                "--limit", str(limit),
                "--format", "json",
                "--expand",
                "--project", "ecommerce"
            ],
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.fail(
                f"Search failed for '{query}'\n"
                f"Exit code: {result.returncode}\n"
                f"Output: {result.stdout}\n{result.stderr}"
            )

        # Parse JSON
        try:
            parsed = json.loads(result.stdout)
            assert isinstance(parsed, dict), "Search result must be a dictionary"
            return parsed
        except json.JSONDecodeError as e:
            pytest.fail(
                f"Invalid JSON in search output: {e}\n"
                f"Output: {result.stdout[:500]}"
            )

    return _search


# ==============================================================================
# Ground Truth Data
# ==============================================================================

# Legacy mapping patterns - No longer needed for ecommerce ground truth
# Ecommerce ground truth uses full paths directly
# This remains for backward compatibility if needed
_PREFIX_PATTERNS: dict[str, list[str]] = {}


def _build_file_index(samples_dir: Path, project_root: Path) -> dict[str, list[str]]:
    """Build filename to full path index."""
    file_index: dict[str, list[str]] = {}

    for file_path in samples_dir.rglob("*"):
        if not file_path.is_file():
            continue

        filename = file_path.name
        # Store relative path from project root
        try:
            relative_path = str(file_path.relative_to(project_root))
        except ValueError:
            # If not under project root, use absolute path
            relative_path = str(file_path)

        if filename not in file_index:
            file_index[filename] = []
        file_index[filename].append(relative_path)

    return file_index


def _resolve_candidate_with_prefix(
    candidates: list[str], gt_path: str, prefix_patterns: dict[str, list[str]]
) -> str:
    """Resolve multiple candidates using prefix hints."""
    gt_prefix = gt_path.split("/")[0] + "/"
    patterns = prefix_patterns.get(gt_prefix, [])

    for candidate in candidates:
        for pattern in patterns:
            if pattern in candidate:
                return candidate

    # Fallback: return first candidate
    return candidates[0]


@pytest.fixture(scope="session")
def path_mapper(samples_dir: Path) -> Callable[[str], str | None]:
    """
    Create path mapping function from ground truth to actual file paths.

    E-commerce ground truth uses full paths directly like:
    - tests/fixtures/ecommerce_samples/docs/business/order-flow.md
    - tests/fixtures/ecommerce_samples/services/order-service/src/main/java/.../OrderService.java

    Returns callable that maps ground truth path to actual path.
    """
    # Get project root (samples_dir -> fixtures -> tests -> codecontext)
    project_root = samples_dir.parent.parent.parent

    # Build filename -> full path index
    file_index = _build_file_index(samples_dir, project_root)

    def map_path(gt_path: str) -> str | None:
        """Map ground truth path to actual file path."""
        filename = Path(gt_path).name
        candidates = file_index.get(filename, [])

        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        return _resolve_candidate_with_prefix(candidates, gt_path, _PREFIX_PATTERNS)

    return map_path


@pytest.fixture(scope="session")
def ground_truth_data(
    fixtures_dir: Path, path_mapper: Callable[[str], str | None]
) -> dict[str, Any]:
    """
    Load ground truth data with path mapping.

    Converts ground truth paths to actual file paths using path_mapper.
    """
    ground_truth_path = fixtures_dir / "ground_truth_ecommerce.yaml"
    if not ground_truth_path.exists():
        pytest.skip(f"Ground truth file not found: {ground_truth_path}")

    with ground_truth_path.open() as f:
        data = yaml.safe_load(f)

    # Convert paths in ground truth data
    for gt in data.get("ground_truth", []):
        if "relevant_items" in gt:
            for item in gt["relevant_items"]:
                original_path = item["path"]
                mapped_path = path_mapper(original_path)
                if mapped_path:
                    item["path"] = mapped_path
                    item["original_path"] = original_path
                else:
                    # Keep original path if mapping fails
                    item["original_path"] = original_path

    return {gt["query_id"]: gt for gt in data.get("ground_truth", [])}


@pytest.fixture(scope="session")
def test_queries(fixtures_dir: Path) -> dict[str, Any]:
    """Load test queries."""
    queries_path = fixtures_dir / "test_queries_ecommerce.yaml"
    if not queries_path.exists():
        pytest.skip(f"Test queries file not found: {queries_path}")

    with queries_path.open() as f:
        data = yaml.safe_load(f)

    return {q["id"]: q for q in data.get("queries", [])}


# ==============================================================================
# Metrics Calculation
# ==============================================================================


def calculate_precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """
    Calculate Precision@K.

    Args:
        retrieved: Ordered list of retrieved items
        relevant: Set of relevant items
        k: Cutoff

    Returns:
        Precision score (0.0 to 1.0)
    """
    if k == 0:
        return 0.0

    top_k = retrieved[:k]
    relevant_in_top_k = sum(1 for item in top_k if item in relevant)
    return relevant_in_top_k / k


def calculate_recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """
    Calculate Recall@K.

    Args:
        retrieved: Ordered list of retrieved items
        relevant: Set of relevant items
        k: Cutoff

    Returns:
        Recall score (0.0 to 1.0)
    """
    if not relevant:
        return 0.0

    top_k = retrieved[:k]
    relevant_in_top_k = sum(1 for item in top_k if item in relevant)
    return relevant_in_top_k / len(relevant)


def calculate_mrr(retrieved: list[str], relevant: set[str]) -> float:
    """
    Calculate Mean Reciprocal Rank.

    Args:
        retrieved: Ordered list of retrieved items
        relevant: Set of relevant items

    Returns:
        MRR score (0.0 to 1.0)
    """
    for rank, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


@pytest.fixture
def metrics_calculator() -> dict[str, Callable[..., Any]]:
    """Metrics calculation utilities."""
    return {
        "precision_at_k": calculate_precision_at_k,
        "recall_at_k": calculate_recall_at_k,
        "mrr": calculate_mrr,
    }


# ==============================================================================
# pytest Configuration
# ==============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "quality: mark test as quality validation test")
    config.addinivalue_line("markers", "indexing: mark test as indexing performance test")
    config.addinivalue_line("markers", "search: mark test as search quality test")
    config.addinivalue_line("markers", "doc_linking: mark test as document-code linking test")


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom command-line options."""
    parser.addoption(
        "--with-ground-truth",
        action="store_true",
        default=False,
        help="Run tests that require ground truth data",
    )
    parser.addoption(
        "--reindex",
        action="store_true",
        default=False,
        help="Force re-indexing even if index exists",
    )
