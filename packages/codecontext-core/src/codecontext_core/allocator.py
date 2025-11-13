"""Memory allocator detection for PyTorch CPU inference."""

import ctypes
import ctypes.util
import logging
import os
import platform
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)

AllocatorType = Literal["jemalloc", "tcmalloc", "ptmalloc", "unknown"]


@dataclass
class AllocatorInfo:
    type: AllocatorType
    detected: bool
    library_path: str | None
    version: str | None
    recommendations: list[str]


class AllocatorDetector:
    @staticmethod
    def detect() -> AllocatorInfo:
        # Check LD_PRELOAD first (most reliable indicator)
        ld_preload = os.environ.get("LD_PRELOAD", "")

        if "jemalloc" in ld_preload:
            return AllocatorDetector._create_jemalloc_info(ld_preload)
        if "tcmalloc" in ld_preload:
            return AllocatorDetector._create_tcmalloc_info(ld_preload)

        # Try to detect via loaded libraries
        allocator_type = AllocatorDetector._detect_from_libraries()

        if allocator_type == "jemalloc":
            return AllocatorDetector._create_jemalloc_info(None)
        if allocator_type == "tcmalloc":
            return AllocatorDetector._create_tcmalloc_info(None)

        # Default allocator (ptmalloc or system default)
        return AllocatorDetector._create_default_info()

    @staticmethod
    def _detect_from_libraries() -> AllocatorType:
        try:
            # Try to find jemalloc symbols
            jemalloc_path = ctypes.util.find_library("jemalloc")
            if jemalloc_path:
                try:
                    lib = ctypes.CDLL(jemalloc_path)
                    if hasattr(lib, "malloc_stats_print"):
                        return "jemalloc"
                except (OSError, AttributeError):
                    pass

            # Try to find tcmalloc symbols
            tcmalloc_path = ctypes.util.find_library("tcmalloc")
            if tcmalloc_path:
                return "tcmalloc"

        except Exception as e:
            logger.debug(f"Library detection failed: {e}")

        return "unknown"

    @staticmethod
    def _create_jemalloc_info(ld_preload: str | None) -> AllocatorInfo:
        library_path = ld_preload if ld_preload else ctypes.util.find_library("jemalloc")

        return AllocatorInfo(
            type="jemalloc",
            detected=True,
            library_path=library_path,
            version=None,
            recommendations=["✓ jemalloc active"],
        )

    @staticmethod
    def _create_tcmalloc_info(ld_preload: str | None) -> AllocatorInfo:
        library_path = ld_preload if ld_preload else ctypes.util.find_library("tcmalloc")

        return AllocatorInfo(
            type="tcmalloc",
            detected=True,
            library_path=library_path,
            version=None,
            recommendations=["✓ tcmalloc active"],
        )

    @staticmethod
    def _create_default_info() -> AllocatorInfo:
        system = platform.system()

        if system == "Linux":
            install = "sudo apt-get install libjemalloc-dev"
            preload = "/usr/lib/x86_64-linux-gnu/libjemalloc.so.2"
        elif system == "Darwin":
            install = "brew install jemalloc"
            preload = "$(brew --prefix jemalloc)/lib/libjemalloc.dylib"
        else:
            install = "see ./scripts/setup-jemalloc.sh"
            preload = "/path/to/libjemalloc.so"

        return AllocatorInfo(
            type="ptmalloc",
            detected=False,
            library_path=None,
            version=None,
            recommendations=[
                "⚠ CPU memory fragmentation likely",
                f"Install: {install}",
                f"Use: LD_PRELOAD={preload} codecontext index",
            ],
        )

    @staticmethod
    def log_allocator_status(verbose: bool = True) -> AllocatorInfo:
        info = AllocatorDetector.detect()

        if info.detected and info.type in ("jemalloc", "tcmalloc"):
            logger.info(f"Allocator: {info.type}")
        else:
            logger.warning("Default allocator - memory fragmentation likely")
            if verbose:
                for rec in info.recommendations:
                    logger.warning(f"  {rec}")

        return info
