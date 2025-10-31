"""
File System Monitor

Watchdog-based real-time file system monitoring for automatic change detection.
"""

import asyncio
import logging
import os
import sys
from typing import List, Optional, Callable
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.config.settings import settings

logger = logging.getLogger(__name__)


class FileChangeHandler(FileSystemEventHandler):
    """
    Handler for file system events
    
    Processes file create, modify, and delete events and queues them for indexing.
    """
    
    def __init__(self, on_change_callback: Optional[Callable] = None):
        """
        Initialize file change handler
        
        Args:
            on_change_callback: Optional callback function for file changes
        """
        super().__init__()
        self.on_change_callback = on_change_callback
        self.ignore_patterns = settings.ignore_patterns
        logger.info(f"FileChangeHandler initialized with ignore patterns: {self.ignore_patterns}")
    
    def _should_ignore(self, path: str) -> bool:
        """
        Check if path should be ignored based on ignore patterns
        
        Args:
            path: File path to check
            
        Returns:
            bool: True if path should be ignored
        """
        path_obj = Path(path)
        
        # Check each ignore pattern
        for pattern in self.ignore_patterns:
            # Check if pattern is in any part of the path
            if pattern in path_obj.parts:
                return True
            # Check if filename matches pattern
            if path_obj.name.startswith(pattern):
                return True
        
        return False
    
    def _is_supported_file(self, path: str) -> bool:
        """
        Check if file type is supported for indexing
        
        Args:
            path: File path to check
            
        Returns:
            bool: True if file type is supported
        """
        supported_extensions = {
            '.py',  # Python
            '.js', '.jsx',  # JavaScript
            '.ts', '.tsx',  # TypeScript
            '.java',  # Java
            '.cpp', '.hpp', '.h', '.cc', '.cxx',  # C++
        }
        
        path_obj = Path(path)
        return path_obj.suffix in supported_extensions
    
    def on_created(self, event: FileSystemEvent):
        """
        Handle file creation event
        
        Args:
            event: File system event
        """
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        if self._should_ignore(file_path):
            logger.debug(f"Ignoring created file (matches ignore pattern): {file_path}")
            return
        
        if not self._is_supported_file(file_path):
            logger.debug(f"Ignoring created file (unsupported type): {file_path}")
            return
        
        logger.info(f"File created: {file_path}")
        
        if self.on_change_callback:
            asyncio.create_task(self.on_change_callback('created', file_path))
    
    def on_modified(self, event: FileSystemEvent):
        """
        Handle file modification event
        
        Args:
            event: File system event
        """
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        if self._should_ignore(file_path):
            logger.debug(f"Ignoring modified file (matches ignore pattern): {file_path}")
            return
        
        if not self._is_supported_file(file_path):
            logger.debug(f"Ignoring modified file (unsupported type): {file_path}")
            return
        
        logger.info(f"File modified: {file_path}")
        
        if self.on_change_callback:
            asyncio.create_task(self.on_change_callback('modified', file_path))
    
    def on_deleted(self, event: FileSystemEvent):
        """
        Handle file deletion event
        
        Args:
            event: File system event
        """
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        if self._should_ignore(file_path):
            logger.debug(f"Ignoring deleted file (matches ignore pattern): {file_path}")
            return
        
        # For deleted files, we can't check if they're supported
        # So we process all deletions and let the indexer handle it
        logger.info(f"File deleted: {file_path}")
        
        if self.on_change_callback:
            asyncio.create_task(self.on_change_callback('deleted', file_path))


class FileMonitor:
    """
    File System Monitor
    
    Monitors configured paths for file changes using Watchdog observer.
    """
    
    def __init__(self, paths: Optional[List[str]] = None, on_change_callback: Optional[Callable] = None):
        """
        Initialize file monitor
        
        Args:
            paths: List of paths to monitor (defaults to settings.indexed_paths)
            on_change_callback: Optional callback function for file changes
        """
        self.paths = paths or settings.indexed_paths
        self.on_change_callback = on_change_callback
        self.observer: Optional[Observer] = None
        self.is_running = False
        
        logger.info(f"FileMonitor initialized for paths: {self.paths}")
    
    async def start(self):
        """Start file system monitoring"""
        if self.is_running:
            logger.warning("FileMonitor is already running")
            return
        
        logger.info("Starting FileMonitor...")
        
        try:
            # Create observer
            self.observer = Observer()
            
            # Create event handler
            event_handler = FileChangeHandler(on_change_callback=self.on_change_callback)
            
            # Schedule monitoring for each path
            for path in self.paths:
                # Resolve path relative to project root
                if not os.path.isabs(path):
                    path = os.path.abspath(path)
                
                if not os.path.exists(path):
                    logger.warning(f"Path does not exist, skipping: {path}")
                    continue
                
                logger.info(f"Monitoring path: {path}")
                self.observer.schedule(event_handler, path, recursive=True)
            
            # Start observer
            self.observer.start()
            self.is_running = True
            
            logger.info("FileMonitor started successfully")
            logger.info(f"Monitoring {len(self.paths)} paths with ignore patterns: {settings.ignore_patterns}")
            
        except Exception as e:
            logger.error(f"Failed to start FileMonitor: {e}", exc_info=True)
            self.is_running = False
            raise
    
    async def stop(self):
        """Stop file system monitoring"""
        if not self.is_running:
            logger.warning("FileMonitor is not running")
            return
        
        logger.info("Stopping FileMonitor...")
        
        try:
            if self.observer:
                self.observer.stop()
                self.observer.join(timeout=5)
            
            self.is_running = False
            logger.info("FileMonitor stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping FileMonitor: {e}", exc_info=True)
    
    def get_status(self) -> dict:
        """
        Get file monitor status
        
        Returns:
            dict: Monitor status information
        """
        return {
            "running": self.is_running,
            "monitored_paths": self.paths,
            "ignore_patterns": settings.ignore_patterns,
            "observer_alive": self.observer.is_alive() if self.observer else False
        }


# Global file monitor instance
file_monitor = FileMonitor()


async def start_file_monitor(on_change_callback: Optional[Callable] = None):
    """
    Start the file monitor (entry point for integration)
    
    Args:
        on_change_callback: Optional callback function for file changes
    """
    if on_change_callback:
        file_monitor.on_change_callback = on_change_callback
    await file_monitor.start()


async def stop_file_monitor():
    """Stop the file monitor (entry point for integration)"""
    await file_monitor.stop()


def get_monitor_status() -> dict:
    """Get file monitor status (entry point for health checks)"""
    return file_monitor.get_status()

