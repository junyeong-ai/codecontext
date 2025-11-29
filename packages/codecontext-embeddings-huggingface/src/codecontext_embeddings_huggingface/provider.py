"""HuggingFace embedding provider."""

import asyncio
import gc
import logging
import time
from pathlib import Path
from typing import AsyncGenerator

import torch
from transformers import AutoModel, AutoTokenizer

try:
    from peft import PeftModel

    PEFT_AVAILABLE = True
except ImportError:
    PEFT_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.debug("PEFT library not installed, LoRA adapter support disabled")

from codecontext_core.device import DeviceStrategy, DeviceConfig, create_device_strategy
from codecontext_core.interfaces import EmbeddingProvider, InstructionType

from .config import HuggingFaceConfig

logger = logging.getLogger(__name__)


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    def __init__(self, config: HuggingFaceConfig):
        self.config = config
        self.model: AutoModel | None = None
        self.tokenizer: AutoTokenizer | None = None
        self.device_strategy: DeviceStrategy | None = None
        self._batch_counter = 0
        self._initialized = False
        self._adapter_loaded: bool = False
        self._current_adapter_path: str | None = None

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

        self._cleanup_interval = self.config.cleanup_interval

        if self.config.use_jemalloc and self.device_strategy.get_device_name() == "cpu":
            from codecontext_core.allocator import AllocatorDetector

            AllocatorDetector.log_allocator_status(verbose=True)

        if not self.tokenizer:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config.model_name, cache_dir=self.config.cache_dir, trust_remote_code=True
            )
            self.tokenizer.padding_side = "left"

        self._load_model()

        self._initialized = True

        device_name = self.device_strategy.get_device_name()
        quant = f"({self.config.quantization})" if self.config.quantization != "none" else ""
        logger.info(
            f"Initialized {self.config.model_name}{quant} on {device_name} (cleanup_interval={self._cleanup_interval})"
        )

    def _load_model(self) -> None:
        load_kwargs = {"cache_dir": self.config.cache_dir, "trust_remote_code": True}

        if self.config.quantization == "8bit":
            load_kwargs.update({"load_in_8bit": True, "device_map": "auto"})
        elif self.config.quantization == "4bit":
            load_kwargs.update({"load_in_4bit": True, "device_map": "auto"})

        self.model = AutoModel.from_pretrained(self.config.model_name, **load_kwargs)

        if self.config.quantization == "none" and self.device_strategy:
            self.model.to(self.device_strategy.get_device_name())

        self.model.eval()

        # Load LoRA adapter if configured
        if self.config.lora_adapter_path:
            self._load_adapter()

    def _load_adapter(self) -> None:
        """Load LoRA adapter onto base model.

        Requires PEFT library to be installed. If not available, logs warning
        and continues with base model only (graceful degradation).
        """
        if not PEFT_AVAILABLE:
            logger.warning(
                f"PEFT library not installed, cannot load LoRA adapter: "
                f"{self.config.lora_adapter_path}. "
                f"Install with: pip install peft"
            )
            return

        if not self.config.lora_adapter_path:
            return

        adapter_path = Path(self.config.lora_adapter_path).expanduser()

        # Skip if already loaded
        if self._adapter_loaded and self._current_adapter_path == str(adapter_path):
            logger.debug(f"LoRA adapter already loaded from: {adapter_path}")
            return

        logger.info(f"Loading LoRA adapter from: {adapter_path}")
        load_start = time.time()

        try:
            self.model = PeftModel.from_pretrained(
                self.model, str(adapter_path), is_trainable=False
            )

            load_time = (time.time() - load_start) * 1000
            logger.info(f"LoRA adapter loaded successfully in {load_time:.1f}ms")

            self._adapter_loaded = True
            self._current_adapter_path = str(adapter_path)

        except Exception as e:
            logger.error(f"Failed to load LoRA adapter from {adapter_path}: {e}")
            logger.warning("Continuing with base model only")

    def _last_token_pooling(
        self, last_hidden_states: torch.Tensor, attention_mask: torch.Tensor
    ) -> torch.Tensor:
        left_padding = attention_mask[:, -1].sum() == attention_mask.shape[0]
        if left_padding:
            return last_hidden_states[:, -1]
        sequence_lengths = attention_mask.sum(dim=1) - 1
        batch_size = last_hidden_states.shape[0]
        return last_hidden_states[
            torch.arange(batch_size, device=last_hidden_states.device), sequence_lengths
        ]

    def _apply_instruction(self, text: str, instruction_type: InstructionType) -> str:
        """Apply instruction prefix based on type."""
        instruction_map = {
            InstructionType.NL2CODE_QUERY: self.config.instructions.nl2code_query,
            InstructionType.NL2CODE_PASSAGE: self.config.instructions.nl2code_passage,
            InstructionType.CODE2CODE_QUERY: self.config.instructions.code2code_query,
            InstructionType.CODE2CODE_PASSAGE: self.config.instructions.code2code_passage,
            InstructionType.QA_QUERY: self.config.instructions.qa_query,
            InstructionType.QA_PASSAGE: self.config.instructions.qa_passage,
        }
        return instruction_map.get(instruction_type, "") + text

    def embed_text(
        self, text: str, instruction_type: InstructionType = InstructionType.NL2CODE_QUERY
    ) -> list[float]:
        """Embed text with instruction prefix.

        Args:
            text: Text to embed
            instruction_type: Type of instruction to apply

        Returns:
            Embedding vector (896-dim)
        """
        if not self.model or not self.tokenizer:
            raise RuntimeError("Provider not initialized")

        text_with_instruction = self._apply_instruction(text, instruction_type)
        embeddings = self._embed_batch([text_with_instruction])
        return embeddings[0]

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not self.model or not self.tokenizer or not self.device_strategy:
            raise RuntimeError("Provider not initialized")

        device = self.device_strategy.get_device_name()
        batch_size = self.device_strategy.get_batch_size()
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            encoded = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=self.config.max_length,
                return_tensors="pt",
            )

            ids = encoded["input_ids"].to(device)
            mask = encoded["attention_mask"].to(device)

            with torch.no_grad():
                if self.config.use_fp16 and device != "cpu":
                    with torch.autocast(device_type=device, dtype=torch.float16):
                        output = self.model(input_ids=ids, attention_mask=mask)
                        pooled = self._last_token_pooling(output.last_hidden_state, mask)
                else:
                    output = self.model(input_ids=ids, attention_mask=mask)
                    pooled = self._last_token_pooling(output.last_hidden_state, mask)

                if self.config.normalize_embeddings:
                    pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)

                embeddings.extend(pooled.cpu().numpy().tolist())

            del ids, mask, output, pooled, encoded

            self._batch_counter += 1
            if self._batch_counter % self._cleanup_interval == 0:
                gc.collect()
                if self.device_strategy:
                    self.device_strategy.cleanup_memory()

        return embeddings

    async def embed_stream(
        self,
        chunks: AsyncGenerator[list[str], None],
        *,
        progress: object = None,
    ) -> AsyncGenerator[list[list[float]], None]:
        await self.initialize()

        batch_idx = 0
        async for batch in chunks:
            if not batch:
                yield []
                continue

            if progress and hasattr(progress, "on_batch_start"):
                progress.on_batch_start(batch_idx, len(batch))

            embeddings = await asyncio.to_thread(self._embed_batch, batch)

            if progress and hasattr(progress, "on_batch_complete"):
                progress.on_batch_complete(batch_idx, len(embeddings))

            batch_idx += 1
            yield embeddings

    def get_batch_size(self) -> int:
        return self.device_strategy.get_batch_size() if self.device_strategy else 64

    def get_dimension(self) -> int:
        if not self.model:
            raise RuntimeError("Provider not initialized")
        return int(self.model.config.hidden_size)

    async def cleanup(self) -> None:
        if not self._initialized or not self.model or not self.device_strategy:
            return

        device = self.device_strategy.get_device_name()

        with torch.no_grad():
            _ = torch.zeros(1, device=device).sum()

        gc.collect()
        await asyncio.sleep(0.05)
