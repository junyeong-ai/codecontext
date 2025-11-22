"""Device optimization strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DeviceConfig:
    """Device configuration.

    Attributes:
        threads: CPU threads (0 = auto)
        memory_fraction: GPU memory limit (0.0-1.0)
        batch_size: Device-specific batch size (None = use device default)
        enable_tf32: Enable TF32 for GPU matmul
        sync_before_cleanup: Sync GPU before cache clear
    """

    threads: int = 0
    memory_fraction: float = 0.8
    batch_size: int | None = None
    enable_tf32: bool = True
    sync_before_cleanup: bool = True


class DeviceStrategy(ABC):
    """Device strategy."""

    def __init__(self, config: DeviceConfig):
        self.config = config

    @abstractmethod
    def setup(self) -> None:
        """Setup device."""
        pass

    @abstractmethod
    def cleanup_memory(self) -> None:
        """Cleanup memory."""
        pass

    @abstractmethod
    def get_device_name(self) -> str:
        """Get device name (cpu, cuda, mps)."""
        pass

    def get_batch_size(self) -> int:
        if self.config.batch_size is None:
            return 16  # Default batch size
        return self.config.batch_size


class CPUStrategy(DeviceStrategy):
    def __init__(self, config: DeviceConfig):
        super().__init__(config)
        self._allocator_checked = False

    def setup(self) -> None:
        import torch
        import os

        threads = self.config.threads or os.cpu_count() or 4
        torch.set_num_threads(threads)
        os.environ["OMP_NUM_THREADS"] = str(threads)
        os.environ["MKL_NUM_THREADS"] = str(threads)

        torch.set_flush_denormal(True)

        if not self._allocator_checked:
            self._check_allocator()
            self._allocator_checked = True

    def _check_allocator(self) -> None:
        try:
            from codecontext_core.allocator import AllocatorDetector
            import logging

            logger = logging.getLogger(__name__)
            info = AllocatorDetector.detect()

            if info.type in ("jemalloc", "tcmalloc"):
                logger.info(f"Allocator: {info.type}")
            else:
                logger.warning("Default allocator - memory fragmentation likely")
                for rec in info.recommendations:
                    logger.warning(f"  {rec}")
        except ImportError:
            pass

    def cleanup_memory(self) -> None:
        import gc
        import torch

        with torch.no_grad():
            _ = torch.zeros(1).sum()

        gc.collect()
        self._malloc_trim()

    def _malloc_trim(self) -> None:
        try:
            import ctypes
            import sys

            if sys.platform == "darwin":
                try:
                    libjemalloc = ctypes.CDLL("libjemalloc.dylib")
                    libjemalloc.malloc_stats_print(None, None, None)
                except OSError:
                    pass
            else:
                libc = ctypes.CDLL("libc.so.6")
                if hasattr(libc, "malloc_trim"):
                    libc.malloc_trim(0)
        except Exception:
            pass

    def get_device_name(self) -> str:
        return "cpu"


def cleanup_all_devices() -> None:
    """Cleanup all device memory (CPU, CUDA, MPS).

    Can be called without DeviceStrategy instance.
    Safe to call even if torch is not installed.
    """
    import gc

    gc.collect()

    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.synchronize()
            torch.cuda.empty_cache()

        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            if hasattr(torch, "mps") and hasattr(torch.mps, "synchronize"):
                torch.mps.synchronize()
            if hasattr(torch.backends.mps, "empty_cache"):
                torch.backends.mps.empty_cache()
    except ImportError:
        pass


class CUDAStrategy(DeviceStrategy):
    """CUDA strategy."""

    def setup(self) -> None:
        import torch

        if self.config.memory_fraction < 1.0:
            torch.cuda.set_per_process_memory_fraction(self.config.memory_fraction)

        torch.backends.cuda.matmul.allow_tf32 = self.config.enable_tf32
        torch.backends.cudnn.allow_tf32 = self.config.enable_tf32

    def cleanup_memory(self) -> None:
        import gc
        import torch

        if self.config.sync_before_cleanup:
            torch.cuda.synchronize()

        gc.collect()
        torch.cuda.empty_cache()

    def get_device_name(self) -> str:
        return "cuda"


class MPSStrategy(DeviceStrategy):
    """MPS strategy."""

    def setup(self) -> None:
        import os

        os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = str(self.config.memory_fraction)

    def cleanup_memory(self) -> None:
        import gc
        import torch

        if self.config.sync_before_cleanup:
            torch.mps.synchronize()

        gc.collect()
        torch.mps.empty_cache()

    def get_device_name(self) -> str:
        return "mps"


# Device strategy registry (follows Elasticsearch pattern)
_DEVICE_STRATEGIES: dict[str, type[DeviceStrategy]] = {
    "cpu": CPUStrategy,
    "cuda": CUDAStrategy,
    "mps": MPSStrategy,
}


def create_device_strategy(device: str, config: DeviceConfig) -> DeviceStrategy:
    """Factory for device strategies.

    Args:
        device: Device type (cpu, cuda, mps) or "auto"
        config: Device configuration

    Returns:
        Appropriate device strategy

    Raises:
        ValueError: If device is unknown or unavailable
    """
    # Normalize to lowercase to handle case variations
    device = device.lower().strip()

    # Auto-detect device if requested
    if device == "auto":
        device = _auto_detect_device()

    # Lookup strategy class
    strategy_class = _DEVICE_STRATEGIES.get(device)
    if not strategy_class:
        valid = ", ".join(_DEVICE_STRATEGIES.keys())
        raise ValueError(f"Unknown device: {device}. Valid: {valid}, auto")

    return strategy_class(config)


def _auto_detect_device() -> str:
    """Auto-detect best available device.

    Returns:
        Device name: "mps", "cuda", or "cpu"
    """
    import torch

    if torch.backends.mps.is_available():
        return "mps"
    elif torch.cuda.is_available():
        return "cuda"
    else:
        return "cpu"
