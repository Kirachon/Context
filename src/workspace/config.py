"""
Workspace Configuration System

Provides Pydantic models for workspace configuration with comprehensive
validation, I/O operations, and path resolution.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class IndexingConfig(BaseModel):
    """Configuration for project indexing behavior"""

    enabled: bool = Field(default=True, description="Whether indexing is enabled for this project")
    priority: Literal["critical", "high", "medium", "low"] = Field(
        default="medium", description="Indexing priority level"
    )
    exclude: List[str] = Field(
        default_factory=list,
        description="Patterns to exclude from indexing (glob patterns)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "priority": "high",
                "exclude": ["node_modules", "dist", ".next"],
            }
        }


class ProjectConfig(BaseModel):
    """Configuration for an individual project within a workspace"""

    id: str = Field(..., description="Unique project identifier")
    name: str = Field(..., description="Human-readable project name")
    path: str = Field(..., description="Absolute or relative path to project directory")
    type: str = Field(
        default="application",
        description="Project type (e.g., web_frontend, api_server, library, documentation)",
    )
    language: List[str] = Field(
        default_factory=list, description="Programming languages used in project"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of project IDs this project depends on",
    )
    indexing: IndexingConfig = Field(
        default_factory=IndexingConfig, description="Indexing configuration"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional project metadata"
    )

    # Internal field for resolved absolute path
    _resolved_path: Optional[Path] = None

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate project ID is a valid identifier"""
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError(
                f"Project ID '{v}' must contain only alphanumeric characters and underscores"
            )
        return v

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate path is not empty"""
        if not v or not v.strip():
            raise ValueError("Project path cannot be empty")
        return v.strip()

    def resolve_path(self, workspace_dir: Path) -> Path:
        """
        Resolve project path to absolute path.

        If path is relative, resolve it relative to workspace directory.
        If path is absolute, use it as-is.

        Args:
            workspace_dir: Directory containing the workspace config file

        Returns:
            Resolved absolute path
        """
        path_obj = Path(self.path)
        if path_obj.is_absolute():
            self._resolved_path = path_obj
        else:
            self._resolved_path = (workspace_dir / path_obj).resolve()
        return self._resolved_path

    def get_resolved_path(self) -> Optional[Path]:
        """Get the resolved absolute path if available"""
        return self._resolved_path

    class Config:
        json_schema_extra = {
            "example": {
                "id": "frontend",
                "name": "Frontend (React)",
                "path": "/home/user/projects/myapp-frontend",
                "type": "web_frontend",
                "language": ["typescript", "tsx"],
                "dependencies": ["backend", "shared"],
                "indexing": {
                    "enabled": True,
                    "priority": "high",
                    "exclude": ["node_modules", "dist"],
                },
                "metadata": {"framework": "next.js", "version": "14.0.0"},
            }
        }


class RelationshipConfig(BaseModel):
    """Configuration for project-to-project relationships"""

    from_project: str = Field(..., alias="from", description="Source project ID")
    to_project: str = Field(..., alias="to", description="Target project ID")
    type: Literal[
        "imports",
        "api_client",
        "shared_database",
        "event_driven",
        "semantic_similarity",
        "dependency",
    ] = Field(..., description="Type of relationship")
    description: Optional[str] = Field(
        default=None, description="Human-readable description of the relationship"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional relationship metadata"
    )

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "from": "frontend",
                "to": "backend",
                "type": "api_client",
                "description": "Frontend calls backend REST API",
            }
        }


class SearchConfig(BaseModel):
    """Configuration for search behavior across the workspace"""

    default_scope: Literal["project", "dependencies", "workspace", "related"] = Field(
        default="workspace", description="Default search scope"
    )
    cross_project_ranking: bool = Field(
        default=True, description="Enable relationship-aware ranking across projects"
    )
    relationship_boost: float = Field(
        default=1.5,
        ge=1.0,
        le=3.0,
        description="Boost factor for results from related projects",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "default_scope": "workspace",
                "cross_project_ranking": True,
                "relationship_boost": 1.5,
            }
        }


class WorkspaceConfig(BaseModel):
    """Top-level workspace configuration"""

    version: str = Field(default="2.0.0", description="Workspace configuration version")
    name: str = Field(..., description="Workspace name")
    projects: List[ProjectConfig] = Field(
        default_factory=list, description="List of projects in the workspace"
    )
    relationships: List[RelationshipConfig] = Field(
        default_factory=list, description="Explicit project relationships"
    )
    search: SearchConfig = Field(
        default_factory=SearchConfig, description="Search configuration"
    )

    # Internal field for workspace directory
    _workspace_dir: Optional[Path] = None

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate version format"""
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError(f"Version '{v}' must be in semver format (e.g., 2.0.0)")
        return v

    @model_validator(mode="after")
    def validate_workspace(self):
        """Perform cross-field validations"""
        # Validate project ID uniqueness
        project_ids = [p.id for p in self.projects]
        duplicate_ids = [pid for pid in project_ids if project_ids.count(pid) > 1]
        if duplicate_ids:
            raise ValueError(
                f"Duplicate project IDs found: {', '.join(set(duplicate_ids))}"
            )

        # Validate relationship references
        valid_ids = set(project_ids)
        for rel in self.relationships:
            if rel.from_project not in valid_ids:
                raise ValueError(
                    f"Relationship references unknown project: '{rel.from_project}'"
                )
            if rel.to_project not in valid_ids:
                raise ValueError(
                    f"Relationship references unknown project: '{rel.to_project}'"
                )
            if rel.from_project == rel.to_project:
                raise ValueError(
                    f"Relationship cannot be self-referential: '{rel.from_project}'"
                )

        # Validate dependency references
        for project in self.projects:
            for dep_id in project.dependencies:
                if dep_id not in valid_ids:
                    raise ValueError(
                        f"Project '{project.id}' references unknown dependency: '{dep_id}'"
                    )
                if dep_id == project.id:
                    raise ValueError(
                        f"Project '{project.id}' cannot depend on itself"
                    )

        # Detect circular dependencies
        self._detect_circular_dependencies()

        return self

    def _detect_circular_dependencies(self) -> None:
        """
        Detect circular dependencies in the project dependency graph.

        Uses depth-first search to detect cycles.

        Raises:
            ValueError: If circular dependencies are detected
        """
        # Build adjacency list
        graph = {p.id: p.dependencies for p in self.projects}

        def has_cycle(node: str, visited: set, rec_stack: set, path: List[str]) -> Optional[List[str]]:
            """DFS to detect cycles, returns cycle path if found"""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    cycle = has_cycle(neighbor, visited, rec_stack, path[:])
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found cycle - return path from neighbor to node
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]

            rec_stack.remove(node)
            return None

        visited = set()
        for project_id in graph:
            if project_id not in visited:
                cycle = has_cycle(project_id, visited, set(), [])
                if cycle:
                    cycle_str = " -> ".join(cycle)
                    raise ValueError(f"Circular dependency detected: {cycle_str}")

    def validate_paths(self) -> List[str]:
        """
        Validate that all project paths exist on disk.

        Returns:
            List of error messages for non-existent paths
        """
        if not self._workspace_dir:
            raise RuntimeError("Workspace directory not set. Call resolve_paths() first.")

        errors = []
        for project in self.projects:
            resolved_path = project.get_resolved_path()
            if not resolved_path:
                raise RuntimeError(
                    f"Project '{project.id}' path not resolved. Call resolve_paths() first."
                )

            if not resolved_path.exists():
                errors.append(
                    f"Project '{project.id}' path does not exist: {resolved_path}"
                )
            elif not resolved_path.is_dir():
                errors.append(
                    f"Project '{project.id}' path is not a directory: {resolved_path}"
                )

        return errors

    def resolve_paths(self, workspace_dir: Path) -> None:
        """
        Resolve all project paths to absolute paths.

        Args:
            workspace_dir: Directory containing the workspace config file
        """
        self._workspace_dir = workspace_dir
        for project in self.projects:
            project.resolve_path(workspace_dir)

    def validate(self, check_paths: bool = True) -> None:
        """
        Run all validations on the workspace configuration.

        Args:
            check_paths: Whether to validate that paths exist on disk

        Raises:
            ValueError: If validation fails
        """
        # Pydantic validations already run during construction
        # Run path validation if requested
        if check_paths:
            if not self._workspace_dir:
                raise ValueError(
                    "Cannot validate paths: workspace directory not set. "
                    "Use WorkspaceConfig.load() to automatically resolve paths."
                )

            path_errors = self.validate_paths()
            if path_errors:
                raise ValueError(
                    f"Path validation failed:\n" + "\n".join(f"  - {e}" for e in path_errors)
                )

    @classmethod
    def load(cls, path: str | Path, validate_paths: bool = True) -> "WorkspaceConfig":
        """
        Load workspace configuration from JSON file.

        Args:
            path: Path to .context-workspace.json file
            validate_paths: Whether to validate that project paths exist

        Returns:
            Loaded and validated WorkspaceConfig

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If validation fails
            json.JSONDecodeError: If JSON is invalid
        """
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Workspace config file not found: {config_path}")

        if not config_path.is_file():
            raise ValueError(f"Workspace config path is not a file: {config_path}")

        # Load JSON
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Parse with Pydantic
        config = cls.model_validate(data)

        # Resolve paths relative to config file directory
        workspace_dir = config_path.parent.resolve()
        config.resolve_paths(workspace_dir)

        # Validate paths if requested
        if validate_paths:
            config.validate(check_paths=True)

        return config

    def save(self, path: str | Path) -> None:
        """
        Save workspace configuration to JSON file.

        Args:
            path: Path to save .context-workspace.json file
        """
        config_path = Path(path)

        # Ensure parent directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict and write
        data = self.model_dump(mode="json", by_alias=True, exclude_none=False)

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")  # Add trailing newline

    def get_project(self, project_id: str) -> Optional[ProjectConfig]:
        """
        Get a project by ID.

        Args:
            project_id: Project identifier

        Returns:
            ProjectConfig if found, None otherwise
        """
        for project in self.projects:
            if project.id == project_id:
                return project
        return None

    def get_project_dependencies(self, project_id: str, transitive: bool = False) -> List[str]:
        """
        Get dependencies for a project.

        Args:
            project_id: Project identifier
            transitive: Whether to include transitive dependencies

        Returns:
            List of dependency project IDs
        """
        project = self.get_project(project_id)
        if not project:
            return []

        if not transitive:
            return project.dependencies

        # Get transitive dependencies using BFS
        dependencies = set()
        queue = list(project.dependencies)
        visited = {project_id}

        while queue:
            dep_id = queue.pop(0)
            if dep_id in visited:
                continue

            visited.add(dep_id)
            dependencies.add(dep_id)

            dep_project = self.get_project(dep_id)
            if dep_project:
                queue.extend(dep_project.dependencies)

        return list(dependencies)

    def get_project_dependents(self, project_id: str) -> List[str]:
        """
        Get projects that depend on the given project.

        Args:
            project_id: Project identifier

        Returns:
            List of dependent project IDs
        """
        dependents = []
        for project in self.projects:
            if project_id in project.dependencies:
                dependents.append(project.id)
        return dependents

    def get_relationships(
        self, project_id: Optional[str] = None, relationship_type: Optional[str] = None
    ) -> List[RelationshipConfig]:
        """
        Get relationships, optionally filtered by project or type.

        Args:
            project_id: Filter by source or target project
            relationship_type: Filter by relationship type

        Returns:
            List of matching relationships
        """
        relationships = self.relationships

        if project_id:
            relationships = [
                r
                for r in relationships
                if r.from_project == project_id or r.to_project == project_id
            ]

        if relationship_type:
            relationships = [r for r in relationships if r.type == relationship_type]

        return relationships

    class Config:
        json_schema_extra = {
            "example": {
                "version": "2.0.0",
                "name": "My Full-Stack App",
                "projects": [
                    {
                        "id": "frontend",
                        "name": "Frontend (React)",
                        "path": "/home/user/projects/myapp-frontend",
                        "type": "web_frontend",
                        "language": ["typescript"],
                        "dependencies": ["backend"],
                        "indexing": {"enabled": True, "priority": "high"},
                    }
                ],
                "relationships": [
                    {
                        "from": "frontend",
                        "to": "backend",
                        "type": "api_client",
                        "description": "Frontend calls backend REST API",
                    }
                ],
                "search": {
                    "default_scope": "workspace",
                    "cross_project_ranking": True,
                    "relationship_boost": 1.5,
                },
            }
        }
