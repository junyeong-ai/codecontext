#!/usr/bin/env bash
# CodeContext Quality Report Generator
# Runs full quality tests and generates comprehensive report with ground truth evaluation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORT_DIR="$PROJECT_ROOT/quality_tests/reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

# Create report directory
mkdir -p "$REPORT_DIR"

cd "$PROJECT_ROOT"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  CodeContext Quality Report Generator"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Step 1: Check ChromaDB
log_info "Checking ChromaDB status..."
if ! ./scripts/chroma-cli.sh status > /dev/null 2>&1; then
    log_warn "ChromaDB not running, starting..."
    ./scripts/chroma-cli.sh start
fi
log_success "ChromaDB is running"

# Step 2: Reset ChromaDB
log_info "Resetting ChromaDB for clean test..."
./scripts/chroma-cli.sh stop
./scripts/chroma-cli.sh init --force
./scripts/chroma-cli.sh start
log_success "ChromaDB reset completed"

# Step 3: Run quality tests with re-indexing and ground truth
log_info "Running quality tests (with re-indexing and ground truth)..."
echo ""
log_info "This may take 5-15 minutes depending on your system..."
echo ""

# Run tests with JSON report
REPORT_FILE="$REPORT_DIR/quality_report_${TIMESTAMP}.json"
if uv run pytest quality_tests/ \
    --reindex \
    --with-ground-truth \
    -v \
    --json-report \
    --json-report-file="$REPORT_FILE" \
    --json-report-indent=2 \
    --tb=short; then
    log_success "All quality tests passed"
    TEST_RESULT="PASSED"
else
    log_warn "Some tests failed or have warnings"
    TEST_RESULT="FAILED"
fi

# Step 4: Generate markdown report
log_info "Generating markdown report..."
MARKDOWN_REPORT="$REPORT_DIR/QUALITY_REPORT_${TIMESTAMP}.md"

cat > "$MARKDOWN_REPORT" << 'REPORT_HEADER'
# CodeContext Quality Test Report

**Generated:** $(date '+%Y-%m-%d %H:%M:%S')
**Configuration:** quality_tests/config.yaml
**Test Mode:** Full re-index with ground truth evaluation

---

## Executive Summary

REPORT_HEADER

# Add test results summary
if [ -f "$REPORT_FILE" ]; then
    log_info "Parsing test results..."

    # Extract key metrics using Python
    python3 << 'EOF' >> "$MARKDOWN_REPORT"
import json
import sys
from pathlib import Path

report_file = Path("$REPORT_FILE")
if not report_file.exists():
    print("Report file not found")
    sys.exit(1)

with open(report_file) as f:
    data = json.load(f)

# Summary
summary = data.get("summary", {})
print(f"**Test Result:** {'✅ PASSED' if summary.get('failed', 0) == 0 else '⚠️ FAILED'}")
print(f"**Total Tests:** {summary.get('total', 0)}")
print(f"**Passed:** {summary.get('passed', 0)}")
print(f"**Failed:** {summary.get('failed', 0)}")
print(f"**Skipped:** {summary.get('skipped', 0)}")
print(f"**Duration:** {summary.get('duration', 0):.2f} seconds ({summary.get('duration', 0)/60:.1f} minutes)")
print()
print("---")
print()

# Test categories
print("## Test Results by Category")
print()

tests = data.get("tests", [])
categories = {}

for test in tests:
    # Extract category from test name
    nodeid = test.get("nodeid", "")
    if "::" in nodeid:
        parts = nodeid.split("::")
        category = parts[0].replace("quality_tests/", "").replace(".py", "")
        test_name = parts[-1] if len(parts) > 1 else "unknown"
    else:
        category = "other"
        test_name = nodeid

    if category not in categories:
        categories[category] = []

    categories[category].append({
        "name": test_name,
        "outcome": test.get("outcome", "unknown"),
        "duration": test.get("duration", 0)
    })

for category, tests_list in sorted(categories.items()):
    print(f"### {category.replace('_', ' ').title()}")
    print()
    print("| Test | Result | Duration |")
    print("|------|--------|----------|")

    for test in tests_list:
        outcome = test["outcome"]
        if outcome == "passed":
            icon = "✅"
        elif outcome == "failed":
            icon = "❌"
        elif outcome == "skipped":
            icon = "⏭️"
        else:
            icon = "❓"

        print(f"| {test['name']} | {icon} {outcome.upper()} | {test['duration']:.2f}s |")

    print()

print("---")
print()
EOF

fi

# Add indexing metrics if available
INDEXING_METRICS="$PROJECT_ROOT/tests/data/quality_results/indexing_metrics.json"
if [ -f "$INDEXING_METRICS" ]; then
    log_info "Adding indexing performance metrics..."

    cat >> "$MARKDOWN_REPORT" << 'EOF'

## Indexing Performance

EOF

    python3 << 'METRICS_EOF' >> "$MARKDOWN_REPORT"
import json
from pathlib import Path

metrics_file = Path("$INDEXING_METRICS")
if metrics_file.exists():
    with open(metrics_file) as f:
        metrics = json.load(f)

    print("| Metric | Value |")
    print("|--------|-------|")
    print(f"| Duration | {metrics.get('duration_seconds', 0):.2f}s ({metrics.get('duration_seconds', 0)/60:.1f} min) |")
    print(f"| Peak CPU | {metrics.get('peak_cpu_percent', 0):.1f}% |")
    print(f"| Avg CPU | {metrics.get('avg_cpu_percent', 0):.1f}% |")
    print(f"| Peak Memory | {metrics.get('peak_memory_mb', 0):.1f} MB |")
    print(f"| Avg Memory | {metrics.get('avg_memory_mb', 0):.1f} MB |")
    print()

    # Performance assessment
    duration = metrics.get('duration_seconds', 0)
    baseline = 300.0  # 5 minutes

    print("### Performance Assessment")
    print()
    if duration < baseline:
        print(f"✅ **EXCELLENT** - Indexing completed in {duration:.1f}s (baseline: {baseline:.0f}s)")
    elif duration < baseline * 2:
        print(f"⚠️ **ACCEPTABLE** - Indexing took {duration:.1f}s (baseline: {baseline:.0f}s, {(duration/baseline-1)*100:.1f}% over)")
    else:
        print(f"❌ **NEEDS OPTIMIZATION** - Indexing took {duration:.1f}s (baseline: {baseline:.0f}s, {(duration/baseline-1)*100:.1f}% over)")
    print()

METRICS_EOF
fi

# Add search quality metrics if available
SEARCH_QUALITY="$PROJECT_ROOT/tests/data/quality_results/search_quality_report.json"
if [ -f "$SEARCH_QUALITY" ]; then
    log_info "Adding search quality metrics..."

    cat >> "$MARKDOWN_REPORT" << 'EOF'

---

## Search Quality Metrics

EOF

    python3 << 'SEARCH_EOF' >> "$MARKDOWN_REPORT"
import json
from pathlib import Path

search_file = Path("$SEARCH_QUALITY")
if search_file.exists():
    with open(search_file) as f:
        data = json.load(f)

    # Overall metrics
    overall = data.get("overall_metrics", {})
    print("### Overall Performance")
    print()
    print("| Metric | Value | Status |")
    print("|--------|-------|--------|")

    p10 = overall.get("precision_at_10", 0)
    r20 = overall.get("recall_at_20", 0)
    mrr = overall.get("mrr", 0)

    p10_status = "✅ PASS" if p10 >= 0.4 else "❌ FAIL"
    r20_status = "✅ PASS" if r20 >= 0.5 else "❌ FAIL"
    mrr_status = "✅ PASS" if mrr >= 0.6 else "❌ FAIL"

    print(f"| Precision@10 | {p10:.1%} | {p10_status} |")
    print(f"| Recall@20 | {r20:.1%} | {r20_status} |")
    print(f"| MRR | {mrr:.3f} | {mrr_status} |")
    print()

    # Per-query results
    results = data.get("results", [])
    if results:
        print("### Top Queries Performance")
        print()
        print("| Query | P@10 | R@20 | MRR |")
        print("|-------|------|------|-----|")

        for result in results[:10]:  # Top 10 queries
            query = result.get("query", "")[:50]
            if len(result.get("query", "")) > 50:
                query += "..."
            p10 = result.get("precision_at_10", 0)
            r20 = result.get("recall_at_20", 0)
            mrr = result.get("mrr", 0)
            print(f"| {query} | {p10:.2f} | {r20:.2f} | {mrr:.3f} |")

        print()

SEARCH_EOF
fi

# Add configuration summary
cat >> "$MARKDOWN_REPORT" << 'CONFIG_EOF'

---

## Configuration Summary

**Embeddings:**
- Provider: HuggingFace
- Model: jinaai/jina-code-embeddings-0.5b
- Device: auto (MPS/CUDA/CPU)
- Batch Size: 32
- FP16: false (precision mode)
- Inference Threads: 0 (auto)

**Indexing:**
- Batch Size: 256
- Parallel Workers: 10
- File Chunk Size: 30

**Search:**
- BM25 Weight: 0.4 (40% keyword + 60% semantic)
- MMR Lambda: 0.75 (75% relevance + 25% diversity)
- Graph Expansion: Enabled (1-hop PPR)
- Max Chunks Per File: 3

---

## Recommendations

Based on the test results:

1. **Performance Optimization**
   - If indexing time exceeds baseline, consider:
     - Enabling FP16 for GPU acceleration (2-3x speedup)
     - Increasing batch sizes for better throughput
     - Checking system resource availability

2. **Search Quality**
   - Monitor Precision@10 (target: ≥40%)
   - Monitor Recall@20 (target: ≥50%)
   - Adjust hybrid weights if needed

3. **Next Steps**
   - Review failed tests (if any)
   - Update ground truth annotations for new features
   - Consider CI/CD integration if performance is acceptable

---

## Files Generated

CONFIG_EOF

echo "- JSON Report: \`$REPORT_FILE\`" >> "$MARKDOWN_REPORT"
echo "- Markdown Report: \`$MARKDOWN_REPORT\`" >> "$MARKDOWN_REPORT"
if [ -f "$INDEXING_METRICS" ]; then
    echo "- Indexing Metrics: \`$INDEXING_METRICS\`" >> "$MARKDOWN_REPORT"
fi
if [ -f "$SEARCH_QUALITY" ]; then
    echo "- Search Quality: \`$SEARCH_QUALITY\`" >> "$MARKDOWN_REPORT"
fi

log_success "Markdown report generated"

# Summary
echo ""
echo "═══════════════════════════════════════════════════════════════"
log_success "Quality report generation completed!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
log_info "Reports generated:"
echo "  - JSON:     $REPORT_FILE"
echo "  - Markdown: $MARKDOWN_REPORT"
echo ""
log_info "View report:"
echo "  cat $MARKDOWN_REPORT"
echo ""
