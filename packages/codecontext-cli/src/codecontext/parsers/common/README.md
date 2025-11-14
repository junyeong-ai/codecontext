# Parser Common Utilities

This directory contains shared utilities and mixins for language parsers to reduce code duplication.

## Overview

The common utilities provide:
- **SignatureExtractorMixin**: Extract function/method signatures, parameters, return types
- **ComplexityCalculator**: Calculate cyclomatic and cognitive complexity
- **AbstractChunker**: Base class for hierarchical content chunking

## Usage

### SignatureExtractorMixin

Use this mixin to extract signature information from AST nodes:

```python
from codecontext.parsers.base import BaseCodeParser
from codecontext.parsers.common.signature_extractor import SignatureExtractorMixin

class PythonParser(BaseCodeParser, SignatureExtractorMixin):
    def parse_function(self, node):
        # Extract complete signature
        signature = self.extract_function_signature(node)
        # signature = {
        #     "name": "my_function",
        #     "parameters": ["arg1", "arg2", "arg3"],
        #     "return_type": "int",
        #     "parameter_count": 3
        # }

        # Or extract individual components
        params = self.extract_parameters(node)
        return_type = self.extract_return_type(node)
        modifiers = self.extract_modifiers(node)
        generics = self.extract_generic_parameters(node)
```

**Benefits**:
- Eliminates duplicate signature extraction logic across parsers
- Consistent API across Python, Kotlin, Java, TypeScript, JavaScript
- Handles language-specific node types automatically

### ComplexityCalculator

Calculate complexity metrics for any AST node:

```python
from codecontext.parsers.common.complexity import ComplexityCalculator

class PythonParser(BaseCodeParser):
    def parse_function(self, node):
        # Calculate cyclomatic complexity
        complexity = ComplexityCalculator.calculate(node)

        # Calculate nesting depth
        nesting = ComplexityCalculator.calculate_nesting_depth(node)

        # Calculate cognitive complexity
        cognitive = ComplexityCalculator.calculate_cognitive_complexity(node)

        # Get complexity rating
        rating = ComplexityCalculator.get_complexity_rating(complexity)

        return {
            "complexity": complexity,
            "nesting_depth": nesting,
            "cognitive_complexity": cognitive,
            "complexity_rating": rating,
        }
```

**Complexity Ratings**:
- **A (1-5)**: Simple, easy to maintain
- **B (6-10)**: More complex, acceptable
- **C (11-20)**: Complex, consider refactoring
- **D (21-30)**: Very complex, should refactor
- **E (31-40)**: Extremely complex, urgent refactoring needed
- **F (>40)**: Unmaintainable, must refactor

### AbstractChunker

Base class for content chunkers with validation and post-processing:

```python
from codecontext.parsers.common.chunkers import AbstractChunker, Chunk

class YAMLChunker(AbstractChunker):
    def chunk(self, content: str) -> list[Chunk]:
        # Custom chunking logic
        raw_chunks = self._split_by_hierarchy(content)

        # Automatic post-processing:
        # - Validates chunk sizes
        # - Splits oversized chunks
        # - Merges small chunks
        # - Adds overlap
        return self.post_process_chunks(raw_chunks)
```

**Features**:
- Configurable `max_chunk_size`, `min_chunk_size`, `overlap`
- Automatic chunk validation
- Oversized chunk splitting with overlap
- Small chunk merging
- Line number tracking

## Testing

All common utilities have comprehensive unit tests:

```bash
# Test signature extraction
pytest tests/unit/parsers/test_signature_extractor.py

# Test complexity calculation
pytest tests/unit/parsers/test_complexity.py

# Test chunkers
pytest tests/unit/parsers/test_chunkers.py
```

## Contributing

When adding a new language parser:

1. Inherit from `SignatureExtractorMixin` for signature extraction
2. Use `ComplexityCalculator` for complexity metrics
3. Extend `AbstractChunker` for custom chunking logic
4. Add tests to verify the utilities work with your language
