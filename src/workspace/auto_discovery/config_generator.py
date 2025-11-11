"""
Config Generator

Generates WorkspaceConfig from discovered projects with intelligent defaults.
Creates complete workspace configuration ready to save.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

from src.workspace.config import (
    IndexingConfig,
    ProjectConfig,
    RelationshipConfig,
    WorkspaceConfig,
)

from .classifier import TypeClassifier
from .models import DependencyRelation, DiscoveredProject


class ConfigGenerator:
    """
    Generates workspace configuration from discovered projects.

    Takes discovered projects and creates a complete WorkspaceConfig
    with all fields filled in with intelligent defaults.
    """

    def __init__(self):
        """Initialize config generator"""
        self.classifier = TypeClassifier()

    def generate(
        self,
        projects: List[DiscoveredProject],
        relations: List[DependencyRelation],
        workspace_name: Optional[str] = None,
        base_path: Optional[str] = None,
    ) -> WorkspaceConfig:
        """
        Generate workspace configuration.

        Args:
            projects: List of discovered projects
            relations: List of dependency relations
            workspace_name: Optional workspace name (auto-generated if not provided)
            base_path: Optional base path for relative path resolution

        Returns:
            Complete WorkspaceConfig ready to save
        """
        # Generate workspace name if not provided
        if not workspace_name:
            workspace_name = self._generate_workspace_name(projects, base_path)

        # Convert discovered projects to ProjectConfig
        project_configs = []
        project_id_map = {}  # Map path to ID for relationship building

        for idx, project in enumerate(projects):
            project_config, project_id = self._create_project_config(
                project, idx, base_path
            )
            project_configs.append(project_config)
            project_id_map[project.path] = project_id

        # Convert dependency relations to RelationshipConfig
        relationship_configs = self._create_relationship_configs(
            relations, project_id_map
        )

        # Create workspace config
        config = WorkspaceConfig(
            version="2.0.0",
            name=workspace_name,
            projects=project_configs,
            relationships=relationship_configs,
        )

        return config

    def _generate_workspace_name(
        self, projects: List[DiscoveredProject], base_path: Optional[str] = None
    ) -> str:
        """
        Generate workspace name from projects or base path.

        Args:
            projects: List of discovered projects
            base_path: Optional base path

        Returns:
            Generated workspace name
        """
        if base_path:
            # Use directory name
            path_obj = Path(base_path)
            name = path_obj.name
            if name and name != ".":
                return self._humanize_name(name)

        # Try to find common prefix in project names
        if projects:
            project_names = [Path(p.path).name for p in projects]

            # Find common prefix
            if len(project_names) > 1:
                common_prefix = self._find_common_prefix(project_names)
                if common_prefix and len(common_prefix) > 3:
                    return self._humanize_name(common_prefix)

            # Fall back to first project name
            return self._humanize_name(project_names[0]) + " Workspace"

        return "My Workspace"

    def _find_common_prefix(self, names: List[str]) -> str:
        """
        Find common prefix among names.

        Args:
            names: List of names

        Returns:
            Common prefix
        """
        if not names:
            return ""

        # Remove common suffixes first
        cleaned_names = [
            re.sub(
                r'[-_](frontend|backend|api|client|server|shared|common|lib|core|mobile|web|app)$',
                '',
                name.lower()
            )
            for name in names
        ]

        # Find common prefix
        prefix = cleaned_names[0]
        for name in cleaned_names[1:]:
            while not name.startswith(prefix) and prefix:
                prefix = prefix[:-1]

        return prefix.strip("-_")

    def _humanize_name(self, name: str) -> str:
        """
        Convert technical name to human-readable name.

        Args:
            name: Technical name (e.g., 'my-app-frontend')

        Returns:
            Human-readable name (e.g., 'My App Frontend')
        """
        # Replace separators with spaces
        name = re.sub(r'[-_]', ' ', name)

        # Capitalize words
        words = name.split()
        capitalized = [word.capitalize() for word in words]

        return ' '.join(capitalized)

    def _create_project_config(
        self,
        project: DiscoveredProject,
        index: int,
        base_path: Optional[str] = None,
    ) -> tuple[ProjectConfig, str]:
        """
        Create ProjectConfig from DiscoveredProject.

        Args:
            project: Discovered project
            index: Project index (for ID generation)
            base_path: Optional base path for relative paths

        Returns:
            Tuple of (ProjectConfig, project_id)
        """
        # Generate project ID
        project_id = self._generate_project_id(project, index)

        # Determine path (relative or absolute)
        if base_path:
            try:
                project_path = Path(project.path)
                base_path_obj = Path(base_path)
                relative_path = project_path.relative_to(base_path_obj)
                path_str = str(relative_path)
            except ValueError:
                # Can't make relative, use absolute
                path_str = project.path
        else:
            path_str = project.path

        # Generate human-readable name
        name = self._humanize_name(Path(project.path).name)

        # Get suggested priority
        priority = self.classifier.get_suggested_priority(project.type)

        # Create indexing config
        indexing_config = IndexingConfig(
            enabled=True,
            priority=priority,
            exclude=project.suggested_excludes,
        )

        # Build metadata
        metadata = project.metadata.copy()
        if project.framework:
            metadata["framework"] = project.framework
        if project.framework_version:
            metadata["framework_version"] = project.framework_version
        metadata["discovery_confidence"] = project.confidence
        metadata["auto_discovered"] = True

        # Map dependency paths to IDs (will be updated later)
        dependencies = []  # Will be set by caller based on relations

        # Create project config
        project_config = ProjectConfig(
            id=project_id,
            name=name,
            path=path_str,
            type=project.type.value,
            language=project.detected_languages,
            dependencies=dependencies,
            indexing=indexing_config,
            metadata=metadata,
        )

        return project_config, project_id

    def _generate_project_id(
        self, project: DiscoveredProject, index: int
    ) -> str:
        """
        Generate unique project ID.

        Args:
            project: Discovered project
            index: Project index

        Returns:
            Generated project ID
        """
        # Use directory name as base
        dir_name = Path(project.path).name

        # Sanitize to valid ID format
        project_id = dir_name.lower()
        project_id = re.sub(r'[^a-z0-9_]', '_', project_id)
        project_id = re.sub(r'_+', '_', project_id)  # Remove consecutive underscores
        project_id = project_id.strip('_')

        # Ensure it starts with a letter
        if project_id and not project_id[0].isalpha():
            project_id = 'p_' + project_id

        # Fallback to index-based ID if sanitization failed
        if not project_id:
            project_id = f"project_{index + 1}"

        return project_id

    def _create_relationship_configs(
        self,
        relations: List[DependencyRelation],
        project_id_map: Dict[str, str],
    ) -> List[RelationshipConfig]:
        """
        Create RelationshipConfig list from DependencyRelation list.

        Args:
            relations: List of dependency relations
            project_id_map: Mapping of project paths to IDs

        Returns:
            List of RelationshipConfig objects
        """
        relationship_configs = []
        seen_pairs = set()  # Avoid duplicates

        for relation in relations:
            # Get project IDs
            from_id = project_id_map.get(relation.from_project)
            to_id = project_id_map.get(relation.to_project)

            # Skip if either project not found
            if not from_id or not to_id:
                continue

            # Skip self-references
            if from_id == to_id:
                continue

            # Skip duplicates
            pair_key = (from_id, to_id, relation.relation_type)
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            # Map relation type to valid relationship type
            rel_type = self._map_relation_type(relation.relation_type)

            # Create description
            description = self._generate_relationship_description(
                from_id, to_id, rel_type, relation
            )

            # Create relationship config
            relationship_config = RelationshipConfig(
                from_project=from_id,
                to_project=to_id,
                type=rel_type,
                description=description,
                metadata=relation.metadata,
            )

            relationship_configs.append(relationship_config)

        # Also update project dependencies
        # Build dependency map
        dep_map = {}
        for rel_config in relationship_configs:
            if rel_config.from_project not in dep_map:
                dep_map[rel_config.from_project] = []
            if rel_config.to_project not in dep_map[rel_config.from_project]:
                dep_map[rel_config.from_project].append(rel_config.to_project)

        return relationship_configs

    def _map_relation_type(self, relation_type: str) -> str:
        """
        Map discovered relation type to valid RelationshipConfig type.

        Args:
            relation_type: Discovered relation type

        Returns:
            Valid relationship type
        """
        type_mapping = {
            "workspace": "dependency",
            "dependency": "dependency",
            "import": "imports",
            "api": "api_client",
            "semantic_similarity": "semantic_similarity",
        }

        return type_mapping.get(relation_type, "dependency")

    def _generate_relationship_description(
        self,
        from_id: str,
        to_id: str,
        rel_type: str,
        relation: DependencyRelation,
    ) -> Optional[str]:
        """
        Generate human-readable relationship description.

        Args:
            from_id: Source project ID
            to_id: Target project ID
            rel_type: Relationship type
            relation: Original dependency relation

        Returns:
            Generated description
        """
        descriptions = {
            "dependency": f"{from_id} depends on {to_id}",
            "imports": f"{from_id} imports code from {to_id}",
            "api_client": f"{from_id} calls {to_id} API",
            "semantic_similarity": f"{from_id} and {to_id} appear to be related projects",
        }

        base_desc = descriptions.get(rel_type, f"{from_id} relates to {to_id}")

        # Add confidence if low
        if relation.confidence < 0.8:
            base_desc += f" (confidence: {relation.confidence:.0%})"

        return base_desc
