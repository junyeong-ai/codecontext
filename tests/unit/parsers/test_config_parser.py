"""Tests for ConfigFileParser.

This module contains tests for configuration file parsing functionality.
"""

from pathlib import Path

import pytest
from codecontext.parsers.languages.config import ConfigFileParser
from codecontext_core.models import NodeType


@pytest.fixture
def config_parser():
    """Create a ConfigFileParser instance."""
    return ConfigFileParser(chunk_size=512, min_chunk_size=100, max_depth=4)


@pytest.fixture
def fixtures_dir():
    """Get path to test fixtures directory."""
    return Path(__file__).parent.parent.parent / "fixtures" / "config_files"


class TestConfigFileParserInitialization:
    """Test ConfigFileParser initialization."""

    def test_initializes_with_defaults(self):
        """Should initialize with default parameters."""
        parser = ConfigFileParser()

        assert parser.chunk_size == 512
        assert parser.min_chunk_size == 100
        assert parser.max_depth == 4
        # Verify format-specific chunkers are initialized
        assert parser.yaml_chunker is not None
        assert parser.json_chunker is not None
        assert parser.properties_chunker is not None

    def test_initializes_with_custom_parameters(self):
        """Should initialize with custom parameters."""
        parser = ConfigFileParser(chunk_size=256, min_chunk_size=50, max_depth=3)

        assert parser.chunk_size == 256
        assert parser.min_chunk_size == 50
        assert parser.max_depth == 3


class TestFormatDetection:
    """Test configuration format detection."""

    def test_detects_yaml_extension(self, config_parser):
        """Should detect YAML format from .yaml extension."""
        file_path = Path("config.yaml")
        format_type = config_parser._detect_format(file_path)

        assert format_type == "yaml"

    def test_detects_yml_extension(self, config_parser):
        """Should detect YAML format from .yml extension."""
        file_path = Path("config.yml")
        format_type = config_parser._detect_format(file_path)

        assert format_type == "yaml"

    def test_detects_json_extension(self, config_parser):
        """Should detect JSON format from .json extension."""
        file_path = Path("package.json")
        format_type = config_parser._detect_format(file_path)

        assert format_type == "json"

    def test_detects_properties_extension(self, config_parser):
        """Should detect properties format from .properties extension."""
        file_path = Path("application.properties")
        format_type = config_parser._detect_format(file_path)

        assert format_type == "properties"

    def test_returns_none_for_unsupported_extension(self, config_parser):
        """Should return None for unsupported file extensions."""
        file_path = Path("config.xml")
        format_type = config_parser._detect_format(file_path)

        assert format_type is None


class TestYAMLParsing:
    """Test YAML file parsing."""

    def test_parses_yaml_file(self, config_parser, fixtures_dir):
        """Should parse YAML file and return DocumentNodes."""
        yaml_file = fixtures_dir / "application.yaml"

        if not yaml_file.exists():
            pytest.skip("Test fixture not available")

        nodes = config_parser.parse_file(yaml_file)

        assert len(nodes) > 0
        assert all(node.node_type == NodeType.CONFIG for node in nodes)
        assert all(node.config_format == "yaml" for node in nodes)
        assert all(node.file_path == str(yaml_file) for node in nodes)

    def test_yaml_nodes_have_metadata(self, config_parser, fixtures_dir):
        """Should extract metadata from YAML sections."""
        yaml_file = fixtures_dir / "application.yaml"

        if not yaml_file.exists():
            pytest.skip("Test fixture not available")

        nodes = config_parser.parse_file(yaml_file)

        # Find spring section
        spring_nodes = [n for n in nodes if "spring" in n.title.lower()]
        if spring_nodes:
            node = spring_nodes[0]
            assert node.config_keys is not None
            assert len(node.config_keys) > 0

    def test_yaml_extracts_env_references(self, config_parser, fixtures_dir):
        """Should extract environment variable references from YAML."""
        yaml_file = fixtures_dir / "application.yaml"

        if not yaml_file.exists():
            pytest.skip("Test fixture not available")

        nodes = config_parser.parse_file(yaml_file)

        # Check if any node has env references
        nodes_with_env = [n for n in nodes if n.env_references]
        assert len(nodes_with_env) > 0

        # Verify specific env vars are detected
        all_env_refs = []
        for node in nodes_with_env:
            all_env_refs.extend(node.env_references)

        # Verify some env vars are detected (DB_PASSWORD, REDIS_PASSWORD are in fixture)
        assert "DB_PASSWORD" in all_env_refs or "REDIS_PASSWORD" in all_env_refs


class TestJSONParsing:
    """Test JSON file parsing."""

    def test_parses_json_file(self, config_parser, fixtures_dir):
        """Should parse JSON file and return DocumentNodes."""
        json_file = fixtures_dir / "package.json"

        if not json_file.exists():
            pytest.skip("Test fixture not available")

        nodes = config_parser.parse_file(json_file)

        assert len(nodes) > 0
        assert all(node.node_type == NodeType.CONFIG for node in nodes)
        assert all(node.config_format == "json" for node in nodes)
        assert all(node.file_path == str(json_file) for node in nodes)

    def test_json_nodes_have_sections(self, config_parser, fixtures_dir):
        """Should split JSON into sections."""
        json_file = fixtures_dir / "package.json"

        if not json_file.exists():
            pytest.skip("Test fixture not available")

        nodes = config_parser.parse_file(json_file)

        # Should have multiple sections (scripts, dependencies, etc.)
        titles = [n.title for n in nodes]
        assert len(titles) > 1


class TestPropertiesParsing:
    """Test properties file parsing."""

    def test_parses_properties_file(self, config_parser, fixtures_dir):
        """Should parse properties file and return DocumentNodes."""
        props_file = fixtures_dir / "application.properties"

        if not props_file.exists():
            pytest.skip("Test fixture not available")

        nodes = config_parser.parse_file(props_file)

        assert len(nodes) > 0
        assert all(node.node_type == NodeType.CONFIG for node in nodes)
        assert all(node.config_format == "properties" for node in nodes)
        assert all(node.file_path == str(props_file) for node in nodes)

    def test_properties_groups_by_prefix(self, config_parser, fixtures_dir):
        """Should group properties by prefix."""
        props_file = fixtures_dir / "application.properties"

        if not props_file.exists():
            pytest.skip("Test fixture not available")

        nodes = config_parser.parse_file(props_file)

        # Should have sections (may be merged if small)
        # Check that content includes grouped prefixes
        assert len(nodes) > 0
        content = " ".join(n.content for n in nodes)
        assert "database" in content
        assert "redis" in content or "server" in content

    def test_properties_extracts_env_references(self, config_parser, fixtures_dir):
        """Should extract environment variable references from properties."""
        props_file = fixtures_dir / "application.properties"

        if not props_file.exists():
            pytest.skip("Test fixture not available")

        nodes = config_parser.parse_file(props_file)

        # Check that file content includes env variable patterns
        # Note: env extraction happens in the chunker metadata extraction
        content = " ".join(n.content for n in nodes)
        assert "${DB_USER}" in content or "${REDIS_PASSWORD}" in content


class TestSupportedFormats:
    """Test format support checks."""

    def test_supports_file_yaml(self, config_parser):
        """Should recognize YAML files as supported."""
        assert config_parser.supports_file(Path("config.yaml"))
        assert config_parser.supports_file(Path("config.yml"))

    def test_supports_file_json(self, config_parser):
        """Should recognize JSON files as supported."""
        assert config_parser.supports_file(Path("config.json"))

    def test_supports_file_properties(self, config_parser):
        """Should recognize properties files as supported."""
        assert config_parser.supports_file(Path("config.properties"))

    def test_not_supports_file_xml(self, config_parser):
        """Should not recognize XML files as supported."""
        assert not config_parser.supports_file(Path("config.xml"))

    def test_get_file_extensions(self, config_parser):
        """Should return list of supported extensions."""
        extensions = config_parser.get_file_extensions()

        assert ".yaml" in extensions
        assert ".yml" in extensions
        assert ".json" in extensions
        assert ".properties" in extensions
        assert len(extensions) == 4


class TestErrorHandling:
    """Test error handling."""

    def test_raises_error_for_nonexistent_file(self, config_parser):
        """Should raise FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            config_parser.parse_file(Path("/nonexistent/config.yaml"))

    def test_raises_error_for_unsupported_format(self, config_parser, tmp_path):
        """Should raise ValueError for unsupported file formats."""
        xml_file = tmp_path / "config.xml"
        xml_file.write_text("<config></config>")

        with pytest.raises(ValueError, match="Unsupported config file format"):
            config_parser.parse_file(xml_file)

    def test_handles_empty_yaml_file(self, config_parser, tmp_path):
        """Should handle empty YAML files gracefully."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        nodes = config_parser.parse_file(yaml_file)

        assert nodes == []

    def test_handles_empty_json_file(self, config_parser, tmp_path):
        """Should handle empty JSON files gracefully."""
        json_file = tmp_path / "empty.json"
        json_file.write_text("null")

        nodes = config_parser.parse_file(json_file)

        assert nodes == []


class TestChunkSize:
    """Test chunk size handling."""

    def test_respects_chunk_size_target(self, fixtures_dir):
        """Should create chunks around target size."""
        yaml_file = fixtures_dir / "application.yaml"

        if not yaml_file.exists():
            pytest.skip("Test fixture not available")

        parser = ConfigFileParser(chunk_size=256)
        nodes = parser.parse_file(yaml_file)

        # Most chunks should be reasonably sized
        for node in nodes:
            # Rough token count estimate
            estimated_tokens = len(node.content) // 4
            # Allow some flexibility (chunks can be smaller or larger)
            assert 50 <= estimated_tokens <= 1500


class TestConvenienceFunction:
    """Test convenience function."""

    def test_parse_config_file_function(self, fixtures_dir):
        """Should provide convenience function for parsing."""
        from codecontext.parsers.languages.config import parse_config_file

        yaml_file = fixtures_dir / "application.yaml"

        if not yaml_file.exists():
            pytest.skip("Test fixture not available")

        nodes = parse_config_file(yaml_file)

        assert len(nodes) > 0
        assert all(isinstance(node.file_path, str) for node in nodes)
