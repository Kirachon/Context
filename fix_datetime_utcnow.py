#!/usr/bin/env python3
"""
Script to automatically fix datetime.utcnow() deprecation warnings.
Replaces datetime.utcnow() with datetime.now(timezone.utc).
"""

import re
import sys
from pathlib import Path

def fix_file(file_path):
    """Fix datetime.utcnow() in a single file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Check if file uses datetime.utcnow()
    if 'utcnow' not in content:
        return False
    
    # Fix import statement
    if 'from datetime import datetime' in content and 'timezone' not in content:
        content = re.sub(
            r'from datetime import datetime(?!\w)',
            'from datetime import datetime, timezone',
            content
        )
    
    # Replace datetime.utcnow() with datetime.now(timezone.utc)
    content = re.sub(
        r'datetime\.utcnow\(\)',
        'datetime.now(timezone.utc)',
        content
    )
    
    # Handle default_factory cases
    content = re.sub(
        r'default_factory=datetime\.now\(timezone\.utc\)\)',
        'default_factory=lambda: datetime.now(timezone.utc))',
        content
    )
    
    # Handle Column default cases (need lambda)
    content = re.sub(
        r'default=datetime\.now\(timezone\.utc\)\)',
        'default=lambda: datetime.now(timezone.utc))',
        content
    )
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    
    return False

def main():
    """Fix all files with datetime.utcnow()"""
    files_to_fix = [
        # Search module
        "src/search/ast_models.py",
        "src/search/ast_search.py",
        "src/search/embedding_cache.py",
        "src/search/pagination.py",
        "src/search/query_profiler.py",
        "src/search/ranking.py",
        "src/search/semantic_search.py",
        # Vector DB
        "src/vector_db/qdrant_client.py",
        # MCP Server
        "src/mcp_server/mcp_app.py",
        "src/mcp_server/server.py",
        "src/mcp_server/tools/ast_search.py",
        "src/mcp_server/tools/capabilities.py",
        "src/mcp_server/tools/cross_language_analysis.py",
        "src/mcp_server/tools/health.py",
        "src/mcp_server/tools/indexing.py",
        "src/mcp_server/tools/pattern_search.py",
        "src/mcp_server/tools/search.py",
        "src/mcp_server/tools/vector.py",
        # Tests
        "tests/unit/test_advanced_search_filtering.py",
        "tests/unit/test_semantic_search.py",
    ]
    
    fixed_count = 0
    for file_path in files_to_fix:
        path = Path(file_path)
        if path.exists():
            if fix_file(path):
                print(f"✅ Fixed: {file_path}")
                fixed_count += 1
            else:
                print(f"⏭️  Skipped: {file_path} (no changes needed)")
        else:
            print(f"❌ Not found: {file_path}")
    
    print(f"\n🎉 Fixed {fixed_count} files")
    return 0

if __name__ == "__main__":
    sys.exit(main())

