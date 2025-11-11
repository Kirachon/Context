"""
Workspace Module

Multi-project workspace management with relationship tracking.
"""

from src.workspace.relationship_graph import (
    ProjectRelationshipGraph,
    ProjectMetadata,
    RelationshipMetadata,
    RelationshipType,
)

from src.workspace.relationship_discovery import (
    RelationshipDiscoveryEngine,
    ImportDiscovery,
    APIDiscovery,
    discover_project_relationships,
    discover_workspace_relationships,
)

__all__ = [
    "ProjectRelationshipGraph",
    "ProjectMetadata",
    "RelationshipMetadata",
    "RelationshipType",
    "RelationshipDiscoveryEngine",
    "ImportDiscovery",
    "APIDiscovery",
    "discover_project_relationships",
    "discover_workspace_relationships",
]
