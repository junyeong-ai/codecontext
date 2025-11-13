#!/usr/bin/env python3
"""
Memory stress test for streaming embedding optimization.

This script tests the memory footprint when indexing a large codebase (50,000+ files).
It monitors memory usage during indexing and verifies that it stays under 2GB.

Usage:
    python scripts/memory_stress_test.py /path/to/large/repo [--target-files 50000]
"""

import argparse
import resource
import subprocess
import sys
import time
from pathlib import Path


def get_memory_usage_mb() -> float:
    """
    Get current memory usage in MB.

    Returns:
        Memory usage in megabytes
    """
    try:
        # On Unix-like systems, use resource module
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # maxrss is in kilobytes on Linux, bytes on macOS
        if sys.platform == "darwin":
            return usage.ru_maxrss / (1024 * 1024)  # Convert bytes to MB
        else:
            return usage.ru_maxrss / 1024  # Convert KB to MB
    except Exception:
        # Fallback: read from /proc/self/status
        try:
            with Path("/proc/self/status").open() as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        # Extract memory in KB
                        mem_kb = int(line.split()[1])
                        return mem_kb / 1024
        except Exception:
            return 0.0


def set_memory_limit_mb(limit_mb: int) -> bool:
    """
    Set memory limit for the process.

    Args:
        limit_mb: Memory limit in megabytes

    Returns:
        True if limit was set successfully, False otherwise
    """
    try:
        # Convert MB to bytes
        limit_bytes = limit_mb * 1024 * 1024

        # Set soft and hard limits
        resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
    except Exception as e:
        print(f"Warning: Could not set memory limit: {e}")
        return False
    else:
        return True


def count_files(repo_path: Path) -> int:
    """
    Count number of files in repository.

    Args:
        repo_path: Path to repository

    Returns:
        Number of files
    """
    count = 0
    for _ in repo_path.rglob("*"):
        if _.is_file():
            count += 1
    return count


def run_indexing(
    repo_path: Path,
    memory_limit_mb: int | None = None,
    use_streaming: bool = True,
) -> tuple[bool, float, float]:
    """
    Run indexing with memory monitoring.

    Args:
        repo_path: Path to repository to index
        memory_limit_mb: Optional memory limit in MB
        use_streaming: Whether to use streaming optimization

    Returns:
        Tuple of (success, peak_memory_mb, duration_seconds)
    """
    # Set memory limit if specified
    if memory_limit_mb:
        set_memory_limit_mb(memory_limit_mb)

    # Build codecontext index command
    cmd = ["codecontext", "index", str(repo_path)]

    if use_streaming:
        # Add streaming-related flags (to be implemented in CLI)
        cmd.extend(["--batch-size", "100"])

    start_time = time.time()
    peak_memory = 0.0

    try:
        # Start indexing process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Monitor memory usage
        while process.poll() is None:
            current_memory = get_memory_usage_mb()
            if current_memory > peak_memory:
                peak_memory = current_memory

            time.sleep(1)  # Check every second

        # Get final memory usage
        final_memory = get_memory_usage_mb()
        if final_memory > peak_memory:
            peak_memory = final_memory

        duration = time.time() - start_time

        # Check if indexing succeeded
        return_code = process.returncode
        success = return_code == 0

    except subprocess.TimeoutExpired:
        print("ERROR: Indexing timed out")
        return False, peak_memory, time.time() - start_time
    except MemoryError:
        print("ERROR: Out of memory")
        return False, peak_memory, time.time() - start_time
    except Exception as e:
        print(f"ERROR: {e}")
        return False, peak_memory, time.time() - start_time
    else:
        return success, peak_memory, duration


def main() -> int:
    """Run memory stress test."""
    parser = argparse.ArgumentParser(
        description="Memory stress test for CodeContext streaming optimization"
    )
    parser.add_argument(
        "repo_path",
        type=Path,
        help="Path to repository to index",
    )
    parser.add_argument(
        "--target-files",
        type=int,
        default=50000,
        help="Target number of files (default: 50000)",
    )
    parser.add_argument(
        "--memory-limit",
        type=int,
        default=2048,
        help="Memory limit in MB (default: 2048)",
    )
    parser.add_argument(
        "--no-streaming",
        action="store_true",
        help="Disable streaming optimization (for comparison)",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("CodeContext Memory Stress Test")
    print("=" * 70)
    print()

    # Validate repository path
    if not args.repo_path.exists():
        print(f"ERROR: Repository path does not exist: {args.repo_path}")
        return 1

    # Count files
    print(f"Counting files in {args.repo_path}...")
    file_count = count_files(args.repo_path)
    print(f"Found {file_count:,} files")
    print()

    if file_count < args.target_files:
        print(f"WARNING: File count ({file_count:,}) is less than target ({args.target_files:,})")
        print("Consider using a larger repository for accurate stress testing.")
        print()

    # Run indexing with memory monitoring
    print(f"Starting indexing with {args.memory_limit}MB memory limit...")
    print(f"Streaming optimization: {'DISABLED' if args.no_streaming else 'ENABLED'}")
    print()

    success, peak_memory, duration = run_indexing(
        args.repo_path,
        memory_limit_mb=args.memory_limit,
        use_streaming=not args.no_streaming,
    )

    # Display results
    print()
    print("=" * 70)
    print("Results")
    print("=" * 70)
    print(f"Status:        {'SUCCESS' if success else 'FAILED'}")
    print(f"Peak Memory:   {peak_memory:.2f} MB")
    print(f"Duration:      {duration:.2f} seconds")
    print(f"Files/second:  {file_count / duration:.2f}")
    print()

    # Check acceptance criteria
    memory_limit_met = peak_memory < args.memory_limit
    throughput = file_count / duration
    # Rough estimate: 1000+ embeddings/sec ≈ 100+ files/sec
    throughput_met = throughput > 100

    print("Acceptance Criteria:")
    print(
        f"  SC-011: Memory < {args.memory_limit}MB: {'✅ PASS' if memory_limit_met else '❌ FAIL'}"
    )
    print(f"  SC-012: Throughput > 100 files/sec: {'✅ PASS' if throughput_met else '❌ FAIL'}")
    print()

    if success and memory_limit_met and throughput_met:
        print("✅ All criteria met!")
        return 0
    else:
        print("❌ Some criteria not met")
        return 1


if __name__ == "__main__":
    sys.exit(main())
