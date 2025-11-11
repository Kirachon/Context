# Context CLI - Quick Reference

## Installation

```bash
pip install -e .
```

## Commands

### 1. Init Workspace
```bash
context workspace init --name "WORKSPACE_NAME" [--output FILE]
```

### 2. Add Project
```bash
context workspace add-project \
  --id PROJECT_ID \
  --name "Project Name" \
  --path /path/to/project \
  [--type TYPE] \
  [--language LANG] \
  [--depends-on ID1,ID2] \
  [--exclude PATTERN] \
  [--priority PRIORITY]
```

### 3. List Projects
```bash
context workspace list [--verbose] [--json]
```

### 4. Index Projects
```bash
context workspace index [--project ID] [--parallel] [--force]
```

### 5. Search
```bash
context workspace search "query" \
  [--project ID] \
  [--scope SCOPE] \
  [--limit N] \
  [--json]
```

### 6. Status
```bash
context workspace status [--project ID] [--json]
```

### 7. Validate
```bash
context workspace validate [--file FILE]
```

### 8. Migrate
```bash
context workspace migrate \
  --from /old/path \
  --name "Project Name" \
  [--project-id ID] \
  [--type TYPE]
```

## Common Options

- `--workspace FILE` - Workspace config file (default: `.context-workspace.json`)
- `--json` - JSON output for scripting
- `--verbose`, `-v` - Detailed output
- `--help` - Show help message

## Project Types

- `web_frontend` - Web frontend (React, Vue, Angular)
- `api_server` - Backend API
- `mobile_app` - Mobile application
- `library` - Shared library
- `documentation` - Documentation
- `application` - Generic application (default)

## Indexing Priorities

- `critical` - Highest priority
- `high` - High priority
- `medium` - Normal priority (default)
- `low` - Low priority

## Search Scopes

- `project` - Single project only
- `dependencies` - Project + dependencies
- `workspace` - Entire workspace (default)
- `related` - Project + related projects

## Examples

### Quick Start
```bash
# 1. Create workspace
context workspace init --name "My App"

# 2. Add backend
context workspace add-project \
  --id backend --name "Backend" --path ./backend \
  --type api_server --language python

# 3. Add frontend
context workspace add-project \
  --id frontend --name "Frontend" --path ./frontend \
  --type web_frontend --language typescript \
  --depends-on backend

# 4. Index
context workspace index

# 5. Search
context workspace search "authentication"
```

### Migration
```bash
# Migrate existing project
context workspace migrate \
  --from ~/old-project \
  --name "Legacy App"
```

### Scripting
```bash
# Get project IDs
context workspace list --json | jq -r '.projects[].id'

# Check status
context workspace status --json | jq '.projects.frontend.status'
```

## Exit Codes

- `0` - Success
- `1` - Error

## Help

```bash
context --help
context workspace --help
context workspace COMMAND --help
```

## Documentation

- Full guide: `CLI_USAGE.md`
- Implementation: `CLI_IMPLEMENTATION_SUMMARY.md`
- Example config: `examples/example-workspace.json`
