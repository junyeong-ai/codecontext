# Multi-Project Support

CodeContext supports indexing and searching multiple projects independently with isolated Qdrant collections.

## Features

- **Auto-detection**: Project IDs automatically detected from Git remote URLs
- **Isolation**: Each project has separate Qdrant collections (no cross-contamination)
- **Management**: List, view status, and delete projects independently

## Usage

### Index a Project

```bash
# Auto-detect project from git remote
codecontext index /path/to/my-repo

# Explicitly specify project name
codecontext index /path/to/my-repo --project my-custom-name

# Incremental update for specific project
codecontext index /path/to/my-repo --project my-app --incremental
```

### Search a Project

```bash
# Search in auto-detected project (current directory)
codecontext search "authentication logic"

# Search specific project
codecontext search "auth flow" --project my-app

# Search with filters
codecontext search "database" --project backend --language python
```

### List All Projects

```bash
codecontext list-projects
```

Output:
```
Found 3 project(s):

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ my-app                                     ┃
┃ Path: /Users/user/workspace/my-app        ┃
┃ Last indexed: 2025-10-13 14:30:00         ┃
┃ Files: 250 | Objects: 1,500 | Docs: 45    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### View Project Status

```bash
# Status of current project
codecontext status

# Status of specific project
codecontext status --project my-app
```

### Delete a Project

```bash
# With confirmation prompt
codecontext delete-project my-app

# Skip confirmation
codecontext delete-project my-app --yes
```

## Project ID Detection

### Priority Order

1. **Explicit `--project` flag**: Highest priority
2. **Git remote URL**: Extracted from `git config --get remote.origin.url`
3. **Directory name**: Cleaned and normalized
4. **Path hash**: Fallback for temporary directories

### Examples

| Source | Project ID |
|--------|------------|
| https://github.com/user/my-repo.git | `my-repo` |
| git@github.com:user/awesome-app.git | `awesome-app` |
| /workspace/my-project/ | `my-project` |
| /tmp/tmpXYZ123/ | `project-a1b2c3d4e5f6g7h8` |

### Normalization Rules

- Lowercase conversion
- Special characters → hyphens
- Max 63 characters (DNS label limit)
- Leading/trailing hyphens removed

## Collection Structure

Each project gets a single Qdrant collection with dual vectors (dense + sparse):

```
codecontext_{project_id}
```

Example for project `my-app`:
```
codecontext_my-app
```

**Vector Configuration**:
- **Dense vector**: Code embeddings (auto-detected dimension, typically 768)
- **Sparse vector**: FastEmbed BM25 for keyword matching
- **Payload**: file_path, content, metadata, relationships, state

## Best Practices

### 1. Use Git Remote Names

Let CodeContext auto-detect project names from Git:
```bash
cd /workspace/my-app
codecontext index  # Detects as "my-app"
```

### 2. Consistent Naming

For non-Git projects, use explicit names:
```bash
codecontext index /data/legacy-code --project legacy-system
codecontext search "..." --project legacy-system
```

### 3. Workspace Organization

```bash
# Multiple projects in workspace
cd /workspace/frontend && codecontext index
cd /workspace/backend && codecontext index
cd /workspace/mobile && codecontext index

# List all
codecontext list-projects
```

### 4. CI/CD Integration

```yaml
# .github/workflows/index.yml
- name: Index codebase
  run: |
    codecontext index --project ${{ github.repository }}
```

## Troubleshooting

### Project Not Found

```bash
$ codecontext search "query" --project nonexistent
Error: No index found for project 'nonexistent'
```

**Solution**: Check available projects with `codecontext list-projects`

### Multiple Projects Same Name

If you have multiple projects with the same Git repository name:

```bash
# Use explicit project names
codecontext index /workspace/client/my-app --project my-app-client
codecontext index /workspace/server/my-app --project my-app-server
```

### Cross-Project Search

To search across multiple projects:

```bash
# Currently not supported - search one project at a time
codecontext search "auth" --project project-a
codecontext search "auth" --project project-b
```

## Advanced Topics

### Project Isolation Guarantees

- **Zero cross-contamination**: Search results never include other projects
- **Independent versioning**: Each project tracks its own index state
- **Concurrent indexing**: Multiple projects can be indexed simultaneously
- **Atomic operations**: Project deletion is all-or-nothing

### Performance Characteristics

| Operation | Performance |
|-----------|-------------|
| Auto-detection | <10ms (Git) / <1ms (directory) |
| Project switching | <100ms (collection lookup) |
| List projects | <500ms for 50+ projects |
| Delete project | ~50ms (single collection) |

### Storage Requirements

Per project overhead:
- **Metadata**: ~1KB per project (IndexState in payload)
- **Collections**: Single Qdrant collection with dual vectors
- **Indexes**: HNSW index for dense vector, inverted index for sparse vector

Estimated storage per 10K files:
- Code objects: ~500MB
- Embeddings: ~1.5GB (768-dim vectors)
- Relationships: ~50MB
- Documents: ~200MB

**Total**: ~2.25GB per 10,000-file project

## Migration Guide

### From Single Project to Multi-Project

If you have an existing single-project index:

1. **Check current collections**:
   ```bash
   # Via Qdrant API or embedded storage
   # Look for: codecontext_{project_id}
   ```

2. **Rename collections** (manual):
   ```python
   # Note: Qdrant supports collection aliasing
   # You can create an alias or re-index
   codecontext index --project old-project-name
   ```

3. **Delete old collections**:
   ```bash
   codecontext delete-project default
   ```

## API Reference

See `codecontext --help` for complete command reference:

```bash
codecontext index --help
codecontext search --help
codecontext status --help
codecontext list-projects --help
codecontext delete-project --help
```
