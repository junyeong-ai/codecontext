"""Natural Language description generator for code objects (inline, zero re-parsing)."""


class NLGeneratorMixin:
    """
    Mixin providing natural language description generation for code parsers.

    This mixin generates NL descriptions inline during AST traversal,
    eliminating the need for re-parsing (reduces overhead from +135% to +20%).

    Usage:
        class PythonParser(BaseCodeParser, NLGeneratorMixin):
            def _extract_function(self, node: Node, ...):
                info = extract_function_info(node)
                return CodeObject(...)
    """

    def _generate_function_nl(
        self,
        name: str,
        params: list[str] | None = None,
        return_type: str | None = None,
        is_async: bool = False,
        is_constructor: bool = False,
        docstring: str | None = None,
        relative_path: str | None = None,
        parent_context: str | None = None,
        content_preview: str | None = None,
    ) -> str:
        """
        Generate context-rich natural language description for a function/method.

        Args:
            name: Function name
            params: List of parameter names
            return_type: Return type annotation
            is_async: Whether function is async
            is_constructor: Whether this is a constructor
            docstring: Existing docstring (if any)
            relative_path: File path for context
            parent_context: Parent class/module name
            content_preview: First few lines of code for context

        Returns:
            Natural language description with context
        """
        parts = []

        # Context: file location
        if relative_path:
            parts.append(f"Located in {relative_path}.")

        # Context: parent class/module
        if parent_context:
            parts.append(f"Part of {parent_context}.")

        # Primary description from docstring or template
        if docstring:
            first_sentence = docstring.split(".")[0].strip()
            if first_sentence:
                parts.append(f"{first_sentence}.")
        else:
            # Template-based generation
            if is_constructor:
                if params and len(params) > 0:
                    param_desc = self._format_params(params)
                    parts.append(f"Constructor that initializes with {param_desc}.")
                else:
                    parts.append("Constructor that initializes the object.")
            elif is_async:
                if params and len(params) > 0:
                    param_desc = self._format_params(params)
                    if return_type:
                        parts.append(
                            f"Async function '{name}' that takes {param_desc} and returns {return_type}."
                        )
                    else:
                        parts.append(f"Async function '{name}' that takes {param_desc}.")
                else:
                    parts.append(f"Async function '{name}'.")
            else:
                # Regular function
                if params and len(params) > 0:
                    param_desc = self._format_params(params)
                    if return_type:
                        parts.append(
                            f"Function '{name}' that takes {param_desc} and returns {return_type}."
                        )
                    else:
                        parts.append(f"Function '{name}' that takes {param_desc}.")
                elif return_type:
                    parts.append(f"Function '{name}' that returns {return_type}.")
                else:
                    parts.append(f"Function '{name}'.")

        # Context: code preview (first 2 lines)
        if content_preview:
            preview_lines = content_preview.strip().split("\n")[:2]
            if preview_lines:
                preview_text = " ".join(line.strip() for line in preview_lines if line.strip())
                if preview_text and len(preview_text) < 150:
                    parts.append(f"Implementation: {preview_text}")

        return " ".join(parts)

    def _generate_class_nl(
        self,
        name: str,
        base_classes: list[str] | None = None,
        methods_count: int = 0,
        is_abstract: bool = False,
        docstring: str | None = None,
        relative_path: str | None = None,
        parent_context: str | None = None,
        content_preview: str | None = None,
    ) -> str:
        """
        Generate context-rich natural language description for a class.

        Args:
            name: Class name
            base_classes: List of base class names
            methods_count: Number of methods
            is_abstract: Whether class is abstract
            docstring: Existing docstring (if any)
            relative_path: File path for context
            parent_context: Parent module name
            content_preview: First few lines of code for context

        Returns:
            Natural language description with context
        """
        parts = []

        # Context: file location
        if relative_path:
            parts.append(f"Located in {relative_path}.")

        # Context: parent module
        if parent_context:
            parts.append(f"Part of module {parent_context}.")

        # Primary description from docstring or template
        if docstring:
            first_sentence = docstring.split(".")[0].strip()
            if first_sentence:
                parts.append(f"{first_sentence}.")
        else:
            # Template-based generation
            class_parts = []

            # Abstract prefix
            if is_abstract:
                class_parts.append("Abstract class")
            else:
                class_parts.append("Class")

            # Class name
            class_parts.append(f"'{name}'")

            # Inheritance info
            if base_classes and len(base_classes) > 0:
                if len(base_classes) == 1:
                    class_parts.append(f"extending {base_classes[0]}")
                else:
                    bases_str = ", ".join(base_classes[:-1]) + f" and {base_classes[-1]}"
                    class_parts.append(f"extending {bases_str}")

            # Methods count (if significant)
            if methods_count > 0:
                class_parts.append(
                    f"with {methods_count} method{'s' if methods_count != 1 else ''}"
                )

            parts.append(" ".join(class_parts) + ".")

        # Context: code preview (first 2 lines)
        if content_preview:
            preview_lines = content_preview.strip().split("\n")[:2]
            if preview_lines:
                preview_text = " ".join(line.strip() for line in preview_lines if line.strip())
                if preview_text and len(preview_text) < 150:
                    parts.append(f"Implementation: {preview_text}")

        return " ".join(parts)

    def _generate_interface_nl(
        self,
        name: str,
        base_interfaces: list[str] | None = None,
        methods_count: int = 0,
        docstring: str | None = None,
        relative_path: str | None = None,
        parent_context: str | None = None,
        content_preview: str | None = None,
    ) -> str:
        """
        Generate context-rich natural language description for an interface.

        Args:
            name: Interface name
            base_interfaces: List of base interface names
            methods_count: Number of methods
            docstring: Existing docstring (if any)
            relative_path: File path for context
            parent_context: Parent module name
            content_preview: First few lines of code for context

        Returns:
            Natural language description with context
        """
        parts = []

        # Context: file location
        if relative_path:
            parts.append(f"Located in {relative_path}.")

        # Context: parent module
        if parent_context:
            parts.append(f"Part of module {parent_context}.")

        # Primary description from docstring or template
        if docstring:
            first_sentence = docstring.split(".")[0].strip()
            if first_sentence:
                parts.append(f"{first_sentence}.")
        else:
            # Template-based generation
            interface_parts = [f"Interface '{name}'"]

            if base_interfaces and len(base_interfaces) > 0:
                if len(base_interfaces) == 1:
                    interface_parts.append(f"extending {base_interfaces[0]}")
                else:
                    bases_str = ", ".join(base_interfaces[:-1]) + f" and {base_interfaces[-1]}"
                    interface_parts.append(f"extending {bases_str}")

            if methods_count > 0:
                interface_parts.append(
                    f"defining {methods_count} method{'s' if methods_count != 1 else ''}"
                )

            parts.append(" ".join(interface_parts) + ".")

        # Context: code preview (first 2 lines)
        if content_preview:
            preview_lines = content_preview.strip().split("\n")[:2]
            if preview_lines:
                preview_text = " ".join(line.strip() for line in preview_lines if line.strip())
                if preview_text and len(preview_text) < 150:
                    parts.append(f"Implementation: {preview_text}")

        return " ".join(parts)

    def _generate_enum_nl(
        self,
        name: str,
        values_count: int = 0,
        docstring: str | None = None,
        relative_path: str | None = None,
        parent_context: str | None = None,
        content_preview: str | None = None,
    ) -> str:
        """
        Generate context-rich natural language description for an enum.

        Args:
            name: Enum name
            values_count: Number of enum values
            docstring: Existing docstring (if any)
            relative_path: File path for context
            parent_context: Parent module name
            content_preview: First few lines of code for context

        Returns:
            Natural language description with context
        """
        parts = []

        # Context: file location
        if relative_path:
            parts.append(f"Located in {relative_path}.")

        # Context: parent module
        if parent_context:
            parts.append(f"Part of module {parent_context}.")

        # Primary description from docstring or template
        if docstring:
            first_sentence = docstring.split(".")[0].strip()
            if first_sentence:
                parts.append(f"{first_sentence}.")
        else:
            # Template-based generation
            if values_count > 0:
                parts.append(
                    f"Enum '{name}' with {values_count} value{'s' if values_count != 1 else ''}."
                )
            else:
                parts.append(f"Enum '{name}'.")

        # Context: code preview (first 2 lines)
        if content_preview:
            preview_lines = content_preview.strip().split("\n")[:2]
            if preview_lines:
                preview_text = " ".join(line.strip() for line in preview_lines if line.strip())
                if preview_text and len(preview_text) < 150:
                    parts.append(f"Values: {preview_text}")

        return " ".join(parts)

    def _format_params(self, params: list[str]) -> str:
        """
        Format parameter list[Any] for natural language.

        Args:
            params: List of parameter names

        Returns:
            Formatted parameter description
        """
        if not params:
            return "no parameters"

        if len(params) == 1:
            return f"parameter '{params[0]}'"

        if len(params) == 2:
            return f"parameters '{params[0]}' and '{params[1]}'"

        # 3+ parameters
        param_str = ", ".join(f"'{p}'" for p in params[:-1])
        return f"parameters {param_str} and '{params[-1]}'"

    def _extract_docstring_summary(self, docstring: str | None) -> str | None:
        """
        Extract first sentence from docstring.

        Args:
            docstring: Docstring content

        Returns:
            First sentence or None
        """
        if not docstring:
            return None

        # Clean up docstring
        cleaned = docstring.strip()
        if not cleaned:
            return None

        # Extract first sentence
        first_sentence = cleaned.split(".")[0].strip()
        if first_sentence:
            return f"{first_sentence}."

        return None
