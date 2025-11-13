"""Chunk optimization utilities for configuration chunkers."""

from typing import Any


def optimize_chunks(
    chunks: list[dict[str, Any]], min_chunk_size: int, max_chunk_size: int, token_to_char_ratio: int
) -> list[dict[str, Any]]:
    """Merge small chunks to meet minimum chunk size.

    Args:
        chunks: List of chunk dictionaries
        min_chunk_size: Minimum chunk size threshold
        max_chunk_size: Maximum chunk size threshold
        token_to_char_ratio: Token to character ratio

    Returns:
        Optimized chunk list
    """
    if not chunks:
        return []

    optimized = []
    buffer = []
    buffer_size = 0

    for chunk in chunks:
        size = chunk["size_tokens"]

        if size < min_chunk_size:
            # Small chunk: add to buffer
            buffer.append(chunk)
            buffer_size += size

            # Flush buffer if it reaches minimum size
            if buffer_size >= min_chunk_size:
                optimized.append(merge_chunks(buffer, token_to_char_ratio))
                buffer = []
                buffer_size = 0
        else:
            # Normal sized chunk
            if buffer:
                # Flush buffer first
                optimized.append(merge_chunks(buffer, token_to_char_ratio))
                buffer = []
                buffer_size = 0
            optimized.append(chunk)

    # Flush remaining buffer
    if buffer:
        if optimized and optimized[-1]["size_tokens"] + buffer_size < max_chunk_size:
            # Merge with last chunk if possible
            last = optimized.pop()
            buffer.insert(0, last)
        optimized.append(merge_chunks(buffer, token_to_char_ratio))

    return optimized


def merge_chunks(chunks: list[dict[str, Any]], token_to_char_ratio: int) -> dict[str, Any]:
    """Merge multiple chunks into one.

    Args:
        chunks: List of chunks to merge
        token_to_char_ratio: Token to character ratio

    Returns:
        Merged chunk dictionary
    """
    if len(chunks) == 1:
        return chunks[0]

    # Combine content
    merged_content = "\n\n".join(c["content"] for c in chunks)

    # Combine keys
    all_keys = []
    for c in chunks:
        if "all_keys" in c.get("metadata", {}):
            all_keys.extend(c["metadata"]["all_keys"])

    # Combine env refs
    all_env_refs = []
    for c in chunks:
        env_refs = c.get("metadata", {}).get("env_references")
        if env_refs:
            all_env_refs.extend(env_refs)

    # Use first chunk as base
    merged = chunks[0].copy()
    merged.update(
        {
            "content": merged_content,
            "size_tokens": len(merged_content) // token_to_char_ratio,
            "path": " + ".join(str(c["path"]) for c in chunks),
            "key": " + ".join(str(c["key"]) for c in chunks),
            "metadata": {
                "all_keys": list(set(all_keys)),
                "env_references": list(set(all_env_refs)) if all_env_refs else None,
                "merged": True,
                "merged_count": len(chunks),
            },
        }
    )

    return merged
