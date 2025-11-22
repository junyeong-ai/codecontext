# Quality Tests for CodeContext

**Purpose**: E2E validation of search quality using ground truth-based testing.

## Overview

**Test Scope**: CLI-based E2E tests with comprehensive ground truth validation
- ✅ Tests actual `codecontext` CLI commands
- ✅ Validates full package integration (cli + embeddings + storage)
- ✅ Measures quality metrics (Precision@K, MRR, Top-3 Match Rate)
- ✅ Ground truth-based evaluation with ecommerce_samples dataset

**Execution Profile**:
- Duration: ~5-10 minutes (depends on dataset size)
- Location: `quality_tests/` at project root
- Dataset: `tests/fixtures/ecommerce_samples/` (27 files: 16 code + 7 docs + 4 config)
- Indexed Objects: ~292 total (162 code objects + 130 document chunks)
- CI/CD: Explicitly excluded (local validation only)

## Prerequisites

1. **E-commerce Sample Dataset**: `tests/fixtures/ecommerce_samples/`
   - 27 total files (16 code + 7 docs + 4 config)
   - Languages: Java, Kotlin, Python, TypeScript, JavaScript
   - ~292 indexed objects (162 code objects + 130 document chunks)

2. **Python Environment**:
   ```bash
   uv sync
   uv run codecontext --help  # verify installation
   ```

## Quick Start

### Option 1: Run Pre-built Test Script

```bash
# Simple, automated testing
cd tests/fixtures/ecommerce_samples
uv run codecontext index --force  # Index the dataset
cd -
uv run python /tmp/ecommerce_search_quality_test.py  # Run quality tests
```

### Option 2: Run pytest Tests

```bash
# Full pytest suite with all quality tests
uv run pytest quality_tests/ -v -s

# Run only search quality tests
uv run pytest quality_tests/test_search_quality.py -v

# Run with ground truth validation
uv run pytest quality_tests/ -v --with-ground-truth
```

## Ground Truth Structure

### Location
- **Test Queries**: `quality_tests/fixtures/test_queries_ecommerce.yaml`
- **Ground Truth**: `quality_tests/fixtures/ground_truth_ecommerce.yaml`

### Ground Truth Format

```yaml
ground_truth:
  - query_id: Q001
    category: single_domain
    difficulty: easy
    relevant_items:
      - path: tests/fixtures/ecommerce_samples/docs/business/order-flow.md
        grade: 3  # Must-have
        reason: "Primary documentation for order processing"
      - path: tests/fixtures/ecommerce_samples/services/order-service/.../OrderService.java
        grade: 3
        reason: "Core order processing business logic"
      - path: tests/fixtures/ecommerce_samples/services/order-service/.../Order.java
        grade: 2  # Important
        reason: "Order domain entity"
    ranking:
      top_3_must_include:
        - tests/fixtures/ecommerce_samples/docs/business/order-flow.md
        - tests/fixtures/ecommerce_samples/services/order-service/.../OrderService.java
```

**Grading System:**
- **Grade 3** (Must-have): Core, directly relevant results
- **Grade 2** (Important): Supporting, highly relevant results
- **Grade 1** (Nice-to-have): Related, somewhat relevant results

## Test Queries

10 test queries covering different categories:

| ID | Query | Category | Difficulty |
|----|-------|----------|------------|
| Q001 | order processing flow | single_domain | easy |
| Q002 | payment gateway integration | single_domain | easy |
| Q003 | customer tier discount system | single_domain | easy |
| Q004 | inventory stock management | single_domain | easy |
| Q005 | checkout process with payment | cross_domain | medium |
| Q006 | order status tracking | cross_language | medium |
| Q007 | price calculation with tier discount | business_workflow | medium |
| Q008 | shipping cost calculation logic | technical_layer | medium |
| Q009 | complete order lifecycle from cart to delivery | complex_workflow | hard |
| Q010 | REST API endpoints and design | technical_layer | medium |

## Quality Metrics

**Primary Metrics:**
- **Precision@K**: Ratio of relevant results in top K positions
- **MRR (Mean Reciprocal Rank)**: Position of first relevant result
- **Top-3 Match Rate**: Coverage of must-have items in top 3 results

**Pass Criteria:**
- `Top-3 Match Rate >= 67%` AND `Precision@3 >= 33%`

**Expected Performance:**
- Precision@1: ≥ 70%
- Precision@3: ≥ 50%
- MRR: ≥ 70%
- Pass Rate: ≥ 70% (7/10 queries)

## Test Structure

```
quality_tests/
├── fixtures/
│   ├── ground_truth_ecommerce.yaml    # Relevance judgments
│   └── test_queries_ecommerce.yaml    # Test queries
├── monitors/
│   └── progress_monitor.py             # Progress tracking
├── conftest.py                         # Pytest fixtures
├── config.yaml                         # Test configuration
├── test_search_quality.py              # Search quality tests
├── test_indexing_performance.py        # Indexing performance tests
└── test_document_code_linking.py       # Document-code linking tests
```

## Adding New Test Queries

1. **Add query** to `test_queries_ecommerce.yaml`:
   ```yaml
   - id: Q011
     text: "new query text"
     category: single_domain
     difficulty: easy
   ```

2. **Add ground truth** to `ground_truth_ecommerce.yaml`:
   ```yaml
   - query_id: Q011
     relevant_items:
       - path: tests/fixtures/ecommerce_samples/...
         grade: 3
         reason: "Why this is relevant"
     ranking:
       top_3_must_include:
         - tests/fixtures/ecommerce_samples/...
   ```

3. **Run tests** to verify:
   ```bash
   uv run python /tmp/ecommerce_search_quality_test.py
   ```

## Interpreting Results

### Good Performance Example
```
Query Q002: "payment gateway integration"
  Precision@1: 1.000  ✅
  Precision@3: 1.000  ✅
  MRR: 1.000         ✅
  Top-3 Match: 100%  ✅
  Status: PASS
```

### Needs Improvement Example
```
Query Q003: "customer tier discount system"
  Precision@1: 0.000  ❌ (non-relevant at #1)
  Precision@3: 0.333  ❌ (only 1/3 relevant)
  MRR: 0.333         ⚠️  (first relevant at #3)
  Top-3 Match: 0%    ❌ (must-have not in top-3)
  Status: FAIL
```

**Common Issues:**
- Low Precision@1: Ranking issue, check BM25 vs Vector balance
- Low Top-3 Match: Missing core documents, check query expansion
- Low MRR: First result quality, check intent classification

## Continuous Improvement

### Workflow for Improving Search Quality

1. **Run baseline tests**:
   ```bash
   uv run python /tmp/ecommerce_search_quality_test.py > baseline.txt
   ```

2. **Identify failing queries**: Look for FAIL status

3. **Analyze root causes**:
   - Check BM25 vs Vector score balance
   - Review query classification (domain_search vs code_search)
   - Examine actual search results vs ground truth

4. **Make improvements**:
   - Adjust search weights in `.codecontext.yaml`
   - Update query expansion rules
   - Refine ground truth if expectations were wrong

5. **Verify improvements**:
   ```bash
   uv run python /tmp/ecommerce_search_quality_test.py > improved.txt
   diff baseline.txt improved.txt
   ```

## Troubleshooting

**Issue: 0% Pass Rate**
- **Cause**: Wrong dataset indexed or stale data
- **Fix**:
  ```bash
  cd tests/fixtures/ecommerce_samples
  uv run codecontext index --force
  ```

**Issue: Storage errors**
- **Cause**: Configuration issue or corrupted data
- **Fix**: Check your `.codecontext.toml` configuration and ensure Qdrant settings are correct

## Configuration

Test configuration in `quality_tests/config.yaml`:

```yaml
embeddings:
  provider: huggingface
  huggingface:
    model_name: "jinaai/jina-code-embeddings-0.5b"
    device: cpu  # Use cpu for consistency
    batch_size: 32

search:
  bm25_weight: 0.4
  vector_weight: 0.6
  rrf_k: 60
  mmr_lambda: 0.7
```

## Best Practices

1. **Always index before testing**: Ensure fresh, clean index
2. **Review failing queries individually**: Each failure has specific root cause
3. **Update ground truth carefully**: Maintain semantic accuracy
4. **Track improvements over time**: Keep baseline reports
5. **Test after major changes**: Verify no regressions

---

**Version**: 1.0 (E-commerce Ground Truth)
**Last Updated**: 2024-11-12
