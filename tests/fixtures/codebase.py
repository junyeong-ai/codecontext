"""Codebase-related test fixtures."""

import pytest


@pytest.fixture(scope="session")
def sample_codebase_100_files(tmp_path_factory):
    """Create a sample codebase with 100 Python files."""
    root = tmp_path_factory.mktemp("sample_codebase_100")
    for i in range(100):
        file_path = root / f"module_{i}.py"
        file_path.write_text(
            f"""
# Module {i}

def func_{i}():
    return {i}

class Class{i}:
    def method(self):
        return {i}
"""
        )
    return root
