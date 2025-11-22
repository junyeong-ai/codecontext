#!/usr/bin/env python3
"""
Profiling tool for analyzing CodeContext indexing performance.

Usage:
    python scripts/profile_indexing.py <repository_path> [output_path]

Example:
    python scripts/profile_indexing.py tests/fixtures/ecommerce_samples
    python scripts/profile_indexing.py /path/to/repo indexing_profile.txt
"""

import cProfile
import pstats
import sys
from io import StringIO
from pathlib import Path

from codecontext.config.settings import load_config
from codecontext.embeddings.factory import EmbeddingProviderFactory
from codecontext.indexer.sync.full import FullSyncStrategy
from codecontext.storage.factory import StorageProviderFactory


def profile_indexing(repository_path: Path, output_path: Path) -> None:
    """
    Profile indexing performance and generate timing breakdown.

    Args:
        repository_path: Path to repository to index
        output_path: Path to write profile output
    """
    print(f"Profiling indexing for: {repository_path}")
    print(f"Output will be written to: {output_path}")
    print()

    # Load configuration
    config = load_config()

    # Initialize providers
    print("Initializing providers...")
    embedding_provider = EmbeddingProviderFactory.create(config)
    storage_provider = StorageProviderFactory.create(config)

    # Create sync strategy
    strategy = FullSyncStrategy(
        config=config, storage=storage_provider, embedding_provider=embedding_provider
    )

    # Profile the indexing
    print("Starting profiled indexing...")
    profiler = cProfile.Profile()

    try:
        profiler.enable()
        state = strategy.sync(repository_path, show_progress=False)
        profiler.disable()

        print("\nIndexing complete!")
        print(f"  Files: {state.total_files}")
        print(f"  Objects: {state.total_objects}")
        print(f"  Documents: {state.total_documents}")
        print()

    except Exception as e:
        profiler.disable()
        print(f"\nError during indexing: {e}")
        raise
    finally:
        # Clean up test collection (if needed)
        # Note: In production, you might want to keep the data
        # For profiling, we optionally clean up
        pass

    # Generate statistics
    print("Generating profile statistics...")

    # Create stats object
    stats = pstats.Stats(profiler)

    # Sort by cumulative time
    stats.sort_stats("cumulative")

    # Write to file
    with Path(output_path).open("w") as f:
        # Write header
        f.write("=" * 80 + "\n")
        f.write("CodeContext Indexing Performance Profile\n")
        f.write("=" * 80 + "\n")
        f.write(f"\nRepository: {repository_path}\n")
        f.write(f"Files: {state.total_files}\n")
        f.write(f"Objects: {state.total_objects}\n")
        f.write(f"Documents: {state.total_documents}\n")
        f.write("\n" + "=" * 80 + "\n")
        f.write("Top 50 Functions by Cumulative Time\n")
        f.write("=" * 80 + "\n\n")

        # Redirect stdout to capture stats output
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        stats.print_stats(50)
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout

        # Write stats
        f.write(output)

        # Write separator
        f.write("\n" + "=" * 80 + "\n")
        f.write("Top 20 Functions by Total Time\n")
        f.write("=" * 80 + "\n\n")

        # Sort by total time
        sys.stdout = StringIO()
        stats.sort_stats("tottime")
        stats.print_stats(20)
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout

        f.write(output)

    print(f"\nProfile written to: {output_path}")
    print("\nKey metrics to look for:")
    print("  - Total time spent in parsing functions")
    print("  - Time spent in embedding generation")
    print("  - Time spent in storage operations")
    print("  - Overhead from multiprocessing (if enabled)")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/profile_indexing.py <repository_path> [output_path]")
        print("\nExample:")
        print("  python scripts/profile_indexing.py tests/fixtures/ecommerce_samples")
        sys.exit(1)

    repository_path = Path(sys.argv[1])
    if not repository_path.exists():
        print(f"Error: Repository path does not exist: {repository_path}")
        sys.exit(1)

    # Default output path
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("indexing_profile.txt")

    try:
        profile_indexing(repository_path, output_path)
    except Exception as e:
        print(f"\nProfileing failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
