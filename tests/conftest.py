"""Pytest configuration for tests.

With UV workspace editable installs, all packages are properly installed
and importable. No sys.path manipulation needed.
"""

import pytest


# Force anyio to use only asyncio backend (not trio)
@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# ParserFactory is now instance-based, so test isolation is automatic
# No global state to reset between tests
@pytest.fixture(autouse=True)
def reset_parser_factory():
    """ParserFactory test isolation (now automatic with instance-based design)."""
    yield  # Nothing to clean up - each test creates its own instance
