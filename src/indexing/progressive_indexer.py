"""
Progressive Indexing for Large Codebases (Story 2-7, Phase 2)

Implements progressive indexing with priority queue and adaptive batching
for optimal performance on large codebases.
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from heapq import heappush, heappop
import psutil

from src.config.settings import settings

logger = logging.getLogger(__name__)


class IndexingPriority(Enum):
    """Indexing priority levels"""
    CRITICAL = 0  # System files, core modules
    HIGH = 1      # Recently modified files
    NORMAL = 2    # Regular files
    LOW = 3       # Rarely accessed files


@dataclass
class IndexingTask:
    """Task in the indexing queue"""
    file_path: str
    priority: IndexingPriority
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __lt__(self, other):
        """Compare tasks by priority"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


class ProgressiveIndexer:
    """
    Progressive indexer with priority queue and adaptive batching
    
    Features:
    - Priority-based indexing queue
    - Adaptive batch sizing based on system resources
    - Progress tracking and reporting
    - Pause/resume capability
    - Performance metrics
    """
    
    def __init__(
        self,
        initial_batch_size: int = 10,
        max_batch_size: int = 50,
        min_batch_size: int = 1
    ):
        """
        Initialize progressive indexer
        
        Args:
            initial_batch_size: Starting batch size
            max_batch_size: Maximum batch size
            min_batch_size: Minimum batch size
        """
        self.initial_batch_size = initial_batch_size
        self.max_batch_size = max_batch_size
        self.min_batch_size = min_batch_size
        self.current_batch_size = initial_batch_size
        
        # Priority queue for tasks
        self.task_queue: List[IndexingTask] = []
        
        # Tracking
        self.total_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.paused = False
        
        # Metrics
        self.metrics = {
            "start_time": None,
            "end_time": None,
            "total_duration": 0,
            "avg_batch_time": 0,
            "batch_count": 0,
            "throughput": 0  # tasks per second
        }
    
    def add_task(
        self,
        file_path: str,
        priority: IndexingPriority = IndexingPriority.NORMAL
    ):
        """
        Add task to indexing queue
        
        Args:
            file_path: Path to file to index
            priority: Task priority level
        """
        task = IndexingTask(file_path=file_path, priority=priority)
        heappush(self.task_queue, task)
        self.total_tasks += 1
        logger.debug(f"Added indexing task: {file_path} (priority: {priority.name})")
    
    def add_tasks_batch(
        self,
        file_paths: List[str],
        priority: IndexingPriority = IndexingPriority.NORMAL
    ):
        """
        Add multiple tasks to queue
        
        Args:
            file_paths: List of file paths
            priority: Task priority level
        """
        for file_path in file_paths:
            self.add_task(file_path, priority)
        logger.info(f"Added {len(file_paths)} indexing tasks")
    
    def get_next_batch(self) -> List[IndexingTask]:
        """
        Get next batch of tasks to process
        
        Returns:
            List of tasks for next batch
        """
        batch = []
        for _ in range(min(self.current_batch_size, len(self.task_queue))):
            if self.task_queue:
                batch.append(heappop(self.task_queue))
        return batch
    
    def adapt_batch_size(self):
        """
        Adapt batch size based on system resources
        
        Increases batch size if system has available resources,
        decreases if system is under load.
        """
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent
            
            # Calculate load factor (0.0 to 1.0)
            load_factor = (cpu_percent + memory_percent) / 200
            
            if load_factor < 0.5:
                # System has capacity, increase batch size
                self.current_batch_size = min(
                    self.current_batch_size + 1,
                    self.max_batch_size
                )
            elif load_factor > 0.8:
                # System under load, decrease batch size
                self.current_batch_size = max(
                    self.current_batch_size - 1,
                    self.min_batch_size
                )
            
            logger.debug(
                f"Batch size adapted to {self.current_batch_size} "
                f"(CPU: {cpu_percent}%, Memory: {memory_percent}%)"
            )
            
        except Exception as e:
            logger.warning(f"Failed to adapt batch size: {e}")
    
    def get_progress(self) -> Dict[str, Any]:
        """
        Get indexing progress
        
        Returns:
            Dict with progress information
        """
        progress_percent = (
            (self.completed_tasks / self.total_tasks * 100)
            if self.total_tasks > 0 else 0
        )
        
        return {
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "pending_tasks": len(self.task_queue),
            "progress_percent": round(progress_percent, 2),
            "current_batch_size": self.current_batch_size,
            "paused": self.paused
        }
    
    def mark_completed(self, task: IndexingTask):
        """Mark task as completed"""
        self.completed_tasks += 1
        logger.debug(f"Completed indexing: {task.file_path}")
    
    def mark_failed(self, task: IndexingTask, error: str):
        """
        Mark task as failed
        
        Retries task if retry count not exceeded.
        """
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            heappush(self.task_queue, task)
            logger.warning(
                f"Retrying failed task: {task.file_path} "
                f"(attempt {task.retry_count}/{task.max_retries})"
            )
        else:
            self.failed_tasks += 1
            logger.error(f"Failed to index {task.file_path}: {error}")
    
    def pause(self):
        """Pause indexing"""
        self.paused = True
        logger.info("Indexing paused")
    
    def resume(self):
        """Resume indexing"""
        self.paused = False
        logger.info("Indexing resumed")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get indexing metrics"""
        return {
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "pending_tasks": len(self.task_queue),
            "current_batch_size": self.current_batch_size,
            "metrics": self.metrics
        }


# Global progressive indexer instance
_progressive_indexer: Optional[ProgressiveIndexer] = None


def get_progressive_indexer() -> ProgressiveIndexer:
    """Get global progressive indexer instance"""
    global _progressive_indexer
    if _progressive_indexer is None:
        _progressive_indexer = ProgressiveIndexer(
            initial_batch_size=settings.batch_size,
            max_batch_size=50,
            min_batch_size=1
        )
    return _progressive_indexer

