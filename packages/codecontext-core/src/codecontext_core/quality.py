"""Code score weighting for search ranking."""


def calculate_score_weight(
    token_count: int,
    unique_token_count: int,
    has_docstring: bool,
    has_qualified_name: bool,
) -> float:
    """Calculate score weight multiplier for code chunk.

    Returns:
        0.1-1.2 weight where:
        - < 10 tokens: 0.1-0.6 (low information)
        - 10-20 tokens: 0.5-1.0 (borderline)
        - >= 20 tokens: 1.0-1.2 (normal)
    """
    if token_count >= 20:
        base = 1.0
    elif token_count >= 10:
        base = 0.5 + (token_count - 10) / 20
    else:
        base = max(0.1, token_count / 10)

    bonus = 1.0
    if has_docstring:
        bonus += 0.15
    if has_qualified_name:
        bonus += 0.10

    quality = base * bonus

    if token_count >= 20:
        quality = min(quality, 1.2)

    return max(0.1, min(quality, 1.2))
