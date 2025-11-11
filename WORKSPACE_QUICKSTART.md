# Workspace Manager Quick Start Guide

Get started with the multi-project workspace management system in 5 minutes.

---

## Installation

No additional dependencies required beyond the existing Context codebase. The workspace manager integrates with existing components.

**Optional Enhancement:**
```bash
pip install networkx  # For enhanced graph operations (falls back to simple graph if not available)
```

---

## Quick Start

### 1. Create Workspace Configuration

Create `.context-workspace.json` in your workspace root:

```json
{
  "version": "2.0.0",
  "name": "My Workspace",
  "projects": [
    {
      "id": "backend",
      "name": "Backend API",
      "path": "./backend",
      "type": "api_server",
      "language": ["python"],
      "indexing": {
        "enabled": true,
        "priority": "high",
        "exclude": ["venv", "__pycache__"]
      }
    },
    {
      "id": "frontend",
      "name": "Frontend App",
      "path": "./frontend",
      "type": "web_frontend",
      "language": ["typescript"],
      "dependencies": ["backend"],
      "indexing": {
        "enabled": true,
        "priority": "high",
        "exclude": ["node_modules", "dist"]
      }
    }
  ],
  "relationships": [
    {
      "from": "frontend",
      "to": "backend",
      "type": "api_client"
    }
  ],
  "search": {
    "default_scope": "workspace",
    "cross_project_ranking": true,
    "relationship_boost": 1.5
  }
}
```

### 2. Initialize Workspace

```python
from src.workspace.manager import WorkspaceManager

# Initialize workspace
workspace = WorkspaceManager(".context-workspace.json")
await workspace.initialize()

# Index all projects
await workspace.index_all_projects(parallel=True)
```

### 3. Search Workspace

```python
# Search across all projects
results = await workspace.search_workspace(
    query="authentication",
    limit=20
)

# Print results
for result in results:
    print(f"[{result['project_id']}] {result['payload']['file_path']}")
    print(f"  Score: {result['score']:.3f}")
```

---

## Common Operations

### Project Management

```python
from src.workspace.config import ProjectConfig, IndexingConfig

# Add new project
new_project = ProjectConfig(
    id="mobile",
    name="Mobile App",
    path="./mobile",
    type="mobile_app",
    language=["typescript"],
    dependencies=["backend"],
    indexing=IndexingConfig(enabled=True, priority="high")
)
await workspace.add_project(new_project)

# Reload project index
await workspace.reload_project("backend")

# Remove project
await workspace.remove_project("mobile")
```

### Project-Scoped Search

```python
# Get specific project
project = workspace.get_project("backend")

# Search within project only
results = await project.search(
    query="user authentication",
    limit=10
)
```

### Workspace Status

```python
# Get complete status
status = await workspace.get_workspace_status()

print(f"Workspace: {status['workspace']['name']}")
print(f"Projects: {len(status['projects'])}")

for project_id, project_status in status['projects'].items():
    print(f"\n{project_id}:")
    print(f"  Status: {project_status['status']}")
    print(f"  Files: {project_status['indexing']['files_indexed']}")
    print(f"  Errors: {project_status['indexing']['errors']}")
```

---

## Configuration Options

### Project Types

- `web_frontend` - React, Vue, Angular apps
- `api_server` - REST/GraphQL backends
- `library` - Shared libraries
- `documentation` - Docs sites
- `mobile_app` - React Native, Flutter
- `application` - Generic applications

### Relationship Types

- `imports` - Direct code imports
- `api_client` - API consumption
- `shared_database` - Shared data layer
- `event_driven` - Message queues
- `dependency` - Generic dependency
- `semantic_similarity` - Computed similarity

### Indexing Priorities

- `critical` - Index first, highest importance
- `high` - High priority
- `medium` - Normal priority (default)
- `low` - Index last, lowest importance

### Search Scopes

- `workspace` - All projects (default)
- `project` - Single project only
- `dependencies` - Project + dependencies
- `related` - Semantically related projects

---

## Error Handling

The workspace manager handles errors gracefully:

```python
# Initialize with error checking
success = await workspace.initialize()
if not success:
    print("Workspace initialization failed")

# Check individual project status
for project_id, project in workspace.projects.items():
    if project.status == ProjectStatus.FAILED:
        print(f"Project {project_id} failed: {project.initialization_error}")
```

---

## Performance Tips

### 1. Parallel Operations

```python
# Initialize all projects in parallel (5x faster)
await workspace.initialize(lazy_load=False)

# Index in parallel
await workspace.index_all_projects(parallel=True)
```

### 2. Lazy Loading

```python
# Only initialize projects on demand
await workspace.initialize(lazy_load=True)

# Projects initialize when first accessed
project = workspace.get_project("backend")
if not project.initialized:
    await project.initialize()
```

### 3. Selective Indexing

```python
# Disable indexing for non-critical projects
{
  "id": "docs",
  "indexing": {
    "enabled": false  # Skip this project
  }
}
```

### 4. Exclude Patterns

```python
# Exclude large directories
{
  "indexing": {
    "exclude": [
      "node_modules",
      "venv",
      "dist",
      "build",
      ".next",
      "coverage"
    ]
  }
}
```

---

## Migration from Single-Folder

Convert existing single-folder setup to workspace:

### Before (Single Folder)

```python
from src.indexing.file_indexer import file_indexer
from src.vector_db.vector_store import vector_store

# Global singletons
await file_indexer.index_file("myfile.py")
results = await vector_store.search(query_vector)
```

### After (Workspace)

```python
from src.workspace.manager import WorkspaceManager

# Per-project instances
workspace = WorkspaceManager(".context-workspace.json")
await workspace.initialize()

project = workspace.get_project("myproject")
await project.index()
results = await project.search("my query")
```

### Migration Steps

1. **Create workspace config**:
   ```json
   {
     "version": "2.0.0",
     "name": "My Project",
     "projects": [
       {
         "id": "default",
         "name": "My Project",
         "path": ".",
         "type": "application",
         "language": ["python"]
       }
     ]
   }
   ```

2. **Update code**:
   - Replace global singletons with workspace manager
   - Use `workspace.get_project("default")` for single-project access

3. **Re-index**:
   ```python
   await workspace.index_all_projects()
   ```

---

## Troubleshooting

### Collection Dimension Mismatch

```
WARNING: Collection has dimension mismatch (expected: 384, found: 768)
```

**Solution:** The system auto-recreates collections with correct dimensions. Re-index after:
```python
await workspace.reload_project("project_id")
```

### Circular Dependencies

```
ValueError: Circular dependency detected: frontend -> backend -> shared -> frontend
```

**Solution:** Remove circular dependencies from config:
```json
{
  "id": "frontend",
  "dependencies": ["backend"]  // Remove "shared" if it creates a cycle
}
```

### Project Path Not Found

```
ValueError: Project path does not exist: /path/to/project
```

**Solution:** Use relative paths in config (resolved relative to workspace file):
```json
{
  "path": "./frontend"  // Relative to .context-workspace.json
}
```

### NetworkX Warning

```
WARNING: NetworkX not available - using simple graph implementation
```

**Solution:** Install NetworkX for enhanced performance (optional):
```bash
pip install networkx
```

---

## Advanced Usage

### Custom Relationship Boost Factors

```python
# Get boost factors for related projects
boosts = workspace.relationship_graph.get_relationship_boost_factors(
    source_project="frontend",
    boost_factor=2.0  # Custom boost factor
)

# Use in search
results = await workspace.multi_root_store.search_workspace(
    query_vector=query_vector,
    relationship_boost=boosts
)
```

### File Monitoring

```python
# Enable real-time file watching
project = workspace.get_project("backend")
await project.start_monitoring()

# File changes are automatically re-indexed
# ...

# Disable monitoring
await project.stop_monitoring()
```

### Custom Search Filters

```python
# Search with Qdrant filters
from qdrant_client.http import models

filter_conditions = models.Filter(
    must=[
        models.FieldCondition(
            key="file_type",
            match=models.MatchValue(value="python")
        )
    ]
)

results = await workspace.multi_root_store.search_project(
    project_id="backend",
    query_vector=query_vector,
    filter_conditions=filter_conditions
)
```

---

## Best Practices

1. **Project Organization**
   - Keep projects self-contained
   - Use clear, descriptive project IDs
   - Document relationships explicitly

2. **Indexing**
   - Exclude build artifacts and dependencies
   - Use appropriate priorities
   - Index incrementally (not all at once)

3. **Search**
   - Use project-scoped search when possible (faster)
   - Enable relationship boost for better ranking
   - Adjust score thresholds based on results

4. **Error Handling**
   - Always check initialization success
   - Monitor project status
   - Log errors for debugging

5. **Performance**
   - Use parallel operations
   - Lazy load when possible
   - Cache workspace status

---

## Example: Full-Stack Application

Complete example for a typical full-stack app:

**Directory Structure:**
```
myapp/
├── .context-workspace.json
├── frontend/           # React app
├── backend/            # FastAPI server
├── shared/             # Shared types
└── docs/               # Documentation
```

**Workspace Config:**
```json
{
  "version": "2.0.0",
  "name": "MyApp Full-Stack",
  "projects": [
    {
      "id": "frontend",
      "name": "Frontend (React)",
      "path": "./frontend",
      "type": "web_frontend",
      "language": ["typescript", "tsx"],
      "dependencies": ["backend", "shared"],
      "indexing": {
        "enabled": true,
        "priority": "high",
        "exclude": ["node_modules", "dist", ".next", "coverage"]
      },
      "metadata": {
        "framework": "next.js",
        "version": "14.0.0"
      }
    },
    {
      "id": "backend",
      "name": "Backend (FastAPI)",
      "path": "./backend",
      "type": "api_server",
      "language": ["python"],
      "dependencies": ["shared"],
      "indexing": {
        "enabled": true,
        "priority": "high",
        "exclude": ["venv", "__pycache__", ".pytest_cache"]
      }
    },
    {
      "id": "shared",
      "name": "Shared Libraries",
      "path": "./shared",
      "type": "library",
      "language": ["typescript", "python"],
      "indexing": {
        "enabled": true,
        "priority": "critical"
      }
    },
    {
      "id": "docs",
      "name": "Documentation",
      "path": "./docs",
      "type": "documentation",
      "language": ["markdown"],
      "indexing": {
        "enabled": true,
        "priority": "low"
      }
    }
  ],
  "relationships": [
    {
      "from": "frontend",
      "to": "backend",
      "type": "api_client",
      "description": "REST API client"
    },
    {
      "from": "frontend",
      "to": "shared",
      "type": "imports",
      "description": "TypeScript types"
    },
    {
      "from": "backend",
      "to": "shared",
      "type": "imports",
      "description": "Python utilities"
    }
  ],
  "search": {
    "default_scope": "workspace",
    "cross_project_ranking": true,
    "relationship_boost": 1.5
  }
}
```

**Usage:**
```python
from src.workspace.manager import WorkspaceManager

# Initialize
workspace = WorkspaceManager("myapp/.context-workspace.json")
await workspace.initialize()

# Index all projects
results = await workspace.index_all_projects(parallel=True)
print(f"Indexed {sum(1 for v in results.values() if v)}/4 projects")

# Search for authentication code
auth_results = await workspace.search_workspace(
    query="user authentication login",
    limit=20,
    use_relationship_boost=True
)

# Results will be ranked with boost:
# - Results from 'backend' (where auth likely is)
# - Results from 'shared' (dependencies of backend)
# - Results from 'frontend' (depends on backend, boosted)
```

---

## Support & Documentation

- **Architecture**: See `ARCHITECTURE_PROJECT_AWARE.md`
- **Implementation**: See `WORKSPACE_MANAGER_IMPLEMENTATION.md`
- **Example Config**: See `.context-workspace.example.json`
- **Validation**: Run `python3 validate_workspace_implementation.py`

---

## What's Next?

After setting up your workspace:

1. **Test your setup**: Run searches, check status
2. **Enable monitoring**: Start file watchers for real-time updates
3. **Integrate with MCP**: Use workspace tools in Claude Desktop
4. **Add CLI commands**: Build `context workspace` CLI
5. **Write tests**: Add integration tests for your workspace

Happy coding with multi-project workspaces!
