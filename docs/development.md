# CodeContext Development Guide

Guide for developing and testing CodeContext.

---

## Installation Methods

### 1. Development Mode (Recommended for Development)

Changes to source code are reflected immediately without reinstallation.

```bash
# Option A: Use uv run (no installation)
uv run codecontext search "query"
uv run codecontext index

# Option B: Editable install
./scripts/dev-install.sh

# Or manually:
uv pip install -e ./packages/codecontext-cli --system
```

**Pros:**
- ✅ Changes reflected immediately
- ✅ No reinstallation needed
- ✅ Fast development cycle

**Cons:**
- ⚠️ May have import issues with workspace dependencies

---

### 2. Tool Installation (Recommended for Testing)

Isolated installation like production, requires reinstallation after changes.

```bash
# Initial install
./scripts/install.sh

# Reinstall after changes
./scripts/reinstall.sh

# Or manually:
uv tool install --force --from ./packages/codecontext-cli codecontext-cli
```

**Pros:**
- ✅ Production-like environment
- ✅ Clean isolated installation
- ✅ Tests actual distribution

**Cons:**
- ⚠️ Requires reinstallation after every change

---

## Development Workflow

### Quick Testing (uv run)

```bash
# No installation needed
uv run codecontext index tests/fixtures/ecommerce_samples
uv run codecontext search "OrderService"
uv run codecontext search "payment" --format=json --expand=content
```

### Full Testing (tool install)

```bash
# After code changes
./scripts/reinstall.sh

# Test installed binary
codecontext index tests/fixtures/ecommerce_samples
codecontext search "OrderService"
```

---

## Testing Changes

### 1. Text Format Changes

**File:** `packages/codecontext-cli/src/codecontext/formatters/text_formatter.py`

```bash
# Test with uv run
uv run codecontext search "payment"

# Or reinstall and test
./scripts/reinstall.sh
codecontext search "payment"
```

### 2. Search Logic Changes

**File:** `packages/codecontext-cli/src/codecontext/search/retriever.py`

```bash
# Reindex with changes
uv run codecontext index tests/fixtures/ecommerce_samples --force

# Test search
uv run codecontext search "OrderService" --verbose
```

### 3. Config Changes

**File:** `packages/codecontext-cli/src/codecontext/config/schema.py`

```bash
# Test with new config
uv run codecontext config show --effective
```

---

## Debugging

### Enable Verbose Logging

```bash
# With uv run
uv run codecontext search "query" --verbose

# With installed tool
codecontext search "query" --verbose
```

### Check Installation

```bash
# Tool installation
which codecontext
# → ~/.local/bin/codecontext (symlink to ~/.local/share/uv/tools/...)

# Tool info
uv tool list | grep codecontext

# Check version
codecontext version
```

---

## Common Issues

### Changes Not Reflected

**Problem:** Modified source code but `codecontext` command shows old behavior.

**Cause:** `uv tool install` copies packages to `~/.local/share/uv/tools/` so source changes don't apply automatically.

**Solution:**
```bash
# Option 1: Reinstall tool (RECOMMENDED)
./scripts/reinstall.sh

# Option 2: Manual reinstall with cache clear
uv tool uninstall codecontext-cli
rm -rf ~/.cache/uv
find packages -type d -name "build" -o -name "__pycache__" | xargs rm -rf
uv tool install --python 3.13 --from ./packages/codecontext-cli codecontext-cli

# Option 3: Use editable install (development mode)
./scripts/dev-install.sh
```

**Note:** `uv run codecontext` runs the **installed tool**, not the source code. Always reinstall after changes.

### Import Errors

**Problem:** `ModuleNotFoundError` when using `uv run`.

**Solution:**
```bash
# Sync workspace dependencies
uv sync

# Or use tool installation
./scripts/install.sh
```

---

## Scripts Reference

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `scripts/install.sh` | Initial installation | First time setup |
| `scripts/reinstall.sh` | Quick reinstallation | After code changes (tool mode) |
| `scripts/dev-install.sh` | Editable installation | Development mode |
| `scripts/uninstall.sh` | Complete removal | Cleanup |

---

## Best Practices

1. **Development:**
   - Use `uv run codecontext` for quick testing
   - No installation overhead

2. **Testing:**
   - Use `./scripts/reinstall.sh` before testing installed binary
   - Test both text and JSON output formats

3. **Distribution:**
   - Use `./scripts/install.sh` for production-like testing
   - Test in clean environment

---

**Last Updated:** 2025-11-17
