"""File checksum calculation utilities.

Uses xxHash for fast, non-cryptographic checksums suitable for cache invalidation
and change detection. Provides 50-60x speedup over SHA-256.
"""

from pathlib import Path

import xxhash


class ChecksumCalculator:
    """Calculate checksums for files and content using xxHash."""

    @staticmethod
    def calculate_file_checksum(file_path: Path) -> str:
        """
        Calculate xxHash checksum for a file.

        Args:
            file_path: Path to file

        Returns:
            Hexadecimal xxHash64 checksum (16 characters)

        Raises:
            OSError: If file cannot be read

        Note:
            Uses xxHash for 50-60x faster checksums compared to SHA-256.
            Suitable for cache invalidation, not cryptographic purposes.
        """
        xxhash_hash = xxhash.xxh64()

        with Path(file_path).open("rb") as f:
            # Read file in chunks for memory efficiency
            for chunk in iter(lambda: f.read(4096), b""):
                xxhash_hash.update(chunk)

        return xxhash_hash.hexdigest()

    @staticmethod
    def calculate_content_checksum(content: str) -> str:
        """
        Calculate xxHash checksum for text content.

        Args:
            content: Text content

        Returns:
            Hexadecimal xxHash64 checksum (16 characters)

        Note:
            Uses xxHash for fast checksums suitable for cache invalidation.
        """
        return xxhash.xxh64(content.encode("utf-8")).hexdigest()

    @staticmethod
    def calculate_bytes_checksum(content: bytes) -> str:
        """
        Calculate xxHash checksum for binary content.

        Args:
            content: Binary content

        Returns:
            Hexadecimal xxHash64 checksum (16 characters)

        Note:
            Uses xxHash for fast checksums suitable for cache invalidation.
        """
        return xxhash.xxh64(content).hexdigest()


# Convenience functions
def calculate_file_checksum(file_path: Path) -> str:
    """Calculate file checksum."""
    return ChecksumCalculator.calculate_file_checksum(file_path)


def calculate_content_checksum(content: str) -> str:
    """Calculate content checksum."""
    return ChecksumCalculator.calculate_content_checksum(content)
