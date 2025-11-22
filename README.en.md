# CodeContext - AI-Powered Code Search Engine

<div align="center">

[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.5.0-orange.svg)](https://github.com/junyeong-ai/codecontext/releases)
[![Tests](https://github.com/junyeong-ai/codecontext/actions/workflows/test.yml/badge.svg)](https://github.com/junyeong-ai/codecontext/actions/workflows/test.yml)
[![Lint](https://github.com/junyeong-ai/codecontext/actions/workflows/lint.yml/badge.svg)](https://github.com/junyeong-ai/codecontext/actions/workflows/lint.yml)
[![codecov](https://codecov.io/gh/junyeong-ai/codecontext/graph/badge.svg?token=YOUR_TOKEN)](https://codecov.io/gh/junyeong-ai/codecontext)

🌐 **English** | [한국어](README.md)

</div>

> **Hybrid Search (75% Semantic + 25% Keyword) + Tree-sitter AST Parsing + Vector Embeddings**

Get instant answers to questions like **"Where is this feature?"** and **"What will this change affect?"** in large codebases.

---

## Quick Start (3 Steps)

### 1. Install

```bash
# Start Qdrant server
docker compose -f docker-compose.qdrant.yml up -d

# Install CodeContext
./scripts/install.sh
```

### 2. Index

```bash
cd your-project
codecontext index
```

### 3. Search

```bash
codecontext search "user authentication logic"
```

**Results**:
```
1. AuthService.authenticate (score: 0.94)
   Type: method | Language: python | Lines: 45-89
   File: src/services/auth_service.py

2. login_required decorator (score: 0.87)
   Type: function | Language: python | Lines: 12-23
   File: src/middleware/auth.py
```

---

## Core Features

### 🎯 Architecture-First Search

- **Class Priority**: Implementation (Class) ranks higher than Interface for better architecture understanding
- **LOC-Based Complexity**: Large components rank higher than small helpers
- **Graph Expansion**: Auto-expand related symbols (call relationships, inheritance, etc.)

### ⚡ Hybrid Search

- **70% Semantic Matching**: Instruction-based embeddings (Jina Code Embeddings)
- **30% Keyword Matching**: BM25F sparse vector (camelCase/snake_case splitting)
- **RRF Fusion**: Reciprocal Rank Fusion combines results

### 🧬 LoRA Fine-Tuning Support

- **Domain-Specific Embeddings**: Optimize for specific code domains with LoRA adapters
- **Zero-Config Integration**: Just set the adapter path and it works automatically
- **Graceful Degradation**: Works with base model if PEFT library unavailable

### 🌐 Multi-Language Support

Python, Kotlin, Java, JavaScript, TypeScript, Markdown

### 🔍 Relationship-Based Search

12 relationship types (6 bidirectional pairs):
- CALLS/CALLED_BY, EXTENDS/EXTENDED_BY, IMPLEMENTS/IMPLEMENTED_BY
- REFERENCES/REFERENCED_BY, CONTAINS/CONTAINED_BY, IMPORTS/IMPORTED_BY

---

## Why CodeContext?

**High Accuracy**: Keyword noise reduction + semantic understanding + relationship-based expansion minimize false positives

**Large-Scale Scalability**: Verified on 6000+ file projects, incremental indexing 10-100x faster updates

**Full Customization**: Type/field weights, search algorithms, and LoRA fine-tuning tailored to your project

**Performance**: Search <500ms | Indexing ~1000 files/min | Memory <2GB

---

## Requirements

- Python 3.13+
- Docker (for Qdrant)
- UV (auto-installed)

---

## Configuration

Create `.codecontext.toml` in project root (optional, works with defaults):

```toml
[storage.qdrant]
url = "http://localhost:6333"  # Docker Qdrant

[embeddings.huggingface]
device = "cpu"  # or "cuda", "mps"
# lora_adapter_path = "~/.codecontext/adapters/my-domain"  # Optional
```

Advanced settings (type weights, field weights, search algorithms): [scripts/README.md](scripts/README.md)

---

## Usage Examples

### Natural Language Search
```bash
codecontext search "payment gateway integration"
```

### Code Search
```bash
codecontext search "class UserService"
```

### Expanded Information
```bash
codecontext search "order processing" --expand relationships
```

### LoRA Fine-Tuning Usage
```bash
# 1. Prepare LoRA adapter (adapter_config.json + adapter_model.safetensors)
# 2. Add path to config file
codecontext index  # Uses fine-tuned embeddings
codecontext search "domain-specific query"
```

For details, see [scripts/README.md](scripts/README.md#lora-fine-tuning-support).

---

## Architecture

**Module Structure**: CLI + Core + Pluggable Providers (Storage, Embeddings)

**Search Pipeline (5 Stages)**: Query Embedding → Hybrid Search (70%:30%) → Graph Expansion → Boosting+Weight → Diversity

Detailed design: [docs/architecture.md](docs/architecture.md) | [docs/hybrid-search.md](docs/hybrid-search.md)

---

## Development

```bash
./scripts/dev-install.sh  # Setup development environment
pytest                     # Run tests
```

Development guide: [CLAUDE.md](CLAUDE.md) (AI Agent) | [docs/](docs/) (Architecture)

---

## License

MIT License - See [LICENSE](LICENSE)

---

## Contributing

Contributions are always welcome! Please open an Issue or Pull Request.

---

**Made with ❤️ by CodeContext Team**
