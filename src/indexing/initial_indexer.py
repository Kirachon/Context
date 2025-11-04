"""
Initial Indexer

Scans and indexes existing files on startup before file monitoring begins.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import List, Set, Optional
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.config.settings import settings

logger = logging.getLogger(__name__)


class InitialIndexer:
    """
    Initial Indexer
    
    Scans existing files in monitored paths and queues them for indexing.
    This ensures the codebase is indexed on startup, not just when files change.
    """
    
    def __init__(self):
        """Initialize initial indexer"""
        self.ignore_patterns = settings.ignore_patterns
        self.supported_extensions = {
            ".py",  # Python
            ".js", ".jsx",  # JavaScript
            ".ts", ".tsx",  # TypeScript
            ".java",  # Java
            ".cpp", ".hpp", ".h", ".cc", ".cxx",  # C++
            ".c",  # C
            ".go",  # Go
            ".rs",  # Rust
            ".rb",  # Ruby
            ".php",  # PHP
            ".cs",  # C#
            ".swift",  # Swift
            ".kt", ".kts",  # Kotlin
            ".scala",  # Scala
            ".m", ".mm",  # Objective-C
        }
        
        logger.info("InitialIndexer initialized")
    
    def _should_ignore(self, path: Path) -> bool:
        """
        Check if path should be ignored based on ignore patterns
        
        Args:
            path: Path to check
            
        Returns:
            bool: True if path should be ignored
        """
        # Check each ignore pattern
        for pattern in self.ignore_patterns:
            # Check if pattern is in any part of the path
            if pattern in path.parts:
                return True
            # Check if filename matches pattern
            if path.name.startswith(pattern):
                return True
        
        return False
    
    def _is_supported_file(self, path: Path) -> bool:
        """
        Check if file type is supported for indexing
        
        Args:
            path: Path to check
            
        Returns:
            bool: True if file type is supported
        """
        return path.suffix in self.supported_extensions
    
    async def scan_directory(self, directory: str) -> List[str]:
        """
        Recursively scan directory for indexable files
        
        Args:
            directory: Directory path to scan
            
        Returns:
            List of file paths to index
        """
        files_to_index = []
        
        # Resolve to absolute path
        if not os.path.isabs(directory):
            directory = os.path.abspath(directory)
        
        if not os.path.exists(directory):
            logger.warning(f"Directory does not exist: {directory}")
            return files_to_index
        
        logger.info(f"Scanning directory for existing files: {directory}")
        
        try:
            # Walk directory tree
            for root, dirs, files in os.walk(directory):
                root_path = Path(root)
                
                # Filter out ignored directories (modify dirs in-place to prevent descent)
                dirs[:] = [d for d in dirs if not self._should_ignore(root_path / d)]
                
                # Process files
                for file in files:
                    file_path = root_path / file
                    
                    # Skip ignored files
                    if self._should_ignore(file_path):
                        continue
                    
                    # Skip unsupported file types
                    if not self._is_supported_file(file_path):
                        continue
                    
                    # Add to list
                    files_to_index.append(str(file_path))
            
            logger.info(f"Found {len(files_to_index)} files to index in {directory}")
            
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}", exc_info=True)
        
        return files_to_index
    
    async def index_existing_files(
        self, 
        paths: Optional[List[str]] = None,
        on_file_callback: Optional[callable] = None,
        batch_size: int = 50
    ) -> dict:
        """
        Scan and index all existing files in monitored paths
        
        Args:
            paths: List of paths to scan (defaults to settings.indexed_paths)
            on_file_callback: Callback function to queue each file (change_type, file_path)
            batch_size: Number of files to queue per batch
            
        Returns:
            dict: Statistics about the indexing operation
        """
        paths = paths or settings.indexed_paths
        
        logger.info(f"Starting initial indexing of existing files in {len(paths)} paths...")
        
        all_files = []
        
        # Scan all paths
        for path in paths:
            files = await self.scan_directory(path)
            all_files.extend(files)
        
        total_files = len(all_files)
        logger.info(f"Total files found: {total_files}")
        
        if total_files == 0:
            logger.warning("No files found to index!")
            return {
                "total_files": 0,
                "queued_files": 0,
                "failed_files": 0,
            }
        
        # Queue files in batches
        queued_count = 0
        failed_count = 0
        
        for i in range(0, total_files, batch_size):
            batch = all_files[i:i + batch_size]
            
            for file_path in batch:
                try:
                    if on_file_callback:
                        await on_file_callback("created", file_path)
                        queued_count += 1
                except Exception as e:
                    logger.error(f"Failed to queue file {file_path}: {e}")
                    failed_count += 1
            
            # Log progress
            progress = min(i + batch_size, total_files)
            logger.info(f"Queued {progress}/{total_files} files for indexing...")
            
            # Small delay to avoid overwhelming the queue
            await asyncio.sleep(0.1)
        
        logger.info(
            f"Initial indexing complete: {queued_count} files queued, {failed_count} failed"
        )
        
        return {
            "total_files": total_files,
            "queued_files": queued_count,
            "failed_files": failed_count,
        }


# Global initial indexer instance
initial_indexer = InitialIndexer()


async def run_initial_indexing(
    paths: Optional[List[str]] = None,
    on_file_callback: Optional[callable] = None
) -> dict:
    """
    Run initial indexing of existing files (entry point)
    
    Args:
        paths: List of paths to scan (defaults to settings.indexed_paths)
        on_file_callback: Callback function to queue each file
        
    Returns:
        dict: Statistics about the indexing operation
    """
    return await initial_indexer.index_existing_files(paths, on_file_callback)

