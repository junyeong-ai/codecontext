# CodeContext Scripts

Essential scripts for CodeContext installation, uninstallation, and performance optimization.

---

## Available Scripts

### 1. Installation: `install.sh`

Install CodeContext with UV + Python 3.13 environment.

```bash
./scripts/install.sh
```

**Features:**
- ✅ Automatic dependency checks (UV, Python 3.13)
- ✅ UV tool installation (`uv tool install codecontext-cli`)
- ✅ Global configuration setup (`~/.codecontext/config.toml`)
- ✅ Claude Code skill installation (optional)
- ✅ Interactive prompts with version management

**What gets installed:**
- `codecontext` CLI binary (via UV tool)
- Global configuration with Qdrant defaults
- Claude Code skill (user-level or project-level)

---

### 2. Uninstallation: `uninstall.sh`

Clean removal of CodeContext with backup options.

```bash
./scripts/uninstall.sh
```

**Features:**
- 🗑️ Remove codecontext CLI binary
- 📦 Backup global config before deletion
- 🤖 Remove Claude Code skill (optional)
- 🧹 Cache cleanup (optional)
- ⚠️ Safe prompts for each operation

**What gets removed:**
- UV tool installation (`codecontext-cli`)
- Global config (with backup)
- Claude Code skill (optional)
- Caches (optional)

---

### 3. Memory Optimization: `setup-jemalloc.sh`

Install jemalloc for optimal PyTorch CPU inference.

```bash
./scripts/setup-jemalloc.sh          # Install
./scripts/setup-jemalloc.sh --check  # Check status
```

**Performance Benefits:**
- 📉 34% less peak memory
- 📉 53% less average memory
- 🚀 Up to 2.2x speedup in transformer workloads

**Usage:**
```bash
# One-time install
./scripts/setup-jemalloc.sh

# Run codecontext with jemalloc
LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2 codecontext index

# Or add to shell profile (~/.bashrc, ~/.zshrc)
export LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2
```

**Platform Support:**
- Linux: apt/yum/dnf package managers
- macOS: Homebrew

---

## Quick Start

### First-Time Setup

```bash
# 1. Install CodeContext
./scripts/install.sh

# 2. Start Qdrant (remote mode - recommended)
docker compose -f docker-compose.qdrant.yml up -d

# 3. Verify Qdrant is running
curl http://localhost:6333/healthz

# 4. Index your project
cd /path/to/your/project
codecontext index

# 5. Search
codecontext search "authentication flow"
```

### Alternative: Embedded Mode (No Docker)

If you prefer not to use Docker, CodeContext supports embedded Qdrant mode:

```bash
# 1. Install CodeContext
./scripts/install.sh

# 2. Edit config to use embedded mode
codecontext config edit

# 3. Change storage mode
[storage.qdrant]
mode = "embedded"  # Change from "remote" to "embedded"

# 4. Index your project (Qdrant will auto-start)
codecontext index
```

---

## Configuration

### Global Config Location
```
~/.codecontext/config.toml
```

### Edit Config
```bash
codecontext config edit
```

### Key Settings

**Storage (Qdrant)**:
```toml
[storage]
provider = "qdrant"

[storage.qdrant]
mode = "remote"                    # remote | embedded
url = "http://localhost:6333"      # Remote Qdrant URL
fusion_method = "rrf"              # rrf (default) | dbsf
prefetch_ratio_dense = 7.0         # 70% emphasis on semantic
prefetch_ratio_sparse = 3.0        # 30% emphasis on keyword
```

**Embeddings**:
```toml
[embeddings]
provider = "huggingface"

[embeddings.huggingface]
model_name = "jinaai/jina-code-embeddings-0.5b"
device = "cpu"                     # cpu | cuda | mps | auto
batch_size = 16
# lora_adapter_path = "/path/to/adapter"
```

**Search**:
```toml
[search]
default_limit = 10
enable_graph_expansion = true
graph_max_hops = 1
graph_ppr_threshold = 0.4
max_chunks_per_file = 2
diversity_preserve_top_n = 1
```

---

## LoRA Fine-Tuning Support

CodeContext supports LoRA adapters for fine-tuning embeddings on domain-specific code.

### Prerequisites

PEFT library is automatically installed via `install.sh` or `dev-install.sh`.

### Configuration

Edit your project's `.codecontext.toml` or global config:

```toml
[embeddings.huggingface]
model_name = "jinaai/jina-code-embeddings-0.5b"
device = "cpu"
lora_adapter_path = "/path/to/your/adapter"  # Path to LoRA adapter directory
```

### Directory Structure

Your LoRA adapter directory should contain:
```
adapter/
├── adapter_config.json
└── adapter_model.safetensors
```

### Usage

```bash
# 1. Configure LoRA adapter path
codecontext init  # Or edit .codecontext.toml manually

# 2. Index with fine-tuned embeddings
codecontext index

# 3. Search uses fine-tuned model automatically
codecontext search "your domain-specific query"
```

### Verification

Check if LoRA adapter is loaded:
```bash
codecontext index 2>&1 | grep -i "lora\|peft"
```

Expected output:
```
INFO - Loaded LoRA adapter from: /path/to/adapter
```

---

## Qdrant Management

### Start Qdrant
```bash
docker compose -f docker-compose.qdrant.yml up -d
```

### Check Status
```bash
curl http://localhost:6333/healthz
# or
docker ps | grep qdrant
```

### View Logs
```bash
docker logs codecontext-qdrant
docker logs -f codecontext-qdrant  # Follow logs
```

### Stop Qdrant
```bash
docker compose -f docker-compose.qdrant.yml down
```

### Reset Qdrant Data
```bash
# Stop Qdrant
docker compose -f docker-compose.qdrant.yml down

# Remove data volumes
rm -rf qdrant_storage

# Restart Qdrant
docker compose -f docker-compose.qdrant.yml up -d
```

---

## Troubleshooting

### Qdrant Not Starting

```bash
# Check if port 6333 is already in use
lsof -i :6333

# Kill existing process
docker compose -f docker-compose.qdrant.yml down

# Remove container and restart
docker rm -f codecontext-qdrant
docker compose -f docker-compose.qdrant.yml up -d
```

### codecontext Command Not Found

```bash
# Check UV tool installation
uv tool list | grep codecontext

# Ensure UV bin directory is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Add to shell profile (~/.bashrc or ~/.zshrc)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Out of Memory During Indexing

```bash
# Option 1: Install jemalloc (recommended)
./scripts/setup-jemalloc.sh
LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2 codecontext index

# Option 2: Reduce batch sizes
codecontext config edit
# Edit:
[embeddings.huggingface]
batch_size = 8  # Reduce from 16

[indexing]
parallel_workers = 1  # Reduce parallelism
```

### Slow Indexing Performance

```bash
# Option 1: Use GPU (if available)
codecontext config edit
# Edit:
[embeddings.huggingface]
device = "cuda"  # or "mps" for Apple Silicon
batch_size = 64  # Increase for GPU

# Option 2: Use jemalloc for CPU
./scripts/setup-jemalloc.sh
LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2 codecontext index
```

---

## Testing

CodeContext includes comprehensive quality tests in the `quality_tests/` directory.

### Run Tests Manually

```bash
# Ensure Qdrant is running
docker compose -f docker-compose.qdrant.yml up -d

# Run all quality tests
cd /path/to/codecontext
uv run pytest quality_tests/ -v

# Run with reindexing
uv run pytest quality_tests/ -v --reindex

# Run with ground truth evaluation
uv run pytest quality_tests/ -v --with-ground-truth
```

### Test Configuration

Tests use dedicated config: `quality_tests/config.toml`

**Key settings:**
- Storage: Qdrant remote mode (localhost:6333)
- Dataset: `tests/fixtures/ecommerce_samples/` (27 files, ~292 objects)
- Embeddings: CPU-based (jinaai/jina-code-embeddings-0.5b)

---

## Performance Optimization

### CPU Inference (Recommended)

1. **Install jemalloc** (34% memory reduction):
   ```bash
   ./scripts/setup-jemalloc.sh
   ```

2. **Configure optimal MALLOC_CONF**:
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   export MALLOC_CONF="oversize_threshold:1,background_thread:true,metadata_thp:auto,dirty_decay_ms:9000000000,muzzy_decay_ms:9000000000"
   export LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2
   ```

3. **Run indexing**:
   ```bash
   codecontext index
   ```

### GPU Acceleration (CUDA/MPS)

```bash
# Edit config
codecontext config edit

# Set device to GPU
[embeddings.huggingface]
device = "cuda"  # or "mps" for Apple Silicon
batch_size = 128  # Increase batch size for GPU
```

### Qdrant Optimization

For large codebases, enable quantization and on-disk mode:

```bash
# Edit config
codecontext config edit

# Add advanced settings
[storage.qdrant]
quantization = true    # 24x compression
on_disk = true         # Store vectors on disk
```

---

## Commands Reference

### Core Commands

```bash
# Initialize project config
codecontext init

# Index project
codecontext index
codecontext index --incremental  # Git-based incremental

# Search
codecontext search "query"
codecontext search "query" --format json  # JSON output

# Project management
codecontext list-projects
codecontext delete-project <name>
codecontext status

# Configuration
codecontext config init   # Initialize global config
codecontext config edit   # Edit in default editor
```

---

## Script Maintenance

### Active Scripts (3)

| Script | Purpose | Status |
|--------|---------|--------|
| `install.sh` | Installation & setup | ✅ Active |
| `uninstall.sh` | Clean removal | ✅ Active |
| `setup-jemalloc.sh` | Memory optimization | ✅ Active |

### Removed Scripts (2024-11-16)

| Script | Reason | Replacement |
|--------|--------|-------------|
| `chroma-cli.sh` | ChromaDB → Qdrant migration | `docker compose` |
| `quality-report.sh` | Redundant complexity | `pytest --json-report` |
| `run-quality-tests.sh` | Redundant wrapper | `uv run pytest quality_tests/` |

**Migration**: CodeContext fully migrated from ChromaDB to Qdrant (v0.5.0)

---

## Related Documentation

- **Main README**: [../README.md](../README.md)
- **Architecture**: [../docs/architecture.md](../docs/architecture.md)
- **Development Guide**: [../CLAUDE.md](../CLAUDE.md)
- **Quality Tests**: [../quality_tests/README.md](../quality_tests/README.md) (if exists)
- **GitHub**: https://github.com/junyeong-ai/codecontext

---

**Last Updated**: 2024-11-16
**Version**: 0.5.0
**Storage**: Qdrant (ChromaDB deprecated)
