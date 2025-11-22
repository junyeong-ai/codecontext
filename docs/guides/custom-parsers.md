# Guide: Writing Custom Code Parsers

Learn how to create custom parsers for extracting code objects from source files.

**Time Estimate**: 2-4 hours
**Prerequisites**: Familiarity with Tree-sitter and target language syntax

---

## When to Write a Custom Parser

- Adding support for a new programming language
- Customizing extraction behavior for specific code patterns
- Implementing domain-specific code analysis

---

## Parser Interface

All code parsers must implement the `CodeParser` interface:

**Location**: [packages/codecontext-cli/src/codecontext/parsers/interfaces.py](../../packages/codecontext-cli/src/codecontext/parsers/interfaces.py)

### Required Methods

```python
class CodeParser(Parser):
    """Parser for source code files."""

    # Required attributes
    parser: TreeSitterParser
    language: Language

    # Required methods
    def extract_code_objects(self, file_path: Path, source: str) -> list[CodeObject]
    def extract_relationships(self, file_path: Path, source: str, objects: list[CodeObject]) -> list[tuple[str, str, str]]
    def extract_ast_metadata(self, node: Any, source_bytes: bytes) -> dict
    def get_language(self) -> Language
    def supports_file(self, file_path: Path) -> bool
    def get_file_extensions(self) -> list[str]
```

---

## Step-by-Step Implementation

### 1. Verify Tree-sitter Support

```bash
python3 -c "
from tree_sitter_language_pack import get_language
try:
    lang = get_language('your_language')
    print(f'✅ Supported: {lang}')
except Exception as e:
    print(f'❌ Not supported: {e}')
"
```

**Supported languages**: python, kotlin, java, javascript, typescript, go, rust, ruby, c, cpp, c_sharp, php

### 2. Study Existing Parsers

**Example parsers**:
- **Python**: [languages/python.py](../../packages/codecontext-cli/src/codecontext/parsers/languages/python.py) - Full-featured reference
- **Kotlin**: [languages/kotlin.py](../../packages/codecontext-cli/src/codecontext/parsers/languages/kotlin.py) - JVM language example
- **JavaScript**: [languages/javascript.py](../../packages/codecontext-cli/src/codecontext/parsers/languages/javascript.py) - Dynamic language example

### 3. Create Parser Class

**File**: `packages/codecontext-cli/src/codecontext/parsers/languages/<your_language>.py`

```python
from tree_sitter_language_pack import get_language
from codecontext_core.models import CodeObject, Language
from codecontext.parsers.interfaces import CodeParser
from codecontext.indexer.ast_parser import TreeSitterParser

class YourLanguageParser(CodeParser):
    """Parser for YourLanguage source code."""

    def __init__(self, parser_config=None):
        self.language = Language.YOUR_LANGUAGE
        ts_language = get_language("your_language")
        self.parser = TreeSitterParser(language=ts_language, config=parser_config)

    def get_language(self) -> Language:
        return self.language

    def supports_file(self, file_path: Path) -> bool:
        return file_path.suffix in self.get_file_extensions()

    def get_file_extensions(self) -> list[str]:
        return [".ext"]

    def extract_code_objects(self, file_path: Path, source: str) -> list[CodeObject]:
        # Parse source with Tree-sitter
        tree = self.parser.parse(source.encode())
        root_node = tree.root_node

        # Extract code objects (classes, functions, methods)
        objects = []
        # ... extraction logic using Tree-sitter queries
        return objects

    def extract_relationships(self, file_path: Path, source: str, objects: list[CodeObject]) -> list[tuple[str, str, str]]:
        # Extract CALLS, CONTAINS, REFERENCES relationships
        relationships = []
        # ... relationship extraction logic
        return relationships

    def extract_ast_metadata(self, node: Any, source_bytes: bytes) -> dict:
        # Extract language-specific metadata
        return {
            "complexity": self._calculate_complexity(node),
            "nesting_depth": self._calculate_nesting_depth(node),
            "lines_of_code": node.end_point[0] - node.start_point[0] + 1,
        }
```

### 4. Register Language

Add to `LanguageDetector.EXTENSION_MAP` in [indexer/models.py](../../packages/codecontext-cli/src/codecontext/indexer/models.py):

```python
EXTENSION_MAP = {
    # ... existing mappings
    ".ext": Language.YOUR_LANGUAGE,
}
```

### 5. Register in Factory

Add to `ParserFactory._create_parser()` in [parsers/factory.py](../../packages/codecontext-cli/src/codecontext/parsers/factory.py):

```python
def _create_parser(self, language: Language) -> CodeParser:
    # ... existing languages
    elif language == Language.YOUR_LANGUAGE:
        return YourLanguageParser(parser_config=self._parser_config)
```

### 6. Write Tests

**Unit tests**: `tests/unit/parsers/test_your_language_parser.py`

```python
def test_extract_code_objects():
    parser = YourLanguageParser()
    source = "# your test code"
    objects = parser.extract_code_objects(Path("test.ext"), source)
    assert len(objects) > 0
    assert objects[0].object_type == ObjectType.CLASS

def test_extract_relationships():
    parser = YourLanguageParser()
    source = "# your test code"
    objects = parser.extract_code_objects(Path("test.ext"), source)
    relationships = parser.extract_relationships(Path("test.ext"), source, objects)
    assert len(relationships) > 0
```

---

## Common Patterns

### Extracting Classes

```python
class_query = self.parser.language.query("""
    (class_declaration
        name: (identifier) @class_name
        body: (class_body) @class_body) @class
""")

for match in class_query.matches(root_node):
    # Extract class information
    pass
```

### Extracting Functions

```python
function_query = self.parser.language.query("""
    (function_declaration
        name: (identifier) @func_name
        parameters: (parameters) @params
        body: (block) @body) @function
""")
```

### Extracting Method Calls

```python
call_query = self.parser.language.query("""
    (call_expression
        function: (identifier) @callee) @call
""")
```

---

## Testing

```bash
# Run parser tests
pytest tests/unit/parsers/test_your_language_parser.py -v

# Test with real files
codecontext index /path/to/test/project --language your_language
codecontext search "test query" --language your_language
```

---

## Troubleshooting

### AST Node Type Not Found

**Solution**: Use Tree-sitter playground to identify correct node types
- https://tree-sitter.github.io/tree-sitter/playground

### Relationship Extraction Fails

**Solution**: Verify node structure with debug logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Parser Not Recognized

**Solution**: Ensure language is registered in:
1. `Language` enum (codecontext_core/models/core.py)
2. `LanguageDetector.EXTENSION_MAP`
3. `ParserFactory._create_parser()`

---

## Additional Resources

- [AST Patterns Reference](../references/ast-patterns.md)
- [Adding a New Language Guide](adding-new-language.md)
- [Tree-sitter Documentation](https://tree-sitter.github.io/tree-sitter/)
