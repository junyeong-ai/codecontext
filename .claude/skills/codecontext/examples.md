# CodeContext Search Examples

AI agent usage patterns for CodeContext CLI.

---

## Progressive Discovery Strategy

**Token-efficient approach:**

1. **Minimal search** → Locate candidates
2. **Targeted expansion** → Analyze specific results
3. **Deep dive** → Full context when needed

```bash
# Step 1: Locate
codecontext search "payment" --format=json --limit 20

# Step 2: Analyze
codecontext search "PaymentService" --format=json --expand=signature,relationships

# Step 3: Deep dive
codecontext search "process_payment" --format=json --expand=all
```

---

## Core Patterns

### 1. Architecture Exploration

**Find core components:**

```bash
# Locate architecture (Class ranks higher than Interface)
codecontext search "authentication system" --format=json --limit 15

# Analyze component
codecontext search "AuthService" --format=json --expand=relationships,impact
```

**Key fields:**
- `type`: "class" > "interface"
- `impact.recursive_callers`: Total transitive callers (most important)

### 2. Dependency Analysis

```bash
# Locate
codecontext search "PaymentService" --format=json

# Get dependencies
codecontext search "PaymentService" --format=json --expand=relationships,impact
```

**Key fields:**
- `relationships.callers.items[]`: Who calls this
- `relationships.callees.items[]`: What this calls
- `impact.recursive_callers`: Total impact

### 3. API Discovery

```bash
# Find endpoints
codecontext search "REST API endpoint user" --format=json --language python

# Get implementation
codecontext search "create_user" --format=json --expand=signature,content
```

**Key fields:**
- `signature`: Function signature
- `content`: Implementation
- `language`: Language filter

### 4. Cross-Language Integration

```bash
# TypeScript client
codecontext search "UserApiClient" --format=json --expand=content --language typescript

# Java backend
codecontext search "UserService" --format=json --expand=content --language java
```

---

## Query Best Practices

**Use domain terms, not syntax:**
- ✅ "payment processing credit card"
- ✅ "user authentication OAuth JWT"
- ✅ "REST API endpoint user creation"
- ❌ `class PaymentProcessor`
- ❌ `def process_payment(`

**Rationale:** Semantic search understands natural language better.

---

## Key Fields Quick Reference

### Default (minimal)
`name` | `type` | `file` | `lines` | `language` | `score`

### Expanded (--expand)
- `signature`: Function signature with types
- `snippet`: 1-3 lines
- `content`: Full body
- `relationships.callers.items[]`: Callers sample
- `relationships.callers.total_count`: Total callers
- `complexity.cyclomatic`: McCabe complexity
- `impact.recursive_callers`: Total transitive callers

---

## Common Use Cases

### Find Entry Points
```bash
codecontext search "main entry point" --format=json --expand=relationships
```
**Parse:** `relationships.callers.total_count` = 0

### Find High-Impact Components
```bash
codecontext search "service repository" --format=json --expand=impact --limit 50
```
**Sort by:** `impact.recursive_callers` (descending)

### Find Tests
```bash
codecontext search "test unittest" --format=json
```
**Parse:** `file` contains "tests/" or "test_"

---

**Version:** 0.5.0
