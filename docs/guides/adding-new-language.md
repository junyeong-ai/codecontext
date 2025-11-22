# Guide: Adding a New Language to Relationship Extraction

This guide walks through the process of adding support for a new programming language to CodeContext's relationship extraction system.

**Time Estimate**: 4-8 hours per language
**Prerequisites**: Familiarity with Tree-sitter, the target language's syntax

---

## Quick Start Checklist

- [ ] Verify Tree-sitter grammar exists for your language
- [ ] Create inheritance extractor (`relationships/inheritance/{language}.py`)
- [ ] Create call graph extractor (`relationships/call_graph/{language}.py`)
- [ ] Write unit tests for both extractors
- [ ] Create test fixtures with sample code
- [ ] Run integration tests
- [ ] Update documentation

---

## Step 1: Verify Tree-sitter Support

Before starting, ensure a Tree-sitter grammar exists for your language:

```bash
# Check if language is supported by tree-sitter-language-pack
python3 -c "
from tree_sitter_language_pack import get_language
try:
    lang = get_language('your_language_name')
    print(f'✅ {lang} is supported')
except Exception as e:
    print(f'❌ Not supported: {e}')
"
```

**Supported languages**: python, kotlin, java, javascript, typescript, go, rust, ruby, c, cpp, c_sharp, php, etc.

If your language isn't supported, you may need to install a separate Tree-sitter grammar package.

---

## Step 2: Understand the Language's AST Patterns

Use the [Tree-sitter playground](https://tree-sitter.github.io/tree-sitter/playground) or local testing to understand:

### 2.1 Inheritance/Interface Patterns

**Example questions to answer**:
- How does your language express class inheritance? (`extends`, `:`, `<`)
- How are interfaces implemented? (`implements`, `:`, mixins)
- What AST node types represent class declarations?
- What AST node types contain base class information?

**Sample exploration**:

```python
# test_ast_patterns.py
from tree_sitter import Parser
from tree_sitter_language_pack import get_language

code = '''
class MyClass extends BaseClass implements Interface1, Interface2 {
    // ...
}
'''

parser = Parser(get_language('java'))
tree = parser.parse(code.encode())

def print_ast(node, indent=0):
    print("  " * indent + f"{node.type}: {code[node.start_byte:node.end_byte][:30]}")
    for child in node.children:
        print_ast(child, indent + 1)

print_ast(tree.root_node)
```

### 2.2 Method Call Patterns

**Example questions**:
- What AST node represents a function/method call?
- How do you distinguish between `obj.method()` and `function()`?
- Are there special cases (static calls, constructors, operators)?

---

## Step 3: Implement Inheritance Extractor

### Template: `codecontext/indexer/relationships/inheritance/{language}.py`

```python
"""{Language} inheritance relationship extraction."""

from typing import List
from codecontext.indexer.relationships.inheritance.base import InheritanceExtractorBase
from codecontext.core.models import CodeObject, Language
import logging

logger = logging.getLogger(__name__)


class {Language}InheritanceExtractor(InheritanceExtractorBase):
    """Extract REFERENCES relationships for {Language} inheritance."""

    def __init__(self):
        super().__init__(Language.{LANGUAGE_ENUM})

    def extract_base_classes(self, obj: CodeObject) -> List[str]:
        """Extract base class names from {Language} class definition.

        {Language} syntax examples:
            class MyClass extends BaseClass implements Interface1
            # Add language-specific examples

        Args:
            obj: CodeObject representing a class or interface

        Returns:
            List of base class/interface names
        """
        if not self.parser:
            return []

        bases = []

        try:
            tree = self.parser.parse(obj.content.encode())

            # TODO: Implement language-specific extraction
            # 1. Find the class/interface declaration node
            # 2. Extract base class nodes (extends, implements, etc.)
            # 3. Parse base class names from AST nodes

            def find_class_node(node, class_name):
                """Find the class declaration matching the class name."""
                # TODO: Implement based on your language's AST structure
                pass

            class_node = find_class_node(tree.root_node, obj.name)
            if not class_node:
                return []

            # TODO: Extract base classes from class_node
            # Example pattern:
            # for child in class_node.children:
            #     if child.type == 'superclass':  # Language-specific
            #         base_name = extract_name(child)
            #         bases.append(base_name)

        except Exception as e:
            logger.debug(f"Failed to extract bases from {obj.name}: {e}")

        return bases
```

### Implementation Tips

1. **Find the class declaration node**: Traverse AST to find the node matching `obj.name`
2. **Identify base class nodes**: Look for `extends`, `implements`, inheritance markers
3. **Extract names**: Parse identifier/type_identifier nodes to get base class names
4. **Handle generics**: Strip type parameters: `Repository<T>` → `Repository`

**Reference existing implementations**:
- Python (regex-based): `relationships/inheritance/python.py`
- Kotlin (Tree-sitter): `relationships/inheritance/kotlin.py`

---

## Step 4: Implement Call Graph Extractor

### Template: `codecontext/indexer/relationships/call_graph/{language}.py`

```python
"""{Language} call graph relationship extraction."""

from typing import List, Dict
from codecontext.indexer.relationships.call_graph.base import CallGraphExtractorBase
from codecontext.core.models import CodeObject, Language
import logging

logger = logging.getLogger(__name__)


class {Language}CallGraphExtractor(CallGraphExtractorBase):
    """Extract CALLS relationships for {Language} method/function calls."""

    def __init__(self):
        super().__init__(Language.{LANGUAGE_ENUM})

    def extract_calls(self, obj: CodeObject) -> List[Dict]:
        """Extract call expressions from {Language} code.

        {Language} call patterns:
            obj.method(args)       → "method"
            function(args)         → "function"
            # Add language-specific patterns

        Args:
            obj: Method or function CodeObject

        Returns:
            List of dicts with keys: name, pattern, full_text
        """
        if not self.parser:
            return []

        calls = []

        try:
            tree = self.parser.parse(obj.content.encode())

            def traverse(node):
                """Recursively traverse AST to find call expressions."""
                # TODO: Implement language-specific call detection
                # Example pattern:
                # if node.type == 'call_expression':  # Language-specific
                #     call_info = extract_call_info(node)
                #     if call_info:
                #         calls.append(call_info)
                #
                # for child in node.children:
                #     traverse(child)

            traverse(tree.root_node)

        except Exception as e:
            logger.debug(f"Failed to extract calls from {obj.name}: {e}")

        return calls

    def _extract_call_info(self, call_node, source_bytes) -> Dict:
        """Parse method name from call expression.

        Args:
            call_node: AST node representing a call
            source_bytes: Source code as bytes

        Returns:
            Dict with: name, pattern, full_text
            Returns None for unsupported patterns
        """
        # TODO: Implement based on your language's call structure
        # Example:
        # if call_node has member_expression child:
        #     return {
        #         'name': extract_method_name(member_expression),
        #         'pattern': 'member',
        #         'full_text': full_call_text,
        #     }
        pass
```

### Implementation Tips

1. **Identify call nodes**: What AST node type represents calls in your language?
   - Python: `call`
   - Java: `method_invocation`
   - TypeScript: `call_expression`

2. **Extract method names**: Handle different call patterns:
   - Direct: `function()` → extract identifier
   - Member: `obj.method()` → extract last identifier in chain
   - Static: `Class.staticMethod()` → treat same as member

3. **Return format**:
```python
{
    'name': 'methodName',          # The method/function being called
    'pattern': 'member',           # 'identifier', 'member', 'navigation'
    'full_text': 'obj.methodName'  # Full call expression (for debugging)
}
```

4. **Confidence levels** (inherited from base):
   - Identifier call: 0.6
   - Member call: 0.5
   - Default: 0.4

**Reference existing implementations**:
- Python: `relationships/call_graph/python.py`
- Kotlin: `relationships/call_graph/kotlin.py`

---

## Step 5: Write Unit Tests

### Test Template: `tests/unit/indexer/relationships/inheritance/test_{language}_inheritance.py`

```python
"""Tests for {Language} inheritance extraction."""

import pytest
from codecontext.indexer.relationships.inheritance.{language} import {Language}InheritanceExtractor
from codecontext.core.models import CodeObject, ObjectType, Language, RelationType


def test_single_inheritance():
    """Test extraction of single base class."""
    extractor = {Language}InheritanceExtractor()

    code = '''
    class Derived extends Base {
        // ...
    }
    '''

    obj = CodeObject(
        id="derived_class",
        name="Derived",
        object_type=ObjectType.CLASS,
        language=Language.{LANGUAGE_ENUM},
        content=code,
        file_path="Test.ext",
        start_line=1,
        end_line=3,
    )

    base_obj = CodeObject(
        id="base_class",
        name="Base",
        object_type=ObjectType.CLASS,
        language=Language.{LANGUAGE_ENUM},
        content="class Base {}",
        file_path="Base.ext",
        start_line=1,
        end_line=1,
    )

    relationships = extractor.extract_from_object(obj, [obj, base_obj])

    assert len(relationships) == 1
    assert relationships[0].source_id == "derived_class"
    assert relationships[0].target_id == "base_class"
    assert relationships[0].relation_type == RelationType.REFERENCES
    assert relationships[0].confidence == 0.8


def test_multiple_inheritance():
    """Test extraction of multiple base classes/interfaces."""
    # TODO: Implement based on your language's multi-inheritance support
    pass


def test_generic_base_class():
    """Test handling of generic type parameters."""
    # TODO: Test that Repository<T> is extracted as "Repository"
    pass


def test_no_inheritance():
    """Test class with no base classes."""
    # TODO: Verify empty list returned
    pass
```

### Test Template: `tests/unit/indexer/relationships/call_graph/test_{language}_calls.py`

```python
"""Tests for {Language} call graph extraction."""

import pytest
from codecontext.indexer.relationships.call_graph.{language} import {Language}CallGraphExtractor
from codecontext.core.models import CodeObject, ObjectType, Language, RelationType


def test_method_call_extraction():
    """Test extraction of method calls."""
    extractor = {Language}CallGraphExtractor()

    code = '''
    function process() {
        repository.save(obj);
        calculate(amount);
    }
    '''

    obj = CodeObject(
        id="process_func",
        name="process",
        object_type=ObjectType.FUNCTION,
        language=Language.{LANGUAGE_ENUM},
        content=code,
        file_path="Test.ext",
        start_line=1,
        end_line=4,
    )

    save_obj = CodeObject(
        id="save_method",
        name="save",
        object_type=ObjectType.METHOD,
        language=Language.{LANGUAGE_ENUM},
        content="function save(obj) {}",
        file_path="Repository.ext",
        start_line=1,
        end_line=1,
    )

    calculate_obj = CodeObject(
        id="calculate_func",
        name="calculate",
        object_type=ObjectType.FUNCTION,
        language=Language.{LANGUAGE_ENUM},
        content="function calculate(amt) {}",
        file_path="Utils.ext",
        start_line=1,
        end_line=1,
    )

    all_objects = [obj, save_obj, calculate_obj]
    relationships = extractor.extract_from_object(obj, all_objects)

    assert len(relationships) == 2

    # Check save call
    save_rel = next(r for r in relationships if r.target_id == "save_method")
    assert save_rel.relation_type == RelationType.CALLS
    assert save_rel.confidence >= 0.4

    # Check calculate call
    calc_rel = next(r for r in relationships if r.target_id == "calculate_func")
    assert calc_rel.relation_type == RelationType.CALLS


def test_chained_method_calls():
    """Test chained method calls like obj.prop.method()."""
    # TODO: Implement
    pass


def test_static_method_calls():
    """Test static method calls."""
    # TODO: Implement (if applicable to your language)
    pass
```

---

## Step 6: Create Test Fixtures

Create sample code files in `tests/fixtures/{language}_samples/`:

### Example Structure

```
tests/fixtures/{language}_samples/
├── base_class.{ext}          # Simple base class
├── derived_class.{ext}       # Class with inheritance
├── interface.{ext}           # Interface (if applicable)
├── service.{ext}             # Class with method calls
└── utils.{ext}               # Utility functions
```

### Sample Files

**base_class.{ext}**:
```
class BaseRepository {
    function save(obj) { /* ... */ }
    function findById(id) { /* ... */ }
}
```

**derived_class.{ext}**:
```
class UserRepository extends BaseRepository {
    function findByEmail(email) { /* ... */ }
}
```

**service.{ext}**:
```
class UserService {
    function processUser(user) {
        repository.save(user);
        validate(user);
        notify(user);
    }
}
```

---

## Step 7: Integration Testing

Add integration test in `tests/integration/test_multi_language_indexing.py`:

```python
def test_{language}_end_to_end_indexing():
    """Test full indexing pipeline for {Language} code."""
    test_dir = Path("tests/fixtures/{language}_samples")

    # Index all files
    strategy = FullSyncStrategy(...)
    result = strategy.sync(test_dir)

    # Query relationships
    storage = QdrantProvider(...)
    relationships = storage.get_relationships(...)

    # Verify CALLS relationships
    calls = [r for r in relationships if r.relation_type == RelationType.CALLS]
    assert len(calls) > 0, "Expected CALLS relationships"

    # Verify REFERENCES relationships
    references = [r for r in relationships if r.relation_type == RelationType.REFERENCES]
    assert len(references) > 0, "Expected REFERENCES relationships"
```

---

## Step 8: Update Language Enum (if needed)

If adding a language not already in `Language` enum:

**File**: `codecontext_core/models/core.py`

```python
class Language(str, Enum):
    """Programming language enum."""
    PYTHON = "python"
    KOTLIN = "kotlin"
    JAVA = "java"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    YOUR_LANGUAGE = "your_language"  # ADD THIS
```

---

## Step 9: Run Tests

```bash
# Run unit tests for your language
pytest tests/unit/indexer/relationships/inheritance/test_{language}_inheritance.py -v
pytest tests/unit/indexer/relationships/call_graph/test_{language}_calls.py -v

# Run all relationship extraction tests
pytest tests/unit/indexer/relationships/ -v

# Run integration tests
pytest tests/integration/test_multi_language_indexing.py::test_{language}_end_to_end_indexing -v

# Run full test suite
pytest
```

---

## Step 10: Update Documentation

### Update `CLAUDE.md`

```markdown
## Active Technologies
- {Language} X.X.X (Relationship extraction)
```

### Update `MULTI_LANGUAGE_RELATIONSHIPS.md`

Add your language to the supported languages section:

```markdown
### Current State
- **Python**: ✅ Fully implemented
- **Kotlin**: ✅ Fully implemented
- **Java**: ✅ Fully implemented
- **TypeScript**: ✅ Fully implemented
- **JavaScript**: ✅ Fully implemented
- **{Language}**: ✅ Fully implemented  # ADD THIS
```

---

## Common Pitfalls & Solutions

### Pitfall 1: Parser Initialization Fails

**Symptom**: `self.parser` is `None`, extraction returns empty lists

**Solution**:
- Verify language name matches Tree-sitter grammar exactly
- Check `tree_sitter_language_pack` version supports your language
- Test parser initialization in isolation:

```python
from tree_sitter_language_pack import get_language
get_language('your_language')  # Should not raise exception
```

### Pitfall 2: AST Node Types Don't Match

**Symptom**: Extraction returns no results despite valid code

**Solution**:
- Print AST structure to debug:
```python
def debug_ast(node, indent=0):
    print("  " * indent + node.type)
    for child in node.children:
        debug_ast(child, indent + 1)

debug_ast(tree.root_node)
```
- Compare with Tree-sitter playground output
- Verify node type strings are exact matches (case-sensitive)

### Pitfall 3: Generic Types Break Parsing

**Symptom**: `Repository<User, UUID>` not matched

**Solution**:
- Strip generic parameters when extracting names:
```python
base_name = raw_name.split('<')[0].strip()
```

### Pitfall 4: Chained Calls Not Extracted

**Symptom**: `obj.prop.method()` not detected

**Solution**:
- Recursively traverse member/navigation expressions
- Extract the **last** identifier in the chain (the method name)

---

## Example: Real Implementation (Go)

For a complete example, see how Go would be implemented:

### `relationships/inheritance/go.py`

```python
"""Go inheritance extraction (via struct embedding)."""

from typing import List
from codecontext.indexer.relationships.inheritance.base import InheritanceExtractorBase
from codecontext.core.models import CodeObject, Language
import logging

logger = logging.getLogger(__name__)


class GoInheritanceExtractor(InheritanceExtractorBase):
    """Extract REFERENCES for Go struct embedding."""

    def __init__(self):
        super().__init__(Language.GO)

    def extract_base_classes(self, obj: CodeObject) -> List[str]:
        """Extract embedded struct names.

        Go uses struct embedding instead of inheritance:
            type DerivedStruct struct {
                BaseStruct  // Embedded field (anonymous)
                field int
            }

        Args:
            obj: Struct CodeObject

        Returns:
            List of embedded struct names
        """
        if not self.parser:
            return []

        bases = []

        try:
            tree = self.parser.parse(obj.content.encode())

            def find_struct_node(node, struct_name):
                if node.type == 'type_declaration':
                    for child in node.children:
                        if child.type == 'type_spec':
                            # Check if name matches
                            for spec_child in child.children:
                                if spec_child.type == 'type_identifier':
                                    name = obj.content.encode()[
                                        spec_child.start_byte:spec_child.end_byte
                                    ].decode()
                                    if name == struct_name:
                                        return child
                # Recurse
                for child in node.children:
                    result = find_struct_node(child, struct_name)
                    if result:
                        return result
                return None

            struct_node = find_struct_node(tree.root_node, obj.name)
            if not struct_node:
                return []

            # Find struct_type -> field_declaration_list
            for child in struct_node.children:
                if child.type == 'struct_type':
                    for struct_child in child.children:
                        if struct_child.type == 'field_declaration_list':
                            # Extract embedded fields (anonymous fields)
                            for field in struct_child.children:
                                if field.type == 'field_declaration':
                                    # Check if it's an embedded field (no field name)
                                    type_identifiers = [
                                        c for c in field.children
                                        if c.type == 'type_identifier'
                                    ]
                                    if len(type_identifiers) == 1:
                                        # Embedded field
                                        embedded_name = obj.content.encode()[
                                            type_identifiers[0].start_byte:
                                            type_identifiers[0].end_byte
                                        ].decode()
                                        bases.append(embedded_name)

        except Exception as e:
            logger.debug(f"Failed to extract Go embeddings from {obj.name}: {e}")

        return bases
```

---

## Validation Checklist

Before submitting:

- [ ] Parser initializes without errors
- [ ] Inheritance extractor passes all unit tests
- [ ] Call graph extractor passes all unit tests
- [ ] Integration test passes
- [ ] No regressions in existing languages
- [ ] Code formatted with `black`
- [ ] Linting passes (`ruff check`)
- [ ] Type hints validated (`mypy`)
- [ ] Documentation updated
- [ ] Test coverage >= 95%

---

## Getting Help

- **Tree-sitter AST Reference**: https://tree-sitter.github.io/tree-sitter/
- **Language Grammars**: https://github.com/tree-sitter/
- **Existing Implementations**: `codecontext/indexer/relationships/{inheritance,call_graph}/`
- **Constitution**: `.specify/memory/constitution.md`

---

Happy coding! 🚀
