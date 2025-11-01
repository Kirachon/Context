"""
Indexing Queue

Background processing queue for incremental file indexing.
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime
from collections import deque
from enum import Enum

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.indexing.file_indexer import file_indexer
from src.monitoring.metrics import metrics

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """File change types"""

    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"


class IndexingState(Enum):
    """Indexing states"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class IndexingQueue:
    """
    Indexing Queue Manager

    Manages background processing of file changes with incremental updates.
    """

    def __init__(self):
        """Initialize indexing queue"""
        self.queue = deque()
        self.processing = False
        self.stats = {
            "total_queued": 0,
            "total_processed": 0,
            "total_failed": 0,
            "pending_count": 0,
            "last_processing_time": None,
            "processing_duration": 0,
        }
        self.current_item: Optional[Dict[str, Any]] = None

        # Metrics
        self.c_queued = metrics.counter(
            "indexing_queued_total", "Items queued", ("change_type",)
        )
        self.c_processed = metrics.counter(
            "indexing_processed_total", "Items processed", ("status",)
        )
        self.h_item = metrics.histogram(
            "indexing_item_seconds", "Indexing item latency"
        )
        self.h_run = metrics.histogram(
            "indexing_processing_seconds", "Queue processing latency"
        )

        logger.info("IndexingQueue initialized")

    async def add(self, change_type: str, file_path: str):
        """
        Add file change to queue

        Args:
            change_type: Type of change (created, modified, deleted)
            file_path: Path to changed file
        """
        try:
            change_type_enum = ChangeType(change_type)
        except ValueError:
            logger.error(f"Invalid change type: {change_type}")
            return

        item = {
            "change_type": change_type_enum,
            "file_path": file_path,
            "state": IndexingState.PENDING,
            "queued_time": datetime.utcnow(),
            "processed_time": None,
            "error": None,
        }

        self.queue.append(item)
        self.stats["total_queued"] += 1
        self.stats["pending_count"] = len(self.queue)
        try:
            self.c_queued.labels(change_type_enum.value).inc()
        except Exception:
            pass

        logger.info(
            f"Added to queue: {change_type} - {file_path} (queue size: {len(self.queue)})"
        )

        # Start processing if not already running
        if not self.processing:
            asyncio.create_task(self.process_queue())

    async def process_queue(self):
        """Process items in the queue"""
        if self.processing:
            logger.debug("Queue processing already in progress")
            return

        self.processing = True
        logger.info("Starting queue processing...")

        start_time = datetime.utcnow()
        _t0 = asyncio.get_event_loop().time()

        try:
            while self.queue:
                item = self.queue.popleft()
                self.current_item = item
                self.stats["pending_count"] = len(self.queue)

                await self._process_item(item)

            # Calculate processing duration
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            self.stats["last_processing_time"] = end_time
            self.stats["processing_duration"] = duration
            try:
                self.h_run.labels().observe(asyncio.get_event_loop().time() - _t0)
            except Exception:
                pass

            logger.info(f"Queue processing completed in {duration:.2f}s")

        except Exception as e:
            logger.error(f"Error during queue processing: {e}", exc_info=True)

        finally:
            self.processing = False
            self.current_item = None

    async def _process_item(self, item: Dict[str, Any]):
        """
        Process a single queue item

        Args:
            item: Queue item to process
        """
        change_type = item["change_type"]
        file_path = item["file_path"]

        logger.info(f"Processing: {change_type.value} - {file_path}")

        item["state"] = IndexingState.PROCESSING
        _t0 = asyncio.get_event_loop().time()

        try:
            if change_type == ChangeType.CREATED or change_type == ChangeType.MODIFIED:
                # Index or update file
                metadata = await file_indexer.index_file(file_path)

                if metadata:
                    item["state"] = IndexingState.COMPLETED
                    item["metadata"] = metadata
                    self.stats["total_processed"] += 1
                    try:
                        self.h_item.labels().observe(
                            asyncio.get_event_loop().time() - _t0
                        )
                        self.c_processed.labels("ok").inc()
                    except Exception:
                        pass
                    logger.info(f"Successfully processed: {file_path}")
                else:
                    item["state"] = IndexingState.FAILED
                    item["error"] = "Failed to extract metadata"
                    self.stats["total_failed"] += 1
                    try:
                        self.h_item.labels().observe(
                            asyncio.get_event_loop().time() - _t0
                        )
                        self.c_processed.labels("failed").inc()
                    except Exception:
                        pass
                    logger.warning(f"Failed to process: {file_path}")

            elif change_type == ChangeType.DELETED:
                # Remove file from index
                success = await file_indexer.remove_file(file_path)

                if success:
                    item["state"] = IndexingState.COMPLETED
                    self.stats["total_processed"] += 1
                    try:
                        self.h_item.labels().observe(
                            asyncio.get_event_loop().time() - _t0
                        )
                        self.c_processed.labels("ok").inc()
                    except Exception:
                        pass
                    logger.info(f"Successfully removed: {file_path}")
                else:
                    item["state"] = IndexingState.FAILED
                    item["error"] = "Failed to remove file"
                    self.stats["total_failed"] += 1
                    try:
                        self.h_item.labels().observe(
                            asyncio.get_event_loop().time() - _t0
                        )
                        self.c_processed.labels("failed").inc()
                    except Exception:
                        pass
                    logger.warning(f"Failed to remove: {file_path}")

            item["processed_time"] = datetime.utcnow()

        except Exception as e:
            item["state"] = IndexingState.FAILED
            item["error"] = str(e)
            item["processed_time"] = datetime.utcnow()
            self.stats["total_failed"] += 1
            logger.error(f"Error processing {file_path}: {e}", exc_info=True)

    def get_status(self) -> Dict[str, Any]:
        """
        Get queue status

        Returns:
            dict: Queue status and statistics
        """
        return {
            "processing": self.processing,
            "queue_size": len(self.queue),
            "current_item": (
                {
                    "file_path": self.current_item["file_path"],
                    "change_type": self.current_item["change_type"].value,
                    "state": self.current_item["state"].value,
                }
                if self.current_item
                else None
            ),
            "stats": {
                "total_queued": self.stats["total_queued"],
                "total_processed": self.stats["total_processed"],
                "total_failed": self.stats["total_failed"],
                "pending_count": self.stats["pending_count"],
                "last_processing_time": (
                    self.stats["last_processing_time"].isoformat()
                    if self.stats["last_processing_time"]
                    else None
                ),
                "processing_duration": self.stats["processing_duration"],
            },
        }

    def clear(self):
        """Clear the queue"""
        self.queue.clear()
        self.stats["pending_count"] = 0
        logger.info("Queue cleared")


# Global indexing queue instance
indexing_queue = IndexingQueue()


async def queue_file_change(change_type: str, file_path: str):
    """
    Queue a file change for processing (entry point for file monitor)

    Args:
        change_type: Type of change (created, modified, deleted)
        file_path: Path to changed file
    """
    await indexing_queue.add(change_type, file_path)


def get_queue_status() -> Dict[str, Any]:
    """Get queue status (entry point for status endpoints)"""
    return indexing_queue.get_status()
