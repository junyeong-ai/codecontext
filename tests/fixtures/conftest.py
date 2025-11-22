"""Pytest fixtures for tests.

All fixtures are defined in separate modules and imported here
for automatic discovery by pytest.
"""

# Import all fixture modules to make their fixtures available
from tests.fixtures.codebase import *  # noqa: F401, F403
from tests.fixtures.documents import *  # noqa: F401, F403
from tests.fixtures.parsers import *  # noqa: F401, F403
from tests.fixtures.storage import *  # noqa: F401, F403
