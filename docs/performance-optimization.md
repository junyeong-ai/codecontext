# Performance Optimization

Comprehensive guide to optimizing CodeContext indexing and search performance.

---

## Performance Targets

| Operation | Target | Typical |
|-----------|--------|---------|
| **Search response** | <500ms | 200-400ms |
| **Indexing (10K files)** | <10min | 5-8 min |
| **Memory usage** | <2GB | 1-1.5GB |
| **Concurrent users** | 20+ | 50+ |

---

## Indexing Optimization

### 1. Parallel AST Parsing

**Impact:** 4-8x faster indexing

**Configuration:**

**Auto-detect (Recommended):**
```yaml
indexing:
  parallel_enabled: true
  parallel_workers: 0         # 0 = auto (cpu_count // 2, max 8)
  parallel_batch_size: 30     # Files per batch
```

**High-Performance Workstation (8+ cores):**
```yaml
indexing:
  parallel_enabled: true
  parallel_workers: 8         # Explicit worker count
  parallel_batch_size: 30
  batch_size: 200             # Storage batch size
```

**CI/CD (Limited Resources):**
```yaml
indexing:
  parallel_enabled: true
  parallel_workers: 2         # Limit workers
  parallel_batch_size: 10
  batch_size: 50
```

**Sequential Mode (Debugging):**
```yaml
indexing:
  parallel_enabled: false
```

**Performance Impact:**
- **Sequential:** Baseline (1x)
- **Parallel (4 workers):** 3-4x faster
- **Parallel (8 workers):** 5-7x faster

---

### 2. GPU-Accelerated Embeddings

**Impact:** 3-10x faster embedding generation

**Configuration:**

**Auto-Detect (Recommended):**
```yaml
embeddings:
  huggingface:
    device: auto              # Auto: MPS > CUDA > CPU
    batch_size: 64
    use_fp16: false           # Set true for GPU
```

**NVIDIA GPU (CUDA):**
```yaml
embeddings:
  huggingface:
    device: cuda
    batch_size: 128           # Larger batches for GPU
    use_fp16: true            # 2x speedup with FP16
```
- **Speed:** ~100-200 texts/second (10x faster than CPU)
- **Memory:** 2GB+ GPU VRAM

**Apple Silicon (MPS):**
```yaml
embeddings:
  huggingface:
    device: mps
    batch_size: 128
    use_fp16: true
```
- **Speed:** ~50-100 texts/second (5x faster than CPU)
- **Memory:** 2GB+ unified memory

**CPU-Only:**
```yaml
embeddings:
  huggingface:
    device: cpu
    batch_size: 32
```
- **Speed:** ~10-20 texts/second
- **Memory:** 2GB+

**Note:** Embedding generation accounts for <1% of total indexing time (most time is spent in AST parsing). GPU acceleration provides 3-5x speedup for the embedding portion only.

---

### 3. Batch Size Tuning

**Impact:** 1.2-1.5x faster indexing

**Storage Batch Size:**
```yaml
indexing:
  batch_size: 200             # Objects per batch (50-1000)
```

**Recommendations:**
- **Small RAM (<8GB):** `batch_size: 50`
- **Medium RAM (8-16GB):** `batch_size: 100-200`
- **Large RAM (16GB+):** `batch_size: 200-500`

**Trade-offs:**
- **Larger batches:** Faster indexing, higher memory usage
- **Smaller batches:** Slower indexing, lower memory usage

---

### 4. xxHash Checksums

**Impact:** 50-60x faster change detection, ~100 seconds saved per 10k files

**Feature:** Automatic (always enabled)

**Implementation:**
- Uses xxHash (non-cryptographic) instead of SHA-256
- Suitable for cache invalidation and file change detection
- No security requirement for checksums in this use case

**Performance:**
- **SHA-256:** ~2 seconds per 10k files
- **xxHash:** ~0.03 seconds per 10k files
- **Speedup:** 50-60x

---

### 5. Text Pre-Sorting

**Impact:** 20-30% faster embedding generation, ~50-100 seconds saved per 10k objects

**Feature:** Automatic (always enabled)

**Implementation:**
1. Sort texts by length before batching
2. Minimize padding overhead in transformer model
3. Preserve original order in results (internal sorting only)

**Example:**
```python
# Before sorting:
texts = ["short", "very long text here...", "medium text", "tiny"]
batches = [["short", "very long text here..."], ["medium text", "tiny"]]
# Padding waste: significant

# After sorting:
sorted_texts = ["tiny", "short", "medium text", "very long text here..."]
batches = [["tiny", "short"], ["medium text", "very long text here..."]]
# Padding waste: minimal
```

**Performance:**
- **Unsorted:** Baseline (1x)
- **Sorted:** 1.2-1.3x faster

---

### 6. Streaming Pipeline

**Impact:** Constant memory usage (<1GB peak) for large codebases

**Feature:** Automatic (always enabled)

**Implementation:**
- Process code objects in batches (streaming)
- Eliminate redundant file parsing
- Unified pipeline: relationships → embeddings → storage

**Benefits:**
- **Memory:** <1GB peak usage (regardless of codebase size)
- **Efficiency:** No redundant file reads
- **Code Quality:** 229 LOC reduction (DRY principle)

---

## Search Optimization

### 1. BM25 Index Caching

**Impact:** <50ms BM25 search latency

**Feature:** Automatic (always enabled)

**Implementation:**
- Pre-build BM25 index at startup
- Keep index in memory
- Lazy loading on first search

**Memory:** ~100MB for 10k code objects

---

### 2. Vector Search Optimization

**Impact:** ~100-200ms vector search latency

**Configuration:**

**Reduce result limit:**
```bash
codecontext search "query" --limit 5  # Instead of default 10
```

**Use filters to reduce search space:**
```bash
codecontext search "query" --language python --file-pattern "*service*"
```

---

### 3. Qdrant Collection Management

**Impact:** Optimized storage and faster queries

**Architecture:**
- Single collection per project with named vectors (dense, sparse)
- Automatic project isolation via collection naming

**Configuration:**
```toml
[storage.qdrant]
mode = "remote"
url = "http://localhost:6333"
# Collection name auto-generated from project_id
```

---

## Memory Optimization

### 1. Reduce Batch Sizes

**For <8GB RAM:**
```yaml
indexing:
  batch_size: 50
  parallel_workers: 2
  parallel_batch_size: 5

embeddings:
  huggingface:
    batch_size: 16
```

### 2. Disable Parallel Processing

**For <4GB RAM:**
```yaml
indexing:
  parallel_enabled: false
  batch_size: 50

embeddings:
  huggingface:
    batch_size: 16
```

---

## Incremental Indexing

**Impact:** 10-100x faster for small changes

**Usage:**
```bash
codecontext index --incremental
```

**Performance:**
- **Full index (10k files):** 5-8 minutes
- **Incremental (10 changed files):** 5-10 seconds

**How it works:**
1. Git-based change detection (only modified files)
2. xxHash checksums for quick comparison
3. Selective re-indexing of changed files only
4. Automatic relationship updates

---

## Profiling and Monitoring

### Built-in Profiling Tool

```bash
python scripts/profile_indexing.py /path/to/repo
```

**Output:** `indexing_profile.txt` with timing breakdown

**Example Output:**
```
Component            Time (s)    % Total
---------------------------------------
AST Parsing          245.3       82%
Embedding Generation 45.2        15%
Storage              8.1         3%
Total                298.6       100%
```

### Real-Time Monitoring

**For Quality Tests:**
```bash
uv run pytest quality_tests/ -v -s
```
- Monitors CPU, memory, disk I/O
- Tracks resource usage over time

---

## Configuration Presets

### Extreme Performance (M4 Pro/Max, 32GB+ RAM)

```yaml
indexing:
  parallel_enabled: true
  parallel_workers: 0       # Auto: cpu_count // 2, max 8
  parallel_batch_size: 50
  batch_size: 500

embeddings:
  huggingface:
    device: mps
    batch_size: 128
    use_fp16: true
    inference_threads: 0    # Auto: cpu_count // 2, max 8
```

**Expected:** 10k files in 3-5 minutes

---

### High Performance (16GB+ RAM, 8+ cores)

```yaml
indexing:
  parallel_enabled: true
  parallel_workers: 0       # Auto: cpu_count // 2, max 8
  parallel_batch_size: 30
  batch_size: 200

embeddings:
  huggingface:
    device: auto
    batch_size: 64
    use_fp16: true
    inference_threads: 0    # Auto: cpu_count // 2, max 8
```

**Expected:** 10k files in 6-8 minutes

---

### Medium Performance (8GB+ RAM, 4+ cores)

```yaml
indexing:
  parallel_enabled: true
  parallel_workers: 0       # Auto: cpu_count // 2, max 8
  parallel_batch_size: 20
  batch_size: 100

embeddings:
  huggingface:
    device: cpu
    batch_size: 32
    inference_threads: 0    # Auto: cpu_count // 2, max 8
```

**Expected:** 10k files in 10-12 minutes

---

### Low Resources (<8GB RAM)

```yaml
indexing:
  parallel_enabled: true
  parallel_workers: 2
  parallel_batch_size: 10
  batch_size: 50

embeddings:
  huggingface:
    device: cpu
    batch_size: 16
    inference_threads: 2
```

**Expected:** 10k files in 15-20 minutes

---

## Troubleshooting

### Slow Indexing

**Symptom:** Indexing takes >20 minutes for 10k files

**Debug:**
1. Check parallel workers: `parallel_enabled: true`, `parallel_workers: 0`
2. Verify device: `device: auto` (should detect MPS/CUDA if available)
3. Profile with `scripts/profile_indexing.py`

**Common Fixes:**
- Increase parallel workers
- Enable GPU acceleration
- Increase batch sizes (if sufficient RAM)

### Out of Memory

**Symptom:** Process killed during indexing

**Debug:**
1. Check current batch sizes
2. Monitor memory with `top` or `htop`

**Fixes:**
- Reduce `indexing.batch_size`
- Reduce `embeddings.batch_size`
- Disable parallel processing
- Reduce `parallel_workers`

### Slow Search

**Symptom:** Search takes >2 seconds

**Debug:**
1. Check Qdrant server: `docker ps | grep qdrant`
2. Verify collection exists: `curl http://localhost:6333/collections`
3. Check server logs: `docker logs codecontext-qdrant`

**Fixes:**
- Restart Qdrant server: `docker compose -f docker-compose.qdrant.yml restart`
- Reduce `--limit` parameter
- Use filters (`--language`, `--file-pattern`)
- Check Qdrant health: `curl http://localhost:6333/healthz`

---

## Benchmarking

### Indexing Benchmark

```bash
# Full index
time codecontext index --force

# Incremental index
time codecontext index --incremental
```

### Search Benchmark

```bash
# Measure search latency
time codecontext search "authentication flow"

# Multiple queries
for i in {1..10}; do
    time codecontext search "query $i"
done
```

---

## Related Documentation

- [Hybrid Search](hybrid-search.md)
- [Architecture Overview](architecture.md)
- [Language Optimizers](language-optimizers.md)

---

**Last Updated:** 2025-10-22
