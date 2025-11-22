import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import toml


@pytest.fixture(scope="session")
def quality_tests_dir() -> Path:
    return Path(__file__).parent


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def config_path(quality_tests_dir: Path) -> Path:
    return quality_tests_dir / "config.toml"


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(config_path: Path) -> None:
    os.environ["CODECONTEXT_CONFIG"] = str(config_path)


@pytest.fixture(scope="session")
def fixtures_dir(quality_tests_dir: Path) -> Path:
    return quality_tests_dir / "fixtures"


@pytest.fixture(scope="session")
def samples_dir(project_root: Path) -> Path:
    return project_root / "tests" / "fixtures" / "ecommerce_samples"


def check_index_exists(samples_dir: Path) -> dict[str, Any]:
    from codecontext.utils.cli_context import initialize_command

    try:
        ctx = initialize_command(path=samples_dir, need_embedding=False, enable_logging=False)
        stats = ctx.storage.get_statistics()
        count = stats.get("content_count", 0)
        ctx.storage.close()
    except Exception:  # noqa: BLE001
        return {"exists": False, "count": 0, "empty": True}
    else:
        return {"exists": True, "count": count, "empty": count == 0}


@pytest.fixture(scope="session")
def indexed_samples(samples_dir: Path, config_path: Path) -> dict[str, Any]:
    os.environ["CODECONTEXT_CONFIG"] = str(config_path)
    index_status = check_index_exists(samples_dir)

    if index_status["empty"]:
        pytest.fail(
            f"\nNo index found. Please run:\n"
            f"  CODECONTEXT_CONFIG={config_path} codecontext index {samples_dir}\n"
        )

    print(f"\n{'=' * 80}")
    print("✅ Using Existing Index")
    print(f"{'=' * 80}")
    print(f"Indexed: {index_status['count']:,} objects")
    print(f"{'=' * 80}\n")

    return {"count": index_status["count"]}


@pytest.fixture
def search_cli(
    indexed_samples: dict[str, Any], samples_dir: Path
) -> Callable[[str, int], dict[str, Any]]:
    def _search(query: str, limit: int = 20) -> dict[str, Any]:
        from codecontext.search.retriever import SearchRetriever
        from codecontext.utils.cli_context import initialize_command

        _ = indexed_samples
        ctx = initialize_command(path=samples_dir, need_embedding=True, enable_logging=False)
        retriever = SearchRetriever(
            storage=ctx.storage, embedding_provider=ctx.embedding_provider, config=ctx.config.search
        )
        results = retriever.search(query, limit=limit)
        ctx.storage.close()

        return {
            "results": [
                {
                    "chunk_id": r.chunk_id,
                    "name": r.metadata.get("name", ""),
                    "file_path": str(r.file_path),
                    "score": r.score,
                    "object_type": r.node_type,
                }
                for r in results
            ],
            "count": len(results),
        }

    return _search


@pytest.fixture(scope="session")
def ground_truth_data(fixtures_dir: Path) -> dict[str, Any]:
    ground_truth_path = fixtures_dir / "ground_truth.toml"
    if not ground_truth_path.exists():
        pytest.skip(f"Ground truth file not found: {ground_truth_path}")

    data = toml.load(ground_truth_path)
    return {
        q["id"]: {"text": q["text"], "essential_symbols": q.get("essential_symbols", [])}
        for q in data.get("query", [])
    }


@pytest.fixture
def metrics_calculator() -> dict[str, Callable[..., Any]]:
    return {}


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "quality: quality validation test")
