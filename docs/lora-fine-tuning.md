# LoRA Fine-Tuning Guide

**Target:** AI agents implementing/debugging LoRA integration
**Token-Optimized:** Implementation details only

---

## Quick Reference

### Configuration

**File:** `packages/codecontext-embeddings-huggingface/src/codecontext_embeddings_huggingface/config.py:59-112`

```python
lora_adapter_path: str | None  # Optional, validated on config creation
```

**Validation rules:**
- Path must exist
- Must be directory (not file)
- Must contain `adapter_config.json`
- Tilde expansion supported (`~/.codecontext/adapters/my-domain`)

### Loading Logic

**File:** `provider.py:92-134`

```python
# Execution flow
1. Check PEFT_AVAILABLE (import guard: provider.py:13-20)
2. Validate adapter_path exists
3. Skip if already loaded (_adapter_loaded flag)
4. PeftModel.from_pretrained(model, adapter_path, is_trainable=False)
5. Set _adapter_loaded = True
6. Graceful degradation on failure (logs error, continues with base model)
```

### Dependencies

**File:** `packages/codecontext-embeddings-huggingface/pyproject.toml:38-40`

```toml
[project.optional-dependencies]
lora = ["peft>=0.8.0,<1.0.0"]
```

**Auto-installation:**
- `scripts/install.sh:407` - Production install with `--with peft`
- `scripts/dev-install.sh:35` - Development install with `--with peft`

---

## Directory Structure

### Required Files

```
adapter/
├── adapter_config.json         # PEFT config (required)
└── adapter_model.safetensors   # LoRA weights (required)
```

### Validation

**File:** `config.py:108-110`

```python
config_file = path / "adapter_config.json"
if not config_file.exists():
    raise ValueError(f"Invalid LoRA adapter: missing adapter_config.json in {path}")
```

**Why adapter_config.json:**
- PEFT library requirement
- Contains metadata: `peft_type`, `base_model_name_or_path`, `r`, `lora_alpha`, etc.
- Validates adapter compatibility with base model

---

## Usage

### 1. User Configuration

**Project config** (`.codecontext.toml`):
```toml
[embeddings.huggingface]
model_name = "jinaai/jina-code-embeddings-0.5b"
lora_adapter_path = "/path/to/adapter"  # Or ~/.codecontext/adapters/my-domain
```

**Global config** (`~/.codecontext/config.yaml`):
```yaml
embeddings:
  huggingface:
    lora_adapter_path: ~/.codecontext/adapters/default
```

### 2. Provider Initialization

**Flow:**
```python
HuggingFaceEmbeddingProvider.__init__(config)
  ↓
initialize()  # provider.py:51-94
  ↓
_load_adapter()  # provider.py:95-134 (if lora_adapter_path set)
```

**Logs:**
```
INFO - Loading LoRA adapter from: /path/to/adapter
INFO - LoRA adapter loaded successfully in 234.5ms
```

### 3. Embedding Generation

- Automatic: Uses fine-tuned model transparently
- No code changes required
- Same API: `embed_text(text, instruction_type)`

---

## Error Handling

### PEFT Unavailable

**Condition:** `peft` library not installed

**Behavior:**
```python
# provider.py:101-106
if not PEFT_AVAILABLE:
    logger.warning(
        f"PEFT library not installed, cannot load LoRA adapter: "
        f"{self.config.lora_adapter_path}. "
        f"Install with: pip install peft"
    )
    return  # Continues with base model
```

**User action:** `pip install peft` or use install script with `--with peft`

### Invalid Adapter Path

**Condition:** Path doesn't exist, not a directory, or missing `adapter_config.json`

**Behavior:**
```python
# config.py:93-112
raise ValueError(f"LoRA adapter path does not exist: {path}")
raise ValueError(f"LoRA adapter path must be a directory: {path}")
raise ValueError(f"Invalid LoRA adapter: missing adapter_config.json in {path}")
```

**Raised at:** Config creation time (early validation)

### Loading Failure

**Condition:** `PeftModel.from_pretrained()` fails (incompatible adapter, corrupted files, etc.)

**Behavior:**
```python
# provider.py:133-134
except Exception as e:
    logger.error(f"Failed to load LoRA adapter from {adapter_path}: {e}")
    raise  # Stops initialization
```

**User action:** Check adapter compatibility with base model, verify files integrity

---

## Testing

**File:** `tests/unit/embeddings/huggingface/test_lora_loading.py`

### Test Coverage

1. **Config Validation** (`TestLoRAConfigValidation`)
   - None path (LoRA disabled)
   - Non-existent path → ValueError
   - File instead of directory → ValueError
   - Directory without adapter_config.json → ValueError
   - Valid adapter directory → Accepted
   - Tilde expansion

2. **Provider Integration** (`TestLoRAProviderIntegration`)
   - PEFT unavailable → Warning logged, continues
   - PEFT available → Adapter loaded successfully
   - Loading failure → Error logged, exception raised
   - Idempotent loading (skip if already loaded)

### Running Tests

```bash
# Full test suite
pytest tests/unit/embeddings/huggingface/test_lora_loading.py

# Specific test class
pytest tests/unit/embeddings/huggingface/test_lora_loading.py::TestLoRAConfigValidation

# With coverage
pytest tests/unit/embeddings/huggingface/test_lora_loading.py --cov=codecontext_embeddings_huggingface
```

---

## Debugging Entry Points

| Issue | File:Line | Action |
|-------|-----------|--------|
| Config validation fails | config.py:93-112 | Check path exists, is directory, has adapter_config.json |
| PEFT import error | provider.py:13-20 | Verify `pip install peft` or `--with peft` flag |
| Adapter not loading | provider.py:92-134 | Check logs for warnings/errors, verify PEFT_AVAILABLE |
| Loading takes too long | provider.py:120-128 | Check adapter size, model compatibility |
| Graceful degradation | provider.py:101-107 | Verify warning logged, base model used |

---

## Implementation Notes

### Design Decisions

1. **Optional dependency:**
   - Why: LoRA is advanced feature, not needed for basic usage
   - How: `[project.optional-dependencies] lora = ["peft>=0.8.0"]`
   - Benefit: Reduces installation size/time for users not using LoRA

2. **Graceful degradation:**
   - Why: PEFT unavailable shouldn't break basic functionality
   - How: Import guard + warning log + continue with base model
   - Trade-off: Silent fallback might confuse users (addressed via clear warning)

3. **Early validation:**
   - Why: Fail fast at config creation, not during indexing
   - How: Pydantic field_validator checks at config instantiation
   - Benefit: Clear error messages, avoids wasted computation

4. **Lazy loading:**
   - Why: Adapter loaded during `initialize()`, not `__init__()`
   - How: `_load_adapter()` called after base model loaded
   - Benefit: Matches model initialization flow, cleaner separation

5. **Idempotent loading:**
   - Why: Prevent re-loading on multiple `initialize()` calls
   - How: `_adapter_loaded` flag + `_current_adapter_path` tracking
   - Benefit: Performance, avoid redundant PEFT operations

### Performance Characteristics

- **Adapter size:** Typically 1-50MB (vs 1.7GB base model)
- **Loading time:** 50-500ms (depending on adapter size)
- **Memory overhead:** Minimal (<100MB for typical LoRA ranks)
- **Inference speed:** Same as base model (LoRA merged during forward pass)

### Thread Safety

- **Loading:** Not thread-safe (happens during initialization, single-threaded)
- **Inference:** Thread-safe (model.eval() mode, no training)
- **Flag checks:** Safe (`_adapter_loaded` read-only after initialization)

---

## Common Patterns

### Fine-Tuning Your Own Adapter

**Prerequisites:**
- Training dataset (domain-specific code + descriptions)
- PEFT library: `pip install peft`
- Base model: `jinaai/jina-code-embeddings-0.5b`

**Example training script:**
```python
from peft import LoraConfig, get_peft_model
from transformers import AutoModel

# Load base model
base_model = AutoModel.from_pretrained("jinaai/jina-code-embeddings-0.5b")

# Configure LoRA
lora_config = LoraConfig(
    r=8,                      # Rank (lower = smaller adapter)
    lora_alpha=16,            # Scaling factor
    target_modules=["q", "v"], # Which layers to adapt
    lora_dropout=0.1,
    bias="none",
)

# Create PEFT model
model = get_peft_model(base_model, lora_config)

# Train (your training loop)
# ...

# Save adapter
model.save_pretrained("./my-adapter")
# Creates: adapter_config.json + adapter_model.safetensors
```

**Using trained adapter:**
```toml
[embeddings.huggingface]
lora_adapter_path = "./my-adapter"
```

### Switching Adapters

**Scenario:** Different adapters for different projects

**Approach 1: Project-specific config**
```toml
# project-a/.codecontext.toml
[embeddings.huggingface]
lora_adapter_path = "~/.codecontext/adapters/java-spring"

# project-b/.codecontext.toml
[embeddings.huggingface]
lora_adapter_path = "~/.codecontext/adapters/python-django"
```

**Approach 2: Environment variable**
```bash
export CODECONTEXT_EMBEDDINGS__HUGGINGFACE__LORA_ADAPTER_PATH=~/.codecontext/adapters/java-spring
codecontext index
```

### Verifying Adapter Loading

**Check logs:**
```bash
codecontext index 2>&1 | grep -i "lora\|peft"
```

**Expected output:**
```
INFO - Loading LoRA adapter from: /home/user/.codecontext/adapters/my-domain
INFO - LoRA adapter loaded successfully in 123.4ms
```

**If PEFT unavailable:**
```
WARNING - PEFT library not installed, cannot load LoRA adapter: /path/to/adapter. Install with: pip install peft
```

---

## FAQ

**Q: Can I use multiple LoRA adapters simultaneously?**
A: No. Current implementation supports one adapter per provider instance. For multiple adapters, use separate projects with different configs.

**Q: What LoRA ranks are recommended?**
A: r=8 or r=16 for most use cases. Higher ranks (32, 64) for complex domain adaptations.

**Q: Does LoRA slow down search?**
A: No. LoRA adds minimal inference overhead (<5%). Embedding generation time dominated by model forward pass, not adapter.

**Q: Can I fine-tune OpenAI embeddings?**
A: No. LoRA only works with local HuggingFace models. OpenAI embeddings are API-based.

**Q: How do I update an adapter?**
A: Replace files in adapter directory, re-run `codecontext index`. Provider checks `_current_adapter_path` for changes.

---

**Last Updated:** 2025-01-22
**Version:** 0.5.0
