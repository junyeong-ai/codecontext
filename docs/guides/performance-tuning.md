# Guide: Performance Tuning

Optimize CodeContext indexing and search performance for your use case.

---

## Performance Targets

| Operation | Target | Typical |
|-----------|--------|---------|
| **Search response** | <500ms | 200-400ms |
| **Indexing** | 10K files <10min | 5-8 min |
| **Memory usage** | <2GB | 1-1.5GB |
| **Concurrent users** | 20+ | 50+ |

---

## Indexing Performance

### 1. Parallel AST Parsing

**Default** (auto-detect 75% of CPU cores):
```yaml
indexing:
  parallel_enabled: true
  parallel_workers: 0  # 0 = auto-detect
  parallel_batch_size: 10
```

**High-performance workstation** (8+ cores):
```yaml
indexing:
  parallel_enabled: true
  parallel_workers: 8      # Explicit worker count
  parallel_batch_size: 20  # Larger batches
  batch_size: 200          # Storage batch size
```

**CI/CD** (limited resources):
```yaml
indexing:
  parallel_enabled: true
  parallel_workers: 2      # Limit workers
  parallel_batch_size: 5   # Smaller batches
  batch_size: 50
```

**Sequential mode** (debugging):
```yaml
indexing:
  parallel_enabled: false
```

**Performance impact**:
- **Sequential**: Baseline (1x)
- **Parallel (4 workers)**: 3-4x faster
- **Parallel (8 workers)**: 5-7x faster

### 2. Embedding Acceleration

**CPU-only** (default):
```yaml
embeddings:
  huggingface:
    device: cpu
    batch_size: 32
```
- **Speed**: ~10-20 texts/second
- **Memory**: 2GB+

**GPU acceleration** (NVIDIA CUDA):
```yaml
embeddings:
  huggingface:
    device: cuda
    batch_size: 64  # Larger batches for GPU
```
- **Speed**: ~100-200 texts/second (10x faster)
- **Memory**: 2GB GPU VRAM

**Apple Silicon** (MPS):
```yaml
embeddings:
  huggingface:
    device: mps
    batch_size: 64
```
- **Speed**: ~50-100 texts/second (5x faster)
- **Memory**: 2GB+ unified memory

**Auto-detect** (recommended):
```yaml
embeddings:
  huggingface:
    device: auto  # MPS > CUDA > CPU
    batch_size: 64
```

### 3. Batch Size Tuning

**Storage batch size** (how many objects to store at once):
```yaml
indexing:
  batch_size: 100  # Default
  # batch_size: 200  # High memory (faster)
  # batch_size: 50   # Low memory (slower)
```

**Embedding batch size** (how many texts to embed at once):
```yaml
embeddings:
  huggingface:
    batch_size: 32   # CPU
    # batch_size: 64   # GPU
    # batch_size: 16   # Low memory
```

**Guidelines**:
- **16GB+ RAM**: batch_size: 200, embedding batch: 64
- **8GB RAM**: batch_size: 100, embedding batch: 32
- **<8GB RAM**: batch_size: 50, embedding batch: 16

---

## Search Performance

### 1. Result Limit

Reduce number of results returned:

```bash
codecontext search "query" --limit 5   # Fast (top 5)
codecontext search "query" --limit 10  # Default
codecontext search "query" --limit 50  # Slower (more results)
```

**API**:
```yaml
search:
  default_limit: 10
```

### 2. Similarity Threshold

Filter out low-similarity results:

```yaml
search:
  min_score: 0.0   # Default (all results)
  # min_score: 0.5   # Medium threshold
  # min_score: 0.7   # High threshold (faster)
```

### 3. Language Filtering

Filter by language to reduce search space:

```bash
codecontext search "query" --language python  # Faster (language-specific)
codecontext search "query"                    # Slower (all languages)
```

---

## Memory Optimization

### 1. Reduce Batch Sizes

For memory-constrained environments:

```yaml
indexing:
  batch_size: 50
  parallel_workers: 2

embeddings:
  huggingface:
    batch_size: 16
```

### 2. Limit File Size

Skip very large files:

```yaml
indexing:
  max_file_size_mb: 10  # Default
  # max_file_size_mb: 5   # Stricter (skip large files)
```

### 3. Incremental Indexing

Use incremental indexing for daily updates:

```bash
codecontext index --incremental  # Only changed files
```

**Performance**:
- **Full index**: Processes all files
- **Incremental**: Processes only changed files (10-100x faster for small changes)

---

## Profiling

### 1. Indexing Profile

Use the included profiling script:

```bash
python scripts/profile_indexing.py /path/to/repo
```

**Output**: `indexing_profile.txt` with timing breakdown:
```
=== Indexing Performance Profile ===
Total time: 245.3s

AST Parsing:        123.4s (50.3%)
Embedding:           45.2s (18.4%)
Storage:             67.8s (27.6%)
Relationship:         8.9s (3.6%)
```

### 2. Search Profile

Enable debug logging:

```bash
export CODECONTEXT_LOG_LEVEL=DEBUG
codecontext search "query"
```

**Output** includes timing for:
- Query embedding generation
- Vector similarity search
- Relationship expansion
- Result formatting

---

## Qdrant Optimization

### 1. Server Configuration

**Start Qdrant with Docker Compose**:
```bash
# docker-compose.qdrant.yml
services:
  qdrant:
    image: qdrant/qdrant:v1.15.1
    container_name: codecontext-qdrant
    ports:
      - "6333:6333"
    volumes:
      - ./qdrant_storage:/qdrant/storage
    environment:
      - QDRANT__LOG_LEVEL=INFO

# Start server
docker compose -f docker-compose.qdrant.yml up -d
```

### 2. Connection Settings

```toml
[storage.qdrant]
mode = "remote"
url = "http://localhost:6333"
upsert_batch_size = 100  # Increase for faster indexing
```

### 3. Index Optimization

Qdrant automatically optimizes vector indexes using HNSW algorithm. For large codebases:

```toml
[storage.qdrant]
# Enable quantization for 24x compression
quantization = true
# Use on-disk storage for large datasets
on_disk = true
```

---

## Bottleneck Analysis

### Common Bottlenecks

1. **AST Parsing** (50%+ of time)
   - **Solution**: Enable parallel parsing
   - **Solution**: Increase `parallel_workers`

2. **Embedding Generation** (20%+ of time)
   - **Solution**: Use GPU acceleration (cuda/mps)
   - **Solution**: Increase `batch_size`

3. **Storage Operations** (20%+ of time)
   - **Solution**: Increase `batch_size`
   - **Solution**: Use SSD for Qdrant storage

4. **Memory Issues**
   - **Solution**: Reduce batch sizes
   - **Solution**: Use incremental indexing

### Monitoring Tools

**CPU utilization**:
```bash
# During indexing
htop
```

**Memory usage**:
```bash
# During indexing
ps aux | grep codecontext
```

**Disk I/O**:
```bash
# During indexing
iostat -x 1
```

---

## Configuration Examples

### Developer Laptop (8GB RAM, CPU)

```yaml
embeddings:
  huggingface:
    device: cpu
    batch_size: 32

indexing:
  batch_size: 100
  parallel_enabled: true
  parallel_workers: 0  # auto-detect
  parallel_batch_size: 10
```

### Workstation (32GB RAM, NVIDIA GPU)

```yaml
embeddings:
  huggingface:
    device: cuda
    batch_size: 128  # Large batches for GPU

indexing:
  batch_size: 300
  parallel_enabled: true
  parallel_workers: 12
  parallel_batch_size: 30
```

### MacBook Pro (16GB RAM, M1/M2)

```yaml
embeddings:
  huggingface:
    device: mps
    batch_size: 64

indexing:
  batch_size: 150
  parallel_enabled: true
  parallel_workers: 6  # M1/M2 has 6-8 performance cores
  parallel_batch_size: 15
```

### CI/CD Server (4GB RAM, 2 cores)

```yaml
embeddings:
  huggingface:
    device: cpu
    batch_size: 16

indexing:
  batch_size: 50
  parallel_enabled: true
  parallel_workers: 2
  parallel_batch_size: 5
  max_file_size_mb: 5  # Skip large files
```

---

## Benchmarking

### Indexing Benchmark

```bash
# Measure full index time
time codecontext index --force /path/to/repo

# Measure incremental index time
time codecontext index --incremental /path/to/repo
```

### Search Benchmark

```bash
# Measure search time
time codecontext search "query"

# Measure with different limits
time codecontext search "query" --limit 5
time codecontext search "query" --limit 50
```

---

## Expected Performance

### Indexing

| Codebase Size | CPU (Sequential) | CPU (Parallel 8x) | GPU (Parallel 8x) |
|---------------|------------------|-------------------|-------------------|
| 1K files      | 1-2 min          | 20-30 sec         | 15-20 sec         |
| 10K files     | 10-20 min        | 3-5 min           | 2-3 min           |
| 50K files     | 50-100 min       | 10-15 min         | 8-12 min          |

### Search

| Query Type | Response Time |
|------------|---------------|
| Simple (limit 5) | 100-200ms |
| Default (limit 10) | 200-400ms |
| Complex (limit 50) | 500-1000ms |

---

## Troubleshooting

### Slow Indexing

**Check**:
1. Is parallel parsing enabled?
2. Are you using GPU acceleration?
3. Is Qdrant running locally?
4. Do you have enough memory?

**Solution**:
```yaml
indexing:
  parallel_enabled: true
  parallel_workers: 8

embeddings:
  huggingface:
    device: auto  # Use GPU if available
```

### High Memory Usage

**Check**:
```bash
ps aux | grep codecontext
```

**Solution**:
```yaml
indexing:
  batch_size: 50          # Reduce
  parallel_workers: 2     # Reduce

embeddings:
  huggingface:
    batch_size: 16        # Reduce
```

### Slow Search

**Check**:
1. Is Qdrant running?
2. Are you filtering by language?
3. Is the result limit reasonable?

**Solution**:
```bash
codecontext search "query" --language python --limit 5
```

---

## Additional Resources

- [Configuration Reference](../../.codecontext.yaml.example)
- [Embedding Configuration Guide](embedding-configuration.md)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
