"""Intelligent project structure analyzer.

Detects project type, modules, and source directories automatically.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Module:
    """Detected module."""

    path: Path
    type: str  # gradle, maven, npm, python
    sources: list[Path] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Project analysis result."""

    root: Path
    type: str  # simple, multi-module
    modules: list[Module] = field(default_factory=list)
    recommended_includes: list[str] = field(default_factory=list)
    recommended_excludes: list[str] = field(default_factory=list)


class ProjectAnalyzer:
    """Analyze project structure and recommend indexing patterns."""

    BUILD_FILES = {
        "gradle": ["build.gradle", "build.gradle.kts"],
        "maven": ["pom.xml"],
        "npm": ["package.json"],
        "python": ["pyproject.toml", "setup.py"],
    }

    SOURCE_INDICATORS = ["src", "lib", "pkg", "packages"]

    EXCLUDE_PATTERNS = [
        # Build artifacts
        "**/build/**",
        "**/dist/**",
        "**/target/**",
        "**/out/**",
        "**/.gradle/**",
        # Dependencies
        "**/node_modules/**",
        "**/__pycache__/**",
        "**/vendor/**",
        "**/.venv/**",
        "**/venv/**",
        # IDE/VCS
        "**/.git/**",
        "**/.idea/**",
        "**/.vscode/**",
        "**/.vs/**",
        # Test directories
        "**/test/**",
        "**/tests/**",
        "**/e2eTest/**",
        "**/integrationTest/**",
        "**/testFixtures/**",
        "**/__tests__/**",
        # Generated/Cache
        "**/.cache/**",
        "**/coverage/**",
        "**/.next/**",
        "**/.nuxt/**",
    ]

    def __init__(self, root: Path):
        self.root = root.resolve()

    def analyze(self, include_tests: bool = False) -> AnalysisResult:
        """Analyze project and return recommendations.

        Args:
            include_tests: Whether to include test directories

        Returns:
            Analysis result with recommended patterns
        """
        # Find modules
        modules = self._find_modules()

        if not modules:
            # Simple project
            return self._analyze_simple()

        # Multi-module project
        return self._analyze_multi_module(modules, include_tests)

    def _find_modules(self) -> list[Module]:
        """Find modules by build files."""
        modules = []
        seen_dirs = set()

        # Search up to depth 3
        for depth in range(1, 4):
            pattern = "/".join(["*"] * depth)

            for module_type, build_files in self.BUILD_FILES.items():
                for build_file in build_files:
                    for path in self.root.glob(f"{pattern}/{build_file}"):
                        module_dir = path.parent

                        # Skip if already processed
                        if module_dir in seen_dirs:
                            continue

                        # Skip build/dist directories
                        if any(
                            part in {"build", "dist", "node_modules", ".gradle", "target"}
                            for part in module_dir.parts
                        ):
                            continue

                        seen_dirs.add(module_dir)
                        sources = self._find_sources(module_dir)

                        if sources:
                            modules.append(
                                Module(
                                    path=module_dir,
                                    type=module_type,
                                    sources=sources,
                                )
                            )

        return modules

    def _find_sources(self, module_dir: Path) -> list[Path]:
        """Find actual source directories in a module.

        Args:
            module_dir: Module directory to search

        Returns:
            List of source directories
        """
        # Common patterns (ordered by specificity)
        patterns = [
            "src/main/kotlin",
            "src/main/java",
            "src/main/python",
            "src/main",
            "src/kotlin",
            "src/java",
            "src/python",
            "src",
            "lib",
            "pkg",
        ]

        for pattern in patterns:
            path = module_dir / pattern
            if path.is_dir() and not any("test" in part.lower() for part in path.parts):
                return [path]

        return []

    def _analyze_multi_module(self, modules: list[Module], include_tests: bool) -> AnalysisResult:
        """Analyze multi-module project.

        Args:
            modules: List of detected modules
            include_tests: Whether to include test directories

        Returns:
            Analysis result
        """
        includes = []

        # Add docs first (consistent ordering)
        if (self.root / "docs").is_dir():
            includes.append("docs/**")

        # Generate include patterns from actual sources
        for module in modules:
            for source in module.sources:
                rel_path = source.relative_to(self.root)
                includes.append(f"{rel_path}/**")

        # Excludes
        excludes = (
            [e for e in self.EXCLUDE_PATTERNS if "test" not in e.lower()]
            if include_tests
            else self.EXCLUDE_PATTERNS.copy()
        )

        return AnalysisResult(
            root=self.root,
            type="multi-module",
            modules=modules,
            recommended_includes=sorted(includes),
            recommended_excludes=excludes,
        )

    def _analyze_simple(self) -> AnalysisResult:
        """Analyze simple single-module project.

        Returns:
            Analysis result
        """
        includes = []

        # Add docs first (consistent ordering)
        if (self.root / "docs").is_dir():
            includes.append("docs/**")

        # Add common source directories
        for indicator in self.SOURCE_INDICATORS:
            if (self.root / indicator).is_dir():
                includes.append(f"{indicator}/**")

        # Fallback to everything if no sources found
        if not includes:
            includes = ["**"]

        return AnalysisResult(
            root=self.root,
            type="simple",
            modules=[],
            recommended_includes=includes,
            recommended_excludes=self.EXCLUDE_PATTERNS,
        )
