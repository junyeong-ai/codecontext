# Choosing an Embedding Model

CodeContext supports any HuggingFace embedding model compatible with the transformers library. This guide helps you choose the right model for your needs.

---

## Quick Comparison

| Model | Params | Dim | CoIR | License | Memory | Best For |
|-------|--------|-----|------|---------|--------|----------|
| **jina-code-0.5b** 🥇 | 494M | 896 | **78.41** | CC-BY-NC-4.0 | ~1.9GB | Maximum search quality (non-commercial) |
| **jina-code-0.5b** | 600M | 1024 | N/A | Apache 2.0 | ~2.3GB | Multilingual, general-purpose |
| **Qodo-1.5B** | 1.5B | 1536 | 68.53 | OpenRAIL++-M | ~3GB | Commercial projects |
| **jina-v2-base-code** | 161M | ? | N/A | Apache 2.0 | ~800MB | Resource-constrained |
| **jina-code-1.5B** | 1.5B | 1536 | **79.04** | CC-BY-NC-4.0 | ~3GB | Maximum quality (non-commercial) |

---

## Decision Tree

```
Start here
│
├─ Commercial use required?
│  ├─ Yes → Qodo-Embed-1.5B (only commercial option)
│  └─ No → Continue
│
├─ Resource constraints?
│  ├─ <8GB RAM → jina-v2-base-code (161M)
│  ├─ <12GB RAM → jina-code-0.5b (494M) ✓ Recommended
│  └─ ≥16GB RAM → Continue
│
├─ Priority?
│  ├─ Maximum quality → jina-code-1.5B (CoIR 79.04)
│  ├─ Balanced → jina-code-0.5b (CoIR 78.41) ✓ Recommended
│  └─ Multilingual → jina-code-0.5b
│
└─ Speed critical?
   ├─ Yes → jina-v2-base-code or jina-code-0.5b
   └─ No → Any model based on quality needs
```

---

## Detailed Model Profiles

### 🥇 jinaai/jina-code-embeddings-0.5b (Recommended)

**Best balance of quality and efficiency**

```yaml
embeddings:
  huggingface:
    model_name: "jinaai/jina-code-embeddings-0.5b"
    batch_size: 64
```

**Specs:**
- **Performance:** CoIR 78.41 (SOTA for <1B models)
- **Size:** 494M parameters, 896-dim embeddings
- **Memory:** ~1.9GB (FP16)
- **Speed:** Fast inference (smaller than competitors)
- **Languages:** 15+ (Python, Java, TS, JS, Go, C++, C#, PHP, Ruby, SQL, etc.)
- **Tasks:** nl2code, code2code, qa, code2nl, completion

**Pros:**
✅ Excellent search quality (beats 1B+ models)
✅ Efficient memory usage
✅ Fast inference
✅ Code-specialized training

**Cons:**
❌ CC-BY-NC-4.0 license (non-commercial only)

**Best for:**
- Non-commercial projects prioritizing quality
- Medium-spec machines (8-12GB RAM)
- Code-focused search

---

### ⚖️ jinaai/jina-code-embeddings-0.5b

**General-purpose with multilingual support**

```yaml
embeddings:
  huggingface:
    model_name: "jinaai/jina-code-embeddings-0.5b"
    batch_size: 64
```

**Specs:**
- **Performance:** N/A (not benchmarked on CoIR)
- **Size:** 600M parameters, 1024-dim embeddings
- **Memory:** ~2.3GB (FP16)
- **Languages:** 100+ (multilingual focus)
- **Context:** 32k tokens

**Pros:**
✅ Apache 2.0 license (permissive)
✅ Multilingual (100+ languages)
✅ Larger embedding dimension (1024)
✅ General-purpose versatility

**Cons:**
❌ Not code-specialized
❌ Unknown CoIR performance

**Best for:**
- Multilingual codebases
- Mixed code + documentation projects
- License-sensitive environments (Apache 2.0)

---

### 🏢 Qodo/Qodo-Embed-1-1.5B

**Only commercial-friendly code model**

```yaml
embeddings:
  huggingface:
    model_name: "Qodo/Qodo-Embed-1-1.5B"
    batch_size: 32  # Larger model requires smaller batch
```

**Specs:**
- **Performance:** CoIR 68.53
- **Size:** 1.5B parameters, 1536-dim embeddings
- **Memory:** ~3GB (FP16)
- **Languages:** 9 (Python, Java, TS, JS, Go, C++, C#, PHP, Ruby)
- **License:** OpenRAIL++-M (commercial allowed)

**Pros:**
✅ OpenRAIL++-M license (commercial use)
✅ Code-specialized
✅ Qwen2-1.5B based (proven architecture)

**Cons:**
❌ Lower CoIR score (68.53 vs 78.41)
❌ 3x larger than jina-code-0.5b
❌ Higher memory requirements
❌ Slower inference

**Best for:**
- Commercial/enterprise projects
- License compliance critical
- Sufficient resources (≥16GB RAM)

---

### 🪶 jinaai/jina-embeddings-v2-base-code

**Lightweight for resource-constrained environments**

```yaml
embeddings:
  huggingface:
    model_name: "jinaai/jina-embeddings-v2-base-code"
    batch_size: 128  # Small model can use large batches
```

**Specs:**
- **Performance:** Unknown CoIR (older model)
- **Size:** 161M parameters
- **Memory:** ~800MB (FP16)
- **Languages:** 30+ programming languages
- **License:** Apache 2.0

**Pros:**
✅ Very small (161M)
✅ Low memory footprint
✅ Fast inference
✅ Apache 2.0 license

**Cons:**
❌ Older architecture (v2, 2024.02)
❌ Unknown CoIR score
❌ May have lower quality than newer models

**Best for:**
- <8GB RAM systems
- CPU-only environments
- Speed-critical applications
- Prototyping/testing

---

### 🚀 jinaai/jina-code-embeddings-1.5B

**Maximum quality (non-commercial)**

```yaml
embeddings:
  huggingface:
    model_name: "jinaai/jina-code-embeddings-1.5b"
    batch_size: 32
```

**Specs:**
- **Performance:** CoIR 79.04 (SOTA)
- **Size:** 1.5B parameters, 1536-dim embeddings
- **Memory:** ~3GB (FP16)
- **Languages:** 15+ programming languages

**Pros:**
✅ Highest CoIR score (79.04)
✅ Maximum search quality
✅ Code-specialized

**Cons:**
❌ CC-BY-NC-4.0 (non-commercial only)
❌ Large memory requirements
❌ Slower inference than 0.5B

**Best for:**
- Research/academic projects
- Maximum quality priority
- Sufficient resources (≥16GB RAM)

---

## Performance Comparison

### Search Quality (CoIR Benchmark)

```
jina-code-1.5B:    79.04 ████████████████████ (SOTA)
jina-code-0.5B:    78.41 ███████████████████▌ (Recommended)
Qodo-1.5B:         68.53 █████████████████
jina-v2-base-code: N/A   (older, not benchmarked)
jina-code-0.5b:        N/A   (general-purpose, not benchmarked)
```

### Indexing Speed (10k files, M2 Mac, GPU)

```
jina-v2-base-code: 6-8 min   ████████
jina-code-0.5B:    8-10 min  ██████████
jina-code-0.5b:        10-12 min ████████████
Qodo-1.5B:         12-15 min ███████████████
jina-code-1.5B:    12-15 min ███████████████
```

### Memory Usage (FP16)

```
jina-v2-base-code: ~0.8GB ████
jina-code-0.5B:    ~1.9GB █████████▌
jina-code-0.5b:        ~2.3GB ███████████▌
Qodo-1.5B:         ~3.0GB ███████████████
jina-code-1.5B:    ~3.0GB ███████████████
```

---

## Switching Models

### Simple Switch

1. Edit `.codecontext.yaml`:
   ```yaml
   embeddings:
     huggingface:
       model_name: "your-new-model"
       batch_size: [adjust-based-on-model-size]
   ```

2. Re-index:
   ```bash
   codecontext index
   ```

**Important:** Different models have different embedding dimensions. Re-indexing is required when switching models.

### Batch Size Guidelines

| Model Size | Recommended batch_size |
|-----------|----------------------|
| <300M     | 96-128               |
| 300M-800M | 48-64                |
| 800M-2B   | 24-32                |

Adjust based on available GPU memory.

---

## License Considerations

### Commercial Use

**Allowed:**
- jina-code-0.5b (Apache 2.0)
- Qodo-Embed-1.5B (OpenRAIL++-M)
- jina-v2-base-code (Apache 2.0)

**Not Allowed:**
- jina-code-0.5b (CC-BY-NC-4.0)
- jina-code-1.5b (CC-BY-NC-4.0)

### Non-commercial Use

All models are allowed for:
- Personal projects
- Research
- Academic use
- Open-source projects (depends on license compatibility)

---

## Recommendations by Use Case

### Maximum Search Quality (Non-commercial)
→ **jina-code-0.5b** (best balance) or **jina-code-1.5b** (absolute best)

### Commercial Projects
→ **Qodo-Embed-1.5B** (only option)

### Resource-Constrained (<8GB RAM)
→ **jina-v2-base-code** (161M)

### Multilingual Codebases
→ **jina-code-0.5b** (100+ languages)

### Speed-Critical Applications
→ **jina-v2-base-code** or **jina-code-0.5b**

### General-Purpose (Code + Docs)
→ **jina-code-0.5b** (balanced)

---

## Custom Models

CodeContext supports any HuggingFace embedding model. To use a custom model:

1. Ensure it's compatible with `transformers` library
2. Set `model_name` in `.codecontext.yaml`:
   ```yaml
   embeddings:
     huggingface:
       model_name: "your-org/your-model"
   ```
3. Adjust `batch_size` based on model size
4. Run indexing

**Note:** Embedding dimension is auto-detected from the model.

---

## Further Reading

- [CoIR Benchmark](https://github.com/CoIR-team/coir)
- [HuggingFace Model Hub](https://huggingface.co/models?pipeline_tag=feature-extraction)
- [CodeContext Architecture](../architecture.md)
