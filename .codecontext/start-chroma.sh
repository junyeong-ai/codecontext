#!/usr/bin/env bash
# Auto-generated ChromaDB startup script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_PATH="$SCRIPT_DIR/chroma"
PORT=8000

echo "Starting local ChromaDB server..."
echo "Data path: $DATA_PATH"
echo "Port: $PORT"
echo ""
echo "Press Ctrl+C to stop"

chroma run --path "$DATA_PATH" --port $PORT
