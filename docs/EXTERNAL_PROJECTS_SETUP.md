# Indexing External Projects

This guide explains how to configure Context to index codebases located outside the Context repository.

## Quick Start

### Option 1: Automatic (Recommended)

If your projects are in the parent directory of Context (e.g., `D:\GitProjects\Context` and `D:\GitProjects\Boarding_House`), **no configuration needed**! The default mount will work automatically.

Just call the MCP tool:
```
ast_index_directory("D:\\GitProjects\\Boarding_House\\src", recursive=true)
```

### Option 2: Custom Location

If your projects are in a different location (e.g., `C:\Users\username\projects`):

1. **Create/edit `.env` file** in the Context root directory:
   ```bash
   # Windows
   EXTERNAL_PROJECTS_PATH=C:/Users/username/projects
   
   # Linux/Mac
   EXTERNAL_PROJECTS_PATH=/home/username/projects
   ```

2. **Restart the container**:
   ```bash
   docker-compose restart context-server
   ```

3. **Index your project**:
   ```
   ast_index_directory("C:\\Users\\username\\projects\\MyProject\\src", recursive=true)
   ```

## How It Works

### Path Resolution

The system automatically resolves host paths to container paths:

1. **Direct paths** (already in container) - used as-is
2. **Windows absolute paths** (`D:\GitProjects\MyProject`) - mapped to `/external/MyProject`
3. **Unix-style paths** (`/d/gitprojects/MyProject`) - mapped to `/external/MyProject`
4. **Custom mappings** via `PATH_MAPPINGS_JSON` (advanced)

### Container Mount

The `EXTERNAL_PROJECTS_PATH` directory is mounted at `/external` in the container (read-only).

**Default behavior:**
- If `EXTERNAL_PROJECTS_PATH` is not set, defaults to `../..` (parent of parent directory)
- For Context at `D:\GitProjects\Context`, this mounts `D:\GitProjects` at `/external`
- Projects like `D:\GitProjects\Boarding_House` become accessible as `/external/Boarding_House`

## Supported Path Formats

When calling `ast_index_directory`, you can use any of these formats:

```python
# Windows backslash (escaped)
ast_index_directory("D:\\GitProjects\\Boarding_House\\src", recursive=true)

# Windows forward slash
ast_index_directory("D:/GitProjects/Boarding_House/src", recursive=true)

# Unix-style (Git Bash/WSL)
ast_index_directory("/d/gitprojects/Boarding_House/src", recursive=true)

# Container path (if you know it)
ast_index_directory("/external/Boarding_House/src", recursive=true)
```

## Troubleshooting

### Error: "Directory does not exist"

**Cause:** The path is not accessible in the container.

**Solution:**
1. Check that `EXTERNAL_PROJECTS_PATH` is set correctly in `.env`
2. Verify the path exists on your host machine
3. Restart the container: `docker-compose restart context-server`
4. Check the error message for specific configuration hints

### Multiple Project Locations

If you have projects in multiple locations (e.g., `D:\GitProjects` and `C:\Users\username\work`), you have two options:

**Option A: Mount parent directory**
```bash
# Mount the drive root (not recommended for security)
EXTERNAL_PROJECTS_PATH=D:/
```

**Option B: Use PATH_MAPPINGS_JSON (advanced)**
```bash
PATH_MAPPINGS_JSON={"D:/GitProjects": "/external/personal", "C:/Users/username/work": "/external/work"}
```

Then restart the container.

## Security Note

External projects are mounted **read-only** (`ro` flag). The Context server can read and index your code but cannot modify it.

## Performance Tips

- **Index selectively**: Only index the directories you need (e.g., `src/` instead of the entire project)
- **Use `.gitignore` patterns**: The indexer respects common ignore patterns (`node_modules`, `.git`, etc.)
- **Monitor progress**: Use `indexing_progress()` MCP tool to track indexing status

