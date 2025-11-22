"""Process resource monitoring."""

import os
from dataclasses import dataclass

import psutil


@dataclass
class ProcessMetrics:
    """Resource usage for process tree."""

    total_cpu: float
    total_memory: float


class ProcessTree:
    """Track resource usage for process and children."""

    def __init__(self, pid: int | None = None) -> None:
        self.pid = pid or os.getpid()
        self.process = psutil.Process(self.pid)

    def metrics(self) -> ProcessMetrics:
        """Get current CPU and memory usage for entire process tree."""
        try:
            cpu = self.process.cpu_percent(interval=0.1)
            mem = self.process.memory_info().rss / (1024 * 1024)

            for child in self.process.children(recursive=True):
                try:
                    cpu += child.cpu_percent(interval=0.1)
                    mem += child.memory_info().rss / (1024 * 1024)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            return ProcessMetrics(total_cpu=cpu, total_memory=mem)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return ProcessMetrics(total_cpu=0.0, total_memory=0.0)
