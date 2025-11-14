"""Pytest configuration for tests."""

import pytest

# Register fixture modules as pytest plugins
# NOTE: These modules must be registered here to make fixtures available
pytest_plugins = [
    "tests.fixtures.storage",
    "tests.fixtures.parsers",
    "tests.fixtures.documents",
    "tests.fixtures.codebase",
]


# Force anyio to use only asyncio backend (not trio)
@pytest.fixture
def anyio_backend():
    return "asyncio"


# ParserFactory is now instance-based, so test isolation is automatic
# No global state to reset between tests
@pytest.fixture(autouse=True)
def reset_parser_factory():
    """ParserFactory test isolation (now automatic with instance-based design)."""
    yield  # Nothing to clean up - each test creates its own instance
