# CodeContext Translation - NLLB

NLLB-200 translation provider for CodeContext.

## Features

- **SOTA Quality**: BLEU 35-40 for Korean→English translation
- **200 Languages**: Full multilingual support
- **Memory Efficient**: Streaming API, device strategies
- **Fast**: CPU/CUDA/MPS support with automatic device detection
- **Model**: facebook/nllb-200-distilled-600M (2.4GB)

## Installation

```bash
pip install codecontext-translation-nllb
```

## Usage

```python
from codecontext_translation_nllb import NLLBProvider, NLLBConfig

config = NLLBConfig(device="auto")
provider = NLLBProvider(config)

await provider.initialize()

# Single translation
result = provider.translate_text(
    "사용자 인증 정책",
    source_lang="ko",
    target_lang="en"
)
# Output: "user authentication policy"

# Cleanup
await provider.cleanup()
```

## Configuration

```python
config = NLLBConfig(
    model_name="facebook/nllb-200-distilled-600M",
    device="auto",  # auto, cpu, cuda, mps
    batch_size=16,  # None = device auto
    use_fp16=False,  # GPU/MPS only
    cleanup_interval=5
)
```

## Performance

| Device | Speed | Memory |
|--------|-------|--------|
| CPU | 300ms | 4GB |
| CUDA | 50ms | 4GB |
| MPS | 50ms | 4GB |

## License

MIT
