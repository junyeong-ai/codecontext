# Language-Specific Optimizers

Guide to CodeContext's language-specific AST optimization system for improved code parsing and natural language generation.

---

## Overview

CodeContext uses **language-specific optimizers** to post-process AST-parsed code objects and enhance their quality for search and embedding:

1. **Enhanced NL descriptions** - Better natural language representations
2. **Code quality improvements** - Remove noise, normalize formatting
3. **Metadata enrichment** - Add language-specific context
4. **Relationship optimization** - Improve call graph accuracy

**Location:** `packages/codecontext-cli/src/codecontext/parsers/language_optimizers/`

---

## Architecture

### Base Interface

**File:** `base.py`

```python
class BaseLanguageOptimizer(ABC):
    """Base class for language-specific code optimizers."""

    @abstractmethod
    def optimize(self, code_object: CodeObject) -> CodeObject:
        """Optimize a single code object."""
        pass
```

### Factory Pattern

**File:** `optimizer_factory.py`

**Responsibility:** Dynamic optimizer loading based on language

```python
def get_optimizer(language: str) -> Optional[BaseLanguageOptimizer]:
    """Get optimizer for language (returns None if not available)."""
    optimizers = {
        "python": PythonOptimizer(),
        "java": JavaOptimizer(),
        "kotlin": KotlinOptimizer(),
        "typescript": TypeScriptOptimizer(),
        "javascript": TypeScriptOptimizer(),  # TS optimizer handles JS
    }
    return optimizers.get(language.lower())
```

---

## Python Optimizer

**File:** `python_optimizer.py` (13,839 bytes)

**Class:** `PythonOptimizer`

### Features

**1. Docstring Enhancement**
- Extracts docstrings from AST nodes
- Formats according to Google/NumPy/Sphinx style
- Adds parameter/return type information

**2. Type Hint Processing**
- Extracts type annotations from function signatures
- Normalizes type hint syntax
- Adds to metadata for better search

**3. Decorator Handling**
- Recognizes common decorators (`@property`, `@staticmethod`, `@classmethod`)
- Adjusts object classification based on decorators
- Improves relationship extraction

**4. Import Optimization**
- Resolves relative imports to absolute
- Tracks module dependencies
- Improves cross-file relationship accuracy

**Example:**

**Input AST Node:**
```python
@property
def user_name(self) -> str:
    """Get the user's name.

    Returns:
        The full name of the user.
    """
    return self._name
```

**Optimizer Output:**
- **Type:** Property (not regular method)
- **Return Type:** `str`
- **NL Description:** "Property that gets the user's name and returns the full name of the user."
- **Metadata:** `{"is_property": true, "return_type": "str"}`

---

## Java Optimizer

**File:** `java_optimizer.py` (11,329 bytes)

**Class:** `JavaOptimizer`

### Features

**1. Annotation Processing**
- Extracts Java annotations (`@Override`, `@Deprecated`, `@Autowired`)
- Recognizes Spring/Jakarta EE annotations
- Enhances metadata for framework-aware search

**2. Access Modifier Handling**
- Preserves public/private/protected information
- Adds to metadata for filtering
- Improves encapsulation understanding

**3. Generic Type Resolution**
- Resolves generic type parameters (`List<String>`)
- Normalizes wildcard types (`? extends T`)
- Improves type-based search

**4. Javadoc Enhancement**
- Parses Javadoc comments
- Extracts `@param`, `@return`, `@throws` tags
- Generates comprehensive NL descriptions

**Example:**

**Input AST Node:**
```java
/**
 * Retrieves a user by their unique identifier.
 *
 * @param userId the unique ID of the user
 * @return the User object
 * @throws UserNotFoundException if user not found
 */
@Override
public User getUserById(Long userId) throws UserNotFoundException {
    return userRepository.findById(userId)
        .orElseThrow(() -> new UserNotFoundException(userId));
}
```

**Optimizer Output:**
- **Annotations:** `["Override"]`
- **Access Modifier:** `public`
- **Parameters:** `[{"name": "userId", "type": "Long", "description": "the unique ID of the user"}]`
- **Return Type:** `User`
- **Exceptions:** `["UserNotFoundException"]`
- **NL Description:** "Overridden public method that retrieves a user by their unique identifier (userId: Long) and returns the User object, may throw UserNotFoundException if user not found."

---

## Kotlin Optimizer

**File:** `kotlin_optimizer.py` (15,774 bytes)

**Class:** `KotlinOptimizer`

### Features

**1. Data Class Detection**
- Identifies `data class` declarations
- Generates auto-property descriptions
- Adds structural metadata

**2. Null Safety Handling**
- Preserves nullable type annotations (`String?`)
- Adds null safety information to metadata
- Improves type-aware search

**3. Extension Function Recognition**
- Identifies extension functions
- Associates with receiver types
- Enhances relationship graph

**4. Coroutine Support**
- Recognizes `suspend` functions
- Adds concurrency context to metadata
- Improves async code search

**5. KDoc Processing**
- Parses KDoc comments (similar to Javadoc)
- Extracts structured documentation
- Generates rich NL descriptions

**Example:**

**Input AST Node:**
```kotlin
/**
 * Suspends and retrieves user profile from remote API.
 *
 * @param userId the user's unique identifier
 * @return User profile or null if not found
 */
suspend fun String.fetchUserProfile(): User? {
    return apiClient.get("/users/$this")
}
```

**Optimizer Output:**
- **Extension Type:** `String`
- **Is Suspend:** `true`
- **Return Type:** `User?` (nullable)
- **NL Description:** "Suspend extension function on String that retrieves user profile from remote API, returns User profile or null if not found."
- **Metadata:** `{"is_suspend": true, "is_extension": true, "receiver_type": "String", "is_nullable": true}`

---

## TypeScript Optimizer

**File:** `typescript_optimizer.py` (12,407 bytes)

**Class:** `TypeScriptOptimizer`

**Note:** Also handles JavaScript files

### Features

**1. Interface/Type Detection**
- Recognizes TypeScript interfaces and type aliases
- Extracts type definitions
- Improves type-based search

**2. Decorator Handling**
- Supports experimental decorators (Angular, NestJS)
- Extracts decorator metadata
- Enhances framework-aware search

**3. Async/Await Recognition**
- Identifies `async` functions
- Adds concurrency context
- Improves async code search

**4. JSDoc Processing**
- Parses JSDoc comments
- Extracts type information from JSDoc (for JavaScript)
- Generates comprehensive NL descriptions

**5. Module System Normalization**
- Handles ES6 modules (`import`/`export`)
- Handles CommonJS (`require`/`module.exports`)
- Normalizes for consistent relationship extraction

**Example:**

**Input AST Node:**
```typescript
/**
 * Asynchronously authenticates a user with email and password.
 *
 * @param email - User's email address
 * @param password - User's password
 * @returns Authentication token
 * @throws {AuthenticationError} If credentials are invalid
 */
@Injectable()
async function authenticateUser(
    email: string,
    password: string
): Promise<string> {
    const user = await userService.findByEmail(email);
    if (!user || !user.verifyPassword(password)) {
        throw new AuthenticationError("Invalid credentials");
    }
    return tokenService.generate(user.id);
}
```

**Optimizer Output:**
- **Decorators:** `["Injectable"]`
- **Is Async:** `true`
- **Parameters:** `[{"name": "email", "type": "string"}, {"name": "password", "type": "string"}]`
- **Return Type:** `Promise<string>`
- **Exceptions:** `["AuthenticationError"]`
- **NL Description:** "Injectable async function that authenticates a user with email and password, returns authentication token, may throw AuthenticationError if credentials are invalid."
- **Metadata:** `{"is_async": true, "is_injectable": true, "return_type": "Promise<string>"}`

---

## Common Optimization Patterns

### 1. Natural Language Enhancement

**Before Optimization:**
```
Function: getUserById
Description: "Function getUserById"
```

**After Optimization:**
```
Function: getUserById
Description: "Retrieves a user by their unique identifier (userId), returns User object or null if not found"
```

### 2. Metadata Enrichment

**Before:**
```json
{
  "type": "method",
  "name": "getUserById"
}
```

**After:**
```json
{
  "type": "method",
  "name": "getUserById",
  "access_modifier": "public",
  "return_type": "User",
  "parameters": [{"name": "userId", "type": "Long"}],
  "annotations": ["Override"],
  "is_async": false
}
```

### 3. Relationship Improvement

**Before:**
- Calls: Unknown (raw AST doesn't always capture)

**After:**
- Calls: `userRepository.findById`, `UserNotFoundException` (constructor)
- Called By: (reverse relationship tracked)

---

## When Optimizers Run

**Pipeline:**
```
Source File
    ↓
Tree-sitter AST Parsing (BaseLanguageParser)
    ↓
Code Object Extraction
    ↓
Language Optimizer (if available)
    ↓
Enhanced Code Object
    ↓
NL Generation
    ↓
Embedding Generation
```

**Note:** If no optimizer exists for a language, code objects pass through unoptimized.

---

## Adding a New Optimizer

### Step 1: Create Optimizer Class

```python
# packages/codecontext-cli/src/codecontext/parsers/language_optimizers/go_optimizer.py

from .base import BaseLanguageOptimizer
from codecontext_core.models import CodeObject

class GoOptimizer(BaseLanguageOptimizer):
    """Go-specific code optimizer."""

    def optimize(self, code_object: CodeObject) -> CodeObject:
        """Optimize Go code object."""

        # 1. Extract Go-specific features
        code_object = self._extract_receiver_info(code_object)
        code_object = self._process_interfaces(code_object)

        # 2. Enhance NL description
        code_object.natural_language = self._generate_nl_description(code_object)

        # 3. Enrich metadata
        code_object.metadata["is_exported"] = self._is_exported(code_object.name)

        return code_object

    def _extract_receiver_info(self, code_object: CodeObject) -> CodeObject:
        # Implementation...
        pass

    def _process_interfaces(self, code_object: CodeObject) -> CodeObject:
        # Implementation...
        pass

    def _generate_nl_description(self, code_object: CodeObject) -> str:
        # Implementation...
        pass

    def _is_exported(self, name: str) -> bool:
        # In Go, exported names start with uppercase
        return name[0].isupper() if name else False
```

### Step 2: Register in Factory

```python
# packages/codecontext-cli/src/codecontext/parsers/language_optimizers/optimizer_factory.py

from .go_optimizer import GoOptimizer

def get_optimizer(language: str) -> Optional[BaseLanguageOptimizer]:
    optimizers = {
        # ... existing optimizers ...
        "go": GoOptimizer(),
    }
    return optimizers.get(language.lower())
```

### Step 3: Add Tests

```python
# tests/unit/test_go_optimizer.py

def test_go_optimizer_receiver():
    optimizer = GoOptimizer()
    code_object = CodeObject(
        name="String",
        type="method",
        content="func (s String) Len() int { return len(s) }",
        # ...
    )

    optimized = optimizer.optimize(code_object)

    assert "receiver_type" in optimized.metadata
    assert optimized.metadata["receiver_type"] == "String"
```

---

## Performance Impact

**Overhead per Code Object:** ~1-5ms

**Total Impact:**
- Small codebase (1k objects): +1-5 seconds
- Large codebase (100k objects): +100-500 seconds

**Benefit:**
- 20-40% better search relevance (measured on validation tests)
- Improved embedding quality
- More accurate relationship extraction

**Recommendation:** Always enable optimizers in production (enabled by default)

---

## Configuration

**Optimizers are always enabled** and cannot be disabled via configuration.

To skip optimization for specific languages, remove optimizer from factory:
```python
# optimizer_factory.py
optimizers = {
    "python": PythonOptimizer(),
    # "java": JavaOptimizer(),  # Disabled
}
```

---

## Troubleshooting

### Optimizer Not Running

**Symptom:** NL descriptions are generic

**Debug:**
1. Check language detection: `codecontext status --verbose`
2. Verify optimizer exists for language: `optimizer_factory.get_optimizer(language)`
3. Check logs for optimizer errors

### Poor NL Quality

**Symptom:** NL descriptions are incomplete

**Solution:**
1. Improve docstring/comment extraction in optimizer
2. Add more metadata enrichment logic
3. Update NL generation templates

### Slow Optimization

**Symptom:** Indexing is slow

**Solution:**
1. Profile optimizer with `cProfile`
2. Optimize heavy regex/parsing operations
3. Cache repeated computations

---

## Related Documentation

- [Adding a New Language](guides/adding-new-language.md)
- [AST Patterns Reference](references/AST_PATTERNS.md)
- [Architecture Overview](architecture.md)

---

**Last Updated:** 2025-10-22
