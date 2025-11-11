"""
Smart Cache Invalidation

Features:
- Track which files each cached query accessed
- When file changes, invalidate affected queries only
- Incremental invalidation (not full cache clear)
- Batch invalidation (group file changes)
- Debouncing to avoid invalidation storms
"""

import asyncio
import logging
import time
from typing import Dict, Set, List, Optional
from collections import defaultdict
import threading
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class InvalidationEvent:
    """Represents a file change that requires cache invalidation"""

    file_path: str
    event_type: str  # 'modified', 'deleted', 'created'
    timestamp: float
    invalidated: bool = False


class CacheInvalidator:
    """
    Smart cache invalidation based on file changes

    Provides:
    - Tracks file-query relationships
    - Incremental invalidation (only affected queries)
    - Batch invalidation (group multiple file changes)
    - Debouncing (avoid invalidation storms)
    - Pattern-based invalidation (e.g., all .py files)
    """

    def __init__(
        self,
        query_cache=None,
        embedding_cache=None,
        debounce_seconds: float = 2.0,
        batch_size: int = 50,
        stats=None,
    ):
        """
        Initialize cache invalidator

        Args:
            query_cache: QueryCache instance
            embedding_cache: EmbeddingCache instance
            debounce_seconds: Debounce interval to batch changes
            batch_size: Maximum batch size for invalidation
            stats: CacheStats instance
        """
        # Lazy import to avoid circular dependencies
        self.query_cache = query_cache
        self.embedding_cache = embedding_cache

        self.debounce_seconds = debounce_seconds
        self.batch_size = batch_size

        # Pending invalidations (file_path -> event)
        self._pending_events: Dict[str, InvalidationEvent] = {}
        self._pending_lock = threading.Lock()

        # Debounce task
        self._debounce_task = None
        self._running = False

        # Stats
        from .stats import get_cache_stats

        self.stats = stats or get_cache_stats()

        # Patterns for broad invalidation
        self._invalidation_patterns: Dict[str, Set[str]] = defaultdict(set)

        logger.info(
            f"Cache invalidator initialized (debounce: {debounce_seconds}s, "
            f"batch: {batch_size})"
        )

    def get_query_cache(self):
        """Lazy load query cache"""
        if self.query_cache is None:
            from .query_cache import get_query_cache

            self.query_cache = get_query_cache()
        return self.query_cache

    def get_embedding_cache(self):
        """Lazy load embedding cache"""
        if self.embedding_cache is None:
            from .embedding_cache import get_embedding_cache

            self.embedding_cache = get_embedding_cache()
        return self.embedding_cache

    async def invalidate_file(self, file_path: str, event_type: str = "modified"):
        """
        Queue file for invalidation (with debouncing)

        Args:
            file_path: Path to the file that changed
            event_type: Type of change ('modified', 'deleted', 'created')
        """
        with self._pending_lock:
            # Add or update pending event
            self._pending_events[file_path] = InvalidationEvent(
                file_path=file_path, event_type=event_type, timestamp=time.time()
            )

        # Start debounce task if not running
        if not self._running:
            await self._start_debounce_task()

        logger.debug(
            f"Queued invalidation: {file_path} ({event_type}) "
            f"[pending: {len(self._pending_events)}]"
        )

    async def invalidate_files_batch(
        self, file_paths: List[str], event_type: str = "modified"
    ):
        """
        Queue multiple files for invalidation

        Args:
            file_paths: List of file paths
            event_type: Type of change
        """
        with self._pending_lock:
            for file_path in file_paths:
                self._pending_events[file_path] = InvalidationEvent(
                    file_path=file_path, event_type=event_type, timestamp=time.time()
                )

        if not self._running:
            await self._start_debounce_task()

        logger.info(
            f"Queued batch invalidation: {len(file_paths)} files "
            f"[pending: {len(self._pending_events)}]"
        )

    async def invalidate_pattern(self, pattern: str):
        """
        Invalidate all cached queries matching a file pattern

        Args:
            pattern: File pattern (e.g., '*.py', 'src/**/*.ts')
        """
        logger.info(f"Invalidating by pattern: {pattern}")

        # Get affected files from pattern
        affected_files = self._get_files_matching_pattern(pattern)

        if affected_files:
            await self.invalidate_files_batch(list(affected_files))

    async def _start_debounce_task(self):
        """Start the debounce task"""
        if self._running:
            return

        self._running = True

        async def debounce_loop():
            while self._running:
                await asyncio.sleep(self.debounce_seconds)

                # Check if there are pending events
                with self._pending_lock:
                    if not self._pending_events:
                        continue

                    # Get events to process
                    events_to_process = list(self._pending_events.values())
                    self._pending_events.clear()

                # Process invalidations
                await self._process_invalidation_batch(events_to_process)

        self._debounce_task = asyncio.create_task(debounce_loop())
        logger.debug("Debounce task started")

    async def _process_invalidation_batch(self, events: List[InvalidationEvent]):
        """
        Process a batch of invalidation events

        Args:
            events: List of invalidation events
        """
        if not events:
            return

        logger.info(f"Processing invalidation batch: {len(events)} files")
        start_time = time.time()

        # Group by event type
        modified_files = [e.file_path for e in events if e.event_type == "modified"]
        deleted_files = [e.file_path for e in events if e.event_type == "deleted"]
        created_files = [e.file_path for e in events if e.event_type == "created"]

        # Process in batches
        query_cache = self.get_query_cache()

        # Modified/deleted files invalidate queries
        files_to_invalidate = modified_files + deleted_files

        if files_to_invalidate:
            # Split into batches
            for i in range(0, len(files_to_invalidate), self.batch_size):
                batch = files_to_invalidate[i : i + self.batch_size]
                try:
                    await query_cache.invalidate_batch(batch)
                except Exception as e:
                    logger.error(f"Failed to invalidate batch: {e}")

        # Created files don't need invalidation (no queries cached yet)
        if created_files:
            logger.debug(f"Skipping invalidation for {len(created_files)} new files")

        duration = (time.time() - start_time) * 1000
        logger.info(
            f"Invalidation batch complete: {len(events)} files in {duration:.2f}ms"
        )

        # Mark as invalidated
        for event in events:
            event.invalidated = True

    def _get_files_matching_pattern(self, pattern: str) -> Set[str]:
        """
        Get files matching a pattern from tracked files

        Args:
            pattern: File pattern (glob-style)

        Returns:
            Set of matching file paths
        """
        import fnmatch

        query_cache = self.get_query_cache()

        # Get all tracked files
        tracked_files = set(query_cache._file_query_map.keys())

        # Match pattern
        matching = set()
        for file_path in tracked_files:
            if fnmatch.fnmatch(file_path, pattern):
                matching.add(file_path)

        logger.debug(
            f"Pattern '{pattern}' matched {len(matching)}/{len(tracked_files)} files"
        )
        return matching

    async def invalidate_project(self, project_path: str):
        """
        Invalidate all cached queries for a project

        Args:
            project_path: Project root path
        """
        logger.info(f"Invalidating project: {project_path}")

        query_cache = self.get_query_cache()

        # Get all files in project
        project_files = [
            fp
            for fp in query_cache._file_query_map.keys()
            if fp.startswith(project_path)
        ]

        if project_files:
            await self.invalidate_files_batch(project_files)

        logger.info(
            f"Queued invalidation for {len(project_files)} files in project"
        )

    async def invalidate_all(self):
        """
        Clear all caches (nuclear option)

        Use sparingly - defeats the purpose of caching!
        """
        logger.warning("Invalidating ALL caches")

        query_cache = self.get_query_cache()
        query_cache.clear_all()

        logger.info("All caches cleared")

    def get_pending_count(self) -> int:
        """Get number of pending invalidations"""
        with self._pending_lock:
            return len(self._pending_events)

    def get_statistics(self) -> Dict:
        """Get invalidation statistics"""
        query_cache = self.get_query_cache()

        return {
            "debounce_seconds": self.debounce_seconds,
            "batch_size": self.batch_size,
            "pending_invalidations": self.get_pending_count(),
            "running": self._running,
            "tracked_files": len(query_cache._file_query_map),
            "tracked_queries": len(query_cache._query_file_map),
        }

    def stop(self):
        """Stop the invalidator"""
        self._running = False
        if self._debounce_task:
            self._debounce_task.cancel()
        logger.info("Cache invalidator stopped")


# Global invalidator instance
_cache_invalidator: Optional[CacheInvalidator] = None
_invalidator_lock = threading.Lock()


def get_cache_invalidator() -> CacheInvalidator:
    """Get global cache invalidator instance"""
    global _cache_invalidator
    if _cache_invalidator is None:
        with _invalidator_lock:
            if _cache_invalidator is None:
                _cache_invalidator = CacheInvalidator()
    return _cache_invalidator
