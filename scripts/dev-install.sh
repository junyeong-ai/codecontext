#!/usr/bin/env bash
set -e

echo "🔧 Installing CodeContext in development mode..."
echo

# Check UV
if ! command -v uv &> /dev/null; then
    echo "❌ UV is not installed"
    echo "Please install UV first: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check Python 3.13
if ! uv python list | grep -q "3.13"; then
    echo "📦 Installing Python 3.13..."
    uv python install 3.13
fi

echo "🔄 Uninstalling existing tool installation (if any)..."
uv tool uninstall codecontext-cli 2>/dev/null || true

echo
echo "🧹 Cleaning Python caches..."
find packages/ -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find packages/ -type f -name "*.pyc" -delete 2>/dev/null || true
find packages/ -type f -name "*.pyo" -delete 2>/dev/null || true

echo
echo "📦 Installing in editable mode with uv tool..."
uv tool install --python 3.13 \
  --with ./packages/codecontext-core \
  --with ./packages/codecontext-storage-qdrant \
  --with ./packages/codecontext-embeddings-huggingface \
  --with peft \
  --editable ./packages/codecontext-cli

echo
echo "✅ Development installation complete!"
echo
echo "Changes to source code will now be reflected immediately."
echo
echo "Test with:"
echo "  codecontext version"
echo "  codecontext search \"test\""
echo
