# Context CLI - Workspace Management

Command-line interface for managing multi-project workspaces with intelligent indexing, relationship tracking, and cross-project search.

## Installation

```bash
# Install in development mode
pip install -e .

# Or install with all dependencies
pip install -e ".[dev,analysis,security]"
```

## Quick Start

```bash
# Initialize a new workspace
context workspace init --name "My Workspace"

# Add a project
context workspace add-project \
  --id frontend \
  --name "Frontend (React)" \
  --path /path/to/frontend \
  --type web_frontend \
  --language typescript \
  --depends-on backend

# List all projects
context workspace list --verbose

# Index all projects
context workspace index

# Search across workspace
context workspace search "authentication function"

# Get workspace status
context workspace status
```

## Commands

### 1. `context workspace init`

Initialize a new workspace configuration file.

```bash
context workspace init --name "My Workspace" [--output FILE]
```

**Options:**
- `--name` (required): Workspace name
- `--output`: Output file path (default: `.context-workspace.json`)

**Example:**
```bash
context workspace init --name "Full-Stack App" --output workspace.json
```

**Output:**
```
✓ Created workspace configuration: /path/to/.context-workspace.json

Next steps:
  1. Add projects: context workspace add-project
  2. Index projects: context workspace index
  3. Search workspace: context workspace search 'query'
```

---

### 2. `context workspace add-project`

Add a new project to the workspace.

```bash
context workspace add-project \
  --id PROJECT_ID \
  --name "Project Name" \
  --path /path/to/project \
  [--type TYPE] \
  [--language LANG ...] \
  [--depends-on ID1,ID2] \
  [--exclude PATTERN ...] \
  [--priority PRIORITY] \
  [--workspace FILE]
```

**Options:**
- `--id` (required): Unique project identifier (alphanumeric and underscores only)
- `--name` (required): Human-readable project name
- `--path` (required): Path to project directory (absolute or relative to workspace)
- `--type`: Project type (default: `application`)
  - Common types: `web_frontend`, `api_server`, `library`, `documentation`, `mobile_app`
- `--language`: Programming languages (can be specified multiple times)
  - Examples: `python`, `typescript`, `javascript`, `java`, `cpp`, `go`, `rust`
- `--depends-on`: Comma-separated list of project IDs this project depends on
- `--exclude`: Patterns to exclude from indexing (can be specified multiple times)
  - Common: `node_modules`, `dist`, `build`, `.next`, `__pycache__`
- `--priority`: Indexing priority (`critical`, `high`, `medium`, `low`) (default: `medium`)
- `--workspace`: Path to workspace config file (default: `.context-workspace.json`)

**Examples:**

Basic project:
```bash
context workspace add-project \
  --id backend \
  --name "Backend API" \
  --path ./services/backend \
  --type api_server \
  --language python
```

Frontend with dependencies:
```bash
context workspace add-project \
  --id frontend \
  --name "Frontend (Next.js)" \
  --path ./apps/web \
  --type web_frontend \
  --language typescript \
  --language tsx \
  --depends-on backend,shared \
  --exclude node_modules \
  --exclude .next \
  --exclude dist \
  --priority high
```

**Output:**
```
✓ Added project 'frontend' to workspace

┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property    ┃ Value                  ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ ID          │ frontend               │
│ Name        │ Frontend (Next.js)     │
│ Path        │ ./apps/web             │
│ Type        │ web_frontend           │
│ Languages   │ typescript, tsx        │
│ Dependencies│ backend, shared        │
│ Priority    │ high                   │
└─────────────┴────────────────────────┘

Run 'context workspace index --project frontend' to index this project
```

---

### 3. `context workspace list`

List all projects in the workspace.

```bash
context workspace list [--verbose] [--json]
```

**Options:**
- `--verbose`, `-v`: Show detailed information
- `--json`: Output as JSON
- `--workspace`: Path to workspace config file (default: `.context-workspace.json`)

**Examples:**

Basic list:
```bash
context workspace list
```

Verbose output:
```bash
context workspace list --verbose
```

JSON output for scripting:
```bash
context workspace list --json | jq '.projects[] | .id'
```

**Output:**
```
╭─────────────── Workspace ───────────────╮
│ My Full-Stack App                       │
│ Version: 2.0.0                          │
│ Projects: 3                             │
╰─────────────────────────────────────────╯

                         Projects
┏━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ ID      ┃ Name           ┃ Type         ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ backend │ Backend API    │ api_server   │
│ frontend│ Frontend       │ web_frontend │
│ shared  │ Shared Library │ library      │
└─────────┴────────────────┴──────────────┘
```

---

### 4. `context workspace index`

Index workspace projects to enable search.

```bash
context workspace index [--project ID] [--parallel] [--force]
```

**Options:**
- `--project`: Index specific project by ID (default: all projects)
- `--parallel` / `--no-parallel`: Index projects in parallel (default: parallel)
- `--force`: Force re-indexing even if already indexed
- `--workspace`: Path to workspace config file (default: `.context-workspace.json`)

**Examples:**

Index all projects:
```bash
context workspace index
```

Index specific project:
```bash
context workspace index --project frontend
```

Force re-index:
```bash
context workspace index --force
```

Sequential indexing (useful for debugging):
```bash
context workspace index --no-parallel
```

**Output:**
```
⠋ Initializing workspace...
⠋ Indexing 3 projects...
✓ Indexed all 3 projects successfully

                     Indexing Results
┏━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┓
┃ Project ┃ Status   ┃ Files ┃ Errors ┃ Duration ┃
┡━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━╇━━━━━━━━╇━━━━━━━━━━┩
│ backend │ ✓ Success│ 45/45 │      0 │    2.34s │
│ frontend│ ✓ Success│ 87/87 │      0 │    3.12s │
│ shared  │ ✓ Success│ 12/12 │      0 │    0.89s │
└─────────┴──────────┴───────┴────────┴──────────┘
```

---

### 5. `context workspace search`

Search across workspace with relationship-aware ranking.

```bash
context workspace search "query" \
  [--project ID] \
  [--scope SCOPE] \
  [--limit N] \
  [--json]
```

**Options:**
- `query` (required): Search query
- `--project`: Search specific project by ID
- `--scope`: Search scope (`project`, `dependencies`, `workspace`, `related`)
- `--limit`: Maximum number of results (default: 10)
- `--json`: Output as JSON
- `--workspace`: Path to workspace config file (default: `.context-workspace.json`)

**Examples:**

Search entire workspace:
```bash
context workspace search "authentication"
```

Search specific project:
```bash
context workspace search "API endpoint" --project backend
```

Limit results:
```bash
context workspace search "React component" --limit 5
```

JSON output:
```bash
context workspace search "database query" --json
```

**Output:**
```
╭────────────── Search Results ──────────────╮
│ Query: authentication                      │
│ Results: 5                                 │
╰────────────────────────────────────────────╯

1. backend/src/auth/login.py
   Project: backend | Score: 0.892
   def authenticate_user(username: str, password: str) -> User:
       """Authenticate user with username and password"""...

2. frontend/src/components/LoginForm.tsx
   Project: frontend | Score: 0.845
   export function LoginForm() {
       const handleAuthentication = async () => {...

3. shared/src/auth/types.py
   Project: shared | Score: 0.823
   class AuthenticationToken(BaseModel):
       """Authentication token model"""...
```

---

### 6. `context workspace status`

Get workspace or project status with indexing statistics.

```bash
context workspace status [--project ID] [--json]
```

**Options:**
- `--project`: Show status for specific project
- `--json`: Output as JSON
- `--workspace`: Path to workspace config file (default: `.context-workspace.json`)

**Examples:**

Workspace status:
```bash
context workspace status
```

Project status:
```bash
context workspace status --project frontend
```

JSON output:
```bash
context workspace status --json
```

**Output (Workspace):**
```
╭─────────────── Workspace Status ───────────────╮
│ My Full-Stack App                              │
│ Version: 2.0.0                                 │
│ Config: /path/.context-workspace.json          │
│ Projects: 3                                    │
╰────────────────────────────────────────────────╯

                         Projects
┏━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━┳━━━━━━━━┓
┃ ID      ┃ Name         ┃ Status ┃ Files ┃ Errors ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━╇━━━━━━━━┩
│ backend │ Backend API  │ ✓ ready│ 45/45 │      0 │
│ frontend│ Frontend     │ ✓ ready│ 87/87 │      0 │
│ shared  │ Shared Lib   │ ✓ ready│ 12/12 │      0 │
└─────────┴──────────────┴────────┴───────┴────────┘
```

**Output (Project):**
```
╭────────── Project Status ──────────╮
│ Frontend (Next.js)                 │
│ ID: frontend                       │
│ Type: web_frontend                 │
│ Status: ready                      │
│ Path: /path/to/frontend            │
╰────────────────────────────────────╯

       Indexing Statistics
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Property     ┃ Value        ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Enabled      │ Yes          │
│ Priority     │ high         │
│ Files Indexed│ 87/87        │
│ Errors       │ 0            │
│ Last Indexed │ 2025-11-11...│
│ Duration     │ 3.12s        │
└──────────────┴──────────────┘
```

---

### 7. `context workspace validate`

Validate workspace configuration for errors and issues.

```bash
context workspace validate [--file FILE]
```

**Options:**
- `--file`: Path to workspace config file (default: `.context-workspace.json`)

**Examples:**

Validate default workspace:
```bash
context workspace validate
```

Validate specific file:
```bash
context workspace validate --file custom-workspace.json
```

**Checks performed:**
- ✓ JSON syntax validity
- ✓ Schema validation (Pydantic)
- ✓ Project ID uniqueness
- ✓ Valid project references in dependencies
- ✓ Valid project references in relationships
- ✓ Circular dependency detection
- ✓ Project paths exist on disk
- ✓ Project paths are directories
- ⚠ Unused projects warning

**Output (Success):**
```
Validating workspace configuration: .context-workspace.json
✓ Workspace configuration is valid

        Workspace Summary
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Property    ┃ Value         ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Name        │ My App        │
│ Version     │ 2.0.0         │
│ Projects    │ 3             │
│ Relationships│ 2            │
└─────────────┴───────────────┘
```

**Output (Errors):**
```
Validating workspace configuration: .context-workspace.json

Validation Errors:
  ✗ Circular dependency detected: frontend -> backend -> shared -> frontend
  ✗ Project 'frontend' path does not exist: /nonexistent/path
  ✗ Relationship references unknown project: 'api'

3 validation error(s) found
```

**Output (Warnings):**
```
Warnings:
  ⚠ Project 'docs' has no dependencies and is not depended upon
```

---

### 8. `context workspace migrate`

Migrate from single-folder v1 setup to workspace v2.

```bash
context workspace migrate \
  --from /path/to/old/project \
  --name "Project Name" \
  [--workspace FILE] \
  [--project-id ID] \
  [--type TYPE]
```

**Options:**
- `--from` (required): Path to old single-folder project
- `--name` (required): Name for the project in workspace
- `--workspace`: Path to workspace config file (default: `.context-workspace.json`)
- `--project-id`: Project ID (defaults to sanitized name)
- `--type`: Project type (default: `application`)

**Examples:**

Migrate to new workspace:
```bash
context workspace migrate \
  --from /home/user/old-project \
  --name "Legacy Backend"
```

Migrate to existing workspace:
```bash
context workspace migrate \
  --from /home/user/frontend \
  --name "Frontend" \
  --project-id web_frontend \
  --type web_frontend \
  --workspace ./my-workspace.json
```

**Features:**
- ✓ Auto-detects programming languages
- ✓ Auto-detects common exclusion patterns
- ✓ Creates new workspace or adds to existing
- ✓ Validates project path exists
- ✓ Sanitizes project ID from name

**Output:**
```
Migrating project from: /home/user/old-project
Project ID: legacy_backend
Project Name: Legacy Backend

Creating new workspace configuration
✓ Migrated project 'Legacy Backend' to workspace

            Migration Summary
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ Property          ┃ Value              ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ Project ID        │ legacy_backend     │
│ Project Name      │ Legacy Backend     │
│ Path              │ /home/user/old...  │
│ Type              │ application        │
│ Languages Detected│ python, javascript │
│ Exclusions        │ node_modules, ...  │
│ Workspace File    │ /path/.context...  │
└───────────────────┴────────────────────┘

Next steps:
  1. Review workspace: context workspace list --verbose
  2. Index project: context workspace index --project legacy_backend
```

---

## Configuration File Format

The `.context-workspace.json` file:

```json
{
  "version": "2.0.0",
  "name": "My Full-Stack App",
  "projects": [
    {
      "id": "backend",
      "name": "Backend API",
      "path": "/home/user/projects/backend",
      "type": "api_server",
      "language": ["python"],
      "dependencies": ["shared"],
      "indexing": {
        "enabled": true,
        "priority": "high",
        "exclude": ["__pycache__", "venv"]
      },
      "metadata": {
        "framework": "FastAPI",
        "version": "1.0.0"
      }
    },
    {
      "id": "frontend",
      "name": "Frontend (React)",
      "path": "/home/user/projects/frontend",
      "type": "web_frontend",
      "language": ["typescript", "tsx"],
      "dependencies": ["backend", "shared"],
      "indexing": {
        "enabled": true,
        "priority": "high",
        "exclude": ["node_modules", "dist", ".next"]
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

## Project Types

Common project types:
- `web_frontend` - Web frontend application (React, Vue, Angular, etc.)
- `api_server` - Backend API server
- `mobile_app` - Mobile application (iOS, Android)
- `library` - Shared library or package
- `documentation` - Documentation project
- `infrastructure` - Infrastructure as code (Terraform, etc.)
- `application` - Generic application (default)

## Relationship Types

- `imports` - Direct code imports between projects
- `api_client` - API client/server relationship
- `shared_database` - Shared database access
- `event_driven` - Event-driven communication
- `semantic_similarity` - Similar functionality/concepts
- `dependency` - Build/runtime dependency

## Exit Codes

- `0` - Success
- `1` - Error (validation failed, command failed, etc.)

## Tips

1. **Use relative paths** for projects within the workspace directory
2. **Use absolute paths** for projects outside the workspace
3. **Run validation** after manual config edits: `context workspace validate`
4. **Check status** regularly to ensure projects are indexed
5. **Use JSON output** for scripting: `context workspace list --json`
6. **Leverage relationship tracking** for better search results
7. **Exclude build artifacts** to speed up indexing

## Troubleshooting

**Command not found:**
```bash
# Reinstall in development mode
pip install -e .
```

**Module import errors:**
```bash
# Install dependencies
pip install -r requirements/base.txt
```

**Indexing fails:**
```bash
# Check project paths exist
context workspace validate

# Try indexing sequentially
context workspace index --no-parallel

# Force re-index
context workspace index --force
```

**Search returns no results:**
```bash
# Ensure projects are indexed
context workspace status

# Re-index if needed
context workspace index
```

## Examples

### Example 1: Full-Stack Monorepo

```bash
# Initialize workspace
context workspace init --name "Full-Stack Monorepo"

# Add backend
context workspace add-project \
  --id api \
  --name "API Server" \
  --path ./services/api \
  --type api_server \
  --language python \
  --priority critical

# Add frontend
context workspace add-project \
  --id web \
  --name "Web App" \
  --path ./apps/web \
  --type web_frontend \
  --language typescript \
  --depends-on api \
  --exclude node_modules --exclude .next \
  --priority high

# Add shared library
context workspace add-project \
  --id shared \
  --name "Shared Types" \
  --path ./packages/shared \
  --type library \
  --language typescript \
  --priority medium

# Index all
context workspace index

# Search
context workspace search "user authentication"
```

### Example 2: Microservices Architecture

```bash
# Initialize
context workspace init --name "Microservices Platform"

# Add services
for service in auth users payments notifications; do
  context workspace add-project \
    --id $service \
    --name "${service^} Service" \
    --path ./services/$service \
    --type api_server \
    --language python
done

# Add API gateway
context workspace add-project \
  --id gateway \
  --name "API Gateway" \
  --path ./gateway \
  --type api_server \
  --language go \
  --depends-on auth,users,payments,notifications

# Index and validate
context workspace index
context workspace validate
```

### Example 3: Migration from Single Project

```bash
# Migrate existing project
context workspace migrate \
  --from ~/projects/my-old-app \
  --name "Legacy Application" \
  --type application

# Add new projects to workspace
context workspace add-project \
  --id frontend \
  --name "New Frontend" \
  --path ~/projects/new-frontend \
  --type web_frontend \
  --depends-on legacy_application

# Index all
context workspace index
```

## See Also

- [Workspace Architecture](src/workspace/README.md)
- [Configuration Schema](src/workspace/schemas.py)
- [API Documentation](docs/api.md)
