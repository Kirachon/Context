"""
Relationship Discovery

Auto-discover relationships between projects by analyzing:
- Import statements (Python, JavaScript/TypeScript)
- API client usage patterns
- Database connections
- Event/message queue patterns
"""

import ast
import asyncio
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass

from src.workspace.relationship_graph import (
    ProjectRelationshipGraph,
    RelationshipType,
    ProjectMetadata,
)

logger = logging.getLogger(__name__)


@dataclass
class ImportDiscovery:
    """Discovered import relationship"""
    source_file: str
    source_project: str
    target_module: str
    target_project: Optional[str] = None
    import_type: str = "direct"  # "direct", "from_import", "require", "es6_import"


@dataclass
class APIDiscovery:
    """Discovered API client relationship"""
    source_file: str
    source_project: str
    api_endpoint: str
    http_method: str
    target_project: Optional[str] = None


class RelationshipDiscoveryEngine:
    """
    Auto-discovers relationships between projects by analyzing code patterns.
    """

    def __init__(self, graph: ProjectRelationshipGraph):
        """
        Initialize discovery engine.

        Args:
            graph: Project relationship graph to populate
        """
        self.graph = graph
        self.import_discoveries: List[ImportDiscovery] = []
        self.api_discoveries: List[APIDiscovery] = []

    # ==================== Python Import Discovery ====================

    async def discover_python_imports(
        self, project: ProjectMetadata, base_path: Path
    ) -> List[ImportDiscovery]:
        """
        Discover Python import relationships by parsing Python files.

        Args:
            project: Project metadata
            base_path: Base path to scan

        Returns:
            List of discovered imports
        """
        discoveries = []
        python_files = list(base_path.rglob("*.py"))

        for py_file in python_files:
            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content, filename=str(py_file))

                for node in ast.walk(tree):
                    # Handle "import module"
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            discoveries.append(
                                ImportDiscovery(
                                    source_file=str(py_file.relative_to(base_path)),
                                    source_project=project.id,
                                    target_module=alias.name,
                                    import_type="direct",
                                )
                            )

                    # Handle "from module import ..."
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            discoveries.append(
                                ImportDiscovery(
                                    source_file=str(py_file.relative_to(base_path)),
                                    source_project=project.id,
                                    target_module=node.module,
                                    import_type="from_import",
                                )
                            )

            except (SyntaxError, UnicodeDecodeError) as e:
                logger.warning(f"Error parsing {py_file}: {e}")
                continue

        logger.info(f"Discovered {len(discoveries)} Python imports in {project.id}")
        return discoveries

    # ==================== JavaScript/TypeScript Import Discovery ====================

    async def discover_js_imports(
        self, project: ProjectMetadata, base_path: Path
    ) -> List[ImportDiscovery]:
        """
        Discover JavaScript/TypeScript import relationships.

        Args:
            project: Project metadata
            base_path: Base path to scan

        Returns:
            List of discovered imports
        """
        discoveries = []
        js_patterns = ["*.js", "*.jsx", "*.ts", "*.tsx", "*.mjs"]
        js_files = []

        for pattern in js_patterns:
            js_files.extend(base_path.rglob(pattern))

        # Regex patterns for different import styles
        es6_import_pattern = re.compile(r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]')
        require_pattern = re.compile(r'require\([\'"]([^\'"]+)[\'"]\)')
        dynamic_import_pattern = re.compile(r'import\([\'"]([^\'"]+)[\'"]\)')

        for js_file in js_files:
            try:
                content = js_file.read_text(encoding="utf-8")

                # ES6 imports
                for match in es6_import_pattern.finditer(content):
                    module_name = match.group(1)
                    discoveries.append(
                        ImportDiscovery(
                            source_file=str(js_file.relative_to(base_path)),
                            source_project=project.id,
                            target_module=module_name,
                            import_type="es6_import",
                        )
                    )

                # CommonJS require()
                for match in require_pattern.finditer(content):
                    module_name = match.group(1)
                    discoveries.append(
                        ImportDiscovery(
                            source_file=str(js_file.relative_to(base_path)),
                            source_project=project.id,
                            target_module=module_name,
                            import_type="require",
                        )
                    )

                # Dynamic imports
                for match in dynamic_import_pattern.finditer(content):
                    module_name = match.group(1)
                    discoveries.append(
                        ImportDiscovery(
                            source_file=str(js_file.relative_to(base_path)),
                            source_project=project.id,
                            target_module=module_name,
                            import_type="dynamic_import",
                        )
                    )

            except (UnicodeDecodeError, Exception) as e:
                logger.warning(f"Error parsing {js_file}: {e}")
                continue

        logger.info(f"Discovered {len(discoveries)} JS/TS imports in {project.id}")
        return discoveries

    # ==================== API Client Discovery ====================

    async def discover_api_clients(
        self, project: ProjectMetadata, base_path: Path
    ) -> List[APIDiscovery]:
        """
        Discover API client relationships by finding HTTP request patterns.

        Args:
            project: Project metadata
            base_path: Base path to scan

        Returns:
            List of discovered API calls
        """
        discoveries = []

        # Patterns for HTTP client libraries
        api_patterns = [
            # Python
            re.compile(r'requests\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]'),
            re.compile(r'httpx\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]'),
            re.compile(r'aiohttp\.ClientSession\(\)\.(\w+)\([\'"]([^\'"]+)[\'"]'),
            # JavaScript/TypeScript
            re.compile(r'fetch\([\'"]([^\'"]+)[\'"]'),
            re.compile(r'axios\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]'),
            re.compile(r'http\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]'),
        ]

        # Scan all code files
        code_files = []
        for ext in ["*.py", "*.js", "*.ts", "*.jsx", "*.tsx"]:
            code_files.extend(base_path.rglob(ext))

        for code_file in code_files:
            try:
                content = code_file.read_text(encoding="utf-8")

                for pattern in api_patterns:
                    for match in pattern.finditer(content):
                        groups = match.groups()
                        if len(groups) == 2:
                            method, endpoint = groups
                        else:
                            method = "GET"
                            endpoint = groups[0]

                        # Only track external API calls (http/https)
                        if endpoint.startswith(("http://", "https://")):
                            discoveries.append(
                                APIDiscovery(
                                    source_file=str(code_file.relative_to(base_path)),
                                    source_project=project.id,
                                    api_endpoint=endpoint,
                                    http_method=method.upper() if isinstance(method, str) else "GET",
                                )
                            )

            except (UnicodeDecodeError, Exception) as e:
                logger.warning(f"Error parsing {code_file}: {e}")
                continue

        logger.info(f"Discovered {len(discoveries)} API client calls in {project.id}")
        return discoveries

    # ==================== Relationship Mapping ====================

    async def map_imports_to_projects(
        self,
        imports: List[ImportDiscovery],
        all_projects: List[ProjectMetadata]
    ) -> None:
        """
        Map discovered imports to target projects.

        Args:
            imports: List of discovered imports
            all_projects: All projects in workspace
        """
        # Build project path index
        project_paths = {p.id: Path(p.path) for p in all_projects}
        project_names = {p.name.lower(): p.id for p in all_projects}

        for import_disc in imports:
            module_parts = import_disc.target_module.split(".")
            base_module = module_parts[0]

            # Check if module matches any project name
            if base_module.lower() in project_names:
                target_project_id = project_names[base_module.lower()]

                # Skip self-imports
                if target_project_id != import_disc.source_project:
                    import_disc.target_project = target_project_id

                    # Add relationship to graph
                    try:
                        self.graph.add_relationship(
                            from_id=import_disc.source_project,
                            to_id=target_project_id,
                            rel_type=RelationshipType.IMPORTS,
                            metadata={
                                "source_files": [import_disc.source_file],
                                "target_modules": [import_disc.target_module],
                                "discovered": True,
                            },
                            weight=0.8,  # Discovered relationships have lower weight
                        )
                        logger.debug(
                            f"Mapped import: {import_disc.source_project} -> {target_project_id} "
                            f"({import_disc.target_module})"
                        )
                    except ValueError:
                        # Projects don't exist in graph yet
                        pass

    async def map_apis_to_projects(
        self,
        apis: List[APIDiscovery],
        all_projects: List[ProjectMetadata]
    ) -> None:
        """
        Map discovered API calls to target projects.

        Args:
            apis: List of discovered API calls
            all_projects: All projects in workspace
        """
        # Build project endpoint index (if metadata contains base URLs)
        project_base_urls: Dict[str, str] = {}
        for project in all_projects:
            if hasattr(project, "metadata") and isinstance(project.metadata, dict):
                base_url = project.metadata.get("base_url") or project.metadata.get("api_url")
                if base_url:
                    project_base_urls[project.id] = base_url

        for api_disc in apis:
            endpoint = api_disc.api_endpoint

            # Try to match endpoint to project base URL
            for project_id, base_url in project_base_urls.items():
                if endpoint.startswith(base_url) and project_id != api_disc.source_project:
                    api_disc.target_project = project_id

                    # Add relationship to graph
                    try:
                        self.graph.add_relationship(
                            from_id=api_disc.source_project,
                            to_id=project_id,
                            rel_type=RelationshipType.API_CLIENT,
                            metadata={
                                "api_endpoints": [endpoint],
                                "discovered": True,
                            },
                            weight=0.9,
                        )
                        logger.debug(
                            f"Mapped API call: {api_disc.source_project} -> {project_id} ({endpoint})"
                        )
                    except ValueError:
                        pass

    # ==================== Main Discovery ====================

    async def discover_all_relationships(
        self,
        project: ProjectMetadata,
        all_projects: List[ProjectMetadata]
    ) -> Dict[str, Any]:
        """
        Discover all relationships for a project.

        Args:
            project: Project to analyze
            all_projects: All projects in workspace

        Returns:
            Discovery results summary
        """
        base_path = Path(project.path)

        if not base_path.exists():
            logger.warning(f"Project path does not exist: {base_path}")
            return {
                "imports": [],
                "api_calls": [],
                "relationships_added": 0,
            }

        logger.info(f"Starting relationship discovery for project: {project.id}")

        # Discover imports based on language
        imports = []
        if "python" in [lang.lower() for lang in project.language]:
            imports.extend(await self.discover_python_imports(project, base_path))

        if any(lang.lower() in ["javascript", "typescript"] for lang in project.language):
            imports.extend(await self.discover_js_imports(project, base_path))

        # Discover API calls
        api_calls = await self.discover_api_clients(project, base_path)

        # Map discoveries to projects
        await self.map_imports_to_projects(imports, all_projects)
        await self.map_apis_to_projects(api_calls, all_projects)

        # Store discoveries
        self.import_discoveries.extend(imports)
        self.api_discoveries.extend(api_calls)

        # Count relationships added
        relationships_added = len([i for i in imports if i.target_project]) + \
                            len([a for a in api_calls if a.target_project])

        logger.info(
            f"Discovery complete for {project.id}: "
            f"{len(imports)} imports, {len(api_calls)} API calls, "
            f"{relationships_added} relationships added"
        )

        return {
            "imports": imports,
            "api_calls": api_calls,
            "relationships_added": relationships_added,
        }

    async def discover_workspace_relationships(
        self, projects: List[ProjectMetadata]
    ) -> Dict[str, Any]:
        """
        Discover relationships for all projects in workspace.

        Args:
            projects: List of all projects

        Returns:
            Summary of all discoveries
        """
        logger.info(f"Starting workspace-wide relationship discovery for {len(projects)} projects")

        results = []
        for project in projects:
            result = await self.discover_all_relationships(project, projects)
            results.append((project.id, result))

        total_imports = sum(len(r["imports"]) for _, r in results)
        total_api_calls = sum(len(r["api_calls"]) for _, r in results)
        total_relationships = sum(r["relationships_added"] for _, r in results)

        summary = {
            "projects_analyzed": len(projects),
            "total_imports": total_imports,
            "total_api_calls": total_api_calls,
            "total_relationships": total_relationships,
            "results_by_project": {pid: r for pid, r in results},
        }

        logger.info(
            f"Workspace discovery complete: "
            f"{total_imports} imports, {total_api_calls} API calls, "
            f"{total_relationships} relationships discovered"
        )

        return summary


# ==================== Utility Functions ====================


async def discover_project_relationships(
    graph: ProjectRelationshipGraph,
    project: ProjectMetadata,
    all_projects: List[ProjectMetadata]
) -> Dict[str, Any]:
    """
    Convenience function to discover relationships for a single project.

    Args:
        graph: Project relationship graph
        project: Project to analyze
        all_projects: All projects in workspace

    Returns:
        Discovery results
    """
    engine = RelationshipDiscoveryEngine(graph)
    return await engine.discover_all_relationships(project, all_projects)


async def discover_workspace_relationships(
    graph: ProjectRelationshipGraph,
    projects: List[ProjectMetadata]
) -> Dict[str, Any]:
    """
    Convenience function to discover relationships for entire workspace.

    Args:
        graph: Project relationship graph
        projects: All projects in workspace

    Returns:
        Discovery summary
    """
    engine = RelationshipDiscoveryEngine(graph)
    return await engine.discover_workspace_relationships(projects)
