#!/usr/bin/env bash
set -e

echo "🧹 Clean Reinstall - CodeContext"
echo "=================================="
echo ""
echo "This will:"
echo "  1. Remove all Python caches (__pycache__, *.pyc)"
echo "  2. Remove all build artifacts (build/, dist/, *.egg-info)"
echo "  3. Uninstall existing UV tool installation"
echo "  4. Reinstall with ALL local dependencies"
echo ""
read -p "Continue? [Y/n]: " choice
case "$choice" in
    n|N)
        echo "❌ Cancelled"
        exit 0
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1/4: Cleaning Python caches"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Remove __pycache__ directories
find packages/ -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo "✅ Removed __pycache__ directories"

# Remove .pyc files
find packages/ -type f -name "*.pyc" -delete 2>/dev/null || true
echo "✅ Removed .pyc files"

# Remove .pyo files
find packages/ -type f -name "*.pyo" -delete 2>/dev/null || true
echo "✅ Removed .pyo files"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2/4: Cleaning build artifacts"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Remove build directories
find packages/ -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
echo "✅ Removed build/ directories"

# Remove dist directories
find packages/ -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
echo "✅ Removed dist/ directories"

# Remove .egg-info directories
find packages/ -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
echo "✅ Removed *.egg-info directories"

# Remove .egg files
find packages/ -type f -name "*.egg" -delete 2>/dev/null || true
echo "✅ Removed *.egg files"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3/4: Uninstalling existing installation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

uv tool uninstall codecontext-cli 2>/dev/null || true
echo "✅ Removed UV tool installation"

# Also remove any stray executables
if [ -f "$HOME/.local/bin/codecontext" ]; then
    rm -f "$HOME/.local/bin/codecontext"
    echo "✅ Removed stray executable"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 4/4: Installing with local dependencies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Install with ALL local dependencies in EDITABLE mode
uv tool install --python 3.13 --force \
  --with ./packages/codecontext-core \
  --with ./packages/codecontext-storage-qdrant \
  --with ./packages/codecontext-embeddings-huggingface \
  --with peft \
  --editable ./packages/codecontext-cli

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Clean Reinstall Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Verify installation:"
echo "  codecontext version"
echo ""
echo "Test with:"
echo "  codecontext index tests/fixtures/ecommerce_samples --force"
echo ""
