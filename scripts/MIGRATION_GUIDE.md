# Workspace Migration Guide

Complete guide for migrating from v1 single-folder setup to v2 multi-project workspace.

## Overview

The migration script (`migrate_to_workspace.py`) automates the conversion of your existing v1 Context setup to the new v2 workspace configuration. It handles:

- ✅ Automatic project detection and language analysis
- ✅ Workspace configuration generation
- ✅ Qdrant collection migration (v1 → v2 naming)
- ✅ Automatic backups before changes
- ✅ Dry-run mode for safety
- ✅ Rollback support
- ✅ Complete validation

## Prerequisites

1. **Install Dependencies**
   ```bash
   pip install -r requirements/base.txt
   ```

2. **Verify Qdrant is Running**
   ```bash
   # Check Qdrant status
   curl http://localhost:6333/collections
   ```

3. **Backup Your Data** (Optional but recommended)
   ```bash
   # The script creates automatic backups, but you can also:
   cp -r .env .env.backup
   ```

## Usage

### Basic Migration

```bash
python scripts/migrate_to_workspace.py \
  --from /path/to/your/project \
  --name "My Project"
```

### Dry-Run (Recommended First Step)

Test the migration without making any changes:

```bash
python scripts/migrate_to_workspace.py \
  --from /path/to/your/project \
  --name "My Project" \
  --dry-run
```

This will show:
- Detected languages and project type
- Workspace configuration that will be created
- Qdrant collections that will be migrated
- No actual changes are made

### Custom Output Location

```bash
python scripts/migrate_to_workspace.py \
  --from /path/to/your/project \
  --name "My Project" \
  --output /custom/path/.context-workspace.json
```

### Skip Backups (Not Recommended)

```bash
python scripts/migrate_to_workspace.py \
  --from /path/to/your/project \
  --name "My Project" \
  --no-backup
```

### Rollback Migration

If something goes wrong, rollback using the backup directory:

```bash
python scripts/migrate_to_workspace.py \
  --rollback migration_backup_20231110_120000
```

## Migration Process

### Step 1: Pre-flight Checks

The script verifies:
- ✓ No existing `.context-workspace.json` (prevents double migration)
- ✓ Project path exists and is valid
- ✓ Qdrant connection is working
- ✓ Required dependencies are installed

### Step 2: Analyze Current Setup

Automatic detection:
- **Languages**: Scans for `.py`, `.js`, `.ts`, `.tsx`, `.java`, `.cpp`, `.go`, `.rs`, etc.
- **Project Type**: Detects framework (Django, FastAPI, React, Next.js, etc.)
- **Existing Collections**: Finds v1 collections (`context_vectors`, `context_symbols`, etc.)

### Step 3: Create Backups

Before making changes:
- Backs up `settings.py`
- Exports Qdrant collection metadata
- Creates timestamped backup directory: `migration_backup_YYYYMMDD_HHMMSS/`

### Step 4: Generate Workspace Config

Creates `.context-workspace.json` with:
```json
{
  "version": "2.0.0",
  "name": "Your Project Name",
  "projects": [
    {
      "id": "default",
      "name": "Your Project Name",
      "path": "/absolute/path/to/project",
      "type": "application",
      "language": ["python", "typescript"],
      "indexing": {
        "enabled": true,
        "priority": "high",
        "exclude": [".git", "node_modules", "__pycache__"]
      },
      "metadata": {
        "migrated_from_v1": true,
        "migration_timestamp": "2023-11-10T12:00:00Z"
      }
    }
  ]
}
```

### Step 5: Migrate Qdrant Collections

Renames collections with project-scoped naming:

| Old Name (v1)        | New Name (v2)                |
|---------------------|------------------------------|
| `context_vectors`   | `project_default_vectors`    |
| `context_symbols`   | `project_default_symbols`    |
| `context_classes`   | `project_default_classes`    |
| `context_imports`   | `project_default_imports`    |

**How it works:**
1. Creates new collection with same vector configuration
2. Copies all vectors (with payloads) in batches
3. Deletes old collection after verification
4. Handles large collections efficiently (100 vectors per batch)

### Step 6: Validation

Post-migration checks:
- ✓ Workspace config file exists and is valid
- ✓ Project paths are accessible
- ✓ New collections exist in Qdrant
- ✓ No validation errors

### Step 7: Next Steps

After successful migration:
1. Review `.context-workspace.json`
2. Set environment variable: `export WORKSPACE_MODE=true`
3. Start Context server: `python -m src.main`
4. Test workspace features

## Project Type Detection

The script automatically detects project types:

| Indicators | Detected Type |
|-----------|--------------|
| `package.json` + `react` | `web_frontend` |
| `package.json` + `express` | `api_server` |
| `manage.py` (Django) | `web_backend` |
| FastAPI imports | `api_server` |
| Flask imports | `web_backend` |
| `Cargo.toml` | `library` |
| `go.mod` | `application` |
| Default | `application` |

## Language Detection

Detected by file extensions:

| Extensions | Language |
|-----------|----------|
| `.py` | `python` |
| `.js`, `.jsx` | `javascript` |
| `.ts`, `.tsx` | `typescript` |
| `.java` | `java` |
| `.cpp`, `.hpp`, `.h` | `cpp` |
| `.go` | `go` |
| `.rs` | `rust` |
| `.rb` | `ruby` |
| `.php` | `php` |

## Troubleshooting

### Error: "Workspace config already exists"

**Cause**: You've already migrated or `.context-workspace.json` exists

**Solution**:
```bash
# Option 1: Remove existing config (if it's safe)
rm .context-workspace.json

# Option 2: Verify you need to migrate
cat .context-workspace.json
```

### Error: "Cannot connect to Qdrant"

**Cause**: Qdrant is not running or wrong connection settings

**Solution**:
```bash
# Check Qdrant is running
docker ps | grep qdrant

# Start Qdrant if needed
docker-compose up -d qdrant

# Verify connection
curl http://localhost:6333/collections
```

### Error: "Project path does not exist"

**Cause**: Invalid `--from` path

**Solution**:
```bash
# Use absolute path
python scripts/migrate_to_workspace.py \
  --from $(pwd) \
  --name "My Project"
```

### Migration Fails Mid-Process

**Recovery**:
```bash
# Use the backup directory created before migration
python scripts/migrate_to_workspace.py \
  --rollback migration_backup_YYYYMMDD_HHMMSS
```

### Collections Not Migrated

**Cause**: No v1 collections found

**Result**: This is normal for fresh installations. The script will:
- Still create workspace config
- Collections will be created during first indexing

## Examples

### Example 1: Simple Python Project

```bash
python scripts/migrate_to_workspace.py \
  --from /home/user/my-fastapi-app \
  --name "My FastAPI App"
```

**Result**:
- Detected: `python`, `api_server`
- Collections: `context_vectors` → `project_default_vectors`
- Config: `.context-workspace.json` created

### Example 2: Full-Stack Project

```bash
python scripts/migrate_to_workspace.py \
  --from /home/user/fullstack-app \
  --name "Full-Stack Application"
```

**Result**:
- Detected: `python`, `javascript`, `typescript`
- Type: `application` (multiple languages)
- All collections migrated

### Example 3: Dry-Run First (Recommended)

```bash
# Step 1: See what will happen
python scripts/migrate_to_workspace.py \
  --from /home/user/my-project \
  --name "My Project" \
  --dry-run

# Step 2: Review output

# Step 3: Execute for real
python scripts/migrate_to_workspace.py \
  --from /home/user/my-project \
  --name "My Project"
```

## Advanced Features

### Multiple Projects (Post-Migration)

After migration, you can add more projects by editing `.context-workspace.json`:

```json
{
  "version": "2.0.0",
  "name": "My Workspace",
  "projects": [
    {
      "id": "default",
      "name": "Main Project",
      "path": "/path/to/main"
    },
    {
      "id": "frontend",
      "name": "Frontend",
      "path": "/path/to/frontend"
    }
  ]
}
```

### Custom Exclusions

Edit the generated config to add custom exclusions:

```json
{
  "indexing": {
    "enabled": true,
    "priority": "high",
    "exclude": [
      ".git",
      "node_modules",
      "custom-vendor-dir",
      "*.min.js"
    ]
  }
}
```

## Logs

All migration activity is logged to:
- **Console**: Progress and summary
- **File**: `migration.log` (detailed logs)

```bash
# View detailed logs
cat migration.log

# Follow logs in real-time
tail -f migration.log
```

## Safety Features

1. **Pre-flight Checks**: Validates environment before starting
2. **Automatic Backups**: Creates timestamped backups
3. **Dry-Run Mode**: Test without changes
4. **Atomic Operations**: Collections fully migrated or rolled back
5. **Validation**: Post-migration verification
6. **Rollback Support**: Undo if needed
7. **Detailed Logging**: Track every step

## FAQ

**Q: Can I migrate multiple times?**
A: No. The script detects existing workspace configs and aborts to prevent double migration.

**Q: What happens to my existing data?**
A: All vector data is preserved. Collections are renamed, not recreated.

**Q: Do I need to re-index after migration?**
A: No. All indexed data is migrated. However, you may want to re-index to ensure consistency.

**Q: Can I use v1 and v2 simultaneously?**
A: No. Once migrated, you're in v2 workspace mode. Rollback if you need v1.

**Q: What if I have custom collection names?**
A: The script only migrates standard v1 collections. Custom collections are not affected.

**Q: How long does migration take?**
A: Depends on collection size:
- Small (< 1k vectors): ~5-10 seconds
- Medium (1k-10k vectors): ~30-60 seconds
- Large (10k-100k vectors): ~5-10 minutes

## Support

If you encounter issues:

1. Check logs: `cat migration.log`
2. Run with `--dry-run` to diagnose
3. Verify Qdrant connection
4. Check file permissions
5. Review this guide's troubleshooting section

## Version History

- **v1.0.0** (2023-11-10): Initial release
  - Basic migration support
  - Qdrant collection renaming
  - Automatic detection
  - Dry-run mode
  - Rollback support
