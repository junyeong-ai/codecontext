"""Unit tests for instruction-based embeddings.

Tests the instruction framework for code embeddings:
- InstructionType enum
- InstructionConfig validation
- Instruction application logic
- Feature flag (enable/disable)
"""

import pytest
from codecontext_core.interfaces import InstructionType
from codecontext_embeddings_huggingface.config import HuggingFaceConfig, InstructionConfig
from codecontext_embeddings_huggingface.provider import HuggingFaceEmbeddingProvider


class TestInstructionType:
    """Test InstructionType enum."""

    def test_enum_values(self):
        """All instruction types should have correct values."""
        assert InstructionType.NL2CODE_QUERY == "nl2code_query"
        assert InstructionType.NL2CODE_PASSAGE == "nl2code_passage"
        assert InstructionType.CODE2CODE_QUERY == "code2code_query"
        assert InstructionType.CODE2CODE_PASSAGE == "code2code_passage"
        assert InstructionType.QA_QUERY == "qa_query"
        assert InstructionType.QA_PASSAGE == "qa_passage"
        assert InstructionType.DOCUMENT_PASSAGE == "document_passage"

    def test_enum_count(self):
        """Should have exactly 7 instruction types."""
        assert len(list(InstructionType)) == 7

    def test_enum_is_string(self):
        """Instruction types should be string enum."""
        for inst_type in InstructionType:
            assert isinstance(inst_type.value, str)


class TestInstructionConfig:
    """Test InstructionConfig validation."""

    def test_default_config(self):
        """Default config should have instructions enabled with Jina official instructions."""
        config = InstructionConfig()

        assert config.enabled is True
        assert (
            config.nl2code_query
            == "Find the most relevant code snippet given the following query:\n"
        )
        assert config.nl2code_passage == "Candidate code snippet:\n"
        assert config.qa_query == "Find the most relevant answer given the following question:\n"
        assert config.qa_passage == "Candidate answer:\n"
        assert config.document_passage == "Candidate documentation:\n"

    def test_custom_config(self):
        """Should allow custom instruction strings."""
        config = InstructionConfig(
            enabled=False, nl2code_query="Custom query: ", nl2code_passage="Custom passage: "
        )

        assert config.enabled is False
        assert config.nl2code_query == "Custom query: "
        assert config.nl2code_passage == "Custom passage: "

    def test_all_instructions_present(self):
        """All 7 instruction fields should be present."""
        config = InstructionConfig()

        assert hasattr(config, "enabled")
        assert hasattr(config, "nl2code_query")
        assert hasattr(config, "nl2code_passage")
        assert hasattr(config, "code2code_query")
        assert hasattr(config, "code2code_passage")
        assert hasattr(config, "qa_query")
        assert hasattr(config, "qa_passage")
        assert hasattr(config, "document_passage")


class TestHuggingFaceConfigIntegration:
    """Test InstructionConfig integration with HuggingFaceConfig."""

    def test_default_huggingface_config_has_instructions(self):
        """HuggingFaceConfig should include InstructionConfig by default."""
        config = HuggingFaceConfig()

        assert hasattr(config, "instructions")
        assert isinstance(config.instructions, InstructionConfig)
        assert config.instructions.enabled is True

    def test_custom_instructions_in_huggingface_config(self):
        """Should allow custom instruction config in HuggingFaceConfig."""
        custom_instructions = InstructionConfig(enabled=False, nl2code_query="Test: ")
        config = HuggingFaceConfig(instructions=custom_instructions)

        assert config.instructions.enabled is False
        assert config.instructions.nl2code_query == "Test: "


class TestInstructionApplication:
    """Test instruction application logic."""

    @pytest.fixture
    def mock_provider(self):
        """Create provider with mocked model/tokenizer."""
        config = HuggingFaceConfig()
        provider = HuggingFaceEmbeddingProvider(config)
        # Don't initialize (would load model), just test _apply_instruction
        return provider

    def test_apply_instruction_nl2code_query(self, mock_provider):
        """NL2CODE_QUERY instruction should be applied correctly."""
        text = "repository pattern"
        result = mock_provider._apply_instruction(text, InstructionType.NL2CODE_QUERY)

        expected = (
            "Find the most relevant code snippet given the following query:\nrepository pattern"
        )
        assert result == expected

    def test_apply_instruction_nl2code_passage(self, mock_provider):
        """NL2CODE_PASSAGE instruction should be applied correctly."""
        text = "class Repository:"
        result = mock_provider._apply_instruction(text, InstructionType.NL2CODE_PASSAGE)

        expected = "Candidate code snippet:\nclass Repository:"
        assert result == expected

    def test_apply_instruction_qa_query(self, mock_provider):
        """QA_QUERY instruction should be applied correctly."""
        text = "how to configure database"
        result = mock_provider._apply_instruction(text, InstructionType.QA_QUERY)

        expected = (
            "Find the most relevant answer given the following question:\nhow to configure database"
        )
        assert result == expected

    def test_apply_instruction_qa_passage(self, mock_provider):
        """QA_PASSAGE instruction should be applied correctly."""
        text = "Configure DB with connection string"
        result = mock_provider._apply_instruction(text, InstructionType.QA_PASSAGE)

        expected = "Candidate answer:\nConfigure DB with connection string"
        assert result == expected

    def test_apply_instruction_document_passage(self, mock_provider):
        """DOCUMENT_PASSAGE instruction should be applied correctly."""
        text = "# Installation Guide"
        result = mock_provider._apply_instruction(text, InstructionType.DOCUMENT_PASSAGE)

        expected = "Candidate documentation:\n# Installation Guide"
        assert result == expected

    def test_apply_instruction_disabled(self, mock_provider):
        """When disabled, should return original text."""
        mock_provider.config.instructions.enabled = False
        text = "test text"

        result = mock_provider._apply_instruction(text, InstructionType.NL2CODE_QUERY)

        assert result == "test text"

    def test_apply_instruction_empty_text(self, mock_provider):
        """Should handle empty text correctly."""
        text = ""
        result = mock_provider._apply_instruction(text, InstructionType.NL2CODE_QUERY)

        expected = "Find the most relevant code snippet given the following query:\n"
        assert result == expected

    def test_apply_instruction_unknown_type(self, mock_provider):
        """Unknown instruction type should return plain text."""
        text = "test"
        # This won't happen in practice due to enum, but test the fallback
        result = mock_provider._apply_instruction(text, None)  # type: ignore

        # Should return instruction + text (instruction = "" for unknown type)
        assert result == "test"


class TestFeatureFlag:
    """Test instruction feature flag behavior."""

    @pytest.fixture
    def enabled_provider(self):
        """Provider with instructions enabled."""
        config = HuggingFaceConfig()
        config.instructions.enabled = True
        return HuggingFaceEmbeddingProvider(config)

    @pytest.fixture
    def disabled_provider(self):
        """Provider with instructions disabled."""
        config = HuggingFaceConfig()
        config.instructions.enabled = False
        return HuggingFaceEmbeddingProvider(config)

    def test_enabled_applies_instruction(self, enabled_provider):
        """When enabled, instruction should be applied."""
        text = "test"
        result = enabled_provider._apply_instruction(text, InstructionType.NL2CODE_QUERY)

        assert result.startswith("Find the most relevant")
        assert "test" in result

    def test_disabled_returns_plain_text(self, disabled_provider):
        """When disabled, should return plain text."""
        text = "test"
        result = disabled_provider._apply_instruction(text, InstructionType.NL2CODE_QUERY)

        assert result == "test"

    def test_disabled_no_prefix(self, disabled_provider):
        """When disabled, no instruction prefix should be added."""
        text = "repository pattern"
        result = disabled_provider._apply_instruction(text, InstructionType.NL2CODE_QUERY)

        assert not result.startswith("Find the most relevant")
        assert result == text


class TestInstructionImmutability:
    """Test that instruction application doesn't mutate original text."""

    @pytest.fixture
    def provider(self):
        """Create provider."""
        config = HuggingFaceConfig()
        return HuggingFaceEmbeddingProvider(config)

    def test_original_text_unchanged(self, provider):
        """Original text should not be modified."""
        original = "test text"
        text = original

        result = provider._apply_instruction(text, InstructionType.NL2CODE_QUERY)

        assert text == original
        assert result != original
        assert original in result


class TestInstructionLength:
    """Test instruction prefix lengths for performance analysis."""

    def test_instruction_lengths(self):
        """Instruction lengths should be reasonable (for tokenization overhead)."""
        config = InstructionConfig()

        # Query instructions (longer is OK, only used at query time)
        assert len(config.nl2code_query) < 100
        assert len(config.code2code_query) < 120
        assert len(config.qa_query) < 100

        # Passage instructions (shorter is better, used during indexing)
        assert len(config.nl2code_passage) < 40
        assert len(config.qa_passage) < 30
        assert len(config.document_passage) < 40

    def test_instruction_newline_suffix(self):
        """Instructions should end with newline for clean separation."""
        config = InstructionConfig()

        assert config.nl2code_query.endswith("\n")
        assert config.nl2code_passage.endswith("\n")
        assert config.qa_query.endswith("\n")
        assert config.qa_passage.endswith("\n")
        assert config.document_passage.endswith("\n")
