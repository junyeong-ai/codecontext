# JSON Schema Reference

## Minimal Output

```json
{
  "results": [{
    "name": "process_payment",
    "type": "function",
    "file": "src/payment.py",
    "lines": "42-68",
    "language": "python",
    "score": 0.95
  }],
  "total": 10,
  "query": "payment"
}
```

## Expanded Output (`--expand all`)

```json
{
  "name": "process_payment",
  "type": "function",
  "file": "src/payment.py",
  "lines": "42-68",
  "language": "python",
  "score": 0.95,
  "signature": "def process_payment(amount: Decimal) -> bool",
  "snippet": "def process_payment(amount):\n    validate(amount)",
  "content": "def process_payment(amount):\n    ...",
  "parent": "PaymentService",
  "relationships": {
    "callers": {"items": [{"name": "checkout", "type": "method", "file": "src/cart.py", "line": 89}], "total_count": 12},
    "callees": {"items": [{"name": "validate", "type": "function", "file": "src/utils.py", "line": 15}], "total_count": 5},
    "contained_by": {"items": [{"name": "PaymentService", "type": "class", "file": "src/payment.py", "line": 10}], "total_count": 1}
  },
  "complexity": {"cyclomatic": 5, "lines": 26},
  "impact": {"direct_callers": 12}
}
```

## Relationship Item Structure

```json
{"name": "function_name", "type": "function", "file": "src/module.py", "line": 42}
```

## Object Types

Code: `function`, `method`, `class`, `interface`, `enum`, `variable`, `field`

Document: `markdown`, `config`
