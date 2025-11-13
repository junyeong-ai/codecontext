"""Progress Monitor for Quality Tests."""

import json
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import psutil

from codecontext_core.monitoring import ProcessTree


@dataclass
class ResourceSnapshot:
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float


@dataclass
class TestMetrics:
    test_name: str
    duration_seconds: float
    peak_cpu_percent: float
    peak_memory_mb: float
    avg_cpu_percent: float
    avg_memory_mb: float


class ProgressMonitor:
    """Monitors system resources in background thread."""

    def __init__(self, test_name: str, progress_file: Path | None = None, update_interval: float = 5.0) -> None:
        self.test_name = test_name
        self.progress_file = progress_file or Path("/tmp/codecontext_progress.log")
        self.update_interval = update_interval
        self.start_time: float | None = None
        self.snapshots: list[ResourceSnapshot] = []
        self.tree = ProcessTree()
        self._stop_event = threading.Event()
        self._monitor_thread: threading.Thread | None = None

    def start(self) -> None:
        """Start background monitoring."""
        self.start_time = time.time()
        self._capture_snapshot()
        self.progress_file.write_text("")

        print(f"\n{'=' * 80}")
        print(f"🔍 {self.test_name}")
        print(f"{'=' * 80}")
        print(f"\n💡 Monitor: tail -f {self.progress_file}\n")

        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while not self._stop_event.is_set():
            self._capture_snapshot()
            if self.snapshots and self.start_time:
                latest = self.snapshots[-1]
                elapsed = latest.timestamp - self.start_time
                status = (
                    f"⏱️  {elapsed:.1f}s | "
                    f"💻 CPU: {latest.cpu_percent:.1f}% | "
                    f"🧠 Memory: {latest.memory_mb:.0f}MB ({latest.memory_percent:.1f}%)\n"
                )
                try:
                    with self.progress_file.open("a") as f:
                        f.write(status)
                except Exception:
                    pass
            time.sleep(self.update_interval)

    def _capture_snapshot(self) -> None:
        """Capture current resource usage."""
        try:
            metrics = self.tree.metrics()
            mem_percent = (metrics.total_memory * 1024 * 1024) / psutil.virtual_memory().total * 100

            self.snapshots.append(
                ResourceSnapshot(
                    timestamp=time.time(),
                    cpu_percent=metrics.total_cpu,
                    memory_mb=metrics.total_memory,
                    memory_percent=mem_percent,
                )
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    def finish(self, output_path: Path | None = None) -> TestMetrics:
        """Stop monitoring and save metrics."""
        self._stop_event.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)

        self._capture_snapshot()

        if not self.start_time or not self.snapshots:
            raise RuntimeError("No monitoring data - start() not called")

        duration = time.time() - self.start_time
        cpu_values = [s.cpu_percent for s in self.snapshots]
        mem_values = [s.memory_mb for s in self.snapshots]

        metrics = TestMetrics(
            test_name=self.test_name,
            duration_seconds=duration,
            peak_cpu_percent=max(cpu_values),
            avg_cpu_percent=sum(cpu_values) / len(cpu_values),
            peak_memory_mb=max(mem_values),
            avg_memory_mb=sum(mem_values) / len(mem_values),
        )

        print(f"\n{'=' * 80}")
        print(f"✅ {self.test_name} - Completed")
        print(f"{'=' * 80}")
        print(f"Duration: {duration:.2f}s")
        print(f"Peak CPU: {metrics.peak_cpu_percent:.1f}% | Avg CPU: {metrics.avg_cpu_percent:.1f}%")
        print(f"Peak Memory: {metrics.peak_memory_mb:.0f}MB | Avg Memory: {metrics.avg_memory_mb:.0f}MB")
        print(f"{'=' * 80}\n")

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w") as f:
                json.dump(
                    {
                        "summary": asdict(metrics),
                        "snapshots": [asdict(s) for s in self.snapshots],
                    },
                    f,
                    indent=2,
                )

        return metrics
