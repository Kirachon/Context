# Context Scripts

Utility scripts for Context workspace management.

## Available Scripts

### `migrate_to_workspace.py`

Migrates single-folder v1 setups to multi-project workspace v2.

**Quick Start:**
```bash
# Dry-run first (recommended)
python scripts/migrate_to_workspace.py \
  --from /path/to/project \
  --name "My Project" \
  --dry-run

# Execute migration
python scripts/migrate_to_workspace.py \
  --from /path/to/project \
  --name "My Project"
```

**Documentation:** See [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) for complete documentation.

**Features:**
- ✅ Automatic language and project type detection
- ✅ Qdrant collection migration
- ✅ Automatic backups
- ✅ Dry-run mode
- ✅ Rollback support
- ✅ Complete validation

**Requirements:**
```bash
pip install -r requirements/base.txt
```

## Common Use Cases

### First-Time Migration

```bash
# 1. Check what will happen (no changes)
python scripts/migrate_to_workspace.py \
  --from . \
  --name "My Project" \
  --dry-run

# 2. Execute migration
python scripts/migrate_to_workspace.py \
  --from . \
  --name "My Project"

# 3. Review the generated config
cat .context-workspace.json

# 4. Start using workspace mode
export WORKSPACE_MODE=true
python -m src.main
```

### Rollback After Failed Migration

```bash
# Use the backup directory created during migration
python scripts/migrate_to_workspace.py \
  --rollback migration_backup_20231110_120000
```

### Custom Configuration

```bash
# Migrate to a specific output location
python scripts/migrate_to_workspace.py \
  --from /path/to/project \
  --name "My Project" \
  --output /custom/path/workspace.json
```

## Script Details

### migrate_to_workspace.py

**Location:** `/home/user/Context/scripts/migrate_to_workspace.py`

**Lines of Code:** 711

**Dependencies:**
- `click` - CLI interface
- `qdrant_client` - Vector database operations
- `pydantic` - Configuration validation
- Standard library: `asyncio`, `json`, `pathlib`, etc.

**Logging:**
- Console output for progress
- Detailed logs in `migration.log`

**Backup Strategy:**
1. Creates timestamped backup directory
2. Backs up `settings.py`
3. Exports Qdrant collection metadata
4. Preserves all data for rollback

**Safety Features:**
- Pre-flight validation
- Atomic collection migrations
- Post-migration validation
- Rollback support
- Dry-run mode

## Installation

### Prerequisites

1. **Python 3.11+**
   ```bash
   python --version
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements/base.txt
   ```

3. **Qdrant Running**
   ```bash
   # Using Docker
   docker-compose up -d qdrant

   # Verify
   curl http://localhost:6333/collections
   ```

### Make Scripts Executable

```bash
chmod +x scripts/*.py
```

## Environment Variables

The migration script uses settings from `src/config/settings.py`:

- `QDRANT_HOST` - Qdrant server host (default: `localhost`)
- `QDRANT_PORT` - Qdrant server port (default: `6333`)
- `QDRANT_API_KEY` - Optional API key for Qdrant Cloud

Example:
```bash
export QDRANT_HOST=localhost
export QDRANT_PORT=6333
python scripts/migrate_to_workspace.py --from . --name "My Project"
```

## Troubleshooting

### Import Errors

```bash
# Error: No module named 'click'
pip install -r requirements/base.txt

# Error: No module named 'src'
# Run from project root:
cd /home/user/Context
python scripts/migrate_to_workspace.py ...
```

### Connection Errors

```bash
# Error: Cannot connect to Qdrant
# Check Qdrant is running:
docker ps | grep qdrant
curl http://localhost:6333/collections

# Start if needed:
docker-compose up -d qdrant
```

### Permission Errors

```bash
# Make scripts executable
chmod +x scripts/*.py

# Check write permissions
ls -la .
```

## Testing

### Test Migration Script

```bash
# Syntax check
python -m py_compile scripts/migrate_to_workspace.py

# Help text
python scripts/migrate_to_workspace.py --help

# Dry-run test
python scripts/migrate_to_workspace.py \
  --from . \
  --name "Test Project" \
  --dry-run
```

## Contributing

When adding new scripts:

1. Add proper documentation header
2. Use `click` for CLI interface
3. Add logging with `logging` module
4. Include `--help` text
5. Add entry to this README
6. Make executable with `chmod +x`

## Support

For detailed migration documentation, see [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md).

For issues or questions:
- Check logs: `cat migration.log`
- Review documentation
- Check troubleshooting sections
