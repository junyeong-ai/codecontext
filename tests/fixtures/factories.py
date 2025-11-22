"""Factory methods for creating common test scenarios.

This module provides convenient factory functions for creating frequently-used
test data patterns, further reducing boilerplate in tests.
"""

import hashlib

from codecontext_core.models import CodeObject, Language, ObjectType, Relationship

from tests.fixtures.builders import CodeObjectBuilder, RelationshipBuilder

# Direct factory method for creating CodeObject with all required fields


def create_code_object(
    name: str,
    file_path: str,
    relative_path: str,
    object_type: ObjectType,
    language: Language = Language.PYTHON,
    content: str = "def example(): pass",
    start_line: int = 1,
    end_line: int = 1,
    parent_deterministic_id: str | None = None,
    signature: str | None = None,
) -> CodeObject:
    """Create CodeObject with all required fields (bypass builder).

    This is a direct factory method for creating CodeObjects with the new API,
    useful when you need fine-grained control over all fields.

    Args:
        name: Object name (e.g., "my_function")
        file_path: Absolute file path (e.g., "/repo/src/module.py")
        relative_path: Relative file path (e.g., "src/module.py")
        object_type: ObjectType enum (CLASS, METHOD, FUNCTION, etc.)
        language: Language enum (default: PYTHON)
        content: Full source code
        start_line: Starting line number (1-indexed)
        end_line: Ending line number
        parent_deterministic_id: Optional parent object deterministic ID
        signature: Optional function/method signature

    Returns:
        CodeObject with all required fields populated

    Example:
        >>> obj = create_code_object(
        ...     name="calculate_total",
        ...     file_path="/repo/src/billing.py",
        ...     relative_path="src/billing.py",
        ...     object_type=ObjectType.FUNCTION,
        ...     content="def calculate_total(items): return sum(items)",
        ... )
    """
    checksum = hashlib.sha256(content.encode()).hexdigest()
    return CodeObject(
        name=name,
        file_path=file_path,
        relative_path=relative_path,
        object_type=object_type,
        language=language,
        start_line=start_line,
        end_line=end_line,
        content=content,
        checksum=checksum,
        parent_deterministic_id=parent_deterministic_id,
        signature=signature,
    )


# Quick factory methods for individual objects


def create_class(name: str, **kwargs) -> CodeObject:
    """Create a test class with minimal configuration.

    Args:
        name: Class name
        **kwargs: Additional builder configuration (file_path, language, etc.)

    Returns:
        CodeObject configured as a class

    Example:
        >>> user_class = create_class("User")
        >>> repo_class = create_class("UserRepository", file_path="repo.py")
    """
    builder = CodeObjectBuilder().as_class(name)

    # Apply optional kwargs
    if "file_path" in kwargs:
        builder = builder.in_file(kwargs["file_path"])
    if "language" in kwargs:
        builder = builder.with_language(kwargs["language"])
    if "content" in kwargs:
        builder = builder.with_content(kwargs["content"])
    if "parent_id" in kwargs:
        builder = builder.with_parent(kwargs["parent_id"])
    if "start_line" in kwargs and "end_line" in kwargs:
        builder = builder.at_lines(kwargs["start_line"], kwargs["end_line"])

    return builder.build()


def create_interface(name: str, **kwargs) -> CodeObject:
    """Create a test interface with minimal configuration.

    Args:
        name: Interface name
        **kwargs: Additional builder configuration

    Returns:
        CodeObject configured as an interface
    """
    builder = CodeObjectBuilder().as_interface(name)

    if "file_path" in kwargs:
        builder = builder.in_file(kwargs["file_path"])
    if "language" in kwargs:
        builder = builder.with_language(kwargs["language"])
    if "content" in kwargs:
        builder = builder.with_content(kwargs["content"])

    return builder.build()


def create_method(name: str, parent_id=None, **kwargs) -> CodeObject:
    """Create a test method with minimal configuration.

    Args:
        name: Method name
        parent_id: Optional parent class/interface ID
        **kwargs: Additional builder configuration

    Returns:
        CodeObject configured as a method

    Example:
        >>> login_method = create_method("login", parent_id=user_class.id)
    """
    builder = CodeObjectBuilder().as_method(name, parent_id)

    if "file_path" in kwargs:
        builder = builder.in_file(kwargs["file_path"])
    if "language" in kwargs:
        builder = builder.with_language(kwargs["language"])
    if "content" in kwargs:
        builder = builder.with_content(kwargs["content"])
    if "start_line" in kwargs and "end_line" in kwargs:
        builder = builder.at_lines(kwargs["start_line"], kwargs["end_line"])

    return builder.build()


def create_function(name: str, **kwargs) -> CodeObject:
    """Create a test function with minimal configuration.

    Args:
        name: Function name
        **kwargs: Additional builder configuration

    Returns:
        CodeObject configured as a function

    Example:
        >>> get_user = create_function("get_user")
    """
    builder = CodeObjectBuilder().as_function(name)

    if "file_path" in kwargs:
        builder = builder.in_file(kwargs["file_path"])
    if "language" in kwargs:
        builder = builder.with_language(kwargs["language"])
    if "content" in kwargs:
        builder = builder.with_content(kwargs["content"])
    if "parent_id" in kwargs:
        builder = builder.with_parent(kwargs["parent_id"])

    return builder.build()


# Scenario factories for common test patterns


def create_inheritance_scenario(
    base_name: str = "BaseRepository", child_name: str = "UserRepository", **kwargs
) -> tuple[CodeObject, CodeObject]:
    """Create a complete inheritance test scenario.

    Args:
        base_name: Name of the base class
        child_name: Name of the child class
        **kwargs: Additional configuration

    Returns:
        Tuple of (base_class, child_class)

    Example:
        >>> base, child = create_inheritance_scenario()
        >>> # Child's content will include inheritance from base
    """
    language = kwargs.get("language", Language.PYTHON)

    base = create_class(base_name, language=language)
    child = (
        CodeObjectBuilder()
        .as_class(child_name)
        .with_language(language)
        .with_content(f"class {child_name}({base_name}): pass")
        .build()
    )

    return base, child


def create_containment_scenario(
    class_name: str = "User", method_name: str = "login", **kwargs
) -> tuple[CodeObject, CodeObject]:
    """Create a complete containment test scenario (class with method).

    Args:
        class_name: Name of the parent class
        method_name: Name of the method
        **kwargs: Additional configuration

    Returns:
        Tuple of (parent_class, method)

    Example:
        >>> parent, method = create_containment_scenario()
        >>> # Method has parent_id set to parent.id
    """
    language = kwargs.get("language", Language.PYTHON)
    file_path = kwargs.get("file_path", "test.py")

    parent_class = create_class(class_name, language=language, file_path=file_path)
    method = create_method(
        method_name,
        parent_id=parent_class.id,
        language=language,
        file_path=file_path,
    )

    return parent_class, method


def create_multi_level_hierarchy(
    class_name: str = "DataProcessor",
    method_name: str = "process",
    nested_fn_name: str = "validate",
    **kwargs,
) -> tuple[CodeObject, CodeObject, CodeObject]:
    """Create a multi-level hierarchy (class > method > nested function).

    Args:
        class_name: Name of the parent class
        method_name: Name of the method
        nested_fn_name: Name of the nested function
        **kwargs: Additional configuration

    Returns:
        Tuple of (class_obj, method_obj, nested_fn_obj)

    Example:
        >>> cls, method, nested = create_multi_level_hierarchy()
        >>> # nested.parent_id == method.id
        >>> # method.parent_id == cls.id
    """
    language = kwargs.get("language", Language.PYTHON)
    file_path = kwargs.get("file_path", "processor.py")

    class_obj = create_class(
        class_name,
        language=language,
        file_path=file_path,
        start_line=1,
        end_line=15,
    )

    method_obj = create_method(
        method_name,
        parent_id=class_obj.id,
        language=language,
        file_path=file_path,
        start_line=2,
        end_line=10,
    )

    nested_fn_obj = create_function(
        nested_fn_name,
        parent_id=method_obj.id,
        language=language,
        file_path=file_path,
    )

    return class_obj, method_obj, nested_fn_obj


def create_multiple_inheritance_scenario(
    base1_name: str = "Serializable",
    base2_name: str = "Cacheable",
    child_name: str = "UserModel",
    **kwargs,
) -> tuple[CodeObject, CodeObject, CodeObject]:
    """Create a multiple inheritance scenario.

    Args:
        base1_name: Name of first base class
        base2_name: Name of second base class
        child_name: Name of child class
        **kwargs: Additional configuration

    Returns:
        Tuple of (base1, base2, child)

    Example:
        >>> base1, base2, child = create_multiple_inheritance_scenario()
        >>> # Child inherits from both base1 and base2
    """
    language = kwargs.get("language", Language.PYTHON)

    base1 = create_class(base1_name, language=language, file_path="interfaces.py")
    base2 = create_class(base2_name, language=language, file_path="interfaces.py")
    child = (
        CodeObjectBuilder()
        .as_class(child_name)
        .with_language(language)
        .with_content(f"class {child_name}({base1_name}, {base2_name}): pass")
        .in_file("models.py")
        .build()
    )

    return base1, base2, child


def create_call_graph_scenario(
    caller_name: str = "create_user", callee_name: str = "validate_email", **kwargs
) -> tuple[CodeObject, CodeObject]:
    """Create a function call scenario.

    Args:
        caller_name: Name of the calling function
        callee_name: Name of the called function
        **kwargs: Additional configuration

    Returns:
        Tuple of (caller, callee)

    Example:
        >>> caller, callee = create_call_graph_scenario()
        >>> # Caller's content includes a call to callee
    """
    language = kwargs.get("language", Language.PYTHON)

    callee = create_function(callee_name, language=language)
    caller = (
        CodeObjectBuilder()
        .as_function(caller_name)
        .with_language(language)
        .with_content(f"def {caller_name}():\n    {callee_name}()")
        .build()
    )

    return caller, callee


# Relationship factories


def create_contains_relationship(parent_id, child_id) -> Relationship:
    """Create a CONTAINS relationship.

    Args:
        parent_id: ID of parent object
        child_id: ID of child object

    Returns:
        CONTAINS relationship with confidence 1.0
    """
    return RelationshipBuilder().contains(parent_id, child_id).build()


def create_references_relationship(source_id, target_id, confidence: float = 0.8) -> Relationship:
    """Create a REFERENCES relationship (inheritance).

    Args:
        source_id: ID of source (child) object
        target_id: ID of target (parent) object
        confidence: Confidence score (default: 0.8)

    Returns:
        REFERENCES relationship
    """
    return RelationshipBuilder().references(source_id, target_id, confidence).build()


def create_calls_relationship(caller_id, callee_id, confidence: float = 0.6) -> Relationship:
    """Create a CALLS relationship.

    Args:
        caller_id: ID of calling function/method
        callee_id: ID of called function/method
        confidence: Confidence score (default: 0.6)

    Returns:
        CALLS relationship
    """
    return RelationshipBuilder().calls(caller_id, callee_id, confidence).build()
