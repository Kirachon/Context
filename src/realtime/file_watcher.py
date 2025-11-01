"""
Real-time File Watcher (Story 2.2 AC1)

Enhanced file system monitoring with sub-second latency, intelligent debouncing,
and advanced filtering for real-time code intelligence.

Builds on Story 1.3 file monitoring foundation with performance optimizations.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from src.config.settings import settings
from src.parsing.parser import detect_language, Language

logger = logging.getLogger(__name__)


@dataclass
class FileChangeEvent:
    """Enhanced file change event with metadata."""
    event_type: str  # created, modified, deleted, moved
    file_path: str
    timestamp: float
    language: Optional[Language] = None
    content_hash: Optional[str] = None
    file_size: Optional[int] = None
    is_debounced: bool = False


@dataclass
class DebounceState:
    """State tracking for file change debouncing."""
    last_event_time: float = 0.0
    event_count: int = 0
    pending_events: deque = field(default_factory=deque)
    debounce_task: Optional[asyncio.Task] = None


class RealTimeFileHandler(FileSystemEventHandler):
    """
    Enhanced file system event handler with intelligent debouncing.
    
    Features:
    - Sub-second change detection
    - Intelligent debouncing for rapid file changes
    - Language-aware filtering
    - Content hash tracking for duplicate detection
    - Performance monitoring
    """
    
    def __init__(self, on_change_callback: Optional[Callable] = None):
        super().__init__()
        self.on_change_callback = on_change_callback
        self.debounce_states: Dict[str, DebounceState] = defaultdict(DebounceState)
        self.debounce_delay = 0.5  # 500ms debounce
        self.max_events_per_second = 10
        self.content_hashes: Dict[str, str] = {}
        
        # Performance tracking
        self.stats = {
            "events_processed": 0,
            "events_debounced": 0,
            "events_filtered": 0,
            "avg_processing_time": 0.0
        }
        
        logger.info("RealTimeFileHandler initialized with intelligent debouncing")

    def _should_process_file(self, file_path: str) -> bool:
        """Check if file should be processed based on language and patterns."""
        path = Path(file_path)
        
        # Check ignore patterns
        for pattern in settings.ignore_patterns:
            if path.match(pattern):
                return False
        
        # Check if it's a supported language
        language = detect_language(path)
        return language is not None

    def _get_content_hash(self, file_path: str) -> Optional[str]:
        """Get content hash for duplicate detection."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.sha256(content).hexdigest()
        except Exception as e:
            logger.debug(f"Could not hash file {file_path}: {e}")
            return None

    def _create_change_event(self, event_type: str, file_path: str) -> FileChangeEvent:
        """Create enhanced file change event with metadata."""
        path = Path(file_path)
        language = detect_language(path) if path.exists() else None
        content_hash = self._get_content_hash(file_path) if path.exists() else None
        file_size = path.stat().st_size if path.exists() else None
        
        return FileChangeEvent(
            event_type=event_type,
            file_path=file_path,
            timestamp=time.time(),
            language=language,
            content_hash=content_hash,
            file_size=file_size
        )

    async def _debounced_callback(self, file_path: str, event_type: str):
        """Execute debounced callback after delay."""
        state = self.debounce_states[file_path]
        
        # Wait for debounce delay
        await asyncio.sleep(self.debounce_delay)
        
        # Check if more events came in during delay
        if time.time() - state.last_event_time < self.debounce_delay:
            # More events came in, extend debounce
            return
        
        # Process the final event
        try:
            change_event = self._create_change_event(event_type, file_path)
            change_event.is_debounced = True
            
            if self.on_change_callback:
                await self.on_change_callback(change_event)
            
            self.stats["events_processed"] += 1
            logger.debug(f"Processed debounced event: {event_type} - {file_path}")
            
        except Exception as e:
            logger.error(f"Error in debounced callback for {file_path}: {e}")
        finally:
            # Clean up debounce state
            state.debounce_task = None

    def _handle_file_event(self, event_type: str, file_path: str):
        """Handle file system event with debouncing."""
        start_time = time.time()
        
        # Check if file should be processed
        if not self._should_process_file(file_path):
            self.stats["events_filtered"] += 1
            return
        
        # Update debounce state
        state = self.debounce_states[file_path]
        state.last_event_time = time.time()
        state.event_count += 1
        
        # Check for rapid events (potential file system storm)
        if state.event_count > self.max_events_per_second:
            logger.warning(f"Rapid events detected for {file_path}, extending debounce")
            self.stats["events_debounced"] += 1
            return
        
        # Cancel existing debounce task
        if state.debounce_task and not state.debounce_task.done():
            state.debounce_task.cancel()
        
        # Start new debounce task
        state.debounce_task = asyncio.create_task(
            self._debounced_callback(file_path, event_type)
        )
        
        # Update performance stats
        processing_time = time.time() - start_time
        self.stats["avg_processing_time"] = (
            (self.stats["avg_processing_time"] * self.stats["events_processed"] + processing_time) /
            (self.stats["events_processed"] + 1)
        )

    def on_created(self, event: FileSystemEvent):
        """Handle file creation with debouncing."""
        if not event.is_directory:
            self._handle_file_event("created", event.src_path)

    def on_modified(self, event: FileSystemEvent):
        """Handle file modification with debouncing."""
        if not event.is_directory:
            self._handle_file_event("modified", event.src_path)

    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion with debouncing."""
        if not event.is_directory:
            self._handle_file_event("deleted", event.src_path)

    def on_moved(self, event: FileSystemEvent):
        """Handle file move/rename with debouncing."""
        if not event.is_directory:
            # Treat as delete + create
            self._handle_file_event("deleted", event.src_path)
            self._handle_file_event("created", event.dest_path)

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            **self.stats,
            "active_debounce_states": len(self.debounce_states),
            "pending_tasks": sum(
                1 for state in self.debounce_states.values()
                if state.debounce_task and not state.debounce_task.done()
            )
        }


class RealTimeFileWatcher:
    """
    Enhanced file watcher for real-time code intelligence.

    Builds on Story 1.3 foundation with performance optimizations:
    - Sub-second latency detection
    - Intelligent debouncing
    - Language-aware filtering
    - Performance monitoring
    - Memory management
    """

    def __init__(self, paths: Optional[List[str]] = None, on_change_callback: Optional[Callable] = None):
        self.paths = paths or settings.indexed_paths
        self.on_change_callback = on_change_callback
        self.observer: Optional[Observer] = None
        self.handler: Optional[RealTimeFileHandler] = None
        self.is_running = False
        self.start_time: Optional[float] = None

        logger.info(f"RealTimeFileWatcher initialized for {len(self.paths)} paths")

    async def start(self):
        """Start enhanced file system monitoring."""
        if self.is_running:
            logger.warning("RealTimeFileWatcher already running")
            return

        logger.info("Starting RealTimeFileWatcher...")
        self.start_time = time.time()

        try:
            # Create observer and handler
            self.observer = Observer()
            self.handler = RealTimeFileHandler(on_change_callback=self.on_change_callback)

            # Schedule monitoring for each path
            monitored_paths = 0
            for path_str in self.paths:
                path = Path(path_str).resolve()
                if not path.exists():
                    logger.warning(f"Path does not exist: {path}")
                    continue

                logger.info(f"Monitoring path: {path}")
                self.observer.schedule(self.handler, str(path), recursive=True)
                monitored_paths += 1

            if monitored_paths == 0:
                raise ValueError("No valid paths to monitor")

            # Start observer
            self.observer.start()
            self.is_running = True

            logger.info(f"RealTimeFileWatcher started - monitoring {monitored_paths} paths")

        except Exception as e:
            logger.error(f"Failed to start RealTimeFileWatcher: {e}")
            self.is_running = False
            raise

    async def stop(self):
        """Stop file system monitoring."""
        if not self.is_running:
            return

        logger.info("Stopping RealTimeFileWatcher...")

        try:
            if self.observer:
                self.observer.stop()
                self.observer.join(timeout=5)

            # Cancel pending debounce tasks
            if self.handler:
                for state in self.handler.debounce_states.values():
                    if state.debounce_task and not state.debounce_task.done():
                        state.debounce_task.cancel()

            self.is_running = False
            logger.info("RealTimeFileWatcher stopped")

        except Exception as e:
            logger.error(f"Error stopping RealTimeFileWatcher: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive watcher status."""
        uptime = time.time() - self.start_time if self.start_time else 0

        status = {
            "running": self.is_running,
            "uptime_seconds": uptime,
            "monitored_paths": self.paths,
            "observer_alive": self.observer.is_alive() if self.observer else False,
        }

        if self.handler:
            status["handler_stats"] = self.handler.get_stats()

        return status


# Global enhanced file watcher instance
real_time_watcher = RealTimeFileWatcher()


async def start_real_time_watcher(on_change_callback: Optional[Callable] = None):
    """Start the enhanced real-time file watcher."""
    if on_change_callback:
        real_time_watcher.on_change_callback = on_change_callback
    await real_time_watcher.start()


async def stop_real_time_watcher():
    """Stop the enhanced real-time file watcher."""
    await real_time_watcher.stop()


def get_watcher_status() -> Dict[str, Any]:
    """Get real-time watcher status."""
    return real_time_watcher.get_status()
