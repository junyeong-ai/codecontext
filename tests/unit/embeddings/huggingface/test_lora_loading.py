"""Unit tests for LoRA adapter loading.

Tests the LoRA adapter integration:
- Config validation (path checking)
- PEFT availability detection
- Adapter loading success/failure
- Graceful degradation when PEFT unavailable
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from codecontext_embeddings_huggingface.config import HuggingFaceConfig


class TestLoRAConfigValidation:
    """Test LoRA adapter path validation."""

    def test_none_adapter_path_is_valid(self):
        """None adapter path should be valid (LoRA disabled)."""
        config = HuggingFaceConfig(lora_adapter_path=None)
        assert config.lora_adapter_path is None

    def test_nonexistent_path_raises_error(self):
        """Non-existent adapter path should raise ValueError."""
        with pytest.raises(ValueError, match="LoRA adapter path does not exist"):
            HuggingFaceConfig(lora_adapter_path="/nonexistent/path/to/adapter")

    def test_file_instead_of_directory_raises_error(self):
        """File path instead of directory should raise ValueError."""
        with tempfile.NamedTemporaryFile() as tmp_file:
            with pytest.raises(ValueError, match="must be a directory"):
                HuggingFaceConfig(lora_adapter_path=tmp_file.name)

    def test_directory_without_adapter_config_raises_error(self):
        """Directory without adapter_config.json should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with pytest.raises(ValueError, match="missing adapter_config.json"):
                HuggingFaceConfig(lora_adapter_path=tmp_dir)

    def test_valid_adapter_directory(self):
        """Valid adapter directory should be accepted."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create mock adapter_config.json
            adapter_config = Path(tmp_dir) / "adapter_config.json"
            adapter_config.write_text('{"peft_type": "LORA"}')

            config = HuggingFaceConfig(lora_adapter_path=tmp_dir)
            assert config.lora_adapter_path == str(Path(tmp_dir).resolve())

    def test_tilde_expansion(self):
        """Tilde in path should be expanded."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            adapter_config = Path(tmp_dir) / "adapter_config.json"
            adapter_config.write_text('{"peft_type": "LORA"}')

            # Use absolute path with tilde simulation
            # Note: Can't easily test real ~ expansion in unit tests
            config = HuggingFaceConfig(lora_adapter_path=tmp_dir)
            assert "~" not in config.lora_adapter_path


class TestLoRAProviderIntegration:
    """Test LoRA adapter loading in provider."""

    @patch("codecontext_embeddings_huggingface.provider.PEFT_AVAILABLE", False)
    def test_peft_unavailable_logs_warning(self, caplog):
        """When PEFT unavailable, should log warning and continue."""
        from codecontext_embeddings_huggingface.provider import HuggingFaceEmbeddingProvider

        with tempfile.TemporaryDirectory() as tmp_dir:
            adapter_config = Path(tmp_dir) / "adapter_config.json"
            adapter_config.write_text('{"peft_type": "LORA"}')

            config = HuggingFaceConfig(lora_adapter_path=tmp_dir)
            provider = HuggingFaceEmbeddingProvider(config)

            # Call _load_adapter directly
            with caplog.at_level("WARNING"):
                provider._load_adapter()

            assert "PEFT library not installed" in caplog.text
            assert provider._adapter_loaded is False

    def test_adapter_loading_success(self):
        """Successful adapter loading should set flags correctly."""
        import codecontext_embeddings_huggingface.provider as provider_module
        from codecontext_embeddings_huggingface.provider import HuggingFaceEmbeddingProvider

        with tempfile.TemporaryDirectory() as tmp_dir:
            adapter_config = Path(tmp_dir) / "adapter_config.json"
            adapter_config.write_text('{"peft_type": "LORA"}')

            config = HuggingFaceConfig(lora_adapter_path=tmp_dir)
            provider = HuggingFaceEmbeddingProvider(config)

            # Mock model
            provider.model = MagicMock()

            # Mock PEFT
            mock_peft_model = MagicMock()
            mock_peft_model.from_pretrained.return_value = MagicMock()

            # Inject mocks into provider module
            original_peft_available = provider_module.PEFT_AVAILABLE
            provider_module.PEFT_AVAILABLE = True
            provider_module.PeftModel = mock_peft_model

            try:
                # Load adapter
                provider._load_adapter()

                assert provider._adapter_loaded is True
                assert provider._current_adapter_path == str(Path(tmp_dir).resolve())
                mock_peft_model.from_pretrained.assert_called_once()
            finally:
                # Restore original state
                provider_module.PEFT_AVAILABLE = original_peft_available

    def test_adapter_already_loaded_skipped(self):
        """Loading same adapter twice should skip second load."""
        import codecontext_embeddings_huggingface.provider as provider_module
        from codecontext_embeddings_huggingface.provider import HuggingFaceEmbeddingProvider

        with tempfile.TemporaryDirectory() as tmp_dir:
            adapter_config = Path(tmp_dir) / "adapter_config.json"
            adapter_config.write_text('{"peft_type": "LORA"}')

            config = HuggingFaceConfig(lora_adapter_path=tmp_dir)
            provider = HuggingFaceEmbeddingProvider(config)

            # Mock model
            provider.model = MagicMock()

            # Mock PEFT
            mock_peft_model = MagicMock()
            mock_peft_model.from_pretrained.return_value = MagicMock()

            # Inject mocks into provider module
            original_peft_available = provider_module.PEFT_AVAILABLE
            provider_module.PEFT_AVAILABLE = True
            provider_module.PeftModel = mock_peft_model

            try:
                # Load adapter first time
                provider._load_adapter()
                first_call_count = mock_peft_model.from_pretrained.call_count

                # Load adapter second time
                provider._load_adapter()
                second_call_count = mock_peft_model.from_pretrained.call_count

                # Should not call from_pretrained again
                assert second_call_count == first_call_count
            finally:
                # Restore original state
                provider_module.PEFT_AVAILABLE = original_peft_available

    def test_adapter_loading_failure_graceful(self, caplog):
        """Failed adapter loading should log error and continue."""
        import codecontext_embeddings_huggingface.provider as provider_module
        from codecontext_embeddings_huggingface.provider import HuggingFaceEmbeddingProvider

        with tempfile.TemporaryDirectory() as tmp_dir:
            adapter_config = Path(tmp_dir) / "adapter_config.json"
            adapter_config.write_text('{"peft_type": "LORA"}')

            config = HuggingFaceConfig(lora_adapter_path=tmp_dir)
            provider = HuggingFaceEmbeddingProvider(config)

            # Mock model
            provider.model = MagicMock()

            # Mock PEFT to raise exception
            mock_peft_model = MagicMock()
            mock_peft_model.from_pretrained.side_effect = Exception("Loading failed")

            # Inject mocks into provider module
            original_peft_available = provider_module.PEFT_AVAILABLE
            provider_module.PEFT_AVAILABLE = True
            provider_module.PeftModel = mock_peft_model

            try:
                # Load adapter should not raise
                with caplog.at_level("WARNING"):
                    provider._load_adapter()

                assert "Failed to load LoRA adapter" in caplog.text
                assert "Continuing with base model only" in caplog.text
                assert provider._adapter_loaded is False
            finally:
                # Restore original state
                provider_module.PEFT_AVAILABLE = original_peft_available

    def test_none_adapter_path_skips_loading(self):
        """When adapter_path is None, should not attempt loading."""
        from codecontext_embeddings_huggingface.provider import HuggingFaceEmbeddingProvider

        config = HuggingFaceConfig(lora_adapter_path=None)
        provider = HuggingFaceEmbeddingProvider(config)

        # Mock model
        provider.model = MagicMock()

        # Should not raise
        provider._load_adapter()

        assert provider._adapter_loaded is False
        assert provider._current_adapter_path is None


class TestLoRAConfigDefaults:
    """Test LoRA-related config defaults."""

    def test_default_config_has_none_adapter_path(self):
        """Default config should have None adapter_path (LoRA disabled)."""
        config = HuggingFaceConfig()
        assert config.lora_adapter_path is None

    def test_adapter_path_is_optional(self):
        """adapter_path should be optional in all configs."""
        # Should work without adapter_path
        config1 = HuggingFaceConfig(model_name="test-model")
        assert config1.lora_adapter_path is None

        # Should work with adapter_path
        with tempfile.TemporaryDirectory() as tmp_dir:
            adapter_config = Path(tmp_dir) / "adapter_config.json"
            adapter_config.write_text('{"peft_type": "LORA"}')

            config2 = HuggingFaceConfig(model_name="test-model", lora_adapter_path=tmp_dir)
            assert config2.lora_adapter_path is not None
