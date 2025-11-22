"""NLLB translation provider."""

import asyncio
import gc
import logging
from typing import AsyncGenerator, Protocol

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

from codecontext_core.device import DeviceStrategy, DeviceConfig, create_device_strategy
from codecontext_core.interfaces import TranslationProvider

from .config import NLLBConfig

logger = logging.getLogger(__name__)


class ProgressProtocol(Protocol):
    """Protocol for progress reporting objects."""

    def on_batch_start(self, batch_idx: int, batch_size: int) -> None:
        """Called when a batch starts processing."""
        ...

    def on_batch_complete(self, batch_idx: int, count: int) -> None:
        """Called when a batch completes processing."""
        ...


class NLLBProvider(TranslationProvider):
    """NLLB-200 translation provider.

    Uses facebook/nllb-200-distilled-600M for high-quality multilingual translation.
    Supports 200 languages with state-of-the-art quality (BLEU 35-40 for ko→en).
    """

    def __init__(self, config: NLLBConfig):
        self.config = config
        self.model: AutoModelForSeq2SeqLM | None = None
        self.tokenizer: AutoTokenizer | None = None
        self.device_strategy: DeviceStrategy | None = None
        self._batch_counter = 0
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return

        device_config = DeviceConfig(
            threads=self.config.device_threads,
            memory_fraction=self.config.device_memory_fraction,
            batch_size=self.config.batch_size,
        )

        self.device_strategy = create_device_strategy(self.config.device, device_config)
        self.device_strategy.setup()

        if not self.tokenizer:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config.model_name, cache_dir=self.config.cache_dir, trust_remote_code=True
            )

        self._load_model()
        self._initialized = True

        device_name = self.device_strategy.get_device_name()
        logger.info(
            f"Initialized {self.config.model_name} on {device_name} "
            f"(cleanup_interval={self.config.cleanup_interval})"
        )

    def _load_model(self) -> None:
        """Load NLLB model."""
        if not self.device_strategy:
            raise RuntimeError("Device strategy not initialized")

        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            self.config.model_name, cache_dir=self.config.cache_dir, trust_remote_code=True
        )

        self.model.to(self.device_strategy.get_device_name())
        self.model.eval()

    def translate_text(self, text: str, source_lang: str, target_lang: str = "en") -> str:
        """Translate single text (sync, for search queries)."""
        if not self.model or not self.tokenizer:
            raise RuntimeError("Provider not initialized")

        if not text or not text.strip():
            return text

        translations = self._translate_batch([text], source_lang, target_lang)
        return translations[0]

    def _translate_batch(self, texts: list[str], source_lang: str, target_lang: str) -> list[str]:
        """Translate batch of texts."""
        if not self.model or not self.tokenizer or not self.device_strategy:
            raise RuntimeError("Provider not initialized")

        if not texts:
            return []

        # Get NLLB language codes
        src_code = self._get_lang_code(source_lang)
        tgt_code = self._get_lang_code(target_lang)

        # Set source language
        self.tokenizer.src_lang = src_code

        # Tokenize
        inputs = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self.config.max_length,
            return_tensors="pt",
        )

        device = self.device_strategy.get_device_name()
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # Get target language token ID using standard API
        tgt_token_id = self.tokenizer.convert_tokens_to_ids(tgt_code)

        # Translate
        with torch.no_grad():
            if self.config.use_fp16 and device != "cpu":
                with torch.autocast(device_type=device, dtype=torch.float16):
                    generated = self.model.generate(
                        **inputs,
                        forced_bos_token_id=tgt_token_id,
                        max_length=self.config.max_length,
                    )
            else:
                generated = self.model.generate(
                    **inputs, forced_bos_token_id=tgt_token_id, max_length=self.config.max_length
                )

        # Decode
        translations: list[str] = self.tokenizer.batch_decode(generated, skip_special_tokens=True)

        # Cleanup
        del inputs, generated

        self._batch_counter += 1
        if self._batch_counter % self.config.cleanup_interval == 0:
            gc.collect()
            self.device_strategy.cleanup_memory()

        return translations

    async def translate_stream(
        self,
        chunks: AsyncGenerator[list[str], None],
        source_lang: str,
        target_lang: str = "en",
        *,
        progress: ProgressProtocol | None = None,
    ) -> AsyncGenerator[list[str], None]:
        """Stream translations for chunks (memory-efficient batch translation)."""
        await self.initialize()

        batch_idx = 0
        async for batch in chunks:
            if not batch:
                yield []
                continue

            if progress:
                progress.on_batch_start(batch_idx, len(batch))

            translations = await asyncio.to_thread(
                self._translate_batch, batch, source_lang, target_lang
            )

            if progress:
                progress.on_batch_complete(batch_idx, len(translations))

            batch_idx += 1
            yield translations

    def _get_lang_code(self, lang: str) -> str:
        """Convert ISO 639-1 to NLLB language code.

        Args:
            lang: ISO 639-1 language code (e.g., "ko", "en")

        Returns:
            NLLB language code (e.g., "kor_Hang", "eng_Latn")
        """
        mapping = {
            "ko": "kor_Hang",
            "en": "eng_Latn",
            "ja": "jpn_Jpan",
            "zh": "zho_Hans",
            "es": "spa_Latn",
            "fr": "fra_Latn",
            "de": "deu_Latn",
            "it": "ita_Latn",
            "pt": "por_Latn",
            "ru": "rus_Cyrl",
            "ar": "arb_Arab",
            "hi": "hin_Deva",
        }
        return mapping.get(lang, "eng_Latn")

    def get_batch_size(self) -> int:
        """Return optimal batch size."""
        return self.device_strategy.get_batch_size() if self.device_strategy else 16

    async def cleanup(self) -> None:
        """Clean up resources."""
        if not self._initialized or not self.model or not self.device_strategy:
            return

        device = self.device_strategy.get_device_name()

        with torch.no_grad():
            _ = torch.zeros(1, device=device).sum()

        if self.model:
            del self.model
            self.model = None
        if self.tokenizer:
            del self.tokenizer
            self.tokenizer = None

        gc.collect()
        await asyncio.sleep(0.05)

        if self.device_strategy:
            self.device_strategy.cleanup_memory()
