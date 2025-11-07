# Automatic Codebase Indexing Solution

## Problem Summary

The Context MCP server was not automatically indexing existing files on startup. The file monitor only watched for file CHANGES (created, modified, deleted events), but never scanned existing files. This is a classic watchdog pattern limitation - it only reacts to new events, not existing state.

**Result**: Even though all services were healthy, 0 files were indexed because no files were being changed.

## Root Cause

The `FileMonitor` class uses Python's `watchdog` library, which only monitors for file system events that occur AFTER the observer starts. It does not scan or report on files that already exist.

**Before:**
```python
# File monitor starts watching
await start_file_monitor(on_change_callback=queue_file_change)

# But no files are queued because:
# 1. Watchdog only reports NEW events (create, modify, delete)
# 2. Existing files don't trigger any events
# 3. Queue remains empty forever unless files are modified
```

## Solution Implemented

### 1. Created Initial Indexer (`src/indexing/initial_indexer.py`)

A new service that scans existing files on startup and queues them for indexing:

**Key Features:**
- Recursively scans all monitored paths
- Respects ignore patterns (`.git`, `node_modules`, etc.)
- Filters by supported file extensions
- Queues files in batches to avoid overwhelming the system
- Provides progress logging
- Returns statistics (total files, queued, failed)

**Usage:**
```python
from src.indexing.initial_indexer import run_initial_indexing
from src.indexing.queue import queue_file_change

stats = await run_initial_indexing(on_file_callback=queue_file_change)
# Returns: {"total_files": 150, "queued_files": 150, "failed_files": 0}
```

### 2. Integrated into Server Startup (`src/mcp_server/server.py`)

Added initial indexing to the startup sequence, AFTER all services are initialized:

**Startup Order:**
1. Initialize MCP server
2. Initialize database
3. Start file monitor (for future changes)
4. Connect to Qdrant
5. Initialize embedding service
6. **Run initial indexing** ← NEW!
7. Start serving requests

**Code:**
```python
# Run initial indexing of existing files
try:
    from src.indexing.initial_indexer import run_initial_indexing
    
    logger.info("Starting initial indexing of existing files...")
    stats = await run_initial_indexing(on_file_callback=queue_file_change)
    logger.info(
        f"Initial indexing completed: {stats['queued_files']} files queued, "
        f"{stats['failed_files']} failed out of {stats['total_files']} total"
    )
except Exception as e:
    logger.error(f"Failed to run initial indexing: {e}", exc_info=True)
```

### 3. Added Manual Trigger Tool (`src/mcp_server/tools/indexing.py`)

Added MCP tool to manually trigger initial indexing:

```python
@mcp.tool()
async def trigger_initial_indexing() -> Dict[str, Any]:
    """
    Manually trigger initial indexing of existing files
    
    Useful for re-indexing the codebase or recovering from indexing failures.
    """
```

### 4. Enhanced Queue Progress Logging (`src/indexing/queue.py`)

Improved logging to show indexing progress:

**Before:**
```
Starting queue processing...
Queue processing completed in 45.2s
```

**After:**
```
Starting queue processing... (150 items in queue)
Indexing progress: 10/150 files processed (10 successful, 0 failed)
Indexing progress: 20/150 files processed (20 successful, 0 failed)
...
Indexing progress: 150/150 files processed (148 successful, 2 failed)
Queue processing completed in 45.2s: 148 successful, 2 failed
```

## How It Works

### Startup Flow

```
Container Start
    ↓
Initialize Services (Qdrant, Embeddings, etc.)
    ↓
Start File Monitor (watches for future changes)
    ↓
Run Initial Indexing
    ↓
    ├─→ Scan directory tree recursively
    ├─→ Filter by ignore patterns
    ├─→ Filter by supported extensions
    ├─→ Queue files in batches (50 at a time)
    └─→ Log progress
    ↓
Queue Processing Starts
    ↓
    ├─→ Check embedding service is ready
    ├─→ Process files one by one
    ├─→ Extract metadata
    ├─→ Generate embeddings
    ├─→ Store in Qdrant
    └─→ Log progress every 10 files
    ↓
Indexing Complete
    ↓
Server Ready (continues monitoring for changes)
```

### Continuous Operation

After initial indexing completes:

1. **File Monitor** continues watching for changes
2. **New/Modified Files** are automatically queued
3. **Queue Processor** handles both initial and incremental indexing
4. **Progress Logging** shows what's happening

## Expected Behavior

### On Container Startup

```
INFO: Starting initial indexing of existing files...
INFO: Scanning directory for existing files: /app
INFO: Found 150 files to index in /app
INFO: Total files found: 150
INFO: Queued 50/150 files for indexing...
INFO: Queued 100/150 files for indexing...
INFO: Queued 150/150 files for indexing...
INFO: Initial indexing complete: 150 files queued, 0 failed
INFO: Initial indexing completed: 150 files queued, 0 failed out of 150 total
INFO: Starting queue processing... (150 items in queue)
INFO: Indexing progress: 10/150 files processed (10 successful, 0 failed)
INFO: Indexing progress: 20/150 files processed (20 successful, 0 failed)
...
INFO: Queue processing completed in 45.2s: 148 successful, 2 failed
```

### During Normal Operation

```
INFO: File created: /app/src/new_file.py
INFO: Added to queue: created - /app/src/new_file.py (queue size: 1)
INFO: Starting queue processing... (1 items in queue)
INFO: Processing: created - /app/src/new_file.py
INFO: Successfully indexed /app/src/new_file.py as python
INFO: Queue processing completed in 0.5s: 1 successful, 0 failed
```

## Configuration

### Monitored Paths

Configured in `src/config/settings.py`:
```python
indexed_paths = ["./"]  # Monitor current directory
```

### Ignore Patterns

```python
ignore_patterns = [
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache"
]
```

### Supported File Extensions

Defined in `src/indexing/initial_indexer.py`:
```python
supported_extensions = {
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".java", ".cpp", ".hpp", ".h", ".cc", ".cxx",
    ".c", ".go", ".rs", ".rb", ".php", ".cs",
    ".swift", ".kt", ".kts", ".scala", ".m", ".mm"
}
```

## Testing

### Manual Testing

1. **Check logs on startup**:
   ```bash
   docker logs context-server --tail 100 | grep -i "initial indexing"
   ```

2. **Verify files are queued**:
   ```bash
   curl http://localhost:8000/indexing/status
   ```

3. **Trigger manual re-indexing**:
   Use the MCP tool `trigger_initial_indexing`

### Expected Results

- Initial indexing should find and queue all eligible files
- Queue should process files with progress logging
- Status endpoint should show indexed files count
- Qdrant should contain vectors for indexed files

## Troubleshooting

### No Files Found

**Symptom**: `Total files found: 0`

**Causes**:
- Wrong monitored path
- All files match ignore patterns
- No supported file types in directory

**Solution**: Check `indexed_paths` and `ignore_patterns` in settings

### Files Not Processing

**Symptom**: Files queued but not processed

**Causes**:
- Embedding service not initialized
- Queue processing error

**Solution**: Check logs for embedding service errors

### Slow Indexing

**Symptom**: Indexing takes very long

**Causes**:
- Large files
- Many files
- Slow embedding generation

**Solution**: 
- Increase batch size
- Use Google Embeddings API (faster than local)
- Add more ignore patterns

## Future Improvements

1. **Parallel Processing**: Process multiple files concurrently
2. **Smart Re-indexing**: Only re-index changed files
3. **Incremental Updates**: Update only changed sections
4. **Progress API**: Real-time progress via WebSocket
5. **Configurable Batch Size**: Allow tuning via environment variables

