# CodeContext ChromaDB Storage Provider

Official ChromaDB storage provider for CodeContext.

## Installation

```bash
pip install codecontext-storage-chromadb
```

## Features

- ✅ Full ChromaDB API support via Python client
- ✅ Auto-registered via entry points
- ✅ HTTP-based client (no embedded mode)
- ✅ Collection management (code_objects, documents, relationships, state)
- ✅ Cosine similarity search
- ✅ Metadata filtering
- ✅ Relationship graph support

## Configuration

```yaml
# .codecontext.yaml
storage:
  provider: chromadb
  chromadb:
    host: localhost
    port: 8000
    collection_name: codecontext_index
```

## Requirements

- ChromaDB server running (start with `./scripts/chroma-cli.sh start`)
- Python 3.11+

## Architecture

Uses official `chromadb` Python client (HttpClient) for:
- ✅ Complete API feature support
- ✅ Stable, maintained by ChromaDB team
- ✅ Consistent with ChromaDB best practices

## Development

```bash
# Install
pip install -e packages/codecontext-storage-chromadb

# Test
pytest tests/integration/test_chromadb_provider.py
```

## Collections

The provider creates 4 collections per project:

1. **code_objects** - Code entities (classes, methods, functions)
2. **documents** - Documentation (markdown files, docstrings)
3. **relationships** - Code relationships (CONTAINS, INHERITS, CALLS)
4. **state** - Index metadata (last indexed time, file checksums)

## License

MIT
