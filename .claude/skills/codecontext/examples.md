# Usage Patterns

## Progressive Discovery (Token-Efficient)

```bash
# 1. Locate candidates
codecontext search "payment" --format json --limit 20

# 2. Analyze specific result
codecontext search "PaymentService" --format json --expand relationships

# 3. Deep dive if needed
codecontext search "process_payment" --format json --expand all
```

## Common Tasks

### Find what calls a function
```bash
codecontext search "authenticate" --format json --expand relationships
# Parse: relationships.callers.items[]
```

### Find dependencies
```bash
codecontext search "UserService" --format json --expand relationships
# Parse: relationships.callees.items[]
```

### Find entry points (no callers)
```bash
codecontext search "main handler" --format json --expand relationships
# Filter: relationships.callers.total_count == 0
```

### Find high-impact code
```bash
codecontext search "service" --format json --expand impact --limit 50
# Sort by: impact.direct_callers (descending)
```

### Cross-language search
```bash
codecontext search "UserClient" --format json --language typescript
codecontext search "UserService" --format json --language java
```

## Query Tips

Use natural language:
- "payment processing" (not `def process_payment`)
- "user authentication OAuth" (not `class AuthService`)
