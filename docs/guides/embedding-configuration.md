# Guide: Configuring Embedding Providers

Learn how to configure and switch between different embedding providers.

---

## Available Providers

### 1. HuggingFace (Local, Free)

**Default**: jinaai/jina-code-embeddings-0.5b (768-dim vectors)

**Implementation**: [codecontext-embeddings-huggingface](../../packages/codecontext-embeddings-huggingface/)

**Pros**:
- ✅ Free and open-source
- ✅ Runs locally (data privacy)
- ✅ Offline support
- ✅ GPU acceleration (CUDA, MPS)

**Cons**:
- ❌ Requires 2GB+ memory
- ❌ Slower on CPU
- ❌ Model download required (~1.2GB)

### 2. OpenAI (API, Paid)

**Models**: text-embedding-3-small, text-embedding-3-large

**Implementation**: [codecontext-embeddings-openai](../../packages/codecontext-embeddings-openai/)

**Pros**:
- ✅ Fast API responses
- ✅ No local resources required
- ✅ High-quality embeddings
- ✅ Built-in cost tracking

**Cons**:
- ❌ Requires API key and payment
- ❌ Data sent to cloud
- ❌ Requires internet connection

---

## Choosing a Provider

| Criterion | HuggingFace | OpenAI |
|-----------|-------------|--------|
| **Cost** | Free | ~$0.02/1M tokens |
| **Privacy** | Local | Cloud |
| **Speed** | CPU: Slow<br>GPU: Fast | Fast |
| **Offline** | ✅ Yes | ❌ No |
| **Setup** | Model download | API key |
| **Memory** | 2GB+ | Minimal |

**Recommendation**:
- **For small teams & privacy**: HuggingFace
- **For large teams & speed**: OpenAI
- **For development**: HuggingFace
- **For production**: Depends on requirements

---

## Configuration

### HuggingFace Configuration

**File**: `.codecontext.yaml` or `~/.codecontext/config.yaml`

```yaml
embeddings:
  provider: huggingface
  huggingface:
    model_name: "jinaai/jina-code-embeddings-0.5b"
    device: auto         # auto-detect: MPS > CUDA > CPU
    batch_size: 32
    cache_dir: null      # null = default (~/.cache/huggingface)
```

**Device Options**:
- `auto` - Auto-detect best device (recommended)
- `cpu` - Force CPU (slower)
- `cuda` - Force NVIDIA GPU
- `mps` - Force Apple Silicon GPU

**Environment Variables**:
```bash
export CODECONTEXT_EMBEDDING_PROVIDER=huggingface
export CODECONTEXT_EMBEDDING_MODEL=jinaai/jina-code-embeddings-0.5b
export CODECONTEXT_EMBEDDING_DEVICE=auto
export CODECONTEXT_EMBEDDING_BATCH_SIZE=32
```

### OpenAI Configuration

**File**: `.codecontext.yaml`

```yaml
embeddings:
  provider: openai
  openai:
    api_key: "${OPENAI_API_KEY}"  # Use env var for security
    model: "text-embedding-3-small"
    batch_size: 100
    max_retries: 3
    timeout_seconds: 30
```

**Model Options**:
- `text-embedding-3-small` - 1536 dims, $0.02/1M tokens
- `text-embedding-3-large` - 3072 dims, $0.13/1M tokens

**Environment Variables**:
```bash
export OPENAI_API_KEY=sk-...
export CODECONTEXT_EMBEDDING_PROVIDER=openai
export CODECONTEXT_EMBEDDING_MODEL=text-embedding-3-small
```

---

## Switching Providers

### Step 1: Update Configuration

Edit `.codecontext.yaml` and change the `provider` field:

```yaml
embeddings:
  provider: openai  # or huggingface
```

### Step 2: Re-index

Switching providers requires re-indexing (embeddings are regenerated):

```bash
# Delete project and re-index
codecontext delete-project <project_name>
codecontext index

# Or force full re-index
codecontext index --force
```

**Note**: Embeddings from different providers are **not compatible**. You must re-index the entire codebase.

---

## Performance Tuning

### HuggingFace Performance

**CPU-only (default)**:
```yaml
embeddings:
  huggingface:
    device: cpu
    batch_size: 32
```
- **Speed**: ~10-20 texts/second
- **Memory**: 2GB+

**GPU acceleration (CUDA)**:
```yaml
embeddings:
  huggingface:
    device: cuda
    batch_size: 64  # Larger batches for GPU
```
- **Speed**: ~100-200 texts/second
- **Memory**: 2GB GPU VRAM

**Apple Silicon (MPS)**:
```yaml
embeddings:
  huggingface:
    device: mps
    batch_size: 64
```
- **Speed**: ~50-100 texts/second
- **Memory**: 2GB+ unified memory

### OpenAI Performance

**Default**:
```yaml
embeddings:
  openai:
    batch_size: 100
    max_retries: 3
```
- **Speed**: ~500-1000 texts/second (API-dependent)
- **Rate limits**: Check OpenAI dashboard

**High-throughput**:
```yaml
embeddings:
  openai:
    batch_size: 200
    max_retries: 5
    timeout_seconds: 60
```

---

## Cost Tracking (OpenAI)

OpenAI provider includes automatic cost tracking:

**View costs**:
```bash
codecontext status --verbose
```

**Output example**:
```
Embedding costs:
  Total tokens processed: 1,234,567
  Estimated cost: $0.25
```

**Implementation**: [codecontext-embeddings-openai/cost_tracker.py](../../packages/codecontext-embeddings-openai/src/codecontext_embeddings_openai/cost_tracker.py)

---

## Custom Embedding Providers

To implement a custom provider, create a package that implements `EmbeddingProvider` interface:

**Interface**: [codecontext-core/interfaces.py](../../packages/codecontext-core/src/codecontext_core/interfaces.py)

**Required methods**:
```python
class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""

    @abstractmethod
    def dimension(self) -> int:
        """Return embedding dimension."""

    @abstractmethod
    def batch_size(self) -> int:
        """Return optimal batch size."""
```

**Register via entry points** in `pyproject.toml`:
```toml
[project.entry-points."codecontext.embeddings"]
my_provider = "my_package:MyProvider"
```

---

## Troubleshooting

### HuggingFace Issues

**Model download fails**:
```bash
# Check cache directory
ls -lh ~/.cache/huggingface/

# Set custom cache location
export HF_HOME=/path/to/cache
```

**Out of memory**:
```yaml
embeddings:
  huggingface:
    batch_size: 16  # Reduce batch size
```

**GPU not detected**:
```python
# Verify GPU support
python -c "import torch; print(torch.cuda.is_available())"  # CUDA
python -c "import torch; print(torch.backends.mps.is_available())"  # MPS
```

### OpenAI Issues

**API key not found**:
```bash
# Check environment variable
echo $OPENAI_API_KEY

# Or set in config
export OPENAI_API_KEY=sk-...
```

**Rate limit exceeded**:
```yaml
embeddings:
  openai:
    batch_size: 50       # Reduce batch size
    max_retries: 10      # Increase retries
```

---

## Additional Resources

- [HuggingFace Provider README](../../packages/codecontext-embeddings-huggingface/README.md)
- [OpenAI Provider README](../../packages/codecontext-embeddings-openai/README.md)
- [Configuration Reference](../../.codecontext.yaml.example)
