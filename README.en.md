# CodeContext

<div align="center">

[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.5.0-orange.svg)](https://github.com/junyeong-ai/codecontext/releases)

🌐 **English** | [한국어](README.md)

</div>

> **"Where is this feature?" "What will this change affect?"** — Get instant answers in large codebases.

**Hybrid Search** (70% Semantic + 30% Keyword) | **AST Parsing** | **Relationship Graph**

---

## Getting Started

```bash
# 1. Start Qdrant
docker compose -f docker-compose.qdrant.yml up -d

# 2. Install
./scripts/install.sh

# 3. Index & Search
cd your-project
codecontext index
codecontext search "user authentication"
```

---

## Why CodeContext?

| Problem | CodeContext Solution |
|---------|---------------------|
| grep doesn't understand meaning | Semantic search + keyword matching |
| IDE search misses relationships | 12 code relationship types (calls, inheritance, references, etc.) |
| Getting lost in large codebases | Architecture-first search (implementation > interface) |

**Performance**: Search <500ms | Verified on 6000+ file projects | Incremental indexing

---

## Core Features

### Hybrid Search
```bash
codecontext search "payment processing"
```
- **70% Semantic**: "payment processing" → finds PaymentService, checkout, billing
- **30% Keyword**: Exact function/class name matching

### Relationship Exploration
```bash
codecontext search "authenticate" --expand relationships --format json
```
```json
{
  "callers": [{"name": "login", "type": "method", "file": "src/auth.py", "line": 42}],
  "callees": [{"name": "validate_token", "type": "function", "file": "src/token.py", "line": 15}]
}
```

### Supported Languages
Python, Java, Kotlin, TypeScript, JavaScript, Markdown

---

## Configuration

`.codecontext.toml` (optional):

```toml
[storage.qdrant]
url = "http://localhost:6333"

[embeddings.huggingface]
device = "cpu"  # cuda, mps
```

---

## Requirements

- Python 3.13+
- Docker (Qdrant)

---

## Links

- [Architecture](docs/architecture.md)
- [Development Guide](CLAUDE.md)
- [License](LICENSE) (MIT)

---

**Made with ❤️ by CodeContext Team**
