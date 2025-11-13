# CodeContext Scripts

Essential scripts for managing ChromaDB, running quality tests, and optimizing performance.

---

## Available Scripts

### 1. ChromaDB Management: `chroma-cli.sh`

Manage ChromaDB server lifecycle.

```bash
./scripts/chroma-cli.sh start       # Start server (localhost:8000)
./scripts/chroma-cli.sh stop        # Stop server
./scripts/chroma-cli.sh status      # Check status
./scripts/chroma-cli.sh restart     # Restart server
./scripts/chroma-cli.sh logs [-f]   # View logs
./scripts/chroma-cli.sh init        # Reset database
```

**Usage:**
- Required before indexing or searching
- Data stored in `~/.chroma/chroma_data`
- Port 8000 must be available

---

### 2. Quality Tests: `run-quality-tests.sh`

Run comprehensive E2E quality tests with ecommerce_samples dataset.

```bash
./scripts/run-quality-tests.sh                  # Use existing index
./scripts/run-quality-tests.sh --reindex        # Force reindex
./scripts/run-quality-tests.sh --clean          # Full cleanup + reindex
./scripts/run-quality-tests.sh --dry-run        # Simulation mode
```

**Test Coverage:**
- **Dataset:** tests/fixtures/ecommerce_samples/ (27 files, ~292 objects)
- **Duration:** ~3-5 minutes
- **Tests:**
  - Indexing Performance (baseline: <120s)
  - Search Quality (Ground Truth validation)
  - Document-Code Linking

**Output:**
- `tests/data/quality_results/indexing_metrics.json`
- `tests/data/quality_results/search_quality_report.json`

---

### 3. Quality Report: `quality-report.sh`

Generate comprehensive quality test report with metrics and visualizations.

```bash
./scripts/quality-report.sh
```

**Features:**
- Full ChromaDB reset
- Re-indexing with performance tracking
- Ground truth evaluation
- JSON + Markdown reports

**Output:**
- `quality_tests/reports/quality_report_YYYYMMDD_HHMMSS.json`
- `quality_tests/reports/QUALITY_REPORT_YYYYMMDD_HHMMSS.md`

---

### 4. ChromaDB Cleanup: `clean-chromadb.py`

Clean ChromaDB collections for fresh testing.

```bash
# Clean all collections
python scripts/clean-chromadb.py

# Clean specific pattern
python scripts/clean-chromadb.py --pattern ecommerce

# Preview without deleting
python scripts/clean-chromadb.py --dry-run
```

**Use Cases:**
- Before full re-indexing
- After changing embedding model
- When debugging indexing issues

---

### 5. Memory Optimization: `setup-jemalloc.sh`

Install and configure jemalloc for optimal PyTorch CPU inference.

```bash
./scripts/setup-jemalloc.sh            # Install
./scripts/setup-jemalloc.sh --check    # Check status
```

**Benefits:**
- 34% less peak memory
- 53% less average memory
- Up to 2.2x speedup

**Usage:**
```bash
# With jemalloc
LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2 codecontext index

# Or add to .bashrc
export LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2
```

---

## Common Workflows

### First-Time Setup
```bash
# 1. Start ChromaDB
./scripts/chroma-cli.sh start

# 2. Verify connection
./scripts/chroma-cli.sh status

# 3. Index your project
codecontext index

# 4. Run quality tests
./scripts/run-quality-tests.sh
```

### Before Major Changes
```bash
# 1. Run baseline tests
./scripts/run-quality-tests.sh --reindex > baseline.txt

# 2. Make your changes
# ... code modifications ...

# 3. Compare results
./scripts/run-quality-tests.sh --reindex > after.txt
diff baseline.txt after.txt
```

### Debugging Indexing Issues
```bash
# 1. Check ChromaDB
./scripts/chroma-cli.sh status
./scripts/chroma-cli.sh logs -n 100

# 2. Clean collections
python scripts/clean-chromadb.py --pattern your-project

# 3. Re-index with verbose output
codecontext index --force
```

### Performance Optimization
```bash
# 1. Install jemalloc (one-time)
./scripts/setup-jemalloc.sh

# 2. Index with jemalloc
LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2 codecontext index

# 3. Verify improvements
./scripts/run-quality-tests.sh --reindex
```

---

## Troubleshooting

### ChromaDB Won't Start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill existing process
pkill -f "chroma run"

# Try restarting
./scripts/chroma-cli.sh restart
```

### Quality Tests Failing
```bash
# 1. Verify ChromaDB is running
./scripts/chroma-cli.sh status

# 2. Clean and reindex
./scripts/run-quality-tests.sh --clean

# 3. Check dataset exists
ls tests/fixtures/ecommerce_samples/
```

### Out of Memory During Indexing
```yaml
# Reduce batch sizes in quality_tests/config.yaml
indexing:
  batch_size: 50
  parallel_workers: 2
embeddings:
  huggingface:
    batch_size: 16
```

---

## Script Maintenance

**Active Scripts (6):**
- ✅ `chroma-cli.sh` - ChromaDB management
- ✅ `clean-chromadb.py` - Collection cleanup
- ✅ `run-quality-tests.sh` - Quality testing
- ✅ `quality-report.sh` - Report generation
- ✅ `setup-jemalloc.sh` - Memory optimization
- ✅ `README.md` - This file

**Removed:**
- ❌ `dev/` - 9 development/debugging scripts (removed 2024-11-12)
- ❌ `run-quality-tests-full.sh` - Merged into run-quality-tests.sh
- ❌ `quality_tests/run.sh` - Redundant wrapper

---

## Related Documentation

- **Quality Tests:** [quality_tests/README.md](../quality_tests/README.md)
- **Configuration:** [.codecontext.yaml.example](../.codecontext.yaml.example)
- **Main Docs:** [README.md](../README.md)

---

**Last Updated:** 2024-11-12
