# Workspace Configuration System - Usage Examples

## Quick Start

### 1. Create a Simple Workspace

```python
from src.workspace import WorkspaceConfig, ProjectConfig

# Create workspace
workspace = WorkspaceConfig(
    name="My Project",
    projects=[
        ProjectConfig(
            id="main",
            name="Main Project",
            path="."
        )
    ]
)

# Save to disk
workspace.save(".context-workspace.json")
```

### 2. Create a Multi-Project Workspace

```python
from src.workspace import (
    WorkspaceConfig,
    ProjectConfig,
    RelationshipConfig,
    IndexingConfig,
)

workspace = WorkspaceConfig(
    name="Full-Stack Application",
    projects=[
        ProjectConfig(
            id="frontend",
            name="React Frontend",
            path="./packages/frontend",
            type="web_frontend",
            language=["typescript", "tsx"],
            dependencies=["shared"],
            indexing=IndexingConfig(
                priority="high",
                exclude=["node_modules", "dist", ".next"]
            ),
            metadata={
                "framework": "next.js",
                "port": 3000
            }
        ),
        ProjectConfig(
            id="backend",
            name="FastAPI Backend",
            path="./packages/backend",
            type="api_server",
            language=["python"],
            dependencies=["shared"],
            indexing=IndexingConfig(
                priority="high",
                exclude=["venv", "__pycache__"]
            ),
            metadata={
                "framework": "fastapi",
                "port": 8000
            }
        ),
        ProjectConfig(
            id="shared",
            name="Shared Library",
            path="./packages/shared",
            type="library",
            language=["typescript", "python"],
            indexing=IndexingConfig(
                priority="critical"
            )
        )
    ],
    relationships=[
        RelationshipConfig(
            from_project="frontend",
            to_project="backend",
            type="api_client",
            description="Frontend consumes backend REST API"
        ),
        RelationshipConfig(
            from_project="frontend",
            to_project="shared",
            type="imports",
            description="Frontend imports shared TypeScript types"
        ),
        RelationshipConfig(
            from_project="backend",
            to_project="shared",
            type="imports",
            description="Backend imports shared Python utilities"
        )
    ]
)

# Save
workspace.save(".context-workspace.json")
```

### 3. Load and Query a Workspace

```python
from src.workspace import WorkspaceConfig

# Load workspace
workspace = WorkspaceConfig.load(".context-workspace.json")

print(f"Workspace: {workspace.name}")
print(f"Projects: {len(workspace.projects)}")

# Get specific project
frontend = workspace.get_project("frontend")
print(f"\nProject: {frontend.name}")
print(f"Path: {frontend.get_resolved_path()}")
print(f"Type: {frontend.type}")
print(f"Languages: {', '.join(frontend.language)}")

# Get dependencies
deps = workspace.get_project_dependencies("frontend")
print(f"\nDirect dependencies: {deps}")

transitive_deps = workspace.get_project_dependencies("frontend", transitive=True)
print(f"All dependencies: {transitive_deps}")

# Get dependents (reverse lookup)
dependents = workspace.get_project_dependents("shared")
print(f"\nProjects depending on 'shared': {dependents}")

# Get relationships
frontend_rels = workspace.get_relationships(project_id="frontend")
print(f"\nRelationships for frontend: {len(frontend_rels)}")
for rel in frontend_rels:
    print(f"  - {rel.from_project} -> {rel.to_project} ({rel.type})")
```

### 4. Validate Configuration

```python
from src.workspace import WorkspaceConfig

try:
    # Load with path validation
    workspace = WorkspaceConfig.load(
        ".context-workspace.json",
        validate_paths=True
    )
    print("✓ Configuration valid!")
    
except FileNotFoundError as e:
    print(f"✗ Config file not found: {e}")
    
except ValueError as e:
    print(f"✗ Validation failed: {e}")
    
except json.JSONDecodeError as e:
    print(f"✗ Invalid JSON: {e}")
```

### 5. Handle Validation Errors

```python
from src.workspace import WorkspaceConfig, ProjectConfig

# This will fail - circular dependency
try:
    workspace = WorkspaceConfig(
        name="Test",
        projects=[
            ProjectConfig(
                id="a",
                name="Project A",
                path="./a",
                dependencies=["b"]
            ),
            ProjectConfig(
                id="b",
                name="Project B",
                path="./b",
                dependencies=["c"]
            ),
            ProjectConfig(
                id="c",
                name="Project C",
                path="./c",
                dependencies=["a"]  # Creates cycle: a -> b -> c -> a
            )
        ]
    )
except ValueError as e:
    print(f"Validation error: {e}")
    # Output: Circular dependency detected: a -> b -> c -> a
```

### 6. Work with Relative Paths

```python
from pathlib import Path
from src.workspace import WorkspaceConfig, ProjectConfig

# Create workspace with relative paths
workspace = WorkspaceConfig(
    name="Monorepo",
    projects=[
        ProjectConfig(id="api", name="API", path="./services/api"),
        ProjectConfig(id="web", name="Web", path="./services/web"),
        ProjectConfig(id="mobile", name="Mobile", path="./apps/mobile"),
        ProjectConfig(id="shared", name="Shared", path="./packages/shared"),
    ]
)

# Save to workspace root
workspace.save("/workspace/.context-workspace.json")

# Load and resolve paths
workspace = WorkspaceConfig.load("/workspace/.context-workspace.json")

# All paths are now absolute
for project in workspace.projects:
    print(f"{project.id}: {project.get_resolved_path()}")
    # Output:
    # api: /workspace/services/api
    # web: /workspace/services/web
    # mobile: /workspace/apps/mobile
    # shared: /workspace/packages/shared
```

### 7. Use with Search Configuration

```python
from src.workspace import WorkspaceConfig, SearchConfig

workspace = WorkspaceConfig(
    name="My Workspace",
    projects=[...],
    search=SearchConfig(
        default_scope="dependencies",  # Search project + dependencies by default
        cross_project_ranking=True,     # Enable relationship-aware ranking
        relationship_boost=2.0          # 2x boost for related projects
    )
)

# Access search config
print(f"Default scope: {workspace.search.default_scope}")
print(f"Relationship boost: {workspace.search.relationship_boost}")
```

### 8. Filter Relationships

```python
from src.workspace import WorkspaceConfig

workspace = WorkspaceConfig.load(".context-workspace.json")

# Get all relationships
all_rels = workspace.get_relationships()
print(f"Total relationships: {len(all_rels)}")

# Filter by project
frontend_rels = workspace.get_relationships(project_id="frontend")
print(f"Frontend relationships: {len(frontend_rels)}")

# Filter by type
api_rels = workspace.get_relationships(relationship_type="api_client")
print(f"API client relationships: {len(api_rels)}")

# Combine filters
frontend_api_rels = [
    rel for rel in workspace.get_relationships(project_id="frontend")
    if rel.type == "api_client"
]
print(f"Frontend API relationships: {len(frontend_api_rels)}")
```

### 9. Update Configuration

```python
from src.workspace import WorkspaceConfig, ProjectConfig

# Load existing workspace
workspace = WorkspaceConfig.load(".context-workspace.json")

# Add a new project
new_project = ProjectConfig(
    id="docs",
    name="Documentation",
    path="./docs",
    type="documentation",
    language=["markdown"],
    indexing={
        "priority": "low"
    }
)
workspace.projects.append(new_project)

# Save updated config
workspace.save(".context-workspace.json")
```

### 10. Load Example Configurations

```python
from src.workspace import WorkspaceConfig

# Load full example (without path validation)
example = WorkspaceConfig.load(
    "/home/user/Context/examples/.context-workspace.example.json",
    validate_paths=False
)

print(f"Example workspace: {example.name}")
print(f"Projects: {len(example.projects)}")
print(f"Relationships: {len(example.relationships)}")

# List all projects
for project in example.projects:
    deps = ", ".join(project.dependencies) if project.dependencies else "none"
    print(f"  - {project.id} ({project.type}): deps={deps}")
```

## Common Patterns

### Monorepo Structure

```python
workspace = WorkspaceConfig(
    name="Monorepo",
    projects=[
        ProjectConfig(id="api", path="./services/api", type="api_server"),
        ProjectConfig(id="worker", path="./services/worker", type="microservice"),
        ProjectConfig(id="web", path="./apps/web", type="web_frontend"),
        ProjectConfig(id="mobile", path="./apps/mobile", type="mobile_app"),
        ProjectConfig(id="shared", path="./packages/shared", type="library"),
    ]
)
```

### Polyrepo Structure

```python
workspace = WorkspaceConfig(
    name="Polyrepo",
    projects=[
        ProjectConfig(id="api", path="/repos/myapp-api"),
        ProjectConfig(id="web", path="/repos/myapp-web"),
        ProjectConfig(id="mobile", path="/repos/myapp-mobile"),
        ProjectConfig(id="shared", path="/repos/myapp-shared"),
    ]
)
```

### Microservices Architecture

```python
workspace = WorkspaceConfig(
    name="Microservices",
    projects=[
        ProjectConfig(id="api_gateway", path="./gateway", dependencies=["auth", "users"]),
        ProjectConfig(id="auth", path="./services/auth"),
        ProjectConfig(id="users", path="./services/users", dependencies=["auth"]),
        ProjectConfig(id="orders", path="./services/orders", dependencies=["auth", "users"]),
        ProjectConfig(id="shared", path="./shared", type="library"),
    ],
    relationships=[
        RelationshipConfig(
            from_project="api_gateway",
            to_project="auth",
            type="api_client"
        ),
        # ... more relationships
    ]
)
```

## Error Handling Examples

### Invalid Project ID
```python
try:
    ProjectConfig(id="front-end", name="Frontend", path="./frontend")
except ValueError as e:
    print(e)
    # Project ID 'front-end' must contain only alphanumeric characters and underscores
```

### Duplicate Project IDs
```python
try:
    WorkspaceConfig(
        name="Test",
        projects=[
            ProjectConfig(id="api", name="API", path="./api"),
            ProjectConfig(id="api", name="API2", path="./api2"),
        ]
    )
except ValueError as e:
    print(e)
    # Duplicate project IDs found: api
```

### Circular Dependencies
```python
try:
    WorkspaceConfig(
        name="Test",
        projects=[
            ProjectConfig(id="a", name="A", path="./a", dependencies=["b"]),
            ProjectConfig(id="b", name="B", path="./b", dependencies=["a"]),
        ]
    )
except ValueError as e:
    print(e)
    # Circular dependency detected: a -> b -> a
```

### Unknown Dependencies
```python
try:
    WorkspaceConfig(
        name="Test",
        projects=[
            ProjectConfig(
                id="api",
                name="API",
                path="./api",
                dependencies=["nonexistent"]
            ),
        ]
    )
except ValueError as e:
    print(e)
    # Project 'api' references unknown dependency: 'nonexistent'
```

### Path Not Found
```python
try:
    workspace = WorkspaceConfig.load(".context-workspace.json")
    workspace.validate(check_paths=True)
except ValueError as e:
    print(e)
    # Path validation failed:
    #   - Project 'frontend' path does not exist: /tmp/frontend
```

## Best Practices

1. **Use relative paths for monorepos**
   ```python
   path="./services/api"  # Good
   path="/absolute/path"   # Only when necessary
   ```

2. **Set appropriate indexing priorities**
   ```python
   # Critical for shared libraries
   indexing=IndexingConfig(priority="critical")
   
   # Low for documentation
   indexing=IndexingConfig(priority="low")
   ```

3. **Exclude build artifacts and dependencies**
   ```python
   exclude=["node_modules", "dist", "__pycache__", "venv"]
   ```

4. **Use meaningful project IDs**
   ```python
   id="frontend"         # Good
   id="web_app"          # Good
   id="proj1"            # Avoid
   ```

5. **Document relationships**
   ```python
   RelationshipConfig(
       from_project="frontend",
       to_project="backend",
       type="api_client",
       description="Frontend calls backend REST API at /api/v1"  # Helpful!
   )
   ```

6. **Load without path validation for templates**
   ```python
   # Template/example configs
   config = WorkspaceConfig.load(path, validate_paths=False)
   
   # Production configs
   config = WorkspaceConfig.load(path, validate_paths=True)
   ```

7. **Use metadata for custom data**
   ```python
   metadata={
       "framework": "fastapi",
       "version": "0.104.0",
       "owner": "backend-team",
       "repo": "https://github.com/org/backend"
   }
   ```
