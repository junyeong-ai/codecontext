#!/usr/bin/env bash
# =============================================================================
# CodeContext Quality Tests - Unified Script
# =============================================================================
#
# E-commerce samples 기반 품질 테스트:
# - Dataset: tests/fixtures/ecommerce_samples/ (27 files, ~292 objects)
# - Tests: Indexing Performance, Search Quality, Document-Code Linking
#
# Usage:
#   ./scripts/run-quality-tests.sh                  # 기존 인덱스 사용
#   ./scripts/run-quality-tests.sh --reindex        # 재색인
#   ./scripts/run-quality-tests.sh --clean          # 완전 초기화
#   ./scripts/run-quality-tests.sh --dry-run        # 시뮬레이션
#
# =============================================================================

set -e  # Exit on error

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
DRY_RUN=false
SKIP_CLEAN=false
CHROMADB_PATTERN="ecommerce"  # Clean ecommerce collections by default

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-clean)
            SKIP_CLEAN=true
            shift
            ;;
        --clean-all)
            CHROMADB_PATTERN=""  # Clean all collections
            shift
            ;;
        -h|--help)
            cat << EOF
Usage: $0 [OPTIONS]

Options:
  --dry-run       시뮬레이션 모드 (실제 삭제/테스트 없음)
  --skip-clean    ChromaDB 초기화 스킵
  --clean-all     모든 ChromaDB 컬렉션 삭제 (기본: quality만)
  -h, --help      도움말 표시

Examples:
  $0                   # 전체 워크플로우 (quality 컬렉션만 초기화)
  $0 --dry-run         # 시뮬레이션
  $0 --skip-clean      # 기존 인덱스로 테스트
  $0 --clean-all       # 모든 컬렉션 초기화 후 테스트
EOF
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${BOLD}${CYAN}"
echo "================================================================================"
echo "🧪 CodeContext Quality Tests - Full Workflow"
echo "================================================================================"
echo -e "${NC}"

# Check if running in dry-run mode
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}🔍 DRY RUN MODE - No actual changes will be made${NC}\n"
fi

# =============================================================================
# Step 1: Check Prerequisites
# =============================================================================
echo -e "${BOLD}${BLUE}Step 1: Checking Prerequisites${NC}"
echo "--------------------------------------------------------------------------------"

# Check ChromaDB is running
echo -n "Checking ChromaDB server... "
if curl -s http://localhost:8000/api/v2 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
    echo ""
    echo -e "${YELLOW}ChromaDB is not running. Starting it now...${NC}"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${CYAN}[DRY RUN] Would run: ./scripts/chroma-cli.sh start${NC}"
    else
        "$SCRIPT_DIR/chroma-cli.sh" start
        sleep 3  # Wait for startup

        # Verify again
        if curl -s http://localhost:8000/api/v2 > /dev/null 2>&1; then
            echo -e "${GREEN}✓ ChromaDB started successfully${NC}"
        else
            echo -e "${RED}✗ Failed to start ChromaDB${NC}"
            exit 1
        fi
    fi
fi

# Check sample fixtures exist
echo -n "Checking sample fixtures... "
SAMPLES_DIR="$PROJECT_ROOT/tests/fixtures/ecommerce_samples"
if [ -d "$SAMPLES_DIR" ]; then
    FILE_COUNT=$(find "$SAMPLES_DIR" -type f \( -name "*.py" -o -name "*.java" -o -name "*.kt" -o -name "*.ts" -o -name "*.js" -o -name "*.md" \) | wc -l | tr -d ' ')
    echo -e "${GREEN}✓ Found ($FILE_COUNT files)${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    echo -e "${RED}Sample directory not found: $SAMPLES_DIR${NC}"
    exit 1
fi

# Check Python environment
echo -n "Checking Python environment... "
if command -v uv &> /dev/null; then
    echo -e "${GREEN}✓ UV installed${NC}"
else
    echo -e "${RED}✗ UV not found${NC}"
    echo -e "${RED}Install UV: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
    exit 1
fi

echo ""

# =============================================================================
# Step 2: Clean ChromaDB Collections (Optional)
# =============================================================================
if [ "$SKIP_CLEAN" = true ]; then
    echo -e "${BOLD}${BLUE}Step 2: ChromaDB Cleanup${NC}"
    echo "--------------------------------------------------------------------------------"
    echo -e "${YELLOW}⏩ Skipped (--skip-clean)${NC}\n"
else
    echo -e "${BOLD}${BLUE}Step 2: Clean ChromaDB Collections${NC}"
    echo "--------------------------------------------------------------------------------"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${CYAN}[DRY RUN] Would clean ChromaDB collections (pattern: ${CHROMADB_PATTERN:-all})${NC}\n"
    else
        # Build clean command (use uv run for proper environment)
        CLEAN_CMD="uv run python $SCRIPT_DIR/clean-chromadb.py"
        if [ -n "$CHROMADB_PATTERN" ]; then
            CLEAN_CMD="$CLEAN_CMD --pattern $CHROMADB_PATTERN"
        fi

        echo -e "${YELLOW}Running: $CLEAN_CMD${NC}\n"

        # Run cleanup (will prompt for confirmation unless automated)
        if [ -t 0 ]; then
            # Interactive mode
            $CLEAN_CMD
        else
            # Non-interactive mode (CI/automation)
            echo "yes" | $CLEAN_CMD
        fi

        echo ""
    fi
fi

# =============================================================================
# Step 3: Show Test Plan
# =============================================================================
echo -e "${BOLD}${BLUE}Step 3: Test Plan${NC}"
echo "--------------------------------------------------------------------------------"

cat << EOF
테스트 구성:
  • Fixture: tests/fixtures/ecommerce_samples/ (27 files, ~292 objects)
  • Config:  quality_tests/config.yaml
  • Model:   jinaai/jina-code-embeddings-0.5b (CPU)
  • Collection: ecommerce-samples_*

테스트 카테고리:
  ✓ Indexing Performance (3 tests)
    - 색인 완료 검증
    - 성능 기준선 검증 (<120s)
    - 출력 형식 검증

  ✓ Search Quality (3 tests)
    - 검색 결과 유효성
    - JSON 형식 검증
    - Ground Truth 품질 메트릭 (Essential Coverage, Actionability, Precision)

  ✓ Document-Code Linking (3 tests)
    - Markdown 검색 가능성
    - 문서→코드 쿼리
    - 다중 언어 연결 (Python, Java, Kotlin, TypeScript, JavaScript)

예상 소요 시간: 3-5분

EOF

if [ "$DRY_RUN" = true ]; then
    if [ "$SKIP_CLEAN" = true ]; then
        echo -e "${CYAN}[DRY RUN] Would run pytest with --with-ground-truth (no reindex)${NC}\n"
    else
        echo -e "${CYAN}[DRY RUN] Would run pytest with --reindex and --with-ground-truth${NC}\n"
    fi
    exit 0
fi

# Confirmation prompt (only in interactive mode)
if [ -t 0 ]; then
    echo -n -e "${YELLOW}Continue with quality tests? (yes/no): ${NC}"
    read -r CONFIRM
    echo ""

    if [ "$CONFIRM" != "yes" ]; then
        echo -e "${RED}❌ Tests cancelled${NC}"
        exit 0
    fi
fi

# =============================================================================
# Step 4: Run Quality Tests
# =============================================================================
echo -e "${BOLD}${BLUE}Step 4: Running Quality Tests${NC}"
echo "--------------------------------------------------------------------------------"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Build pytest command
if [ "$SKIP_CLEAN" = true ]; then
    PYTEST_CMD="uv run pytest quality_tests/ -v -s --with-ground-truth"
else
    PYTEST_CMD="uv run pytest quality_tests/ -v -s --reindex --with-ground-truth"
fi

echo -e "${CYAN}Running: $PYTEST_CMD${NC}\n"
echo -e "${BOLD}${GREEN}"
echo "================================================================================"
echo "🚀 Starting Quality Tests"
echo "================================================================================"
echo -e "${NC}\n"

# Record start time
START_TIME=$(date +%s)

# Run tests
set +e  # Don't exit on test failures
$PYTEST_CMD
TEST_EXIT_CODE=$?
set -e

# Record end time
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo ""
echo -e "${BOLD}${GREEN}"
echo "================================================================================"
echo "📊 Test Results Summary"
echo "================================================================================"
echo -e "${NC}"

# Show results based on exit code
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed${NC}"
else
    echo -e "${YELLOW}⚠️  Some tests failed (exit code: $TEST_EXIT_CODE)${NC}"
fi

echo ""
echo "Duration: ${MINUTES}m ${SECONDS}s"

# =============================================================================
# Step 5: Show Results Location
# =============================================================================
echo ""
echo -e "${BOLD}${BLUE}Step 5: Test Results Location${NC}"
echo "--------------------------------------------------------------------------------"

RESULTS_DIR="$PROJECT_ROOT/tests/data/quality_results"

if [ -d "$RESULTS_DIR" ]; then
    echo "Results saved to: $RESULTS_DIR"
    echo ""

    # List result files
    if [ -f "$RESULTS_DIR/indexing_metrics.json" ]; then
        echo -e "  ${GREEN}✓${NC} indexing_metrics.json"

        # Show key metrics
        if command -v jq &> /dev/null; then
            echo "    Summary:"
            jq -r '
                "    • Duration: \(.summary.duration)s",
                "    • Peak CPU: \(.summary.peak_cpu_percent)%",
                "    • Peak Memory: \(.summary.peak_memory_mb)MB"
            ' "$RESULTS_DIR/indexing_metrics.json" 2>/dev/null || true
        fi
    fi

    echo ""

    if [ -f "$RESULTS_DIR/search_quality_report.json" ]; then
        echo -e "  ${GREEN}✓${NC} search_quality_report.json"

        # Show aggregate metrics
        if command -v jq &> /dev/null; then
            echo "    Aggregate Metrics:"
            jq -r '
                if .aggregate_metrics then
                    "    • Avg Precision@10: \(.aggregate_metrics.avg_precision_at_10)",
                    "    • Avg Recall@20: \(.aggregate_metrics.avg_recall_at_20)",
                    "    • Avg MRR: \(.aggregate_metrics.avg_mrr)"
                else
                    "    (No aggregate metrics found)"
                end
            ' "$RESULTS_DIR/search_quality_report.json" 2>/dev/null || true
        fi
    fi
else
    echo -e "${YELLOW}⚠️  Results directory not found${NC}"
fi

echo ""
echo -e "${BOLD}${GREEN}"
echo "================================================================================"
echo "✨ Quality Test Workflow Complete"
echo "================================================================================"
echo -e "${NC}"

exit $TEST_EXIT_CODE
