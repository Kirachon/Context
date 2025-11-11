"""
Project Relationship Graph

Manages dependencies and relationships between projects in a workspace using NetworkX.
Supports multiple relationship types, transitive dependencies, cycle detection,
semantic similarity, caching, serialization, and visualization.
"""

import json
import logging
from typing import Dict, List, Tuple, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass, asdict, field
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import networkx, but gracefully degrade if not available
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logger.warning("NetworkX not available - using simple graph implementation")


class RelationshipType(str, Enum):
    """Types of relationships between projects"""
    IMPORTS = "imports"
    API_CLIENT = "api_client"
    SHARED_DATABASE = "shared_database"
    EVENT_DRIVEN = "event_driven"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    DEPENDENCY = "dependency"


@dataclass
class ProjectMetadata:
    """Metadata for a project node"""
    id: str
    name: str
    path: str
    type: str = "application"
    language: List[str] = field(default_factory=list)
    framework: Optional[str] = None
    version: Optional[str] = None
    priority: str = "medium"
    indexed: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectMetadata":
        """Create from dictionary"""
        if "language" in data and isinstance(data["language"], str):
            data["language"] = [data["language"]]
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RelationshipMetadata:
    """Metadata for a relationship edge"""
    type: RelationshipType
    weight: float = 1.0
    description: Optional[str] = None
    source_files: Optional[List[str]] = None
    target_modules: Optional[List[str]] = None
    api_endpoints: Optional[List[str]] = None
    similarity_score: Optional[float] = None
    discovered: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data["type"] = self.type.value if isinstance(self.type, RelationshipType) else self.type
        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RelationshipMetadata":
        """Create from dictionary"""
        if "type" in data:
            data["type"] = RelationshipType(data["type"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class SimpleGraph:
    """
    Simple directed graph implementation as fallback when NetworkX is not available
    """

    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._out_edges: Dict[str, Set[str]] = {}
        self._in_edges: Dict[str, Set[str]] = {}

    def add_node(self, node: str, **kwargs):
        """Add a node to the graph"""
        self.nodes[node] = kwargs
        if node not in self._out_edges:
            self._out_edges[node] = set()
        if node not in self._in_edges:
            self._in_edges[node] = set()

    def add_edge(self, from_node: str, to_node: str, **kwargs):
        """Add an edge to the graph"""
        if from_node not in self.nodes:
            self.add_node(from_node)
        if to_node not in self.nodes:
            self.add_node(to_node)
        self.edges[(from_node, to_node)] = kwargs
        self._out_edges[from_node].add(to_node)
        self._in_edges[to_node].add(from_node)

    def remove_node(self, node: str):
        """Remove a node from the graph"""
        if node in self.nodes:
            for target in list(self._out_edges.get(node, [])):
                self.remove_edge(node, target)
            for source in list(self._in_edges.get(node, [])):
                self.remove_edge(source, node)
            del self.nodes[node]
            if node in self._out_edges:
                del self._out_edges[node]
            if node in self._in_edges:
                del self._in_edges[node]

    def remove_edge(self, from_node: str, to_node: str):
        """Remove an edge from the graph"""
        key = (from_node, to_node)
        if key in self.edges:
            del self.edges[key]
            self._out_edges[from_node].discard(to_node)
            self._in_edges[to_node].discard(from_node)

    def has_node(self, node: str) -> bool:
        """Check if node exists"""
        return node in self.nodes

    def has_edge(self, from_node: str, to_node: str) -> bool:
        """Check if edge exists"""
        return (from_node, to_node) in self.edges

    def successors(self, node: str) -> List[str]:
        """Get successors of a node"""
        return list(self._out_edges.get(node, []))

    def predecessors(self, node: str) -> List[str]:
        """Get predecessors of a node"""
        return list(self._in_edges.get(node, []))

    def degree(self, node: str) -> int:
        """Get degree of a node"""
        return len(self._out_edges.get(node, [])) + len(self._in_edges.get(node, []))

    def in_degree(self) -> List[Tuple[str, int]]:
        """Get in-degree for all nodes"""
        return [(node, len(self._in_edges.get(node, []))) for node in self.nodes]

    def out_degree(self) -> List[Tuple[str, int]]:
        """Get out-degree for all nodes"""
        return [(node, len(self._out_edges.get(node, []))) for node in self.nodes]

    def number_of_nodes(self) -> int:
        """Get number of nodes"""
        return len(self.nodes)

    def number_of_edges(self) -> int:
        """Get number of edges"""
        return len(self.edges)

    def get_edge_data(self, from_node: str, to_node: str) -> Optional[Dict[str, Any]]:
        """Get edge data"""
        return self.edges.get((from_node, to_node))


class ProjectRelationshipGraph:
    """
    Graph of relationships between projects

    Tracks dependencies, imports, and semantic relationships using NetworkX
    or a simple fallback implementation.
    """

    def __init__(self):
        """Initialize relationship graph"""
        if NETWORKX_AVAILABLE:
            self.graph = nx.DiGraph()
            logger.info("ProjectRelationshipGraph initialized with NetworkX")
        else:
            self.graph = SimpleGraph()
            logger.info("ProjectRelationshipGraph initialized with simple graph")

        self._semantic_similarity_cache: Dict[Tuple[str, str], float] = {}
        self._dependency_cache: Dict[str, Set[str]] = {}
        self._cache_valid = True
        self.stats = {
            "relationships_added": 0,
            "projects_added": 0,
            "discoveries_performed": 0,
        }

    # ==================== Node Operations ====================

    def add_project(self, project_metadata: ProjectMetadata) -> None:
        """
        Add a project node to the graph.

        Args:
            project_metadata: Project metadata
        """
        if not project_metadata.created_at:
            project_metadata.created_at = datetime.utcnow().isoformat()

        self.graph.add_node(project_metadata.id, **project_metadata.to_dict())
        self.stats["projects_added"] += 1
        self._invalidate_cache()
        logger.debug(f"Added project to graph: {project_metadata.id}")

    def remove_project(self, project_id: str) -> None:
        """
        Remove a project from the graph.

        Args:
            project_id: Project ID to remove
        """
        if NETWORKX_AVAILABLE:
            if project_id in self.graph:
                self.graph.remove_node(project_id)
                self._invalidate_cache()
                logger.debug(f"Removed project from graph: {project_id}")
        else:
            if self.graph.has_node(project_id):
                self.graph.remove_node(project_id)
                self._invalidate_cache()
                logger.debug(f"Removed project from graph: {project_id}")

    def update_project(self, project_id: str, metadata: Dict[str, Any]) -> None:
        """
        Update project metadata.

        Args:
            project_id: Project ID
            metadata: Metadata to update
        """
        if NETWORKX_AVAILABLE:
            if project_id in self.graph:
                self.graph.nodes[project_id].update(metadata)
                self.graph.nodes[project_id]["updated_at"] = datetime.utcnow().isoformat()
        else:
            if self.graph.has_node(project_id):
                self.graph.nodes[project_id].update(metadata)
                self.graph.nodes[project_id]["updated_at"] = datetime.utcnow().isoformat()

    def get_project(self, project_id: str) -> Optional[ProjectMetadata]:
        """
        Get project metadata.

        Args:
            project_id: Project ID

        Returns:
            Project metadata or None if not found
        """
        if NETWORKX_AVAILABLE:
            if project_id not in self.graph:
                return None
            return ProjectMetadata.from_dict(dict(self.graph.nodes[project_id]))
        else:
            if not self.graph.has_node(project_id):
                return None
            return ProjectMetadata.from_dict(self.graph.nodes[project_id])

    def list_projects(self) -> List[ProjectMetadata]:
        """
        List all projects in the graph.

        Returns:
            List of project metadata
        """
        projects = []
        if NETWORKX_AVAILABLE:
            for node in self.graph.nodes():
                projects.append(ProjectMetadata.from_dict(dict(self.graph.nodes[node])))
        else:
            for node, data in self.graph.nodes.items():
                projects.append(ProjectMetadata.from_dict(data))
        return projects

    # ==================== Edge Operations ====================

    def add_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: RelationshipType,
        metadata: Optional[Dict[str, Any]] = None,
        weight: float = 1.0,
        description: Optional[str] = None
    ) -> None:
        """
        Add explicit relationship from workspace config

        Args:
            from_id: Source project ID
            to_id: Target project ID
            rel_type: Type of relationship
            metadata: Additional relationship metadata
            weight: Relationship weight (for ranking)
            description: Human-readable description
        """
        has_from = self.graph.has_node(from_id) if not NETWORKX_AVAILABLE else from_id in self.graph
        has_to = self.graph.has_node(to_id) if not NETWORKX_AVAILABLE else to_id in self.graph

        if not has_from or not has_to:
            raise ValueError(f"Both projects must exist in the graph: {from_id}, {to_id}")

        # Create relationship metadata
        rel_metadata = RelationshipMetadata(
            type=rel_type,
            weight=weight,
            description=description,
            created_at=datetime.utcnow().isoformat()
        )

        # Add custom metadata if provided
        if metadata:
            for key, value in metadata.items():
                if hasattr(rel_metadata, key):
                    setattr(rel_metadata, key, value)

        # Add edge to graph
        self.graph.add_edge(from_id, to_id, **rel_metadata.to_dict())
        self.stats["relationships_added"] += 1
        self._invalidate_cache()
        logger.debug(f"Added relationship: {from_id} -> {to_id} ({rel_type.value})")

    def get_dependencies(self, project_id: str, depth: int = 1) -> List[str]:
        """
        Get all dependencies of a project (projects it depends on)

        Args:
            project_id: Project identifier
            depth: Transitive depth (1 = direct dependencies only)

        Returns:
            List of project IDs
        """
        if not self.graph.has_node(project_id):
            return []

        dependencies = set()

        # Direct dependencies (successors in the graph)
        if NETWORKX_AVAILABLE:
            direct_deps = list(self.graph.successors(project_id))
        else:
            direct_deps = self.graph.successors(project_id)

        dependencies.update(direct_deps)

        # Transitive dependencies
        if depth > 1:
            for dep in direct_deps:
                transitive = self.get_dependencies(dep, depth - 1)
                dependencies.update(transitive)

        return list(dependencies)

    def get_dependents(self, project_id: str) -> List[str]:
        """
        Get all projects that depend on this project

        Args:
            project_id: Project identifier

        Returns:
            List of project IDs
        """
        if not self.graph.has_node(project_id):
            return []

        if NETWORKX_AVAILABLE:
            return list(self.graph.predecessors(project_id))
        else:
            return self.graph.predecessors(project_id)

    def get_related_projects(
        self, project_id: str, threshold: float = 0.7
    ) -> List[Tuple[str, float]]:
        """
        Get semantically related projects with similarity scores

        Args:
            project_id: Project identifier
            threshold: Minimum similarity score (0.0-1.0)

        Returns:
            List of (project_id, similarity_score) tuples
        """
        if not self.graph.has_node(project_id):
            return []

        related = []

        # Check semantic similarity edges
        if NETWORKX_AVAILABLE:
            for neighbor in self.graph.neighbors(project_id):
                edge_data = self.graph.get_edge_data(project_id, neighbor)
                if edge_data and edge_data.get("type") == RelationshipType.SEMANTIC_SIMILARITY.value:
                    weight = edge_data.get("weight", 0.0)
                    if weight >= threshold:
                        related.append((neighbor, weight))
        else:
            # For simple graph, iterate through edges
            for neighbor in self.graph.successors(project_id):
                edge_data = self.graph.get_edge_data(project_id, neighbor)
                if edge_data and edge_data.get("type") == RelationshipType.SEMANTIC_SIMILARITY.value:
                    weight = edge_data.get("weight", 0.0)
                    if weight >= threshold:
                        related.append((neighbor, weight))

        # Sort by similarity score (descending)
        related.sort(key=lambda x: x[1], reverse=True)
        return related

    async def discover_relationships(self, project_id: str, project_path: str) -> None:
        """
        Auto-discover implicit relationships via import analysis

        Note: Full implementation would require:
        - Import statement analysis (AST parsing)
        - Cross-file reference detection
        - Semantic similarity computation (embeddings)

        This is a placeholder for future enhancement.

        Args:
            project_id: Project identifier
            project_path: Path to project root
        """
        self.stats["discoveries_performed"] += 1
        logger.debug(f"Relationship discovery for {project_id} - placeholder (not implemented)")
        # TODO: Implement import analysis, cross-reference detection, etc.

    async def compute_semantic_similarity(self, project_a: str, project_b: str) -> float:
        """
        Compute embedding-based similarity between projects

        Note: Full implementation would require:
        - Project-level embeddings (aggregate of file embeddings)
        - Cosine similarity computation
        - Caching for performance

        This is a placeholder for future enhancement.

        Args:
            project_a: First project ID
            project_b: Second project ID

        Returns:
            Similarity score (0.0-1.0)
        """
        # Check cache
        cache_key = tuple(sorted([project_a, project_b]))
        if cache_key in self.semantic_similarity_cache:
            return self.semantic_similarity_cache[cache_key]

        # Placeholder: return 0.0 (no similarity)
        similarity = 0.0
        self.semantic_similarity_cache[cache_key] = similarity

        logger.debug(f"Semantic similarity {project_a} <-> {project_b}: {similarity} (placeholder)")
        return similarity

    def get_relationship_boost_factors(
        self, source_project: str, boost_factor: float = 1.5
    ) -> Dict[str, float]:
        """
        Calculate boost factors for projects related to source project

        Used in workspace search to rank results from related projects higher.

        Args:
            source_project: Source project ID
            boost_factor: Boost multiplier for related projects

        Returns:
            Dict mapping project_id -> boost_factor
        """
        boosts = {}

        if not self.graph.has_node(source_project):
            return boosts

        # Direct dependencies get full boost
        dependencies = self.get_dependencies(source_project, depth=1)
        for dep in dependencies:
            boosts[dep] = boost_factor

        # Transitive dependencies get reduced boost
        transitive_deps = self.get_dependencies(source_project, depth=2)
        for dep in transitive_deps:
            if dep not in boosts:  # Don't override direct dependencies
                boosts[dep] = boost_factor * 0.7

        # Dependents get moderate boost
        dependents = self.get_dependents(source_project)
        for dep in dependents:
            if dep not in boosts:
                boosts[dep] = boost_factor * 0.8

        # Related projects get slight boost
        related = self.get_related_projects(source_project, threshold=0.7)
        for project, similarity in related:
            if project not in boosts:
                boosts[project] = 1.0 + (boost_factor - 1.0) * similarity

        return boosts

    def has_relationship(self, from_id: str, to_id: str) -> bool:
        """
        Check if a relationship exists between two projects (bidirectional)

        Args:
            from_id: Source project ID
            to_id: Target project ID

        Returns:
            True if any relationship exists between projects
        """
        if not self.graph.has_node(from_id) or not self.graph.has_node(to_id):
            return False

        # Check direct relationship
        if NETWORKX_AVAILABLE:
            if self.graph.has_edge(from_id, to_id) or self.graph.has_edge(to_id, from_id):
                return True
        else:
            if to_id in self.graph.successors(from_id) or from_id in self.graph.successors(to_id):
                return True

        # Check semantic similarity cache
        cache_key = tuple(sorted([from_id, to_id]))
        if cache_key in self.semantic_similarity_cache:
            return self.semantic_similarity_cache[cache_key] > 0.5

        return False

    def get_project_context(self, project_id: str) -> Dict[str, Any]:
        """
        Get complete context for a project (dependencies, dependents, relationships)

        Args:
            project_id: Project identifier

        Returns:
            Context dictionary
        """
        if not self.graph.has_node(project_id):
            return {
                "project_id": project_id,
                "exists": False,
            }

        return {
            "project_id": project_id,
            "exists": True,
            "dependencies": self.get_dependencies(project_id, depth=1),
            "transitive_dependencies": self.get_dependencies(project_id, depth=2),
            "dependents": self.get_dependents(project_id),
            "related_projects": self.get_related_projects(project_id, threshold=0.7),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get relationship graph statistics"""
        if NETWORKX_AVAILABLE:
            num_nodes = self.graph.number_of_nodes()
            num_edges = self.graph.number_of_edges()
        else:
            num_nodes = len(self.graph.nodes)
            num_edges = sum(len(edges) for edges in self.graph.edges.values())

        return {
            "projects": num_nodes,
            "relationships": num_edges,
            "relationships_added": self.stats["relationships_added"],
            "projects_added": self.stats["projects_added"],
            "discoveries_performed": self.stats["discoveries_performed"],
            "using_networkx": NETWORKX_AVAILABLE,
        }

    # ==================== Cycle Detection ====================

    def detect_circular_dependencies(self) -> List[List[str]]:
        """
        Detect circular dependencies in the graph.

        Returns:
            List of cycles, where each cycle is a list of project IDs
        """
        if not NETWORKX_AVAILABLE:
            # Simple DFS-based cycle detection
            cycles = []
            visited = set()
            rec_stack = set()

            def dfs_cycle(node, path):
                visited.add(node)
                rec_stack.add(node)
                path.append(node)

                for neighbor in self.graph.successors(node):
                    if neighbor not in visited:
                        dfs_cycle(neighbor, path.copy())
                    elif neighbor in rec_stack:
                        cycle_start = path.index(neighbor)
                        cycles.append(path[cycle_start:] + [neighbor])

                rec_stack.remove(node)

            for node in self.graph.nodes:
                if node not in visited:
                    dfs_cycle(node, [])

            return cycles

        try:
            cycles = list(nx.simple_cycles(self.graph))
            return cycles
        except Exception as e:
            logger.error(f"Error detecting cycles: {e}")
            return []

    def has_circular_dependencies(self) -> bool:
        """
        Check if the graph has any circular dependencies.

        Returns:
            True if cycles exist, False otherwise
        """
        if NETWORKX_AVAILABLE:
            return not nx.is_directed_acyclic_graph(self.graph)
        else:
            return len(self.detect_circular_dependencies()) > 0

    def get_topological_order(self) -> Optional[List[str]]:
        """
        Get topological ordering of projects (build/dependency order).

        Returns:
            List of project IDs in topological order, or None if cycles exist
        """
        if self.has_circular_dependencies():
            return None

        if not NETWORKX_AVAILABLE:
            # Kahn's algorithm for topological sort
            in_degree = {node: 0 for node in self.graph.nodes}
            for (from_node, to_node) in self.graph.edges:
                in_degree[to_node] += 1

            queue = [node for node, degree in in_degree.items() if degree == 0]
            result = []

            while queue:
                node = queue.pop(0)
                result.append(node)

                for neighbor in self.graph.successors(node):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

            return result if len(result) == len(self.graph.nodes) else None

        try:
            return list(nx.topological_sort(self.graph))
        except nx.NetworkXError:
            return None

    # ==================== Graph Statistics ====================

    def get_graph_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive graph statistics.

        Returns:
            Dictionary with graph metrics
        """
        stats = {
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "has_cycles": self.has_circular_dependencies(),
            "is_dag": not self.has_circular_dependencies(),
            "relationship_types": {},
            "projects_by_type": {},
            "projects_by_language": {},
            "isolated_projects": [],
        }

        # Calculate density
        n = stats["node_count"]
        stats["density"] = stats["edge_count"] / (n * (n - 1)) if n > 1 else 0.0

        # Count relationship types and project types
        if NETWORKX_AVAILABLE:
            for _, _, data in self.graph.edges(data=True):
                rel_type = data.get("type", "unknown")
                stats["relationship_types"][rel_type] = stats["relationship_types"].get(rel_type, 0) + 1

            for node, data in self.graph.nodes(data=True):
                project_type = data.get("type", "unknown")
                stats["projects_by_type"][project_type] = stats["projects_by_type"].get(project_type, 0) + 1

                languages = data.get("language", [])
                if isinstance(languages, list):
                    for lang in languages:
                        stats["projects_by_language"][lang] = stats["projects_by_language"].get(lang, 0) + 1

                if self.graph.degree(node) == 0:
                    stats["isolated_projects"].append(node)

            if stats["node_count"] > 0:
                in_degrees = [d for _, d in self.graph.in_degree()]
                out_degrees = [d for _, d in self.graph.out_degree()]
                stats["avg_in_degree"] = sum(in_degrees) / len(in_degrees)
                stats["avg_out_degree"] = sum(out_degrees) / len(out_degrees)
            else:
                stats["avg_in_degree"] = 0
                stats["avg_out_degree"] = 0
        else:
            for (from_id, to_id), data in self.graph.edges.items():
                rel_type = data.get("type", "unknown")
                stats["relationship_types"][rel_type] = stats["relationship_types"].get(rel_type, 0) + 1

            for node, data in self.graph.nodes.items():
                project_type = data.get("type", "unknown")
                stats["projects_by_type"][project_type] = stats["projects_by_type"].get(project_type, 0) + 1

                languages = data.get("language", [])
                if isinstance(languages, list):
                    for lang in languages:
                        stats["projects_by_language"][lang] = stats["projects_by_language"].get(lang, 0) + 1

                if self.graph.degree(node) == 0:
                    stats["isolated_projects"].append(node)

            if stats["node_count"] > 0:
                in_degrees = [d for _, d in self.graph.in_degree()]
                out_degrees = [d for _, d in self.graph.out_degree()]
                stats["avg_in_degree"] = sum(in_degrees) / len(in_degrees) if in_degrees else 0
                stats["avg_out_degree"] = sum(out_degrees) / len(out_degrees) if out_degrees else 0
            else:
                stats["avg_in_degree"] = 0
                stats["avg_out_degree"] = 0

        return stats

    # ==================== Serialization ====================

    def to_json(self, file_path: Optional[str] = None) -> str:
        """
        Serialize graph to JSON format.

        Args:
            file_path: Optional file path to save JSON

        Returns:
            JSON string representation
        """
        if NETWORKX_AVAILABLE:
            data = nx.node_link_data(self.graph)
        else:
            data = {
                "directed": True,
                "multigraph": False,
                "graph": {},
                "nodes": [{"id": node, **attrs} for node, attrs in self.graph.nodes.items()],
                "links": [
                    {"source": from_id, "target": to_id, **attrs}
                    for (from_id, to_id), attrs in self.graph.edges.items()
                ],
            }

        data["metadata"] = {
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "using_networkx": NETWORKX_AVAILABLE,
        }

        json_str = json.dumps(data, indent=2, default=str)

        if file_path:
            with open(file_path, "w") as f:
                f.write(json_str)
            logger.info(f"Saved graph to {file_path}")

        return json_str

    @classmethod
    def from_json(cls, json_str: Optional[str] = None, file_path: Optional[str] = None) -> "ProjectRelationshipGraph":
        """
        Deserialize graph from JSON format.

        Args:
            json_str: JSON string (takes precedence)
            file_path: Path to JSON file

        Returns:
            ProjectRelationshipGraph instance
        """
        if json_str:
            data = json.loads(json_str)
        elif file_path:
            with open(file_path, "r") as f:
                data = json.load(f)
        else:
            raise ValueError("Either json_str or file_path must be provided")

        graph_obj = cls()

        if NETWORKX_AVAILABLE:
            graph_obj.graph = nx.node_link_graph(data)
        else:
            for node in data.get("nodes", []):
                node_id = node.pop("id")
                graph_obj.graph.add_node(node_id, **node)

            for link in data.get("links", []):
                from_id = link.pop("source")
                to_id = link.pop("target")
                graph_obj.graph.add_edge(from_id, to_id, **link)

        logger.info(f"Loaded graph with {graph_obj.graph.number_of_nodes()} nodes and {graph_obj.graph.number_of_edges()} edges")
        return graph_obj

    # ==================== Visualization ====================

    def export_dot(self, file_path: Optional[str] = None) -> str:
        """
        Export graph to DOT format for Graphviz visualization.

        Args:
            file_path: Optional file path to save DOT file

        Returns:
            DOT format string
        """
        dot_lines = ["digraph ProjectRelationships {"]
        dot_lines.append("  rankdir=LR;")
        dot_lines.append("  node [shape=box, style=rounded];")
        dot_lines.append("")

        # Add nodes
        if NETWORKX_AVAILABLE:
            for node, data in self.graph.nodes(data=True):
                label = data.get("name", node)
                project_type = data.get("type", "unknown")
                color = self._get_node_color(project_type)
                dot_lines.append(
                    f'  "{node}" [label="{label}", fillcolor="{color}", style="filled,rounded"];'
                )
        else:
            for node, data in self.graph.nodes.items():
                label = data.get("name", node)
                project_type = data.get("type", "unknown")
                color = self._get_node_color(project_type)
                dot_lines.append(
                    f'  "{node}" [label="{label}", fillcolor="{color}", style="filled,rounded"];'
                )

        dot_lines.append("")

        # Add edges
        if NETWORKX_AVAILABLE:
            for from_id, to_id, data in self.graph.edges(data=True):
                rel_type = data.get("type", "unknown")
                weight = data.get("weight", 1.0)
                label = rel_type
                style = self._get_edge_style(rel_type)
                thickness = max(1, int(weight * 3))
                dot_lines.append(
                    f'  "{from_id}" -> "{to_id}" [label="{label}", style="{style}", penwidth={thickness}];'
                )
        else:
            for (from_id, to_id), data in self.graph.edges.items():
                rel_type = data.get("type", "unknown")
                weight = data.get("weight", 1.0)
                label = rel_type
                style = self._get_edge_style(rel_type)
                thickness = max(1, int(weight * 3))
                dot_lines.append(
                    f'  "{from_id}" -> "{to_id}" [label="{label}", style="{style}", penwidth={thickness}];'
                )

        dot_lines.append("}")
        dot_str = "\n".join(dot_lines)

        if file_path:
            with open(file_path, "w") as f:
                f.write(dot_str)
            logger.info(f"Exported DOT file to {file_path}")

        return dot_str

    def _get_node_color(self, project_type: str) -> str:
        """Get color for node based on project type"""
        colors = {
            "web_frontend": "lightblue",
            "api_server": "lightgreen",
            "library": "lightyellow",
            "documentation": "lightgray",
            "database": "lightcoral",
            "microservice": "lightpink",
        }
        return colors.get(project_type, "white")

    def _get_edge_style(self, rel_type: str) -> str:
        """Get style for edge based on relationship type"""
        styles = {
            RelationshipType.IMPORTS.value: "solid",
            RelationshipType.API_CLIENT.value: "dashed",
            RelationshipType.SHARED_DATABASE.value: "dotted",
            RelationshipType.EVENT_DRIVEN.value: "bold",
            RelationshipType.SEMANTIC_SIMILARITY.value: "dashed",
            RelationshipType.DEPENDENCY.value: "solid",
        }
        return styles.get(rel_type, "solid")

    # ==================== Cache Management ====================

    def _invalidate_cache(self) -> None:
        """Invalidate all caches"""
        self._cache_valid = False
        self._dependency_cache.clear()

    def refresh_cache(self) -> None:
        """Refresh all caches"""
        self._invalidate_cache()
        self._cache_valid = True

    def clear_similarity_cache(self) -> None:
        """Clear the semantic similarity cache"""
        self._semantic_similarity_cache.clear()
        logger.debug("Cleared semantic similarity cache")

    # ==================== Path Finding ====================

    def find_path(self, from_id: str, to_id: str) -> Optional[List[str]]:
        """
        Find shortest path between two projects.

        Args:
            from_id: Source project ID
            to_id: Target project ID

        Returns:
            List of project IDs in path, or None if no path exists
        """
        has_from = self.graph.has_node(from_id) if not NETWORKX_AVAILABLE else from_id in self.graph
        has_to = self.graph.has_node(to_id) if not NETWORKX_AVAILABLE else to_id in self.graph

        if not has_from or not has_to:
            return None

        if NETWORKX_AVAILABLE:
            try:
                return nx.shortest_path(self.graph, from_id, to_id)
            except nx.NetworkXNoPath:
                return None
        else:
            # Simple BFS for shortest path
            queue = [(from_id, [from_id])]
            visited = {from_id}

            while queue:
                current, path = queue.pop(0)
                if current == to_id:
                    return path

                for neighbor in self.graph.successors(current):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, path + [neighbor]))

            return None

    def find_all_paths(self, from_id: str, to_id: str, max_paths: int = 10) -> List[List[str]]:
        """
        Find all simple paths between two projects.

        Args:
            from_id: Source project ID
            to_id: Target project ID
            max_paths: Maximum number of paths to return

        Returns:
            List of paths, where each path is a list of project IDs
        """
        has_from = self.graph.has_node(from_id) if not NETWORKX_AVAILABLE else from_id in self.graph
        has_to = self.graph.has_node(to_id) if not NETWORKX_AVAILABLE else to_id in self.graph

        if not has_from or not has_to:
            return []

        if NETWORKX_AVAILABLE:
            try:
                paths = nx.all_simple_paths(self.graph, from_id, to_id)
                return list(paths)[:max_paths]
            except nx.NetworkXNoPath:
                return []
        else:
            # DFS to find all simple paths
            all_paths = []

            def dfs(current, target, path, visited):
                if current == target:
                    all_paths.append(path.copy())
                    return

                if len(all_paths) >= max_paths:
                    return

                for neighbor in self.graph.successors(current):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        path.append(neighbor)
                        dfs(neighbor, target, path, visited)
                        path.pop()
                        visited.remove(neighbor)

            dfs(from_id, to_id, [from_id], {from_id})
            return all_paths

    # ==================== Additional Methods ====================

    def remove_relationship(self, from_id: str, to_id: str) -> None:
        """
        Remove a relationship edge.

        Args:
            from_id: Source project ID
            to_id: Target project ID
        """
        if NETWORKX_AVAILABLE:
            if self.graph.has_edge(from_id, to_id):
                self.graph.remove_edge(from_id, to_id)
                self._invalidate_cache()
                logger.debug(f"Removed relationship: {from_id} -> {to_id}")
        else:
            if self.graph.has_edge(from_id, to_id):
                self.graph.remove_edge(from_id, to_id)
                self._invalidate_cache()
                logger.debug(f"Removed relationship: {from_id} -> {to_id}")

    def get_relationship(self, from_id: str, to_id: str) -> Optional[RelationshipMetadata]:
        """
        Get relationship metadata.

        Args:
            from_id: Source project ID
            to_id: Target project ID

        Returns:
            Relationship metadata or None if not found
        """
        if NETWORKX_AVAILABLE:
            if not self.graph.has_edge(from_id, to_id):
                return None
            return RelationshipMetadata.from_dict(dict(self.graph.edges[from_id, to_id]))
        else:
            if not self.graph.has_edge(from_id, to_id):
                return None
            return RelationshipMetadata.from_dict(self.graph.edges[(from_id, to_id)])

    def list_relationships(self, project_id: Optional[str] = None) -> List[Tuple[str, str, RelationshipMetadata]]:
        """
        List relationships, optionally filtered by project.

        Args:
            project_id: Optional project ID to filter by

        Returns:
            List of (from_id, to_id, metadata) tuples
        """
        edges = []

        if NETWORKX_AVAILABLE:
            if project_id:
                for _, to_id in self.graph.out_edges(project_id):
                    metadata = RelationshipMetadata.from_dict(dict(self.graph.edges[project_id, to_id]))
                    edges.append((project_id, to_id, metadata))
                for from_id, _ in self.graph.in_edges(project_id):
                    metadata = RelationshipMetadata.from_dict(dict(self.graph.edges[from_id, project_id]))
                    edges.append((from_id, project_id, metadata))
            else:
                for from_id, to_id in self.graph.edges():
                    metadata = RelationshipMetadata.from_dict(dict(self.graph.edges[from_id, to_id]))
                    edges.append((from_id, to_id, metadata))
        else:
            for (from_id, to_id), data in self.graph.edges.items():
                if project_id is None or from_id == project_id or to_id == project_id:
                    metadata = RelationshipMetadata.from_dict(data)
                    edges.append((from_id, to_id, metadata))

        return edges
