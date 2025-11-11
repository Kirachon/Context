# Workspace Configuration System

A comprehensive multi-project workspace configuration system for the Context code indexing engine, enabling workspace-aware semantic search across multiple repositories, monorepos, and polyrepo architectures.

## Overview

The Workspace Configuration System provides:

- **Multi-project support** - Manage multiple code projects within a single workspace
- **Relationship tracking** - Define and track dependencies between projects
- **Path resolution** - Automatic resolution of relative and absolute paths
- **Comprehensive validation** - Project ID uniqueness, circular dependency detection, path validation
- **I/O operations** - Load/save JSON configuration files
- **Type safety** - Pydantic v2 models with full type checking

## Architecture

### Core Components

1. **WorkspaceConfig** - Top-level workspace configuration
2. **ProjectConfig** - Individual project configuration  
3. **RelationshipConfig** - Project-to-project relationships
4. **SearchConfig** - Search behavior configuration
5. **IndexingConfig** - Per-project indexing configuration

### Validation Rules

The system enforces these validation rules:

#### Project Validation
- ✅ Project IDs must be unique within workspace
- ✅ Project IDs must be valid identifiers (alphanumeric + underscore)
- ✅ Project paths cannot be empty
- ✅ Project paths must exist on disk (optional)
- ✅ Dependencies must reference valid project IDs

#### Relationship Validation
- ✅ Relationship source/target must reference valid projects
- ✅ Relationships cannot be self-referential
- ✅ Relationship types must be from predefined set

#### Dependency Validation
- ✅ No circular dependencies (A→B→C→A)
- ✅ All dependencies must reference valid projects
- ✅ Projects cannot depend on themselves

#### Version Validation
- ✅ Version must be in semver format (e.g., "2.0.0")

## File Format

Configuration is stored in `.context-workspace.json`:

```json
{
  "version": "2.0.0",
  "name": "My Workspace",
  "projects": [
    {
      "id": "frontend",
      "name": "Frontend (React)",
      "path": "./frontend",
      "type": "web_frontend",
      "language": ["typescript", "tsx"],
      "dependencies": ["backend"],
      "indexing": {
        "enabled": true,
        "priority": "high",
        "exclude": ["node_modules", "dist"]
      },
      "metadata": {
        "framework": "next.js"
      }
    }
  ],
  "relationships": [
    {
      "from": "frontend",
      "to": "backend",
      "type": "api_client",
      "description": "Frontend calls backend REST API"
    }
  ],
  "search": {
    "default_scope": "workspace",
    "cross_project_ranking": true,
    "relationship_boost": 1.5
  }
}
```

## Usage

### Loading a Workspace

```python
from src.workspace import WorkspaceConfig

# Load with path validation
config = WorkspaceConfig.load(".context-workspace.json")

# Load without path validation (useful for templates)
config = WorkspaceConfig.load(".context-workspace.json", validate_paths=False)
```

### Creating a Workspace

```python
from src.workspace import WorkspaceConfig, ProjectConfig, RelationshipConfig

config = WorkspaceConfig(
    name="My Workspace",
    projects=[
        ProjectConfig(
            id="frontend",
            name="Frontend",
            path="./frontend",
            type="web_frontend",
            language=["typescript"],
            dependencies=["backend"]
        ),
        ProjectConfig(
            id="backend",
            name="Backend",
            path="./backend",
            type="api_server",
            language=["python"]
        )
    ],
    relationships=[
        RelationshipConfig(
            from_project="frontend",
            to_project="backend",
            type="api_client"
        )
    ]
)

# Save to file
config.save(".context-workspace.json")
```

### Querying Workspace

```python
# Get a project by ID
project = config.get_project("frontend")

# Get direct dependencies
deps = config.get_project_dependencies("frontend")

# Get transitive dependencies
all_deps = config.get_project_dependencies("frontend", transitive=True)

# Get dependents (reverse lookup)
dependents = config.get_project_dependents("backend")

# Get relationships
all_rels = config.get_relationships()
project_rels = config.get_relationships(project_id="frontend")
type_rels = config.get_relationships(relationship_type="api_client")
```

### Path Resolution

Paths can be absolute or relative to the workspace directory:

```python
from pathlib import Path

config = WorkspaceConfig.load("/workspace/.context-workspace.json")

# Paths are automatically resolved
for project in config.projects:
    print(f"{project.id}: {project.get_resolved_path()}")
```

## Relationship Types

Supported relationship types:

- **imports** - Direct code imports between projects
- **api_client** - REST/GraphQL API consumption
- **shared_database** - Shared data layer
- **event_driven** - Message queue/event bus communication
- **semantic_similarity** - Embedding-based similarity
- **dependency** - Generic dependency (npm, pip, cargo, etc.)

## Indexing Priorities

Projects can have different indexing priorities:

- **critical** - Always indexed first (e.g., shared libraries)
- **high** - High priority (e.g., main application code)
- **medium** - Normal priority (default)
- **low** - Low priority (e.g., documentation)

## Search Scopes

Supported search scopes:

- **project** - Search within a single project
- **dependencies** - Search project + its dependencies
- **workspace** - Search all projects (default)
- **related** - Search semantically related projects

## Examples

See `/home/user/Context/examples/` for example configurations:

- `.context-workspace.example.json` - Full-featured workspace with 6 projects
- `.context-workspace.minimal.json` - Minimal workspace with 1 project

## Error Handling

The system provides clear error messages for validation failures:

```python
# Duplicate project IDs
ValueError: Duplicate project IDs found: frontend

# Invalid project ID
ValueError: Project ID 'front-end' must contain only alphanumeric characters and underscores

# Circular dependency
ValueError: Circular dependency detected: a -> b -> c -> a

# Unknown dependency
ValueError: Project 'frontend' references unknown dependency: 'nonexistent'

# Path validation
ValueError: Path validation failed:
  - Project 'frontend' path does not exist: /tmp/frontend
  - Project 'backend' path is not a directory: /tmp/backend.txt
```

## JSON Schema

A complete JSON schema is available in `schemas.py` for IDE autocomplete and validation.

### VS Code Integration

Add to `.vscode/settings.json`:

```json
{
  "json.schemas": [
    {
      "fileMatch": [".context-workspace.json"],
      "url": "https://context-engine.dev/schemas/workspace-config.json"
    }
  ]
}
```

## Design Decisions

### Why Pydantic v2?

- Strong type safety with runtime validation
- Automatic JSON serialization/deserialization
- Clear error messages
- Excellent IDE support
- Field validators for custom validation logic

### Why Separate Collections?

Each project gets its own vector collection to:
- Prevent cross-contamination
- Enable per-project indexing
- Support project-scoped search
- Allow independent project lifecycle

### Why Relationship Graph?

Explicit relationships enable:
- Dependency-aware search
- Relationship-based ranking
- Transitive dependency resolution
- Cross-project impact analysis

## Testing

Run the comprehensive test suite:

```bash
python test_workspace_config.py
```

Tests cover:
- Basic configuration creation
- Project ID validation
- Duplicate detection
- Circular dependency detection
- Unknown dependency detection
- Relationship validation
- Path resolution
- I/O operations
- Helper methods

## Future Enhancements

Planned features:

- [ ] Auto-discovery of relationships via import analysis
- [ ] Semantic similarity computation between projects
- [ ] Project templates for common architectures
- [ ] Migration tool from v1 single-folder setup
- [ ] CLI commands for workspace management
- [ ] Hot-reload on configuration changes
- [ ] Project access control and permissions

## Dependencies

Required packages:
- `pydantic>=2.0` - Data validation and settings management

## License

Part of the Context code indexing engine.
