#!/usr/bin/env python3
"""
Performance benchmark script for CodeContext.

Measures indexing and search performance with detailed metrics.
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Add codecontext to path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages/codecontext-cli/src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "packages/codecontext-core/src"))

import contextlib

from codecontext.config.schema import CodeContextConfig
from codecontext.embeddings.factory import create_embedding_provider
from codecontext.indexer.sync import FullIndexStrategy
from codecontext.search.retriever import SearchRetriever
from codecontext.storage.factory import create_storage_provider
from codecontext_core.models import SearchQuery

app = typer.Typer()
console = Console()


class BenchmarkRunner:
    """Run performance benchmarks with detailed metrics."""

    def __init__(self, config: CodeContextConfig | None = None):
        """Initialize benchmark runner."""
        self.config = config or CodeContextConfig()
        self.metrics: dict = {}
        self.start_time: float | None = None

    async def benchmark_indexing(self, repo_path: Path, force: bool = False) -> dict:
        """
        Benchmark indexing performance.

        Returns:
            Dictionary with performance metrics
        """
        console.print("\n[bold cyan]🚀 Starting Indexing Benchmark[/bold cyan]\n")

        # Initialize components
        embedding_provider = create_embedding_provider(self.config.embeddings)
        storage = create_storage_provider(self.config.storage, project_id=repo_path.name)

        # Initialize storage
        if force:
            console.print("[yellow]Clearing existing index...[/yellow]")
            storage.clear()
        storage.initialize()

        # Memory before
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024**3  # GB

        # Create indexer
        indexer = FullIndexStrategy(self.config, embedding_provider, storage)

        # Start timing
        start_time = time.time()
        start_cpu = time.process_time()

        # Track memory peak
        peak_memory = memory_before

        async def memory_monitor():
            nonlocal peak_memory
            while self.start_time:
                current = process.memory_info().rss / 1024**3
                peak_memory = max(peak_memory, current)
                await asyncio.sleep(0.1)

        # Start memory monitoring
        self.start_time = start_time
        monitor_task = asyncio.create_task(memory_monitor())

        try:
            # Run indexing
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Indexing repository...", total=None)

                state = await indexer.index(repo_path, show_progress=False)

                progress.update(task, completed=True)

        finally:
            # Stop monitoring
            self.start_time = None
            monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await monitor_task

        # Calculate metrics
        elapsed_time = time.time() - start_time
        cpu_time = time.process_time() - start_cpu
        memory_after = process.memory_info().rss / 1024**3
        memory_used = memory_after - memory_before

        # Get statistics
        stats = storage.get_statistics()

        metrics = {
            "files_indexed": state.total_files,
            "objects_extracted": state.total_objects,
            "documents_processed": state.total_documents,
            "relationships_found": stats.get("relationships_count", 0),
            "elapsed_time_sec": elapsed_time,
            "cpu_time_sec": cpu_time,
            "throughput_files_per_sec": state.total_files / elapsed_time if elapsed_time > 0 else 0,
            "throughput_objects_per_sec": (
                state.total_objects / elapsed_time if elapsed_time > 0 else 0
            ),
            "memory_before_gb": memory_before,
            "memory_after_gb": memory_after,
            "memory_used_gb": memory_used,
            "memory_peak_gb": peak_memory,
        }

        # Display results
        self._display_indexing_results(metrics)

        # Cleanup
        embedding_provider.close()
        storage.close()

        return metrics

    def benchmark_search(self, queries: list[str], repo_path: Path | None = None) -> dict:
        """
        Benchmark search performance.

        Returns:
            Dictionary with performance metrics
        """
        console.print("\n[bold cyan]🔍 Starting Search Benchmark[/bold cyan]\n")

        # Initialize components
        embedding_provider = create_embedding_provider(self.config.embeddings)
        project_id = repo_path.name if repo_path else "default"
        storage = create_storage_provider(self.config.storage, project_id=project_id)
        storage.initialize()

        # Create retriever
        retriever = SearchRetriever(self.config, embedding_provider, storage)

        # Warm-up query (triggers BM25 building)
        console.print("[yellow]Warming up search index...[/yellow]")
        warm_up_start = time.time()
        _ = retriever.search(SearchQuery(query_text="test", limit=1))
        warm_up_time = time.time() - warm_up_start

        # Run benchmark queries
        query_times = []
        query_results = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Running {len(queries)} queries...", total=len(queries))

            for query in queries:
                start = time.time()
                results = retriever.search(SearchQuery(query_text=query, limit=10))
                elapsed = time.time() - start

                query_times.append(elapsed)
                query_results.append(
                    {
                        "query": query,
                        "time_ms": elapsed * 1000,
                        "results_count": len(results),
                    }
                )

                progress.update(task, advance=1)

        # Calculate metrics
        metrics = {
            "warm_up_time_sec": warm_up_time,
            "total_queries": len(queries),
            "avg_query_time_ms": sum(query_times) * 1000 / len(query_times) if query_times else 0,
            "min_query_time_ms": min(query_times) * 1000 if query_times else 0,
            "max_query_time_ms": max(query_times) * 1000 if query_times else 0,
            "queries_per_sec": len(queries) / sum(query_times) if query_times else 0,
            "query_results": query_results,
        }

        # Display results
        self._display_search_results(metrics)

        # Cleanup
        embedding_provider.close()
        storage.close()

        return metrics

    def _display_indexing_results(self, metrics: dict):
        """Display indexing benchmark results."""
        table = Table(title="Indexing Performance Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        # Format time
        elapsed = metrics["elapsed_time_sec"]
        minutes = int(elapsed // 60)
        seconds = elapsed % 60

        table.add_row("Files Indexed", f"{metrics['files_indexed']:,}")
        table.add_row("Objects Extracted", f"{metrics['objects_extracted']:,}")
        table.add_row("Relationships Found", f"{metrics['relationships_found']:,}")
        table.add_row("Time Taken", f"{minutes}m {seconds:.1f}s")
        table.add_row("CPU Time", f"{metrics['cpu_time_sec']:.1f}s")
        table.add_row("Throughput (files/sec)", f"{metrics['throughput_files_per_sec']:.1f}")
        table.add_row("Throughput (objects/sec)", f"{metrics['throughput_objects_per_sec']:.1f}")
        table.add_row("Memory Used", f"{metrics['memory_used_gb']:.2f} GB")
        table.add_row("Peak Memory", f"{metrics['memory_peak_gb']:.2f} GB")

        console.print(table)

    def _display_search_results(self, metrics: dict):
        """Display search benchmark results."""
        table = Table(title="Search Performance Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Initial Index Build", f"{metrics['warm_up_time_sec'] * 1000:.0f}ms")
        table.add_row("Total Queries", str(metrics["total_queries"]))
        table.add_row("Average Query Time", f"{metrics['avg_query_time_ms']:.1f}ms")
        table.add_row("Min Query Time", f"{metrics['min_query_time_ms']:.1f}ms")
        table.add_row("Max Query Time", f"{metrics['max_query_time_ms']:.1f}ms")
        table.add_row("Queries/Second", f"{metrics['queries_per_sec']:.1f}")

        console.print(table)

        # Show individual query results
        if len(metrics["query_results"]) <= 10:
            query_table = Table(title="Individual Query Results")
            query_table.add_column("Query", style="cyan")
            query_table.add_column("Time (ms)", style="yellow")
            query_table.add_column("Results", style="green")

            for result in metrics["query_results"]:
                query_table.add_row(
                    result["query"][:50],  # Truncate long queries
                    f"{result['time_ms']:.1f}",
                    str(result["results_count"]),
                )

            console.print(query_table)


@app.command()
def index(
    repo_path: Path,
    force: bool = False,
    output: Path | None = None,
):
    """Run indexing performance benchmark."""
    runner = BenchmarkRunner()

    # Run benchmark
    metrics = asyncio.run(runner.benchmark_indexing(repo_path, force))

    # Save metrics if requested
    if output:
        with Path(output).open("w") as f:
            json.dump(metrics, f, indent=2)
        console.print(f"\n[green]✅ Metrics saved to {output}[/green]")


@app.command()
def search(
    queries_file: Path | None = None,
    repo_path: Path | None = None,
    output: Path | None = None,
):
    """Run search performance benchmark."""
    # Load queries
    if queries_file and queries_file.exists():
        with Path(queries_file).open() as f:
            queries = [line.strip() for line in f if line.strip()]
    else:
        # Default test queries
        queries = [
            "authentication flow",
            "database connection",
            "API endpoints",
            "error handling",
            "user management",
            "payment processing",
            "configuration settings",
            "logging middleware",
            "test coverage",
            "performance optimization",
        ]

    runner = BenchmarkRunner()

    # Run benchmark
    metrics = runner.benchmark_search(queries, repo_path)

    # Save metrics if requested
    if output:
        with Path(output).open("w") as f:
            json.dump(metrics, f, indent=2)
        console.print(f"\n[green]✅ Metrics saved to {output}[/green]")


@app.command()
def full(
    repo_path: Path,
    force: bool = False,
    output: Path | None = None,
):
    """Run full benchmark suite (indexing + search)."""
    runner = BenchmarkRunner()

    console.print("[bold magenta]🎯 Running Full Benchmark Suite[/bold magenta]\n")

    # Run indexing benchmark
    index_metrics = asyncio.run(runner.benchmark_indexing(repo_path, force))

    # Default test queries
    queries = [
        "class definition",
        "function implementation",
        "import statements",
        "error handling",
        "database query",
        "API route",
        "configuration",
        "test case",
        "async function",
        "exception handling",
    ]

    # Run search benchmark
    search_metrics = runner.benchmark_search(queries, repo_path)

    # Combined metrics
    full_metrics = {
        "timestamp": datetime.now().isoformat(),
        "repository": str(repo_path),
        "indexing": index_metrics,
        "search": search_metrics,
    }

    # Save if requested
    if output:
        with Path(output).open("w") as f:
            json.dump(full_metrics, f, indent=2)
        console.print(f"\n[green]✅ Full metrics saved to {output}[/green]")

    # Print summary
    console.print("\n[bold green]📊 Benchmark Summary[/bold green]")
    console.print(f"Files indexed: {index_metrics['files_indexed']:,}")
    console.print(f"Indexing time: {index_metrics['elapsed_time_sec']:.1f}s")
    console.print(f"Avg query time: {search_metrics['avg_query_time_ms']:.1f}ms")
    console.print(f"Peak memory: {index_metrics['memory_peak_gb']:.2f}GB")


@app.command()
def compare(
    before: Path,
    after: Path,
):
    """Compare benchmark results."""
    # Load metrics
    with Path(before).open() as f:
        before_metrics = json.load(f)
    with Path(after).open() as f:
        after_metrics = json.load(f)

    # Create comparison table
    table = Table(title="Performance Comparison")
    table.add_column("Metric", style="cyan")
    table.add_column("Before", style="yellow")
    table.add_column("After", style="green")
    table.add_column("Improvement", style="magenta")

    # Compare indexing
    if "indexing" in before_metrics and "indexing" in after_metrics:
        b_idx = before_metrics["indexing"]
        a_idx = after_metrics["indexing"]

        time_improvement = (
            (b_idx["elapsed_time_sec"] - a_idx["elapsed_time_sec"])
            / b_idx["elapsed_time_sec"]
            * 100
        )
        table.add_row(
            "Indexing Time",
            f"{b_idx['elapsed_time_sec']:.1f}s",
            f"{a_idx['elapsed_time_sec']:.1f}s",
            f"{time_improvement:+.1f}%",
        )

        memory_improvement = (
            (b_idx["memory_peak_gb"] - a_idx["memory_peak_gb"]) / b_idx["memory_peak_gb"] * 100
        )
        table.add_row(
            "Peak Memory",
            f"{b_idx['memory_peak_gb']:.2f}GB",
            f"{a_idx['memory_peak_gb']:.2f}GB",
            f"{memory_improvement:+.1f}%",
        )

    # Compare search
    if "search" in before_metrics and "search" in after_metrics:
        b_search = before_metrics["search"]
        a_search = after_metrics["search"]

        query_improvement = (
            (b_search["avg_query_time_ms"] - a_search["avg_query_time_ms"])
            / b_search["avg_query_time_ms"]
            * 100
        )
        table.add_row(
            "Avg Query Time",
            f"{b_search['avg_query_time_ms']:.1f}ms",
            f"{a_search['avg_query_time_ms']:.1f}ms",
            f"{query_improvement:+.1f}%",
        )

    console.print(table)


if __name__ == "__main__":
    app()
