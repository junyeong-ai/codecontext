# CodeContext Search Examples

Practical query patterns for AI agents using CodeContext CLI.

---

## 1. Architecture Exploration

### Use Case
Understanding system architecture, component locations, and design patterns.

### Example Queries

**Find authentication implementation:**
```bash
codecontext search "authentication flow" --format json --limit 15
```
**What to parse:**
- `results[].metadata.name`: Component names (AuthService, authenticate, login)
- `results[].relationships.callers.total_count`: How many components use auth
- `results[].impact.total_callers`: Total transitive dependencies
- `results[].structure.complexity`: Implementation complexity

**Locate error handling:**
```bash
codecontext search "error handling exception logging" --format json
```
**What to parse:**
- `results[].metadata.type`: FUNCTION, CLASS, METHOD
- `results[].structure.calls[]`: Error handling functions called
- `results[].relationships.contains.items[]`: Nested error handlers

**Identify design patterns:**
```bash
codecontext search "singleton factory builder pattern" --format json --limit 20
```
**What to parse:**
- `results[].metadata.signature`: Pattern implementation details
- `results[].relationships.implements`: Pattern interfaces
- `results[].relationships.extended_by.total_count`: Usage count

---

## 2. API Discovery

### Use Case
Finding REST endpoints, API clients, service interfaces.

### Example Queries

**Find REST endpoints:**
```bash
codecontext search "REST API endpoint user management" --format json --language python
```
**What to parse:**
- `results[].metadata.name`: Endpoint function names (create_user, update_user)
- `results[].metadata.signature`: HTTP method, parameters
- `results[].structure.calls[]`: Database operations, validations
- `results[].relationships.callers[]`: Controllers calling endpoints

**Locate API clients:**
```bash
codecontext search "API client HTTP request" --format json
```
**What to parse:**
- `results[].location.file`: Client implementation files
- `results[].structure.references[]`: API endpoint URLs, models
- `results[].relationships.callees[]`: HTTP libraries used

**Find GraphQL resolvers:**
```bash
codecontext search "GraphQL resolver mutation query" --format json --language typescript
```
**What to parse:**
- `results[].metadata.type`: FUNCTION (resolver functions)
- `results[].structure.calls[]`: Service layer calls
- `results[].relationships.references[]`: GraphQL schema types

---

## 3. Dependency Analysis

### Use Case
Understanding code dependencies, impact analysis, refactoring safety.

### Example Queries

**Find all callers of a service:**
```bash
codecontext search "PaymentService" --format json --limit 30
```
**What to parse:**
- `results[].relationships.callers.total_count`: **Total dependency count**
- `results[].relationships.callers.items[]`: Sample callers (limited display)
- `results[].impact.total_callers`: **Transitive dependency count**
- `results[].metadata.parent`: Parent component

**Analyze component impact:**
```bash
codecontext search "UserRepository" --format json --expand
```
**What to parse:**
- `results[].impact.total_callers`: How many components depend on this
- `results[].impact.total_callees`: How many components this depends on
- `results[].scoring.graph_score`: Graph relationship strength
- `results[].relationships.referenced_by.total_count`: Reference count

**Find database dependencies:**
```bash
codecontext search "database connection query" --format json --file-pattern "src/**/*.py"
```
**What to parse:**
- `results[].structure.calls[]`: Database operations (query, execute, commit)
- `results[].relationships.imports[]`: Database libraries
- `results[].relationships.callees.items[]`: Database access patterns

---

## 4. Implementation Patterns

### Use Case
Finding specific implementations, algorithms, data structures.

### Example Queries

**Find caching implementation:**
```bash
codecontext search "cache Redis memcached LRU" --format json
```
**What to parse:**
- `results[].metadata.name`: Cache function names
- `results[].structure.complexity.cyclomatic`: Implementation complexity
- `results[].structure.calls[]`: Cache operations (get, set, delete)
- `results[].relationships.contains[]`: Cache invalidation logic

**Locate file upload handling:**
```bash
codecontext search "file upload multipart storage" --format json --language java
```
**What to parse:**
- `results[].metadata.signature`: Upload method signatures
- `results[].structure.calls[]`: Storage operations, validations
- `results[].relationships.references[]`: File storage services

**Find async/concurrent code:**
```bash
codecontext search "async await concurrent parallel" --format json
```
**What to parse:**
- `results[].metadata.signature`: async function signatures
- `results[].structure.calls[]`: Async operations (Promise, Future, CompletableFuture)
- `results[].structure.complexity.nesting_depth`: Concurrency complexity

---

## 5. Cross-Language Queries

### Use Case
Multi-language codebases, frontend-backend integration, microservices.

### Example Queries

**Find TypeScript API clients calling Java backend:**
```bash
codecontext search "API client user service" --format json --limit 25
```
**What to parse:**
- `results[].metadata.language`: Filter by "typescript" or "java"
- `results[].structure.references[]`: Shared data models, DTOs
- `results[].relationships.documents[]`: API documentation links

**Locate shared data models:**
```bash
codecontext search "User model DTO entity" --format json
```
**What to parse:**
- `results[].metadata.language`: Multiple languages using same model
- `results[].metadata.type`: CLASS, INTERFACE
- `results[].relationships.referenced_by.total_count`: Usage across languages

**Find Kotlin/Java interop:**
```bash
codecontext search "Kotlin Java interop JvmStatic" --format json --language kotlin
```
**What to parse:**
- `results[].metadata.signature`: @JvmStatic, @JvmOverloads annotations
- `results[].relationships.called_by[]`: Java code calling Kotlin
- `results[].structure.calls[]`: Kotlin calling Java libraries

---

## 6. Documentation-Code Linking

### Use Case
Finding code referenced in documentation, spec implementation.

### Example Queries

**Find code documented in README:**
```bash
codecontext search "main entry point application startup" --format json
```
**What to parse:**
- `results[].relationships.documented_by[]`: Markdown files documenting this code
- `results[].relationships.implements_spec[]`: Spec documents
- `results[].metadata.name`: Entry point functions (main, init, start)

**Locate implementation from spec:**
```bash
codecontext search "payment processing specification" --format json
```
**What to parse:**
- `results[].relationships.implements_spec.items[]`: Implementation files
- `results[].relationships.documents[]`: Related documentation
- `results[].metadata.type`: Implementation type (CLASS, MODULE)

---

## 7. Debugging Scoring Issues

### Use Case
Understanding why certain results rank higher, tuning search quality.

### Example Queries

**Analyze scoring breakdown:**
```bash
codecontext search "authentication" --format json --expand --limit 5
```
**What to parse:**
- `results[].scoring.bm25_score`: Keyword match strength (0-1)
- `results[].scoring.vector_code_score`: Code semantic similarity (0-1)
- `results[].scoring.vector_desc_score`: Description similarity (0-1)
- `results[].scoring.graph_score`: Graph relationship score (0-1)
- `results[].scoring.final_score`: Final fused score (0-1)

**Compare keyword vs semantic:**
```bash
codecontext search "processPayment" --format json --expand
```
**What to check:**
- High `bm25_score` + Low `vector_code_score`: Exact name match, weak semantic
- Low `bm25_score` + High `vector_code_score`: Synonym/related code, strong semantic
- High `graph_score`: Strong relationship connections (callers/callees)

---

## Query Optimization Tips

### ✅ Effective Query Patterns

1. **Use domain terms, not code syntax:**
   - Good: "payment processing credit card"
   - Bad: `class PaymentProcessor`

2. **Combine multiple concepts:**
   - Good: "user authentication OAuth JWT"
   - Better semantic matching across components

3. **Use natural language:**
   - Good: "handle file upload errors"
   - Auto-expands: handle→process/execute, file→document/attachment

4. **Leverage auto-translation:**
   - Korean: "결제 처리 로직"
   - Auto-translates to: "payment processing logic"

### ❌ Ineffective Query Patterns

1. **Code snippets:**
   - Bad: `def process_payment(`
   - Use: "process payment function"

2. **Single short terms:**
   - Bad: "pay"
   - Use: "payment processing" (more context)

3. **File paths:**
   - Bad: "src/services/payment.py"
   - Use: --file-pattern instead

### Performance Tuning

**High precision, low recall:**
```bash
# Increase keyword weight
# Edit .codecontext.yaml: bm25_weight: 0.6 (60% keyword)
```

**High recall, low precision:**
```bash
# Increase semantic weight
# Edit .codecontext.yaml: bm25_weight: 0.3 (30% keyword)
```

**More diverse results:**
```bash
# Decrease MMR lambda
# Edit .codecontext.yaml: mmr_lambda: 0.6 (40% diversity)
```

**More file diversity:**
```bash
# Reduce chunks per file
# Edit .codecontext.yaml: max_chunks_per_file: 1
```

---

## Integration Examples

### Python Script
```python
import subprocess
import json

def search_code(query: str, language: str = None) -> list[dict]:
    """Search codebase using CodeContext CLI."""
    cmd = ["codecontext", "search", query, "--format", "json"]
    if language:
        cmd.extend(["--language", language])

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    return data["results"]

# Find all payment processing code
results = search_code("payment processing", language="python")

for r in results:
    print(f"{r['metadata']['name']} ({r['score']:.2f})")
    print(f"  Callers: {r['relationships']['callers']['total_count']}")
    print(f"  Impact: {r['impact']['total_callers']} transitive callers")
```

### Shell Script
```bash
#!/bin/bash
# Find high-impact functions (many callers)

codecontext search "service function" --format json --limit 50 | \
  jq -r '.results[] |
    select(.relationships.callers.total_count > 10) |
    "\(.metadata.name): \(.relationships.callers.total_count) callers"' | \
  sort -t: -k2 -nr
```

### Node.js
```javascript
const { execSync } = require('child_process');

function searchCode(query, options = {}) {
  const cmd = ['codecontext', 'search', query, '--format', 'json'];
  if (options.language) cmd.push('--language', options.language);
  if (options.limit) cmd.push('--limit', options.limit);

  const output = execSync(cmd.join(' '), { encoding: 'utf-8' });
  return JSON.parse(output);
}

// Find API endpoints
const data = searchCode('REST API endpoint', { language: 'typescript', limit: 20 });

data.results.forEach(r => {
  console.log(`${r.metadata.name} - ${r.location.url}`);
  console.log(`  Complexity: ${r.structure.complexity.cyclomatic}`);
});
```
