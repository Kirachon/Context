"""
Dependency Analyzer

Analyzes dependencies between projects by parsing package files
and detecting local references, workspace packages, and relationships.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .models import DependencyRelation, DiscoveredProject


class DependencyAnalyzer:
    """
    Analyzes dependencies between projects.

    Parses package files (package.json, requirements.txt, etc.) to detect
    local dependencies and build a dependency graph.
    """

    def __init__(self):
        """Initialize dependency analyzer"""
        self.project_map: Dict[str, DiscoveredProject] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}

    def analyze(
        self, projects: List[DiscoveredProject]
    ) -> Tuple[List[DiscoveredProject], List[DependencyRelation]]:
        """
        Analyze dependencies between projects.

        Args:
            projects: List of discovered projects

        Returns:
            Tuple of (updated_projects, dependency_relations)
        """
        # Build project map for quick lookup
        self.project_map = {p.path: p for p in projects}
        self.dependency_graph = {p.path: set() for p in projects}

        # Detect dependencies for each project
        relations = []
        for project in projects:
            project_relations = self._analyze_project_dependencies(project)
            relations.extend(project_relations)

            # Update project's detected dependencies
            deps = [self._path_to_project_name(r.to_project) for r in project_relations]
            project.detected_dependencies = deps

        return projects, relations

    def _analyze_project_dependencies(
        self, project: DiscoveredProject
    ) -> List[DependencyRelation]:
        """
        Analyze dependencies for a single project.

        Args:
            project: Project to analyze

        Returns:
            List of dependency relations
        """
        relations = []

        # Parse package files
        package_deps = self._parse_package_files(project)
        relations.extend(package_deps)

        # Detect local path references
        local_deps = self._detect_local_references(project)
        relations.extend(local_deps)

        return relations

    def _parse_package_files(
        self, project: DiscoveredProject
    ) -> List[DependencyRelation]:
        """
        Parse package files to detect dependencies.

        Args:
            project: Project to analyze

        Returns:
            List of dependency relations
        """
        relations = []
        project_path = Path(project.path)

        # Parse package.json
        if "package.json" in project.markers:
            package_json_deps = self._parse_package_json(project_path)
            relations.extend(package_json_deps)

        # Parse requirements.txt
        if "requirements.txt" in project.markers:
            requirements_deps = self._parse_requirements_txt(project_path)
            relations.extend(requirements_deps)

        # Parse pyproject.toml
        if "pyproject.toml" in project.markers:
            pyproject_deps = self._parse_pyproject_toml(project_path)
            relations.extend(pyproject_deps)

        # Parse Cargo.toml
        if "Cargo.toml" in project.markers:
            cargo_deps = self._parse_cargo_toml(project_path)
            relations.extend(cargo_deps)

        # Parse go.mod
        if "go.mod" in project.markers:
            go_deps = self._parse_go_mod(project_path)
            relations.extend(go_deps)

        return relations

    def _parse_package_json(
        self, project_path: Path
    ) -> List[DependencyRelation]:
        """Parse package.json for dependencies"""
        relations = []
        package_json = project_path / "package.json"

        try:
            with open(package_json, "r") as f:
                data = json.load(f)

                # Check for workspace references (monorepo)
                if "workspaces" in data:
                    for workspace_pattern in data["workspaces"]:
                        # Resolve workspace paths
                        for workspace_path in project_path.glob(workspace_pattern):
                            if workspace_path.is_dir():
                                target = self._find_project_by_path(
                                    str(workspace_path.resolve())
                                )
                                if target:
                                    relations.append(
                                        DependencyRelation(
                                            from_project=str(project_path),
                                            to_project=target,
                                            relation_type="workspace",
                                            confidence=1.0,
                                        )
                                    )

                # Check for local file dependencies
                for dep_type in ["dependencies", "devDependencies"]:
                    if dep_type in data:
                        for dep_name, dep_version in data[dep_type].items():
                            # Check for file: or link: references
                            if isinstance(dep_version, str) and (
                                dep_version.startswith("file:")
                                or dep_version.startswith("link:")
                            ):
                                # Extract path
                                dep_path = dep_version.replace("file:", "").replace(
                                    "link:", ""
                                )
                                target_path = (project_path / dep_path).resolve()
                                target = self._find_project_by_path(
                                    str(target_path)
                                )
                                if target:
                                    relations.append(
                                        DependencyRelation(
                                            from_project=str(project_path),
                                            to_project=target,
                                            relation_type="dependency",
                                            confidence=1.0,
                                            metadata={
                                                "package_name": dep_name,
                                                "version": dep_version,
                                            },
                                        )
                                    )

        except (json.JSONDecodeError, IOError):
            pass

        return relations

    def _parse_requirements_txt(
        self, project_path: Path
    ) -> List[DependencyRelation]:
        """Parse requirements.txt for local dependencies"""
        relations = []
        requirements = project_path / "requirements.txt"

        try:
            with open(requirements, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Check for local package references (-e ./path)
                        if line.startswith("-e") and "./" in line:
                            match = re.search(r'-e\s+["\']?([\.\/][^"\']+)', line)
                            if match:
                                dep_path = match.group(1)
                                target_path = (project_path / dep_path).resolve()
                                target = self._find_project_by_path(
                                    str(target_path)
                                )
                                if target:
                                    relations.append(
                                        DependencyRelation(
                                            from_project=str(project_path),
                                            to_project=target,
                                            relation_type="dependency",
                                            confidence=1.0,
                                        )
                                    )

        except IOError:
            pass

        return relations

    def _parse_pyproject_toml(
        self, project_path: Path
    ) -> List[DependencyRelation]:
        """Parse pyproject.toml for local dependencies"""
        relations = []
        pyproject = project_path / "pyproject.toml"

        try:
            with open(pyproject, "r") as f:
                content = f.read()
                # Look for path references in dependencies
                # Simple regex approach (full TOML parsing would be better but heavier)
                matches = re.findall(
                    r'path\s*=\s*["\']([^"\']+)["\']', content
                )
                for dep_path in matches:
                    if dep_path.startswith("."):
                        target_path = (project_path / dep_path).resolve()
                        target = self._find_project_by_path(str(target_path))
                        if target:
                            relations.append(
                                DependencyRelation(
                                    from_project=str(project_path),
                                    to_project=target,
                                    relation_type="dependency",
                                    confidence=0.9,
                                )
                            )

        except IOError:
            pass

        return relations

    def _parse_cargo_toml(self, project_path: Path) -> List[DependencyRelation]:
        """Parse Cargo.toml for local dependencies"""
        relations = []
        cargo_toml = project_path / "Cargo.toml"

        try:
            with open(cargo_toml, "r") as f:
                content = f.read()
                # Look for path references in dependencies
                matches = re.findall(
                    r'path\s*=\s*["\']([^"\']+)["\']', content
                )
                for dep_path in matches:
                    target_path = (project_path / dep_path).resolve()
                    target = self._find_project_by_path(str(target_path))
                    if target:
                        relations.append(
                            DependencyRelation(
                                from_project=str(project_path),
                                to_project=target,
                                relation_type="dependency",
                                confidence=1.0,
                            )
                        )

        except IOError:
            pass

        return relations

    def _parse_go_mod(self, project_path: Path) -> List[DependencyRelation]:
        """Parse go.mod for local dependencies"""
        relations = []
        go_mod = project_path / "go.mod"

        try:
            with open(go_mod, "r") as f:
                content = f.read()
                # Look for replace directives with local paths
                matches = re.findall(
                    r'replace\s+[^\s]+\s+=>\s+([\.\/][^\s]+)', content
                )
                for dep_path in matches:
                    target_path = (project_path / dep_path).resolve()
                    target = self._find_project_by_path(str(target_path))
                    if target:
                        relations.append(
                            DependencyRelation(
                                from_project=str(project_path),
                                to_project=target,
                                relation_type="dependency",
                                confidence=1.0,
                            )
                        )

        except IOError:
            pass

        return relations

    def _detect_local_references(
        self, project: DiscoveredProject
    ) -> List[DependencyRelation]:
        """
        Detect local project references by analyzing nearby directories.

        Args:
            project: Project to analyze

        Returns:
            List of detected dependency relations
        """
        relations = []
        project_path = Path(project.path)

        # Check parent directory for sibling projects
        parent = project_path.parent
        if parent:
            for sibling in parent.iterdir():
                if sibling.is_dir() and sibling != project_path:
                    # Check if sibling is a known project
                    target = self._find_project_by_path(str(sibling))
                    if target:
                        # Check if project name suggests a relationship
                        # (e.g., myapp-frontend and myapp-backend)
                        if self._likely_related(
                            project_path.name, sibling.name
                        ):
                            relations.append(
                                DependencyRelation(
                                    from_project=str(project_path),
                                    to_project=target,
                                    relation_type="semantic_similarity",
                                    confidence=0.6,
                                    metadata={"reason": "similar_names"},
                                )
                            )

        return relations

    def _likely_related(self, name1: str, name2: str) -> bool:
        """
        Check if two project names suggest a relationship.

        Args:
            name1: First project name
            name2: Second project name

        Returns:
            True if names suggest relationship
        """
        # Extract base name (remove suffixes like -frontend, -backend)
        def extract_base(name: str) -> str:
            return re.sub(
                r'[-_](frontend|backend|api|client|server|shared|common|lib|core|mobile|web|app)$',
                '',
                name.lower()
            )

        base1 = extract_base(name1)
        base2 = extract_base(name2)

        # Check if base names match
        return base1 and base2 and base1 == base2

    def _find_project_by_path(self, path: str) -> Optional[str]:
        """
        Find project by path.

        Args:
            path: Path to search for

        Returns:
            Project path if found, None otherwise
        """
        path_obj = Path(path).resolve()

        # Exact match
        if str(path_obj) in self.project_map:
            return str(path_obj)

        # Check if path is within any project
        for project_path in self.project_map.keys():
            project_path_obj = Path(project_path)
            try:
                if path_obj == project_path_obj:
                    return project_path
                # Check if it's a parent of the path
                path_obj.relative_to(project_path_obj)
                return project_path
            except ValueError:
                continue

        return None

    def _path_to_project_name(self, path: str) -> str:
        """
        Convert project path to a simple name.

        Args:
            path: Project path

        Returns:
            Project name
        """
        return Path(path).name

    def build_dependency_graph(
        self, relations: List[DependencyRelation]
    ) -> Dict[str, List[str]]:
        """
        Build dependency graph from relations.

        Args:
            relations: List of dependency relations

        Returns:
            Dictionary mapping project paths to list of dependency paths
        """
        graph = {}

        for relation in relations:
            if relation.from_project not in graph:
                graph[relation.from_project] = []

            if relation.to_project not in graph[relation.from_project]:
                graph[relation.from_project].append(relation.to_project)

        return graph
