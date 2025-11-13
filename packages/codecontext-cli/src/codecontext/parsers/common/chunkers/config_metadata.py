"""Metadata extraction utilities for configuration chunkers."""

import json
import re
from typing import Any


def flatten_keys(data: dict[str, Any], prefix: str = "") -> list[str]:
    """Flatten nested dictionary keys.

    Args:
        data: Dictionary to flatten
        prefix: Current key prefix

    Returns:
        List of flattened key paths
    """
    keys = []
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        keys.append(full_key)

        if isinstance(value, dict):
            keys.extend(flatten_keys(value, full_key))

    return keys


def calculate_depth(data: object) -> int:
    """Calculate nesting depth of data structure.

    Args:
        data: Data to measure

    Returns:
        Nesting depth (1 for flat, 2+ for nested)
    """
    if not isinstance(data, dict):
        return 1

    if not data:
        return 1

    max_child_depth = 0
    for value in data.values():
        child_depth = calculate_depth(value)
        max_child_depth = max(max_child_depth, child_depth)

    return 1 + max_child_depth


def find_env_references(value: object) -> list[str]:
    """Find environment variable references like ${VAR_NAME}.

    Args:
        value: Value to search

    Returns:
        List of environment variable names
    """
    # Convert to string for pattern matching
    value_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)

    # Pattern: ${VAR_NAME} or $VAR_NAME
    pattern = r"\$\{([A-Z_][A-Z0-9_]*)\}|\$([A-Z_][A-Z0-9_]*)"
    matches = re.findall(pattern, value_str)

    # Flatten tuples from findall
    env_vars = []
    for match in matches:
        env_vars.extend([m for m in match if m])

    return list(set(env_vars))  # Remove duplicates


def extract_config_metadata(key: str, value: object) -> dict[str, Any]:
    """Extract metadata from configuration section.

    Args:
        key: Section key
        value: Section value

    Returns:
        Metadata dictionary
    """
    metadata: dict[str, Any] = {}

    # All keys in this section
    if isinstance(value, dict):
        metadata["all_keys"] = flatten_keys(value, key)
        metadata["depth"] = calculate_depth(value)
    else:
        metadata["all_keys"] = [key]
        metadata["depth"] = 1

    # Environment variable references
    env_refs = find_env_references(value)
    if env_refs:
        metadata["env_references"] = env_refs

    return metadata
