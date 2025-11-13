"""Progress reporters."""

import sys
import time
from typing import TextIO


class SimpleProgress:
    """Unified progress reporter."""

    def __init__(self, total: int, desc: str = "", file: TextIO = sys.stderr):
        self.total = total
        self.desc = desc
        self.file = file
        self.current = 0
        self.start_time = time.time()

    def update(self, n: int = 1) -> None:
        """Update progress by n items."""
        self.current += n
        elapsed = time.time() - self.start_time
        rate = self.current / elapsed if elapsed > 0 else 0

        if self.total > 0:
            pct = self.current * 100 // self.total
            print(
                f"\r{self.desc}: {self.current}/{self.total} ({pct}%) [{rate:.1f} items/s]",
                end="",
                file=self.file,
                flush=True,
            )
        else:
            print(
                f"\r{self.desc}: {self.current} [{rate:.1f} items/s]",
                end="",
                file=self.file,
                flush=True,
            )

        if self.current >= self.total:
            print(file=self.file, flush=True)

    def close(self) -> None:
        """Finalize progress display."""
        if self.current < self.total:
            print(file=self.file, flush=True)

    def on_batch_start(self, batch_idx: int, batch_size: int) -> None:
        """Batch API compatibility."""
        pass

    def on_batch_complete(self, batch_idx: int, count: int) -> None:
        """Batch API compatibility."""
        self.update(count)
