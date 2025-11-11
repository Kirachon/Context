# Project Relationship Graph - Quick API Reference

## Installation

```bash
pip install networkx  # Already installed: NetworkX 3.5
```

## Import

```python
from src.workspace import (
    ProjectRelationshipGraph,
    ProjectMetadata,
    RelationshipMetadata,
    RelationshipType,
    discover_workspace_relationships,
)
```

## Core Classes

### ProjectMetadata

```python
project = ProjectMetadata(
    id="my-project",              # Required: Unique ID
    name="My Project",            # Required: Display name
    path="/path/to/project",      # Required: Filesystem path
    type="web_frontend",          # Optional: Project type
    language=["typescript"],      # Optional: List of languages
    framework="react",            # Optional: Framework name
    version="1.0.0",             # Optional: Version
    priority="high",             # Optional: low/medium/high/critical
    indexed=False,               # Optional: Indexing status
)
```

### RelationshipType (Enum)

```python
RelationshipType.IMPORTS              # Code imports
RelationshipType.API_CLIENT          # REST/GraphQL API
RelationshipType.SHARED_DATABASE     # Shared data
RelationshipType.EVENT_DRIVEN        # Message queue
RelationshipType.SEMANTIC_SIMILARITY # Embedding similarity
RelationshipType.DEPENDENCY          # Package dependency
```

## ProjectRelationshipGraph API

### Node Operations

```python
graph = ProjectRelationshipGraph()

# Add project
graph.add_project(project_metadata)

# Get project
project = graph.get_project("project-id")

# List all projects
projects = graph.list_projects()

# Update project
graph.update_project("project-id", {"indexed": True})

# Remove project
graph.remove_project("project-id")
```

### Edge Operations

```python
# Add relationship
graph.add_relationship(
    from_id="frontend",
    to_id="backend",
    rel_type=RelationshipType.API_CLIENT,
    weight=0.9,                    # 0.0-1.0, default: 1.0
    description="Frontend calls API",
    metadata={                     # Optional custom data
        "api_endpoints": ["/api/users"],
    }
)

# Get relationship
rel = graph.get_relationship("frontend", "backend")

# List relationships (all or for specific project)
all_rels = graph.list_relationships()
project_rels = graph.list_relationships("frontend")

# Remove relationship
graph.remove_relationship("frontend", "backend")
```

### Dependency Analysis

```python
# Get dependencies (direct)
deps = graph.get_dependencies("project-id", depth=1)

# Get transitive dependencies
deps = graph.get_dependencies("project-id", depth=2)

# Get reverse dependencies (who depends on me)
dependents = graph.get_dependents("project-id")

# Get related projects by similarity
related = graph.get_related_projects(
    "project-id",
    threshold=0.7  # Minimum similarity score
)
# Returns: [(project_id, score), ...]
```

### Cycle Detection

```python
# Check for cycles
has_cycles = graph.has_circular_dependencies()

# Detect all cycles
cycles = graph.detect_circular_dependencies()
# Returns: [['a', 'b', 'c'], ...]

# Get topological order (build order)
order = graph.get_topological_order()
# Returns: ['project1', 'project2', ...] or None if cycles exist
```

### Graph Statistics

```python
stats = graph.get_graph_stats()

# Returns dict with:
# - node_count: int
# - edge_count: int
# - density: float
# - has_cycles: bool
# - is_dag: bool
# - relationship_types: Dict[str, int]
# - projects_by_type: Dict[str, int]
# - projects_by_language: Dict[str, int]
# - isolated_projects: List[str]
# - avg_in_degree: float
# - avg_out_degree: float
```

### Path Finding

```python
# Shortest path
path = graph.find_path("project-a", "project-z")
# Returns: ['project-a', 'project-b', ..., 'project-z']

# All simple paths
paths = graph.find_all_paths("project-a", "project-z", max_paths=10)
# Returns: [['a', 'b', 'z'], ['a', 'c', 'z'], ...]
```

### Serialization

```python
# Save to JSON
json_str = graph.to_json("/path/to/graph.json")

# Load from JSON
graph = ProjectRelationshipGraph.from_json(file_path="/path/to/graph.json")

# Or from string
graph = ProjectRelationshipGraph.from_json(json_str=json_str)
```

### Visualization

```python
# Export to Graphviz DOT
dot_str = graph.export_dot("/path/to/graph.dot")

# Render with Graphviz (if installed)
# dot -Tpng graph.dot -o graph.png
```

### Caching

```python
# Clear similarity cache
graph.clear_similarity_cache()

# Refresh all caches
graph.refresh_cache()

# Cache is automatically invalidated on updates
```

### Semantic Similarity

```python
# Compute similarity (requires embeddings)
similarity = await graph.compute_semantic_similarity(
    "project-a",
    "project-b",
    embeddings_a=[...],  # Optional: pre-computed
    embeddings_b=[...],  # Optional: pre-computed
)
# Returns: 0.0-1.0
```

## Auto-Discovery API

```python
from src.workspace import discover_workspace_relationships

# Discover relationships for all projects
summary = await discover_workspace_relationships(
    graph,
    projects=[project1, project2, ...]
)

# Returns dict with:
# - projects_analyzed: int
# - total_imports: int
# - total_api_calls: int
# - total_relationships: int
# - results_by_project: Dict[str, Any]
```

## Complete Example

```python
import asyncio
from src.workspace import (
    ProjectRelationshipGraph,
    ProjectMetadata,
    RelationshipType,
    discover_workspace_relationships,
)

async def main():
    # Create graph
    graph = ProjectRelationshipGraph()
    
    # Add projects
    frontend = ProjectMetadata(
        id="frontend",
        name="Frontend App",
        path="/projects/frontend",
        type="web_frontend",
        language=["typescript", "tsx"],
        framework="react",
    )
    
    backend = ProjectMetadata(
        id="backend",
        name="Backend API",
        path="/projects/backend",
        type="api_server",
        language=["python"],
        framework="fastapi",
    )
    
    graph.add_project(frontend)
    graph.add_project(backend)
    
    # Manual relationship
    graph.add_relationship(
        from_id="frontend",
        to_id="backend",
        rel_type=RelationshipType.API_CLIENT,
        description="Frontend calls backend API",
        weight=0.9,
    )
    
    # Auto-discover relationships
    projects = [frontend, backend]
    summary = await discover_workspace_relationships(graph, projects)
    
    print(f"Discovered {summary['total_relationships']} relationships")
    
    # Query dependencies
    deps = graph.get_dependencies("frontend")
    print(f"Frontend depends on: {deps}")
    
    # Check for cycles
    if graph.has_circular_dependencies():
        print("Warning: Circular dependencies detected!")
        print(f"Cycles: {graph.detect_circular_dependencies()}")
    
    # Get statistics
    stats = graph.get_graph_stats()
    print(f"Graph has {stats['node_count']} projects and {stats['edge_count']} relationships")
    
    # Export visualization
    graph.export_dot("/tmp/graph.dot")
    
    # Save graph
    graph.to_json("/tmp/graph.json")

if __name__ == "__main__":
    asyncio.run(main())
```

## Error Handling

```python
# Projects must exist before adding relationships
try:
    graph.add_relationship("unknown1", "unknown2", RelationshipType.IMPORTS)
except ValueError as e:
    print(f"Error: {e}")  # Both projects must exist in the graph

# Robust file operations
try:
    summary = await discover_workspace_relationships(graph, projects)
except FileNotFoundError:
    print("Project path does not exist")
except PermissionError:
    print("Permission denied reading project files")
```

## Performance Tips

1. **Use depth parameter wisely** - `depth=1` is much faster than `depth=3+`
2. **Cache semantic similarities** - They're automatically cached
3. **Batch operations** - Add all projects before adding relationships
4. **Use async discovery** - Discovery is I/O bound, use async for concurrency
5. **Clear caches periodically** - If graph changes frequently

## Testing

```python
# Run test suite
python src/workspace/test_relationship_graph.py

# Run validation
python validate_relationship_graph.py
```

## File Locations

- **Implementation:** `/home/user/Context/src/workspace/relationship_graph.py`
- **Discovery:** `/home/user/Context/src/workspace/relationship_discovery.py`
- **Tests:** `/home/user/Context/src/workspace/test_relationship_graph.py`
- **Documentation:** `/home/user/Context/RELATIONSHIP_GRAPH_SUMMARY.md`
