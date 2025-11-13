"""Unit tests for TypeScript parser React component extraction.

Tests the TypeScript parser's ability to extract React component patterns,
specifically arrow function components assigned to variables.
"""

from pathlib import Path

import pytest
from codecontext.parsers.languages.typescript import TypeScriptParser
from codecontext_core.models import ObjectType


class TestTypeScriptReactComponentExtraction:
    """Test React component extraction from TypeScript code."""

    @pytest.fixture
    def parser(self):
        """Create TypeScriptParser instance."""
        return TypeScriptParser()

    def test_parse_arrow_function_component_basic(self, parser):
        """Verify basic arrow function components are extracted.

        This tests the simplest React component pattern:
        export const ComponentName = () => { return <JSX />; };
        """
        code = """
export const LoadingIndicator = () => {
  return <Loading />;
};
"""
        objects = parser.extract_code_objects(Path("LoadingIndicator.tsx"), code)

        assert len(objects) == 1, f"Expected 1 object, got {len(objects)}"
        assert objects[0].name == "LoadingIndicator"
        assert objects[0].object_type == ObjectType.FUNCTION
        assert "const LoadingIndicator" in objects[0].signature
        assert objects[0].language == "typescript"

    def test_parse_arrow_function_component_with_props(self, parser):
        """Verify arrow function components with typed props are extracted.

        This tests React component pattern with TypeScript props:
        export const Component = (props: Props) => { ... };
        """
        code = """
interface Props {
  value: string;
  onChange: (value: string) => void;
}

export const OrganizationSelector = (props: Props) => {
  const { value, onChange } = props;
  return <Combobox value={value} onChange={onChange} />;
};
"""
        objects = parser.extract_code_objects(Path("OrganizationSelector.tsx"), code)

        # Should extract: interface Props + OrganizationSelector function
        assert len(objects) >= 1, f"Expected at least 1 function, got {len(objects)} total objects"

        # Find the component function
        component = next((obj for obj in objects if obj.name == "OrganizationSelector"), None)
        assert component is not None, "OrganizationSelector component not found"
        assert component.object_type == ObjectType.FUNCTION
        assert "const OrganizationSelector" in component.signature
        assert "(props: Props)" in component.signature or "props" in component.signature

    def test_parse_nested_arrow_function_excluded(self, parser):
        """Verify nested arrow functions inside components are NOT extracted.

        This tests that we only extract top-level arrow function components,
        not arrow functions defined inside other functions or class methods.
        """
        code = """
export const ParentComponent = () => {
  // This nested arrow function should NOT be extracted
  const handleClick = () => {
    console.log("clicked");
  };

  return <button onClick={handleClick}>Click</button>;
};
"""
        objects = parser.extract_code_objects(Path("ParentComponent.tsx"), code)

        # Should only extract ParentComponent, not handleClick
        assert len(objects) == 1, f"Expected 1 object (ParentComponent only), got {len(objects)}"
        assert objects[0].name == "ParentComponent"
        assert objects[0].object_type == ObjectType.FUNCTION

        # Verify handleClick was NOT extracted
        names = [obj.name for obj in objects]
        assert "handleClick" not in names, "Nested arrow function should not be extracted"

    def test_parse_const_assignment_without_export(self, parser):
        """Verify arrow function components without export are also extracted.

        Tests: const ComponentName = () => { ... };
        """
        code = """
const LocalComponent = () => {
  return <div>Local</div>;
};
"""
        objects = parser.extract_code_objects(Path("LocalComponent.tsx"), code)

        assert len(objects) == 1
        assert objects[0].name == "LocalComponent"
        assert objects[0].object_type == ObjectType.FUNCTION
        assert "const LocalComponent" in objects[0].signature

    def test_parse_multiple_react_components(self, parser):
        """Verify multiple React components in same file are all extracted."""
        code = """
export const FirstComponent = () => {
  return <div>First</div>;
};

export const SecondComponent = () => {
  return <div>Second</div>;
};

const ThirdComponent = () => {
  return <div>Third</div>;
};
"""
        objects = parser.extract_code_objects(Path("Components.tsx"), code)

        assert len(objects) == 3, f"Expected 3 components, got {len(objects)}"
        names = [obj.name for obj in objects]
        assert "FirstComponent" in names
        assert "SecondComponent" in names
        assert "ThirdComponent" in names

        # All should be FUNCTION type
        for obj in objects:
            assert obj.object_type == ObjectType.FUNCTION

    def test_parse_arrow_function_with_return_type(self, parser):
        """Verify arrow function with explicit return type is extracted."""
        code = """
export const TypedComponent = (): JSX.Element => {
  return <div>Typed</div>;
};
"""
        objects = parser.extract_code_objects(Path("TypedComponent.tsx"), code)

        assert len(objects) == 1
        assert objects[0].name == "TypedComponent"
        assert objects[0].object_type == ObjectType.FUNCTION
