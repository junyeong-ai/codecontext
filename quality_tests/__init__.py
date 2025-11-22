"""
Quality Tests for CodeContext

E2E quality validation tests for indexing performance and search quality.
Tests use CLI commands (codecontext index, codecontext search) via CliRunner.

Run: pytest quality_tests/ -v
Execution time: 5-10 minutes
Requirements:
- Qdrant server running (docker compose -f docker-compose.qdrant.yml up -d)
- E-commerce sample dataset at tests/fixtures/ecommerce_samples/
"""
