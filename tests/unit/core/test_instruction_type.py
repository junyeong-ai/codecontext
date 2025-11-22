"""Unit tests for InstructionType enum in core package.

Tests that InstructionType enum is correctly defined and exported.
"""

from codecontext_core import InstructionType
from codecontext_core.interfaces import InstructionType as DirectInstructionType


class TestInstructionTypeExport:
    """Test InstructionType is properly exported from core package."""

    def test_exported_from_core(self):
        """InstructionType should be exported from codecontext_core."""
        from codecontext_core import InstructionType as ExportedType

        assert ExportedType is not None
        assert hasattr(ExportedType, "NL2CODE_QUERY")

    def test_same_as_interfaces(self):
        """Exported InstructionType should be same as interfaces.InstructionType."""
        assert InstructionType is DirectInstructionType

    def test_all_values_accessible(self):
        """All instruction type values should be accessible."""
        assert InstructionType.NL2CODE_QUERY
        assert InstructionType.NL2CODE_PASSAGE
        assert InstructionType.CODE2CODE_QUERY
        assert InstructionType.CODE2CODE_PASSAGE
        assert InstructionType.QA_QUERY
        assert InstructionType.QA_PASSAGE
        assert InstructionType.DOCUMENT_PASSAGE

    def test_string_enum_behavior(self):
        """InstructionType should behave as string enum."""
        query_type = InstructionType.NL2CODE_QUERY

        # Should be comparable to string
        assert query_type == "nl2code_query"

        # Should be usable in string context
        assert str(query_type) == "nl2code_query"

    def test_enum_iteration(self):
        """Should be able to iterate over all instruction types."""
        all_types = list(InstructionType)

        assert len(all_types) == 7
        assert InstructionType.NL2CODE_QUERY in all_types
        assert InstructionType.DOCUMENT_PASSAGE in all_types
