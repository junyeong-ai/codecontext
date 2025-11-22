"""Unit tests for ChecksumOptimizer.

Tests cover:
1. File-level checksum skip logic (should_skip_file)
2. Object-level embedding reuse logic (should_reuse_embedding)
3. Checksum cache updates (update_checksums)
4. Integration with process_file_with_checksum
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from codecontext.indexer.sync.checksum.optimizer import ChecksumOptimizer
from codecontext_core.models import CodeObject, FileChecksum


@pytest.fixture
def mock_storage():
    """Mock storage provider with checksum cache support."""
    storage = Mock()
    storage.get_file_checksum = Mock(return_value=None)
    storage.set_file_checksum = Mock()
    storage.get_file_checksums_batch = Mock(return_value={})
    storage.get_code_objects_by_file = Mock(return_value=[])
    return storage


@pytest.fixture
def checksum_optimizer(mock_storage):
    """Create ChecksumOptimizer instance with mock storage."""
    return ChecksumOptimizer(mock_storage)


@pytest.fixture
def sample_code_object():
    """Create a sample CodeObject for testing."""
    from codecontext_core.models import Language, ObjectType

    return CodeObject(
        name="test_function",
        object_type=ObjectType.FUNCTION,
        file_path="/test/test.py",
        relative_path="test.py",
        start_line=1,
        end_line=10,
        content="def test_function():\n    pass",
        language=Language.PYTHON,
        checksum="abc123",
        embedding=None,
    )


class TestShouldSkipFile:
    """Tests for should_skip_file() method."""

    def test_skip_file_with_matching_checksum(self, checksum_optimizer, mock_storage, tmp_path):
        """Should return True when file checksum matches cached checksum."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        # Mock cached checksum to match current file
        with patch(
            "codecontext.indexer.sync.checksum.optimizer.calculate_file_checksum"
        ) as mock_calc:
            mock_calc.return_value = "matching_checksum"

            # Mock cached checksum
            cached = FileChecksum(
                file_path=str(test_file),
                file_checksum="matching_checksum",
                last_modified=datetime.now(UTC),
                object_checksums={},
            )
            mock_storage.get_file_checksum.return_value = cached

            # Test
            result = checksum_optimizer.should_skip_file(test_file)

            # Assertions
            assert result is True
            mock_calc.assert_called_once_with(test_file)
            mock_storage.get_file_checksum.assert_called_once_with(str(test_file))

    def test_do_not_skip_file_with_different_checksum(
        self, checksum_optimizer, mock_storage, tmp_path
    ):
        """Should return False when file checksum differs from cached checksum."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        # Mock different checksums
        with patch(
            "codecontext.indexer.sync.checksum.optimizer.calculate_file_checksum"
        ) as mock_calc:
            mock_calc.return_value = "new_checksum"

            # Mock cached checksum (different)
            cached = FileChecksum(
                file_path=str(test_file),
                file_checksum="old_checksum",
                last_modified=datetime.now(UTC),
                object_checksums={},
            )
            mock_storage.get_file_checksum.return_value = cached

            # Test
            result = checksum_optimizer.should_skip_file(test_file)

            # Assertions
            assert result is False

    def test_do_not_skip_file_without_cached_checksum(
        self, checksum_optimizer, mock_storage, tmp_path
    ):
        """Should return False when no cached checksum exists."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        # Mock no cached checksum
        mock_storage.get_file_checksum.return_value = None

        with patch(
            "codecontext.indexer.sync.checksum.optimizer.calculate_file_checksum"
        ) as mock_calc:
            mock_calc.return_value = "any_checksum"

            # Test
            result = checksum_optimizer.should_skip_file(test_file)

            # Assertions
            assert result is False

    def test_handle_checksum_calculation_error(self, checksum_optimizer, mock_storage, tmp_path):
        """Should return False when checksum calculation fails."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        # Mock checksum calculation error
        with patch(
            "codecontext.indexer.sync.checksum.optimizer.calculate_file_checksum"
        ) as mock_calc:
            mock_calc.side_effect = OSError("File read error")

            # Test
            result = checksum_optimizer.should_skip_file(test_file)

            # Assertions
            assert result is False  # Don't skip on error, process normally


class TestShouldReuseEmbedding:
    """Tests for should_reuse_embedding() method."""

    def test_cannot_reuse_for_new_object(self, checksum_optimizer, sample_code_object):
        """Should return False when old_obj is None (new object)."""
        new_obj = sample_code_object
        old_obj = None

        result = checksum_optimizer.should_reuse_embedding(new_obj, old_obj)

        assert result is False

    def test_cannot_reuse_when_checksum_changed(self, checksum_optimizer, sample_code_object):
        """Should return False when object checksums differ."""
        from codecontext_core.models import Language, ObjectType

        new_obj = sample_code_object
        new_obj.checksum = "new_checksum"

        old_obj = CodeObject(
            name="test_function",
            object_type=ObjectType.FUNCTION,
            file_path="/test/test.py",
            relative_path="test.py",
            start_line=1,
            end_line=10,
            content="def test_function():\n    return 42",  # Changed content
            language=Language.PYTHON,
            checksum="old_checksum",  # Different checksum
            embedding=[0.1] * 768,  # Has embedding (768 dimensions)
        )

        result = checksum_optimizer.should_reuse_embedding(new_obj, old_obj)

        assert result is False

    def test_cannot_reuse_when_no_embedding_exists(self, checksum_optimizer, sample_code_object):
        """Should return False when old object has no embedding."""
        from codecontext_core.models import Language, ObjectType

        new_obj = sample_code_object
        new_obj.checksum = "same_checksum"

        old_obj = CodeObject(
            name="test_function",
            object_type=ObjectType.FUNCTION,
            file_path="/test/test.py",
            relative_path="test.py",
            start_line=1,
            end_line=10,
            content="def test_function():\n    pass",
            language=Language.PYTHON,
            checksum="same_checksum",
            embedding=None,  # No embedding
        )

        result = checksum_optimizer.should_reuse_embedding(new_obj, old_obj)

        assert result is False

    def test_can_reuse_when_checksum_matches_and_embedding_exists(
        self, checksum_optimizer, sample_code_object
    ):
        """Should return True when checksums match and embedding exists."""
        from codecontext_core.models import Language, ObjectType

        new_obj = sample_code_object
        new_obj.checksum = "same_checksum"

        old_obj = CodeObject(
            name="test_function",
            object_type=ObjectType.FUNCTION,
            file_path="/test/test.py",
            relative_path="test.py",
            start_line=1,
            end_line=10,
            content="def test_function():\n    pass",
            language=Language.PYTHON,
            checksum="same_checksum",  # Same checksum
            embedding=[0.1] * 768,  # Has embedding (768 dimensions)
        )

        result = checksum_optimizer.should_reuse_embedding(new_obj, old_obj)

        assert result is True


class TestChecksumCacheUpdates:
    """Tests for checksum cache update logic."""

    def test_update_checksums_success(
        self, checksum_optimizer, mock_storage, sample_code_object, tmp_path
    ):
        """Should update checksum cache with file and object checksums."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        objects = [sample_code_object]

        with patch(
            "codecontext.indexer.sync.checksum.optimizer.calculate_file_checksum"
        ) as mock_calc:
            mock_calc.return_value = "file_checksum_123"

            # Test
            checksum_optimizer.update_checksums(test_file, objects)

            # Assertions
            mock_calc.assert_called_once_with(test_file)
            mock_storage.set_file_checksum.assert_called_once()

            # Verify the FileChecksum object structure
            call_args = mock_storage.set_file_checksum.call_args[0][0]
            assert call_args.file_path == str(test_file)
            assert call_args.file_checksum == "file_checksum_123"
            assert sample_code_object.deterministic_id in call_args.object_checksums
            assert (
                call_args.object_checksums[sample_code_object.deterministic_id]
                == sample_code_object.checksum
            )

    def test_update_checksums_handles_errors(
        self, checksum_optimizer, mock_storage, sample_code_object, tmp_path
    ):
        """Should handle checksum calculation errors gracefully."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        objects = [sample_code_object]

        with patch(
            "codecontext.indexer.sync.checksum.optimizer.calculate_file_checksum"
        ) as mock_calc:
            mock_calc.side_effect = OSError("File read error")

            # Test - should not raise exception
            checksum_optimizer.update_checksums(test_file, objects)

            # Assertions - checksum cache should not be updated on error
            mock_storage.set_file_checksum.assert_not_called()


class TestProcessFileWithChecksum:
    """Integration tests for process_file_with_checksum() method."""

    async def test_skip_unchanged_file(self, checksum_optimizer, mock_storage, tmp_path):
        """Should skip processing when file checksum unchanged (fast path)."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        # Mock extractor
        mock_extractor = Mock()

        # Mock matching checksum
        with patch(
            "codecontext.indexer.sync.checksum.optimizer.calculate_file_checksum"
        ) as mock_calc:
            mock_calc.return_value = "unchanged_checksum"

            cached = FileChecksum(
                file_path=str(test_file),
                file_checksum="unchanged_checksum",
                last_modified=datetime.now(UTC),
                object_checksums={},
            )
            mock_storage.get_file_checksum.return_value = cached

            # Test
            objects_to_update, deleted_ids = await checksum_optimizer.process_file_with_checksum(
                test_file, mock_extractor
            )

            # Assertions
            assert objects_to_update == []
            assert deleted_ids == []
            mock_extractor.extract_from_file.assert_not_called()  # Fast path

    async def test_process_changed_file_with_new_objects(
        self, checksum_optimizer, mock_storage, sample_code_object, tmp_path
    ):
        """Should extract and process new objects when file changed."""
        from codecontext.indexer.extractor import ExtractionResult

        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        # Mock extractor
        mock_extractor = AsyncMock()
        new_objects = [sample_code_object]
        mock_extractor.extract_from_file.return_value = ExtractionResult(
            objects=new_objects, relationships=[]
        )

        # Mock different checksums
        with patch(
            "codecontext.indexer.sync.checksum.optimizer.calculate_file_checksum"
        ) as mock_calc:
            mock_calc.return_value = "new_checksum"

            cached = FileChecksum(
                file_path=str(test_file),
                file_checksum="old_checksum",
                last_modified=datetime.now(UTC),
                object_checksums={},
            )
            mock_storage.get_file_checksum.return_value = cached

            # No old objects
            mock_storage.get_code_objects_by_file.return_value = []

            # Test
            objects_to_update, deleted_ids = await checksum_optimizer.process_file_with_checksum(
                test_file, mock_extractor
            )

            # Assertions
            assert len(objects_to_update) == 1
            assert objects_to_update[0] == sample_code_object
            assert deleted_ids == []
            mock_extractor.extract_from_file.assert_called_once_with(str(test_file))
            mock_storage.set_file_checksum.assert_called_once()

    async def test_reuse_embeddings_for_unchanged_objects(
        self, checksum_optimizer, mock_storage, sample_code_object, tmp_path
    ):
        """Should reuse embeddings for objects with matching checksums."""
        from codecontext.indexer.extractor import ExtractionResult
        from codecontext_core.models import Language, ObjectType

        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        # Create new object (no embedding)
        new_obj = CodeObject(
            name="test_function",
            object_type=ObjectType.FUNCTION,
            file_path="/test/test.py",
            relative_path="test.py",
            start_line=1,
            end_line=10,
            content="def test_function():\n    pass",
            language=Language.PYTHON,
            checksum="same_checksum",
            embedding=None,
        )

        # Create old object (has embedding)
        old_obj = CodeObject(
            name="test_function",
            object_type=ObjectType.FUNCTION,
            file_path="/test/test.py",
            relative_path="test.py",
            start_line=1,
            end_line=10,
            content="def test_function():\n    pass",
            language=Language.PYTHON,
            checksum="same_checksum",  # Same checksum
            embedding=[0.1] * 768,  # Has embedding (768 dimensions)
        )

        # Mock extractor
        mock_extractor = AsyncMock()
        mock_extractor.extract_from_file.return_value = ExtractionResult(
            objects=[new_obj], relationships=[]
        )

        # Mock different file checksums (file changed)
        with patch(
            "codecontext.indexer.sync.checksum.optimizer.calculate_file_checksum"
        ) as mock_calc:
            mock_calc.return_value = "new_file_checksum"

            cached = FileChecksum(
                file_path=str(test_file),
                file_checksum="old_file_checksum",
                last_modified=datetime.now(UTC),
                object_checksums={},
            )
            mock_storage.get_file_checksum.return_value = cached

            # Mock old objects
            mock_storage.get_code_objects_by_file.return_value = [old_obj]

            # Test
            objects_to_update, deleted_ids = await checksum_optimizer.process_file_with_checksum(
                test_file, mock_extractor
            )

            # Assertions
            assert len(objects_to_update) == 1
            assert objects_to_update[0].embedding == old_obj.embedding  # Embedding reused!
            assert deleted_ids == []

    async def test_detect_deleted_objects(
        self, checksum_optimizer, mock_storage, sample_code_object, tmp_path
    ):
        """Should detect and return IDs of deleted objects."""
        from codecontext.indexer.extractor import ExtractionResult

        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        # Mock extractor - returns empty list (all objects deleted)
        mock_extractor = AsyncMock()
        mock_extractor.extract_from_file.return_value = ExtractionResult(
            objects=[], relationships=[]
        )

        # Mock different file checksums (file changed)
        with patch(
            "codecontext.indexer.sync.checksum.optimizer.calculate_file_checksum"
        ) as mock_calc:
            mock_calc.return_value = "new_file_checksum"

            cached = FileChecksum(
                file_path=str(test_file),
                file_checksum="old_file_checksum",
                last_modified=datetime.now(UTC),
                object_checksums={},
            )
            mock_storage.get_file_checksum.return_value = cached

            # Mock old objects (will be deleted)
            old_obj = sample_code_object
            old_obj.deterministic_id = "deleted_object_id"
            mock_storage.get_code_objects_by_file.return_value = [old_obj]

            # Test
            objects_to_update, deleted_ids = await checksum_optimizer.process_file_with_checksum(
                test_file, mock_extractor
            )

            # Assertions
            assert objects_to_update == []
            assert "deleted_object_id" in deleted_ids

    async def test_fallback_on_checksum_error(
        self, checksum_optimizer, mock_storage, sample_code_object, tmp_path
    ):
        """Should fallback to full re-indexing on checksum calculation error."""
        from codecontext.indexer.extractor import ExtractionResult

        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")

        # Mock extractor
        mock_extractor = AsyncMock()
        mock_extractor.extract_from_file.return_value = ExtractionResult(
            objects=[sample_code_object], relationships=[]
        )

        # Mock checksum calculation error
        with patch(
            "codecontext.indexer.sync.checksum.optimizer.calculate_file_checksum"
        ) as mock_calc:
            mock_calc.side_effect = OSError("File read error")

            # Test - should not raise exception
            objects_to_update, deleted_ids = await checksum_optimizer.process_file_with_checksum(
                test_file, mock_extractor
            )

            # Assertions - should fallback to full indexing
            assert len(objects_to_update) == 1
            assert objects_to_update[0] == sample_code_object
            assert deleted_ids == []
            mock_extractor.extract_from_file.assert_called_once_with(str(test_file))


class TestBatchChecksumCalculation:
    """Tests for should_skip_files_batch() method."""

    def test_batch_with_mixed_changes(self, checksum_optimizer, mock_storage, tmp_path):
        """Should correctly identify changed and unchanged files in a batch."""
        # Create test files
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file3 = tmp_path / "file3.py"

        file1.write_text("def func1(): pass")
        file2.write_text("def func2(): pass")
        file3.write_text("def func3(): pass")

        files = [file1, file2, file3]

        # Mock checksums
        with patch(
            "codecontext.indexer.sync.checksum.optimizer.calculate_file_checksum"
        ) as mock_calc:
            # Different checksums for each file
            mock_calc.side_effect = ["checksum1", "checksum2", "checksum3"]

            # Mock batch checksum query (file1 unchanged, file2 changed, file3 new)
            mock_storage.get_file_checksums_batch.return_value = {
                str(file1): "checksum1",  # Matches
                str(file2): "old_checksum",  # Different
                # file3 not in cache (new file)
            }

            # Test
            changed, unchanged = checksum_optimizer.should_skip_files_batch(files)

            # Assertions
            assert file1 in unchanged
            assert file2 in changed
            assert file3 in changed
            assert len(changed) == 2
            assert len(unchanged) == 1

    def test_batch_with_all_unchanged(self, checksum_optimizer, mock_storage, tmp_path):
        """Should return empty changed list when all files are unchanged."""
        # Create test files
        files = [tmp_path / f"file{i}.py" for i in range(3)]
        for f in files:
            f.write_text("def func(): pass")

        # Mock all checksums match
        with patch(
            "codecontext.indexer.sync.checksum.optimizer.calculate_file_checksum"
        ) as mock_calc:
            mock_calc.return_value = "same_checksum"

            # Mock batch query with all matching checksums
            mock_storage.get_file_checksums_batch.return_value = {
                str(f): "same_checksum" for f in files
            }

            # Test
            changed, unchanged = checksum_optimizer.should_skip_files_batch(files)

            # Assertions
            assert len(changed) == 0
            assert len(unchanged) == 3
            assert all(f in unchanged for f in files)

    def test_batch_with_all_changed(self, checksum_optimizer, mock_storage, tmp_path):
        """Should return all files as changed when nothing matches."""
        # Create test files
        files = [tmp_path / f"file{i}.py" for i in range(3)]
        for f in files:
            f.write_text("def func(): pass")

        # Mock all checksums differ
        with patch(
            "codecontext.indexer.sync.checksum.optimizer.calculate_file_checksum"
        ) as mock_calc:
            mock_calc.return_value = "new_checksum"

            # Mock batch query with all different checksums
            mock_storage.get_file_checksums_batch.return_value = {
                str(f): "old_checksum" for f in files
            }

            # Test
            changed, unchanged = checksum_optimizer.should_skip_files_batch(files)

            # Assertions
            assert len(changed) == 3
            assert len(unchanged) == 0
            assert all(f in changed for f in files)

    def test_batch_with_empty_list(self, checksum_optimizer, mock_storage):
        """Should handle empty file list gracefully."""
        # Test
        changed, unchanged = checksum_optimizer.should_skip_files_batch([])

        # Assertions
        assert changed == []
        assert unchanged == []

    def test_batch_with_checksum_errors(self, checksum_optimizer, mock_storage, tmp_path):
        """Should treat files with checksum errors as changed."""
        # Create test files
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"

        file1.write_text("def func1(): pass")
        file2.write_text("def func2(): pass")

        files = [file1, file2]

        # Mock checksum calculation with one error
        with patch(
            "codecontext.indexer.sync.checksum.optimizer.calculate_file_checksum"
        ) as mock_calc:

            def calc_checksum(file_path):
                if str(file1) in str(file_path):
                    raise OSError("File read error")
                return "checksum2"

            mock_calc.side_effect = calc_checksum

            # Mock batch query returns empty for file2 (new file)
            mock_storage.get_file_checksums_batch.return_value = {}

            # Test
            changed, unchanged = checksum_optimizer.should_skip_files_batch(files)

            # Assertions
            assert file1 in changed  # Error treated as changed
            assert file2 in changed  # New file
            assert len(unchanged) == 0

    def test_batch_parallel_performance(self, checksum_optimizer, mock_storage, tmp_path):
        """Should process multiple files in parallel."""
        # Create many test files
        files = [tmp_path / f"file{i}.py" for i in range(20)]
        for f in files:
            f.write_text("def func(): pass")

        # Mock checksums
        with patch(
            "codecontext.indexer.sync.checksum.optimizer.calculate_file_checksum"
        ) as mock_calc:
            mock_calc.return_value = "checksum"
            # Mock batch query returns empty (all new files)
            mock_storage.get_file_checksums_batch.return_value = {}

            # Test with max_workers parameter
            changed, _unchanged = checksum_optimizer.should_skip_files_batch(files, max_workers=4)

            # Assertions
            assert len(changed) == 20
            assert mock_calc.call_count == 20  # All files processed
            # Verify batch query was called once with all file paths
            mock_storage.get_file_checksums_batch.assert_called_once()
