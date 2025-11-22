# CodeContext CLI Reference

Complete reference for search output and relationships.

---

## Search Behavior

- **Architecture-first:** Class (implementation) > Interface
- **Size matters:** Large components > small helpers
- **Semantic:** Use domain terms, not code syntax

---

## JSON Output Structure

### Minimal (--format=json)

```json
{
  "results": [
    {
      "name": "process_payment",
      "type": "function",
      "file": "src/services/payment.py",
      "lines": "42-68",
      "language": "python",
      "score": 0.95
    }
  ],
  "total": 10,
  "query": "payment processing"
}
```

**Fields:**
- `name`: Function/class/method name
- `type`: Object type (function, method, class, etc.)
- `file`: Relative file path
- `lines`: Line range ("start-end")
- `language`: python, java, kotlin, typescript, javascript
- `score`: Relevance (0.0-1.0, higher is better)

---

### Expanded (--expand=all)

```json
{
  "results": [
    {
      "name": "process_payment",
      "type": "function",
      "file": "src/services/payment.py",
      "lines": "42-68",
      "language": "python",
      "score": 0.95,
      "signature": "def process_payment(amount: Decimal, method: str) -> bool",
      "snippet": "def process_payment(amount: Decimal, method: str) -> bool:\n    if not validate_amount(amount):\n        return False",
      "content": "def process_payment(amount: Decimal, method: str) -> bool:\n    if not validate_amount(amount):\n        return False\n    return charge_card(amount, method)",
      "parent": "PaymentService",
      "relationships": {
        "callers": {
          "items": [
            {"name": "OrderService.checkout", "location": "chunk_id_123", "type": "direct_call"}
          ],
          "total_count": 12
        },
        "callees": {
          "items": [
            {"name": "validate_amount", "location": "chunk_id_789", "external": false}
          ],
          "total_count": 5
        },
        "contains": {
          "items": [],
          "total_count": 0
        }
      },
      "complexity": {
        "cyclomatic": 5,
        "lines": 26
      },
      "impact": {
        "recursive_callers": 25
      }
    }
  ],
  "total": 10,
  "query": "payment processing"
}
```

---

## Expandable Fields

| Field | Description |
|-------|-------------|
| `signature` | Function/method signature with type hints |
| `snippet` | Essential code snippet (1-3 lines) |
| `content` | Full code body |
| `relationships` | Callers, callees, contains |
| `complexity` | Cyclomatic complexity, LOC |
| `impact` | Recursive callers count |
| `all` | All above fields |

**Relationships structure:**
- `callers`: Who calls this code
- `callees`: What this code calls
- `contains`: What this code contains (for classes)
- Each has `items` (sample) and `total_count`

---

## Relationship Types (12 types)

### Code-to-Code (6 bidirectional pairs)

| Forward | Reverse | Description |
|---------|---------|-------------|
| CALLS | CALLED_BY | Function/method invocation |
| EXTENDS | EXTENDED_BY | Class inheritance |
| IMPLEMENTS | IMPLEMENTED_BY | Interface implementation |
| REFERENCES | REFERENCED_BY | Variable/type reference |
| CONTAINS | CONTAINED_BY | Structural containment |
| IMPORTS | IMPORTED_BY | Module import |

---

## Object Types

**Code:**
`function` | `method` | `class` | `interface` | `enum` | `variable` | `field`

**Document:**
`markdown` | `config`

---

**Version:** 0.5.0
