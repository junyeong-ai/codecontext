# codecontext-embeddings-openai

OpenAI embedding provider for CodeContext with rate limiting and cost tracking.

## Installation

```bash
pip install codecontext-embeddings-openai
```

## Usage

```bash
export OPENAI_API_KEY=sk-...
```

Automatically discovered via entry points. No manual configuration needed.

## Features

- OpenAI API embeddings (text-embedding-3-small/large)
- Automatic rate limiting (RPM + TPM)
- Cost tracking and estimation
- Exponential backoff retry
- Adaptive rate limiting

## Configuration

In `.codecontext.yaml`:

```yaml
embeddings:
  provider: openai
  openai:
    api_key: "sk-..."  # or use OPENAI_API_KEY env var
    model: "text-embedding-3-small"
    batch_size: 100
    rate_limit_rpm: 3000
    rate_limit_tpm: 1000000
```

## Cost Tracking

```python
from codecontext_embeddings_openai import OpenAIEmbeddingProvider

with OpenAIEmbeddingProvider(config) as provider:
    embeddings = provider.embed_batch(texts)

    # Check costs
    summary = provider.get_cost_summary()
    print(f"Total cost: ${summary['total_cost_usd']:.6f}")
```

## Python Version Support

- Python 3.13

## License

MIT
