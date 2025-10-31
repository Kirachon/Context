"""
Context Indexing Package

Provides file system monitoring, file indexing, and metadata management.
"""

from src.indexing.file_monitor import FileMonitor
from src.indexing.file_indexer import FileIndexer

__all__ = ["FileMonitor", "FileIndexer"]

