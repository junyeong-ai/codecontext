# CodeContext - Intelligent Code Search Engine

<div align="center">

![Python](https://img.shields.io/badge/python-3.13-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Version](https://img.shields.io/badge/version-0.5.0-orange.svg)
![CI](https://github.com/junyeong-ai/codecontext/actions/workflows/ci.yml/badge.svg)
[![Coverage](https://codecov.io/gh/junyeong-ai/codecontext/graph/badge.svg)](https://codecov.io/gh/junyeong-ai/codecontext)
![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)

**English** | [한국어](README.md)

</div>

> **Next-generation code search powered by AST parsing, vector embeddings, and hybrid search**

CodeContext transforms your codebase into a searchable knowledge graph. Using Tree-sitter AST parsing and vector embeddings, it enables natural language code search with understanding of code structure, relationships, and context.

---

## Why CodeContext?

**Traditional grep/regex:** Match text patterns
**CodeContext:** Understand code semantics

| Feature | Description |
|---------|-------------|
| 🔍 **Hybrid Search** | BM25 keyword matching + Vector semantic search |
| 🎯 **Accurate Ranking** | 8-stage pipeline (Translation → Expansion → BM25 → Vector → Fusion → GraphRAG → MMR → Diversity) |
| 🧠 **Semantic Understanding** | Natural language queries like "authentication flow" |
| 🌍 **Multilingual** | 200 languages auto-translation (Korean → English search supported) |
| 🔗 **Bidirectional Relationships** | 26 relationship types for complete code structure tracking |
| 📚 **Document-Code Linking** | Automatic markdown documentation ↔ code connection |
| ⚡ **Fast** | Git-based incremental indexing |
| 🌐 **Multi-Language** | Python, Java, Kotlin, TypeScript, JS support |
| 🤖 **AI-Optimized** | JSON output (relationships + metadata included) |

---

## Quick Start

### Install

```bash
# Requires Python 3.13, ChromaDB
pip install -e .
chroma run --host localhost --port 8000
```

### Index

```bash
codecontext index                    # First-time full index
codecontext index --incremental      # Incremental updates
```

### Search

```bash
codecontext search "driver activation logic"
codecontext search "auth flow" --language python --format json
codecontext status --verbose
```

---

## Core Features

### 🎯 Hybrid Search System

**8-stage pipeline:** Natural language query → Translation (200 languages) → Query Expansion → BM25 Search (5x over-retrieval) → Vector Search (5x) → Adaptive Fusion (40% keyword + 60% semantic) → Graph Expansion (1-hop PPR) → MMR Reranking (75% relevance + 25% diversity) → File Diversity (max 2 chunks/file) → Final Results

**3 Key Settings:**
- `bm25_weight: 0.4` - Keyword/semantic balance
- `mmr_lambda: 0.75` - Relevance/diversity balance
- `max_chunks_per_file: 2` - Max chunks per file

### 🔗 Bidirectional Relationship Graph

**26 relationship types (13 bidirectional pairs):**

**Code-to-Code (16 types - 8 pairs):**
CALLS ↔ CALLED_BY, REFERENCES ↔ REFERENCED_BY, EXTENDS ↔ EXTENDED_BY, IMPLEMENTS ↔ IMPLEMENTED_BY, CONTAINS ↔ CONTAINED_BY, IMPORTS ↔ IMPORTED_BY, DEPENDS_ON ↔ DEPENDED_BY, ANNOTATES ↔ ANNOTATED_BY

**Document-to-Code (10 types - 5 pairs):**
DOCUMENTS ↔ DOCUMENTED_BY, MENTIONS ↔ MENTIONED_IN, IMPLEMENTS_SPEC ↔ IMPLEMENTED_IN

**Automatic Generation:** All relationships extracted and bidirectional pairs created during indexing

### 📚 Automatic Document-Code Linking

Automatically extracts code references from Markdown documents:

**Supported Patterns:** Backtick references (\`ClassName.method\`), File paths (path/to/file.py), Class/function names

**Matching Confidence:** Exact name 1.0, File path 0.9, Class.method 0.95, Partial match 0.7

### 🌐 Multi-Language Support

**Code Languages:** Python, Kotlin, Java, JavaScript, TypeScript (Tree-sitter AST parsing)
**Configuration Files:** YAML, JSON, Properties
**Documentation:** Markdown (automatic code reference extraction)
**Language-Specific Optimizers:** python_optimizer.py, java_optimizer.py, kotlin_optimizer.py, typescript_optimizer.py

### 📊 AI-Optimized JSON Output

**Search result information:**
- Code location and snippets
- AST metadata (complexity, line count)
- Bidirectional relationships (callers, callees, references, referenced_by, etc.)
- Document-code links (documents, documented_by)
- Similar code suggestions, impact analysis

---

## Use Cases

**CodeContext is useful for:**
- Finding specific feature implementations in large codebases
- Natural language code search ("auth logic", "database connection")
- Tracking function/class relationships (calls, references, inheritance)
- Multilingual team environments (search in Korean, find English code)
- Providing code context to AI agents (JSON output)

**Comparison with alternatives:**
- **grep/ag/rg:** Text pattern matching only, CodeContext understands semantics
- **GitHub Code Search:** Web-based, CodeContext is local + relationship graph
- **Language Servers (LSP):** Single-file analysis in IDE, CodeContext searches entire codebase

**Known limitations:**
- Python 3.13 required (older versions not supported)
- ChromaDB server must run separately
- Initial indexing time: 10,000 files in 8-15 minutes (GPU recommended)
- Memory usage: 4-6GB for 50,000 file codebases

---

## Installation

### Prerequisites

- Python 3.13
- ChromaDB server (localhost:8000)
- Git repository (optional, for incremental indexing)
- 2GB+ free memory

### Quick Setup (10 steps)

```bash
# 1. Install Python 3.13 (asdf recommended)
asdf plugin add python
asdf install python 3.13.2
cd codecontext
echo "python 3.13.2" > .tool-versions

# 2. Create virtual environment
~/.asdf/installs/python/3.13.2/bin/python3.13 -m venv venv
source venv/bin/activate

# 3. Install CodeContext
pip install -e .

# 4. Start ChromaDB
./scripts/chroma-cli.sh start

# 5. Verify installation
codecontext version
```

See [Installation Guide](docs/INSTALLATION.md) for details.

---

## Usage

### Indexing Commands

```bash
codecontext index                    # Index current directory
codecontext index /path/to/project   # Index specific directory
codecontext index --incremental      # Incremental update
codecontext index --force            # Force full re-index
```

### Search Commands

```bash
codecontext search "driver activation logic"
codecontext search "authentication flow" --language python
codecontext search "user registration" --format json  # For AI agents
codecontext search "API handler" --limit 5
```

### Status Commands

```bash
codecontext status
codecontext status --verbose
```

---

## Configuration

### Hierarchical Configuration System

1. Environment variables (`CODECONTEXT_*`)
2. Project config (`.codecontext.yaml`)
3. User config (`~/.codecontext/config.yaml`)
4. Default values (built-in)

### Key Configuration Example

`.codecontext.yaml`:

```yaml
# Embedding Configuration
embeddings:
  provider: huggingface
  huggingface:
    model_name: "jinaai/jina-code-embeddings-0.5b"
    device: auto
    batch_size: null      # null = auto (cpu:16, mps:64, cuda:128)
    max_length: 32768

# Search Configuration
search:
  bm25_weight: 0.4        # 40% keyword + 60% semantic
  mmr_lambda: 0.75        # 75% relevance + 25% diversity
  max_chunks_per_file: 2
```

See [.codecontext.yaml.example](.codecontext.yaml.example) for complete configuration.

---

## Search Result Example

### Natural Language Query: "user authentication logic"

```json
{
  "results": [
    {
      "file": "src/auth/authenticator.py",
      "name": "authenticate_user",
      "type": "function",
      "score": 0.92,
      "snippet": "def authenticate_user(username, password):\n    # Generate JWT token...",
      "relationships": {
        "called_by": ["login_handler", "api_middleware"],
        "calls": ["validate_credentials", "generate_jwt"]
      }
    }
  ]
}
```

---

## Documentation

### For Users
- [README.en.md](README.en.md) - This file (English)
- [README.md](README.md) - 한글 버전

### For Developers
- [CLAUDE.md](CLAUDE.md) - AI agent development reference (tech stack, architecture, development guide)

### Configuration
- [.codecontext.yaml.example](.codecontext.yaml.example) - Complete configuration example

---

## Troubleshooting

### ChromaDB Connection Error

```bash
./scripts/chroma-cli.sh start
./scripts/chroma-cli.sh status
```

### Python Version Error

```bash
python --version  # Must be 3.13.x
```

### Memory Issues

```yaml
indexing:
  batch_size: 50
  parallel_workers: 2
```

---

## Support

- **GitHub:** [https://github.com/junyeong-ai/codecontext](https://github.com/junyeong-ai/codecontext)
- **Issues:** [GitHub Issues](https://github.com/junyeong-ai/codecontext/issues)
- **Discussions:** [GitHub Discussions](https://github.com/junyeong-ai/codecontext/discussions)

---

## License

MIT License - see [LICENSE](LICENSE) for details

---

**Built with** 🌳 Tree-sitter • 🧠 Jina Code Embeddings • 🗄️ ChromaDB • 🐍 Python 3.13
