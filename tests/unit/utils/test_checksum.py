"""Tests for checksum calculation utilities.

This module tests xxHash checksum calculation for files and content.
xxHash provides 50-60x faster checksums than SHA-256 for cache invalidation.
"""

import tempfile
from pathlib import Path

import pytest
from codecontext.utils.checksum import (
    ChecksumCalculator,
    calculate_content_checksum,
    calculate_file_checksum,
)

# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture
def temp_text_file():
    """Create a temporary text file with known content."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
        f.write("Hello, World!")
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def temp_binary_file():
    """Create a temporary binary file."""
    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
        f.write(b"\x00\x01\x02\x03\x04\x05")
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def temp_large_file():
    """Create a large file for chunk reading test."""
    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
        # Write 10KB of data
        f.write(b"A" * 10240)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink(missing_ok=True)


# ======================================================================
# Test Classes
# ======================================================================


class TestChecksumCalculatorFileChecksum:
    """Test file checksum calculation."""

    def test_calculates_checksum_for_text_file(self, temp_text_file):
        """Should calculate xxHash checksum for text file.

        Given: Text file with known content
        When: calculate_file_checksum is called
        Then: Should return xxHash hex digest (16 chars)
        """
        # Act
        result = ChecksumCalculator.calculate_file_checksum(temp_text_file)

        # Assert
        assert isinstance(result, str)
        assert len(result) == 16  # xxHash64 produces 16-character hex string
        assert all(c in "0123456789abcdef" for c in result)

    def test_calculates_checksum_for_binary_file(self, temp_binary_file):
        """Should calculate checksum for binary file."""
        # Act
        result = ChecksumCalculator.calculate_file_checksum(temp_binary_file)

        # Assert
        assert isinstance(result, str)
        assert len(result) == 16

    def test_calculates_checksum_for_empty_file(self):
        """Should calculate checksum for empty file."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            # Write nothing
            temp_path = Path(f.name)

        try:
            # Act
            result = ChecksumCalculator.calculate_file_checksum(temp_path)

            # Assert
            assert isinstance(result, str)
            assert len(result) == 16
            assert all(c in "0123456789abcdef" for c in result)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_calculates_same_checksum_for_same_content(self, temp_text_file):
        """Should return same checksum for multiple calls on same file."""
        # Act
        result1 = ChecksumCalculator.calculate_file_checksum(temp_text_file)
        result2 = ChecksumCalculator.calculate_file_checksum(temp_text_file)

        # Assert
        assert result1 == result2

    def test_calculates_different_checksum_for_different_content(self):
        """Should return different checksums for different content."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f1:
            f1.write("content1")
            path1 = Path(f1.name)

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f2:
            f2.write("content2")
            path2 = Path(f2.name)

        try:
            # Act
            checksum1 = ChecksumCalculator.calculate_file_checksum(path1)
            checksum2 = ChecksumCalculator.calculate_file_checksum(path2)

            # Assert
            assert checksum1 != checksum2
        finally:
            path1.unlink(missing_ok=True)
            path2.unlink(missing_ok=True)

    def test_handles_large_file_with_chunking(self, temp_large_file):
        """Should handle large files by reading in chunks."""
        # Act
        result = ChecksumCalculator.calculate_file_checksum(temp_large_file)

        # Assert
        assert isinstance(result, str)
        assert len(result) == 16

    def test_raises_error_for_nonexistent_file(self):
        """Should raise OSError for nonexistent file."""
        # Arrange
        nonexistent = Path("/nonexistent/file.txt")

        # Act & Assert
        with pytest.raises(OSError):
            ChecksumCalculator.calculate_file_checksum(nonexistent)


class TestChecksumCalculatorContentChecksum:
    """Test content checksum calculation."""

    def test_calculates_checksum_for_text_content(self):
        """Should calculate xxHash checksum for text content.

        Given: Text string
        When: calculate_content_checksum is called
        Then: Should return xxHash hex digest (16 chars)
        """
        # Arrange
        content = "Hello, World!"

        # Act
        result = ChecksumCalculator.calculate_content_checksum(content)

        # Assert
        assert isinstance(result, str)
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_calculates_checksum_for_empty_string(self):
        """Should calculate checksum for empty string."""
        # Act
        result = ChecksumCalculator.calculate_content_checksum("")

        # Assert
        assert isinstance(result, str)
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_calculates_checksum_for_unicode_content(self):
        """Should handle Unicode characters."""
        # Arrange
        content = "Hello 世界 🌍"

        # Act
        result = ChecksumCalculator.calculate_content_checksum(content)

        # Assert
        assert isinstance(result, str)
        assert len(result) == 16

    def test_same_content_produces_same_checksum(self):
        """Should produce same checksum for same content."""
        # Arrange
        content = "test content"

        # Act
        result1 = ChecksumCalculator.calculate_content_checksum(content)
        result2 = ChecksumCalculator.calculate_content_checksum(content)

        # Assert
        assert result1 == result2

    def test_different_content_produces_different_checksum(self):
        """Should produce different checksums for different content."""
        # Act
        checksum1 = ChecksumCalculator.calculate_content_checksum("content1")
        checksum2 = ChecksumCalculator.calculate_content_checksum("content2")

        # Assert
        assert checksum1 != checksum2


class TestChecksumCalculatorBytesChecksum:
    """Test bytes checksum calculation."""

    def test_calculates_checksum_for_bytes(self):
        """Should calculate xxHash checksum for bytes content.

        Given: Binary bytes
        When: calculate_bytes_checksum is called
        Then: Should return xxHash hex digest (16 chars)
        """
        # Arrange
        content = b"Hello, World!"

        # Act
        result = ChecksumCalculator.calculate_bytes_checksum(content)

        # Assert
        assert isinstance(result, str)
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_calculates_checksum_for_empty_bytes(self):
        """Should calculate checksum for empty bytes."""
        # Act
        result = ChecksumCalculator.calculate_bytes_checksum(b"")

        # Assert
        assert isinstance(result, str)
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_calculates_checksum_for_binary_data(self):
        """Should handle binary data."""
        # Arrange
        binary_data = b"\x00\x01\x02\x03\xff\xfe\xfd"

        # Act
        result = ChecksumCalculator.calculate_bytes_checksum(binary_data)

        # Assert
        assert isinstance(result, str)
        assert len(result) == 16

    def test_same_bytes_produce_same_checksum(self):
        """Should produce same checksum for same bytes."""
        # Arrange
        content = b"test bytes"

        # Act
        result1 = ChecksumCalculator.calculate_bytes_checksum(content)
        result2 = ChecksumCalculator.calculate_bytes_checksum(content)

        # Assert
        assert result1 == result2


class TestConvenienceFunctions:
    """Test convenience wrapper functions."""

    def test_calculate_file_checksum_function(self, temp_text_file):
        """Should provide convenience function for file checksum.

        Given: File path
        When: calculate_file_checksum function is called
        Then: Should delegate to ChecksumCalculator
        """
        # Act
        result = calculate_file_checksum(temp_text_file)

        # Assert
        assert isinstance(result, str)
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_calculate_content_checksum_function(self):
        """Should provide convenience function for content checksum.

        Given: Text content
        When: calculate_content_checksum function is called
        Then: Should delegate to ChecksumCalculator
        """
        # Arrange
        content = "Hello, World!"

        # Act
        result = calculate_content_checksum(content)

        # Assert
        assert isinstance(result, str)
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)


class TestChecksumConsistency:
    """Test consistency between different checksum methods."""

    def test_file_and_content_checksums_match(self):
        """File and content checksums should match for same data."""
        # Arrange
        content = "test data"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            # Act
            file_checksum = ChecksumCalculator.calculate_file_checksum(temp_path)
            content_checksum = ChecksumCalculator.calculate_content_checksum(content)

            # Assert
            assert file_checksum == content_checksum
        finally:
            temp_path.unlink(missing_ok=True)

    def test_content_and_bytes_checksums_match(self):
        """Content and bytes checksums should match for same data."""
        # Arrange
        text = "test data"
        bytes_data = text.encode("utf-8")

        # Act
        content_checksum = ChecksumCalculator.calculate_content_checksum(text)
        bytes_checksum = ChecksumCalculator.calculate_bytes_checksum(bytes_data)

        # Assert
        assert content_checksum == bytes_checksum


# ======================================================================
# Parametrized Tests
# ======================================================================


@pytest.mark.parametrize(
    "content,expected_length",
    [
        ("", 16),
        ("a", 16),
        ("short text", 16),
        ("a" * 1000, 16),  # Long text
        ("Hello 世界 🌍", 16),  # Unicode
    ],
)
def test_content_checksum_always_16_chars(content, expected_length):
    """Should always produce 16-character hex string (xxHash64)."""
    # Act
    result = ChecksumCalculator.calculate_content_checksum(content)

    # Assert
    assert len(result) == expected_length
    assert all(c in "0123456789abcdef" for c in result)


@pytest.mark.parametrize(
    "bytes_data",
    [
        b"",
        b"a",
        b"\x00",
        b"\xff",
        b"\x00\x01\x02\x03",
        b"A" * 1000,
    ],
)
def test_bytes_checksum_always_16_chars(bytes_data):
    """Should always produce 16-character hex string for bytes (xxHash64)."""
    # Act
    result = ChecksumCalculator.calculate_bytes_checksum(bytes_data)

    # Assert
    assert len(result) == 16
    assert all(c in "0123456789abcdef" for c in result)
