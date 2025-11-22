# codecontext-cli

Command-line interface for CodeContext - Intelligent Code Search Engine.

## Installation

```bash
pip install codecontext-cli codecontext-embeddings-huggingface codecontext-storage-qdrant
```

## Quick Start

```bash
# Index a codebase (Qdrant embedded mode - no server required)
codecontext index /path/to/repo

# Search with natural language
codecontext search "authentication flow"

# Check status
codecontext status
```

## Commands

### Index

```bash
# Full index
codecontext index

# Incremental index
codecontext index --incremental

# Specific project
codecontext index --project my-app
```

### Search

```bash
# Basic search
codecontext search "query"

# With filters
codecontext search "auth" --language python --format json

# Specific project
codecontext search "query" --project my-app
```

### Projects

```bash
# List all projects
codecontext list-projects

# Delete project
codecontext delete-project my-app
```

## Python Version Support

- Python 3.13

## License

MIT
