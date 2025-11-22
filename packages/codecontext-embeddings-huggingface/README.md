# codecontext-embeddings-huggingface

HuggingFace embedding provider for CodeContext.

## Installation

```bash
pip install codecontext-embeddings-huggingface
```

## Usage

Automatically discovered via entry points. No manual configuration needed.

## Features

- Local embedding generation (no API costs)
- jina-code-embeddings-0.5b model (768-dim vectors)
- Batch processing with configurable size
- CPU and GPU support
- Streaming optimization support

## Configuration

In `.codecontext.yaml`:

```yaml
embeddings:
  provider: huggingface
  huggingface:
    model_name: "jinaai/jina-code-embeddings-0.5b"
    device: cpu  # or "cuda"
    batch_size: 32
```

## Python Version Support

- Python 3.13

## License

MIT
