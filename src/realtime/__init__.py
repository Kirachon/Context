"""
Real-time Code Intelligence Package (Story 2.2)

Provides real-time file watching, incremental indexing, live code analysis,
and performance optimization for large codebases.
"""

from src.realtime.file_watcher import (
    RealTimeFileWatcher,
    RealTimeFileHandler,
    FileChangeEvent,
    start_real_time_watcher,
    stop_real_time_watcher,
    get_watcher_status,
)
from src.realtime.incremental_indexer import IncrementalIndexer, get_incremental_indexer, attach_watcher

__all__ = [
    "RealTimeFileWatcher",
    "RealTimeFileHandler",
    "FileChangeEvent",
    "start_real_time_watcher",
    "stop_real_time_watcher",
    "get_watcher_status",
    "IncrementalIndexer",
    "get_incremental_indexer",
    "attach_watcher",
]
