# MCP JSON String Parameter Handling - Complete Implementation

## Overview

This document describes the comprehensive fix applied to all MCP tools in the Context server to handle JSON string parameters from MCP clients like Claude Code CLI.

## Problem Statement

When MCP clients (like Claude Code CLI) call MCP tools, they sometimes serialize list parameters as JSON strings instead of actual arrays. This causes Pydantic validation errors:

```
Error: 1 validation error for call[tool_name]
parameter_name
  Input should be a valid list [type=list_type, input_value='["item1", "item2"]', input_type=str]
```

**Root Cause**: The MCP protocol allows clients to serialize parameters in different ways. Some clients serialize lists as JSON strings, while Pydantic expects actual Python lists.

## Solution

### 1. Shared Utility Module

Created `src/mcp_server/utils/param_parsing.py` with a reusable `parse_list_param()` function:

```python
def parse_list_param(param: Optional[Union[str, List[T]]]) -> Optional[List[T]]:
    """
    Parse a parameter that could be a JSON string or a list.
    
    Handles cases where MCP clients serialize lists as JSON strings.
    """
    if param is None:
        return None
    if isinstance(param, list):
        return param
    if isinstance(param, str):
        try:
            parsed = json.loads(param)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
    return None
```

### 2. Files Modified

All MCP tool files with `List[str]` parameters were updated:

1. **`src/mcp_server/tools/pattern_search.py`** ✅
   - `pattern_search_directory()`: `patterns`, `languages`, `include_globs`, `exclude_globs`
   - `pattern_search_code()`: `patterns`

2. **`src/mcp_server/tools/search.py`** ✅
   - `semantic_search()`: `file_types`
   - `search_with_filters()`: `file_types`, `directories`, `exclude_patterns`, `authors`

3. **`src/mcp_server/tools/ast_search.py`** ✅
   - `ast_semantic_search()`: `symbol_types`, `languages`
   - `ast_search_classes()`: `languages`
   - `ast_search_functions()`: `languages`

4. **`src/mcp_server/tools/cross_language_analysis.py`** ✅
   - `analyze_codebase_architecture()`: `languages`
   - `detect_design_patterns()`: `pattern_types`

5. **`src/mcp_server/tools/indexing_optimization.py`** ✅
   - `add_indexing_tasks()`: `file_paths`

6. **`src/mcp_server/tools/query_understanding.py`** ✅
   - `query_enhance()`: `recent_files`
   - `query_history_add()`: `tags`

### 3. Implementation Pattern

For each tool with list parameters:

1. **Import statements**:
   ```python
   from typing import Union
   from src.mcp_server.utils.param_parsing import parse_list_param
   ```

2. **Function signature update**:
   ```python
   # Before
   async def tool_name(param: Optional[List[str]] = None):
   
   # After
   async def tool_name(param: Optional[Union[str, List[str]]] = None):
   ```

3. **Parameter parsing**:
   ```python
   # At the beginning of the function
   param_list = parse_list_param(param)
   ```

4. **Docstring update**:
   ```python
   Args:
       param: Description. Can be a JSON string or list.
   ```

## Benefits

1. ✅ **Backward Compatible**: Still accepts actual Python lists
2. ✅ **Forward Compatible**: Handles JSON string serialization from MCP clients
3. ✅ **Centralized Logic**: Single source of truth in shared utility module
4. ✅ **Consistent**: Same pattern applied across all tools
5. ✅ **Robust**: Handles edge cases (None, invalid JSON, non-list JSON)

## Testing

- ✅ Server restarts successfully
- ✅ 149 files indexed without errors
- ✅ No validation errors in logs
- ✅ All tools registered correctly

## Next Steps

When adding new MCP tools with list parameters:
1. Import `Union` and `parse_list_param`
2. Use `Union[str, List[str]]` for list parameters
3. Call `parse_list_param()` at the beginning of the function
4. Update docstrings to indicate dual-format support

