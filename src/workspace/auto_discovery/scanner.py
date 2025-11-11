"""
Project Scanner

Scans directory trees and detects projects by looking for marker files.
Optimized for performance with configurable depth limits and ignore patterns.
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from .models import DiscoveredProject, ProjectType


class ProjectScanner:
    """
    Scans directory trees and detects projects.

    Walks through directories looking for project markers (package.json, setup.py, etc.)
    and returns discovered project paths with detected languages.
    """

    # Project marker files and their associated languages
    MARKERS: Dict[str, str] = {
        "package.json": "javascript",
        "setup.py": "python",
        "pyproject.toml": "python",
        "requirements.txt": "python",
        "Cargo.toml": "rust",
        "go.mod": "go",
        "pom.xml": "java",
        "build.gradle": "java",
        "Gemfile": "ruby",
        "Makefile": "c",
        "CMakeLists.txt": "cpp",
        "composer.json": "php",
        "pubspec.yaml": "dart",
        "Package.swift": "swift",
    }

    # Common directories to ignore
    DEFAULT_IGNORE_PATTERNS: Set[str] = {
        ".git",
        "node_modules",
        "venv",
        ".venv",
        "env",
        ".env",
        "__pycache__",
        ".pytest_cache",
        "target",
        "build",
        "dist",
        ".next",
        ".nuxt",
        "out",
        "bin",
        "obj",
        ".idea",
        ".vscode",
        ".DS_Store",
        "vendor",
        "coverage",
        ".coverage",
    }

    def __init__(
        self,
        max_depth: int = 10,
        ignore_patterns: Optional[Set[str]] = None,
    ):
        """
        Initialize scanner.

        Args:
            max_depth: Maximum directory depth to scan (default: 10)
            ignore_patterns: Additional patterns to ignore (merged with defaults)
        """
        self.max_depth = max_depth
        self.ignore_patterns = self.DEFAULT_IGNORE_PATTERNS.copy()
        if ignore_patterns:
            self.ignore_patterns.update(ignore_patterns)

        self.stats = {
            "directories_scanned": 0,
            "projects_found": 0,
            "files_examined": 0,
            "scan_duration_seconds": 0.0,
        }

    def scan(self, root_path: str) -> List[DiscoveredProject]:
        """
        Scan directory tree for projects.

        Args:
            root_path: Root directory to start scanning from

        Returns:
            List of discovered projects with basic metadata

        Raises:
            ValueError: If root_path doesn't exist or isn't a directory
        """
        start_time = time.time()

        root = Path(root_path).resolve()
        if not root.exists():
            raise ValueError(f"Path does not exist: {root_path}")
        if not root.is_dir():
            raise ValueError(f"Path is not a directory: {root_path}")

        discovered: List[DiscoveredProject] = []
        visited_projects: Set[str] = set()

        # Walk directory tree
        for project_path, markers in self._walk_tree(root):
            project_path_str = str(project_path)

            # Skip if already found (handle nested projects)
            if project_path_str in visited_projects:
                continue

            # Detect languages from markers
            languages = self._detect_languages(markers)

            # Create discovered project entry
            project = DiscoveredProject(
                path=project_path_str,
                type=ProjectType.UNKNOWN,  # Will be classified later
                confidence=0.0,  # Will be computed by classifier
                detected_languages=languages,
                detected_dependencies=[],  # Will be analyzed later
                suggested_excludes=[],  # Will be suggested by classifier
                markers=markers,
            )

            discovered.append(project)
            visited_projects.add(project_path_str)
            self.stats["projects_found"] += 1

        self.stats["scan_duration_seconds"] = time.time() - start_time

        return discovered

    def _walk_tree(self, root: Path, depth: int = 0) -> List[tuple[Path, List[str]]]:
        """
        Walk directory tree and find project roots.

        Args:
            root: Current directory to scan
            depth: Current depth level

        Yields:
            Tuples of (project_path, marker_files)
        """
        if depth > self.max_depth:
            return []

        results = []

        try:
            # Check if current directory is a project root
            markers = self._find_markers(root)
            if markers:
                results.append((root, markers))
                # Don't scan subdirectories of detected projects
                # (prevents nested project confusion)
                return results

            # Scan subdirectories
            self.stats["directories_scanned"] += 1

            entries = list(root.iterdir())
            self.stats["files_examined"] += len(entries)

            for entry in entries:
                # Skip ignored patterns
                if entry.name in self.ignore_patterns:
                    continue

                # Only recurse into directories
                if entry.is_dir():
                    try:
                        sub_results = self._walk_tree(entry, depth + 1)
                        results.extend(sub_results)
                    except (PermissionError, OSError):
                        # Skip directories we can't access
                        continue

        except (PermissionError, OSError):
            # Skip directories we can't access
            pass

        return results

    def _find_markers(self, directory: Path) -> List[str]:
        """
        Find project marker files in directory.

        Args:
            directory: Directory to check

        Returns:
            List of marker filenames found
        """
        markers = []
        try:
            for marker in self.MARKERS.keys():
                if (directory / marker).exists():
                    markers.append(marker)
        except (PermissionError, OSError):
            pass

        return markers

    def _detect_languages(self, markers: List[str]) -> List[str]:
        """
        Detect programming languages from marker files.

        Args:
            markers: List of marker filenames

        Returns:
            List of detected language names
        """
        languages = set()

        for marker in markers:
            if marker in self.MARKERS:
                lang = self.MARKERS[marker]
                languages.add(lang)

        return sorted(list(languages))

    def _is_project_root(self, path: Path) -> bool:
        """
        Check if path is a project root.

        Args:
            path: Path to check

        Returns:
            True if path contains project markers
        """
        return len(self._find_markers(path)) > 0

    def get_stats(self) -> Dict[str, any]:
        """
        Get scan statistics.

        Returns:
            Dictionary of scan statistics
        """
        return self.stats.copy()
