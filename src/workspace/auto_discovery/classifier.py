"""
Project Type Classifier

Classifies projects into types (web_frontend, api_server, etc.) using heuristic rules.
Detects frameworks, computes confidence scores, and suggests intelligent defaults.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .models import DiscoveredProject, FrameworkSignal, ProjectType


class TypeClassifier:
    """
    Classifies project types using heuristics and framework detection.

    Analyzes project structure, configuration files, and code patterns
    to determine project type with confidence scores.
    """

    # Framework detection patterns
    FRAMEWORK_PATTERNS: Dict[str, Dict[str, any]] = {
        # JavaScript/TypeScript Frameworks
        "next.js": {
            "files": ["next.config.js", "next.config.mjs", "next.config.ts"],
            "directories": ["pages", "app"],
            "package_deps": ["next"],
            "type": ProjectType.WEB_FRONTEND,
        },
        "react": {
            "files": [],
            "directories": [],
            "package_deps": ["react"],
            "type": ProjectType.WEB_FRONTEND,
        },
        "vue": {
            "files": ["vue.config.js"],
            "package_deps": ["vue"],
            "type": ProjectType.WEB_FRONTEND,
        },
        "angular": {
            "files": ["angular.json"],
            "package_deps": ["@angular/core"],
            "type": ProjectType.WEB_FRONTEND,
        },
        "svelte": {
            "files": ["svelte.config.js"],
            "package_deps": ["svelte"],
            "type": ProjectType.WEB_FRONTEND,
        },
        "express": {
            "package_deps": ["express"],
            "type": ProjectType.API_SERVER,
        },
        "nestjs": {
            "package_deps": ["@nestjs/core"],
            "type": ProjectType.API_SERVER,
        },
        # Python Frameworks
        "fastapi": {
            "code_patterns": [r"from\s+fastapi", r"FastAPI\("],
            "package_deps": ["fastapi"],
            "type": ProjectType.API_SERVER,
        },
        "django": {
            "files": ["manage.py"],
            "code_patterns": [r"from\s+django", r"django\."],
            "package_deps": ["django"],
            "type": ProjectType.API_SERVER,
        },
        "flask": {
            "code_patterns": [r"from\s+flask", r"Flask\("],
            "package_deps": ["flask"],
            "type": ProjectType.API_SERVER,
        },
        # Mobile Frameworks
        "react-native": {
            "files": ["metro.config.js"],
            "package_deps": ["react-native"],
            "type": ProjectType.MOBILE_APP,
        },
        "flutter": {
            "files": ["pubspec.yaml"],
            "directories": ["lib", "android", "ios"],
            "type": ProjectType.MOBILE_APP,
        },
        # Documentation
        "mkdocs": {
            "files": ["mkdocs.yml"],
            "type": ProjectType.DOCUMENTATION,
        },
        "sphinx": {
            "files": ["conf.py"],
            "directories": ["_build"],
            "type": ProjectType.DOCUMENTATION,
        },
        "docusaurus": {
            "files": ["docusaurus.config.js"],
            "type": ProjectType.DOCUMENTATION,
        },
    }

    # Type-specific exclusion patterns
    TYPE_EXCLUDES: Dict[ProjectType, List[str]] = {
        ProjectType.WEB_FRONTEND: [
            "node_modules",
            "dist",
            "build",
            ".next",
            "out",
            "coverage",
        ],
        ProjectType.API_SERVER: [
            "node_modules",
            "venv",
            ".venv",
            "__pycache__",
            ".pytest_cache",
            "htmlcov",
        ],
        ProjectType.LIBRARY: [
            "node_modules",
            "venv",
            "dist",
            "build",
            "*.egg-info",
        ],
        ProjectType.MOBILE_APP: [
            "node_modules",
            "build",
            "android/build",
            "ios/Pods",
        ],
        ProjectType.DOCUMENTATION: [
            "node_modules",
            "_build",
            "site",
            ".docusaurus",
        ],
    }

    # Priority levels by project type
    TYPE_PRIORITIES: Dict[ProjectType, str] = {
        ProjectType.API_SERVER: "high",
        ProjectType.WEB_FRONTEND: "high",
        ProjectType.LIBRARY: "medium",
        ProjectType.MOBILE_APP: "medium",
        ProjectType.CLI_TOOL: "medium",
        ProjectType.DOCUMENTATION: "low",
    }

    def __init__(self):
        """Initialize classifier"""
        self._cache: Dict[str, Tuple[ProjectType, float, Optional[str]]] = {}

    def classify(self, project: DiscoveredProject) -> DiscoveredProject:
        """
        Classify project type with confidence score.

        Args:
            project: Discovered project to classify

        Returns:
            Project with type, confidence, and suggestions filled in
        """
        # Detect frameworks
        framework_signals = self._detect_frameworks(project)

        # Determine project type and confidence
        project_type, confidence, framework = self._compute_type_and_confidence(
            project, framework_signals
        )

        # Get framework version if detected
        framework_version = None
        if framework:
            framework_version = self._detect_framework_version(project, framework)

        # Suggest exclusion patterns
        suggested_excludes = self._suggest_excludes(project_type, framework)

        # Update project
        project.type = project_type
        project.confidence = confidence
        project.framework = framework
        project.framework_version = framework_version
        project.suggested_excludes = suggested_excludes

        # Add metadata
        project.metadata["framework_signals"] = [
            {
                "framework": sig.framework,
                "confidence": sig.confidence,
                "indicators": sig.indicators,
            }
            for sig in framework_signals
        ]

        return project

    def _detect_frameworks(
        self, project: DiscoveredProject
    ) -> List[FrameworkSignal]:
        """
        Detect frameworks in project.

        Args:
            project: Project to analyze

        Returns:
            List of framework signals with confidence scores
        """
        signals = []
        project_path = Path(project.path)

        for framework, patterns in self.FRAMEWORK_PATTERNS.items():
            indicators = []
            score = 0.0
            max_score = 0.0

            # Check for required files
            if "files" in patterns:
                max_score += 1.0
                for file_pattern in patterns["files"]:
                    if (project_path / file_pattern).exists():
                        indicators.append(f"file:{file_pattern}")
                        score += 1.0
                        break

            # Check for directories
            if "directories" in patterns:
                max_score += 0.5
                for dir_pattern in patterns["directories"]:
                    if (project_path / dir_pattern).exists():
                        indicators.append(f"dir:{dir_pattern}")
                        score += 0.5
                        break

            # Check package dependencies
            if "package_deps" in patterns:
                max_score += 1.5
                deps = self._get_package_dependencies(project)
                for dep in patterns["package_deps"]:
                    if dep in deps:
                        indicators.append(f"dep:{dep}")
                        score += 1.5
                        break

            # Check code patterns (slower, only if needed)
            if "code_patterns" in patterns and score > 0:
                max_score += 1.0
                if self._check_code_patterns(
                    project_path, patterns["code_patterns"]
                ):
                    indicators.append(f"code_pattern")
                    score += 1.0

            # Compute confidence
            if max_score > 0 and score > 0:
                confidence = min(score / max_score, 1.0)
                signals.append(
                    FrameworkSignal(
                        framework=framework,
                        confidence=confidence,
                        indicators=indicators,
                    )
                )

        # Sort by confidence
        signals.sort(key=lambda s: s.confidence, reverse=True)
        return signals

    def _compute_type_and_confidence(
        self,
        project: DiscoveredProject,
        framework_signals: List[FrameworkSignal],
    ) -> Tuple[ProjectType, float, Optional[str]]:
        """
        Compute project type and overall confidence.

        Args:
            project: Project to classify
            framework_signals: Detected framework signals

        Returns:
            Tuple of (project_type, confidence, framework_name)
        """
        # If we have high-confidence framework detection, use that
        if framework_signals and framework_signals[0].confidence >= 0.5:
            top_signal = framework_signals[0]
            framework_type = self.FRAMEWORK_PATTERNS[top_signal.framework]["type"]
            return (framework_type, top_signal.confidence, top_signal.framework)

        # Fallback to heuristics based on markers and languages
        project_type = self._classify_by_heuristics(project)
        confidence = 0.6  # Lower confidence for heuristic-based classification

        return (project_type, confidence, None)

    def _classify_by_heuristics(self, project: DiscoveredProject) -> ProjectType:
        """
        Classify project using simple heuristics.

        Args:
            project: Project to classify

        Returns:
            Classified project type
        """
        project_path = Path(project.path)

        # Check for documentation indicators
        doc_indicators = ["docs", "documentation", "README.md", "mkdocs.yml"]
        if any((project_path / indicator).exists() for indicator in doc_indicators):
            # Check if it's ONLY documentation
            if len(project.markers) <= 1 and "README.md" in str(project_path):
                return ProjectType.DOCUMENTATION

        # Check for library indicators
        if "setup.py" in project.markers or "pyproject.toml" in project.markers:
            # Check if it has src/ directory (common for libraries)
            if (project_path / "src").exists():
                return ProjectType.LIBRARY

        # Check for CLI tool indicators
        if (project_path / "cli.py").exists() or (project_path / "main.py").exists():
            return ProjectType.CLI_TOOL

        # Default based on language
        if "javascript" in project.detected_languages:
            return ProjectType.WEB_FRONTEND
        elif "python" in project.detected_languages:
            return ProjectType.API_SERVER
        elif "rust" in project.detected_languages:
            return ProjectType.CLI_TOOL
        elif "go" in project.detected_languages:
            return ProjectType.API_SERVER

        return ProjectType.UNKNOWN

    def _get_package_dependencies(self, project: DiscoveredProject) -> Set[str]:
        """
        Extract package dependencies from configuration files.

        Args:
            project: Project to analyze

        Returns:
            Set of dependency package names
        """
        deps = set()
        project_path = Path(project.path)

        # Check package.json
        package_json = project_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json, "r") as f:
                    data = json.load(f)
                    for dep_type in ["dependencies", "devDependencies"]:
                        if dep_type in data:
                            deps.update(data[dep_type].keys())
            except (json.JSONDecodeError, IOError):
                pass

        # Check requirements.txt
        requirements_txt = project_path / "requirements.txt"
        if requirements_txt.exists():
            try:
                with open(requirements_txt, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            # Extract package name (before ==, >=, etc.)
                            match = re.match(r"^([a-zA-Z0-9\-_]+)", line)
                            if match:
                                deps.add(match.group(1))
            except IOError:
                pass

        # Check pyproject.toml
        pyproject = project_path / "pyproject.toml"
        if pyproject.exists():
            try:
                with open(pyproject, "r") as f:
                    content = f.read()
                    # Simple regex extraction (not full TOML parsing)
                    matches = re.findall(
                        r'["\']([a-zA-Z0-9\-_]+)["\']', content
                    )
                    deps.update(matches)
            except IOError:
                pass

        # Check Cargo.toml
        cargo_toml = project_path / "Cargo.toml"
        if cargo_toml.exists():
            try:
                with open(cargo_toml, "r") as f:
                    content = f.read()
                    # Extract dependencies section
                    matches = re.findall(
                        r'^\s*([a-zA-Z0-9\-_]+)\s*=', content, re.MULTILINE
                    )
                    deps.update(matches)
            except IOError:
                pass

        return deps

    def _check_code_patterns(
        self, project_path: Path, patterns: List[str]
    ) -> bool:
        """
        Check if code patterns exist in project files.

        Args:
            project_path: Path to project
            patterns: List of regex patterns to search for

        Returns:
            True if any pattern found
        """
        # Only check Python and JavaScript files
        extensions = [".py", ".js", ".ts", ".jsx", ".tsx"]
        checked_files = 0
        max_files = 20  # Limit to avoid performance issues

        try:
            for ext in extensions:
                for file_path in project_path.rglob(f"*{ext}"):
                    if checked_files >= max_files:
                        break

                    # Skip node_modules, venv, etc.
                    if any(
                        part in ["node_modules", "venv", "__pycache__"]
                        for part in file_path.parts
                    ):
                        continue

                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read(10000)  # Read first 10KB only
                            for pattern in patterns:
                                if re.search(pattern, content):
                                    return True
                    except (IOError, UnicodeDecodeError):
                        pass

                    checked_files += 1

        except (PermissionError, OSError):
            pass

        return False

    def _detect_framework_version(
        self, project: DiscoveredProject, framework: str
    ) -> Optional[str]:
        """
        Detect framework version from package files.

        Args:
            project: Project to analyze
            framework: Framework name

        Returns:
            Version string if detected
        """
        project_path = Path(project.path)

        # Check package.json for JavaScript frameworks
        if framework in ["next.js", "react", "vue", "angular", "express"]:
            package_json = project_path / "package.json"
            if package_json.exists():
                try:
                    with open(package_json, "r") as f:
                        data = json.load(f)
                        # Map framework to package name
                        package_name = (
                            "next" if framework == "next.js" else framework
                        )
                        for dep_type in ["dependencies", "devDependencies"]:
                            if (
                                dep_type in data
                                and package_name in data[dep_type]
                            ):
                                version = data[dep_type][package_name]
                                # Remove ^ or ~ prefix
                                return version.lstrip("^~")
                except (json.JSONDecodeError, IOError):
                    pass

        # Check requirements.txt for Python frameworks
        if framework in ["fastapi", "django", "flask"]:
            requirements = project_path / "requirements.txt"
            if requirements.exists():
                try:
                    with open(requirements, "r") as f:
                        for line in f:
                            if line.strip().startswith(framework):
                                match = re.search(
                                    r"==([0-9\.]+)", line
                                )
                                if match:
                                    return match.group(1)
                except IOError:
                    pass

        return None

    def _suggest_excludes(
        self, project_type: ProjectType, framework: Optional[str]
    ) -> List[str]:
        """
        Suggest exclusion patterns for project.

        Args:
            project_type: Classified project type
            framework: Detected framework (if any)

        Returns:
            List of suggested exclusion patterns
        """
        excludes = []

        # Add type-specific excludes
        if project_type in self.TYPE_EXCLUDES:
            excludes.extend(self.TYPE_EXCLUDES[project_type])

        # Add framework-specific excludes
        if framework == "next.js":
            excludes.extend([".next", "out"])
        elif framework == "django":
            excludes.extend(["staticfiles", "media"])
        elif framework == "flutter":
            excludes.extend([".dart_tool", "ios/Pods"])

        # Remove duplicates while preserving order
        seen = set()
        unique_excludes = []
        for pattern in excludes:
            if pattern not in seen:
                seen.add(pattern)
                unique_excludes.append(pattern)

        return unique_excludes

    def get_suggested_priority(self, project_type: ProjectType) -> str:
        """
        Get suggested indexing priority for project type.

        Args:
            project_type: Project type

        Returns:
            Priority level (critical, high, medium, low)
        """
        return self.TYPE_PRIORITIES.get(project_type, "medium")
