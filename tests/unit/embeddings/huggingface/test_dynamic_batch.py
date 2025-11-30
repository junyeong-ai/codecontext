"""Tests for dynamic batch size calculation."""

from unittest.mock import MagicMock, patch

import pytest
from codecontext_embeddings_huggingface.config import HuggingFaceConfig
from codecontext_embeddings_huggingface.provider import HuggingFaceEmbeddingProvider


class TestDynamicBatchSize:
    """Tests for _calculate_dynamic_batch_size method."""

    @pytest.fixture
    def provider(self):
        config = HuggingFaceConfig()
        return HuggingFaceEmbeddingProvider(config)

    def test_zero_length_returns_base_batch_size(self, provider):
        assert provider._calculate_dynamic_batch_size(0, 64) == 64

    def test_short_text_uses_base_batch_size(self, provider):
        assert provider._calculate_dynamic_batch_size(100, 64) == 64

    def test_medium_text_reduces_batch_size(self, provider):
        assert provider._calculate_dynamic_batch_size(10000, 64) == 8  # ~2500 tokens

    def test_long_text_further_reduces_batch_size(self, provider):
        assert provider._calculate_dynamic_batch_size(20000, 64) == 4  # ~5000 tokens

    def test_very_long_text_uses_batch_size_2(self, provider):
        assert provider._calculate_dynamic_batch_size(40000, 64) == 2  # ~10000 tokens

    def test_extremely_long_text_uses_batch_size_1(self, provider):
        assert provider._calculate_dynamic_batch_size(80000, 64) == 1  # ~20000 tokens

    def test_respects_base_batch_size_limit(self, provider):
        assert provider._calculate_dynamic_batch_size(100, 4) == 4


class TestEmbedBatch:
    """Tests for _embed_batch method."""

    @pytest.fixture
    def provider(self):
        config = HuggingFaceConfig()
        provider = HuggingFaceEmbeddingProvider(config)
        provider.model = MagicMock()
        provider.tokenizer = MagicMock()
        provider.device_strategy = MagicMock()
        provider.device_strategy.get_device_name.return_value = "cpu"
        provider.device_strategy.get_batch_size.return_value = 64
        provider._cleanup_interval = 100
        return provider

    @patch.object(HuggingFaceEmbeddingProvider, "_embed_single_batch")
    def test_preserves_original_order(self, mock_embed, provider):
        mock_embed.side_effect = lambda batch, device: [[float(len(t))] for t in batch]

        texts = ["aaa", "a", "aa"]
        result = provider._embed_batch(texts)

        assert result == [[3.0], [1.0], [2.0]]

    @patch.object(HuggingFaceEmbeddingProvider, "_embed_single_batch")
    def test_empty_texts_returns_empty(self, mock_embed, provider):
        result = provider._embed_batch([])
        assert result == []
        mock_embed.assert_not_called()
