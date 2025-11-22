"""Type-based content expansions for improved semantic search."""

from codecontext_core.models.core import CodeObject, ObjectType


TYPE_KEYWORDS = {
    ObjectType.ENUM: ["definition", "constant", "values", "enumeration"],
    ObjectType.INTERFACE: ["contract", "protocol", "specification"],
    ObjectType.CLASS: ["type", "implementation"],
    ObjectType.FUNCTION: ["procedure", "routine"],
    ObjectType.METHOD: ["procedure", "routine"],
}


def expand_content(obj: CodeObject) -> str:
    """Add type-specific keywords to content for better discovery."""
    keywords = TYPE_KEYWORDS.get(obj.object_type)
    if not keywords:
        return obj.content

    return f"{obj.content} {' '.join(keywords)}"
