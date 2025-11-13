"""Code-specific query expansion from configuration file."""

import re
from pathlib import Path
from typing import Any

import logging

import yaml

logger = logging.getLogger(__name__)


class QueryExpander:
    """
    Expand search queries with code-specific terms.

    Expansion types:
    1. Case variants: CamelCase ↔ snake_case ↔ kebab-case
    2. Abbreviations: ctx → context, cfg → config
    3. Synonyms: function → method, class → type

    All rules loaded from query_expansion.yaml for flexibility.
    """

    def __init__(self, config_path: Path | None = None):
        """
        Initialize expander with configuration.

        Args:
            config_path: Path to query_expansion.yaml (defaults to package config)
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "query_expansion.yaml"

        self.config = self._load_config(config_path)
        self.abbreviations: dict[str, str] = self.config.get("abbreviations", {})
        self.synonyms: dict[str, list[str]] = self.config.get("synonyms", {})
        self.case_variants_enabled: bool = self.config.get("case_variants", {}).get("enabled", True)
        self.expansion_limit: int = self.config.get("expansion_limit", 5)
        self.min_term_length: int = self.config.get("min_term_length", 3)

    def _load_config(self, config_path: Path) -> dict[str, Any]:
        """Load expansion rules from YAML file."""
        try:
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning(f"Query expansion config not found: {config_path}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse query expansion config: {e}")
            return {}

    def expand(self, query: str) -> list[str]:
        """
        Expand query into multiple search terms.

        Args:
            query: Original search query

        Returns:
            List of expanded queries (includes original)

        Example:
            >>> expander = QueryExpander()
            >>> expander.expand("processOrder")
            ['processOrder', 'process_order', 'process-order', 'handleOrder']
        """
        if len(query.strip()) < self.min_term_length:
            return [query]

        expansions: set[str] = {query}  # Use set for deduplication

        # 1. Case variants
        if self.case_variants_enabled:
            expansions.update(self._expand_case(query))

        # 2. Abbreviation expansion
        for abbr, full in self.abbreviations.items():
            if abbr in query.lower():
                # Case-insensitive replacement
                pattern = re.compile(re.escape(abbr), re.IGNORECASE)
                expanded = pattern.sub(full, query)
                if expanded != query:
                    expansions.add(expanded)

        # 3. Synonym expansion
        for term, syns in self.synonyms.items():
            if term in query.lower():
                for syn in syns:
                    # Case-insensitive replacement
                    pattern = re.compile(re.escape(term), re.IGNORECASE)
                    expanded = pattern.sub(syn, query)
                    if expanded != query:
                        expansions.add(expanded)

        # Limit expansions to prevent noise
        result = list(expansions)[: self.expansion_limit]

        if len(result) > 1:
            logger.debug(f"Expanded '{query}' to {len(result)} terms")

        return result

    def _expand_case(self, text: str) -> list[str]:
        """
        Generate case variants.

        Args:
            text: Input text

        Returns:
            List of case variants

        Example:
            >>> self._expand_case("processOrder")
            ['process_order', 'process-order', 'ProcessOrder']
        """
        variants = []

        # CamelCase → snake_case
        # Insert underscore before capital letters
        snake = re.sub("([a-z0-9])([A-Z])", r"\1_\2", text)
        snake = snake.lower()
        if snake != text.lower():
            variants.append(snake)

        # CamelCase → kebab-case
        kebab = snake.replace("_", "-")
        if kebab != snake and kebab != text:
            variants.append(kebab)

        # snake_case → CamelCase
        if "_" in text:
            camel = "".join(word.capitalize() for word in text.split("_"))
            if camel != text:
                variants.append(camel)
            # Also add lower camel
            lower_camel = camel[0].lower() + camel[1:] if camel else ""
            if lower_camel and lower_camel != text:
                variants.append(lower_camel)

        # kebab-case → CamelCase
        if "-" in text:
            camel = "".join(word.capitalize() for word in text.split("-"))
            if camel != text:
                variants.append(camel)
            # Also add lower camel
            lower_camel = camel[0].lower() + camel[1:] if camel else ""
            if lower_camel and lower_camel != text:
                variants.append(lower_camel)

        return variants
