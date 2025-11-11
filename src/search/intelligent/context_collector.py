"""
Context Collector

Tracks user context for intelligent search ranking including current file,
recently accessed files, frequently accessed files, and team patterns.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import os

from .models import SearchContext

logger = logging.getLogger(__name__)


class ContextCollector:
    """
    Collects search context from user behavior.

    Tracks:
    - Current file/project being edited
    - Recently accessed files (last hour)
    - Frequently accessed files (top 20)
    - Team usage patterns
    """

    def __init__(self, storage_backend=None):
        """
        Initialize context collector.

        Args:
            storage_backend: Optional storage backend for persistence (Redis, DB, etc.)
        """
        self.storage = storage_backend

        # In-memory storage (fallback)
        self._current_files: Dict[str, str] = {}  # user_id -> file_path
        self._access_history: Dict[str, List[tuple]] = defaultdict(list)  # user_id -> [(file, timestamp)]
        self._query_history: Dict[str, List[tuple]] = defaultdict(list)  # user_id -> [(query, timestamp)]
        self._file_access_counts: Dict[str, Counter] = defaultdict(Counter)  # user_id -> Counter(file -> count)
        self._team_access_patterns: Counter = Counter()  # file -> global access count

    def collect(self, user_id: str) -> SearchContext:
        """
        Collect all context for a user.

        Args:
            user_id: User identifier

        Returns:
            SearchContext with all collected data
        """
        current_file = self._get_current_file(user_id)
        current_project = self._infer_project_from_file(current_file)
        recent_files = self._get_recent_files(user_id, hours=1)
        frequent_files = self._get_frequent_files(user_id, limit=20)
        recent_queries = self._get_recent_queries(user_id, limit=10)
        team_patterns = self._get_team_patterns(top_n=100)

        return SearchContext(
            user_id=user_id,
            current_file=current_file,
            current_project=current_project,
            recent_files=recent_files,
            frequent_files=frequent_files,
            recent_queries=recent_queries,
            team_patterns=team_patterns
        )

    def track_file_access(self, user_id: str, file_path: str, timestamp: Optional[datetime] = None):
        """
        Track file access event.

        Args:
            user_id: User identifier
            file_path: Path to accessed file
            timestamp: Access timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        # Update access history
        self._access_history[user_id].append((file_path, timestamp))

        # Update access counts
        self._file_access_counts[user_id][file_path] += 1

        # Update team patterns
        self._team_access_patterns[file_path] += 1

        # Cleanup old history (keep last 1000 entries per user)
        if len(self._access_history[user_id]) > 1000:
            self._access_history[user_id] = self._access_history[user_id][-1000:]

        logger.debug(f"Tracked file access: user={user_id}, file={file_path}")

    def track_query(self, user_id: str, query: str, timestamp: Optional[datetime] = None):
        """
        Track search query event.

        Args:
            user_id: User identifier
            query: Search query
            timestamp: Query timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        # Update query history
        self._query_history[user_id].append((query, timestamp))

        # Cleanup old history (keep last 100 queries per user)
        if len(self._query_history[user_id]) > 100:
            self._query_history[user_id] = self._query_history[user_id][-100:]

        logger.debug(f"Tracked query: user={user_id}, query={query}")

    def set_current_file(self, user_id: str, file_path: Optional[str]):
        """
        Set the currently open file for a user.

        Args:
            user_id: User identifier
            file_path: Path to current file (None if no file open)
        """
        if file_path:
            self._current_files[user_id] = file_path
            # Also track as an access
            self.track_file_access(user_id, file_path)
        elif user_id in self._current_files:
            del self._current_files[user_id]

        logger.debug(f"Set current file: user={user_id}, file={file_path}")

    def _get_current_file(self, user_id: str) -> Optional[str]:
        """Get currently open file for user"""
        return self._current_files.get(user_id)

    def _get_recent_files(self, user_id: str, hours: int = 1) -> List[str]:
        """
        Get files accessed in the last N hours.

        Args:
            user_id: User identifier
            hours: Number of hours to look back

        Returns:
            List of file paths (most recent first)
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = [
            file_path
            for file_path, timestamp in self._access_history.get(user_id, [])
            if timestamp >= cutoff
        ]

        # Remove duplicates while preserving order (most recent first)
        seen = set()
        result = []
        for file_path in reversed(recent):
            if file_path not in seen:
                seen.add(file_path)
                result.append(file_path)

        return result

    def _get_frequent_files(self, user_id: str, limit: int = 20) -> List[str]:
        """
        Get most frequently accessed files.

        Args:
            user_id: User identifier
            limit: Maximum number of files to return

        Returns:
            List of file paths (most frequent first)
        """
        counts = self._file_access_counts.get(user_id, Counter())
        return [file_path for file_path, _ in counts.most_common(limit)]

    def _get_recent_queries(self, user_id: str, limit: int = 10) -> List[str]:
        """
        Get recent search queries.

        Args:
            user_id: User identifier
            limit: Maximum number of queries to return

        Returns:
            List of queries (most recent first)
        """
        queries = self._query_history.get(user_id, [])
        # Return unique queries, most recent first
        seen = set()
        result = []
        for query, _ in reversed(queries):
            if query not in seen:
                seen.add(query)
                result.append(query)
                if len(result) >= limit:
                    break
        return result

    def _get_team_patterns(self, top_n: int = 100) -> Dict[str, float]:
        """
        Get team-wide file access patterns.

        Args:
            top_n: Number of top files to include

        Returns:
            Dictionary mapping file path to normalized frequency (0-1)
        """
        if not self._team_access_patterns:
            return {}

        # Get top N files
        top_files = self._team_access_patterns.most_common(top_n)

        # Normalize to 0-1 range
        max_count = top_files[0][1] if top_files else 1
        return {
            file_path: count / max_count
            for file_path, count in top_files
        }

    def _infer_project_from_file(self, file_path: Optional[str]) -> Optional[str]:
        """
        Infer project name from file path.

        Args:
            file_path: Path to file

        Returns:
            Project name or None
        """
        if not file_path:
            return None

        # Try to extract project from path structure
        # Assumes structure like: /path/to/project/src/file.py
        parts = file_path.split(os.sep)

        # Look for common project indicators
        project_markers = ['src', 'lib', 'app', 'backend', 'frontend']

        for i, part in enumerate(parts):
            if part in project_markers and i > 0:
                # Project is likely the directory before the marker
                return parts[i - 1]

        # Fallback: use second-to-last directory
        if len(parts) >= 3:
            return parts[-3]

        return None

    def get_file_project(self, file_path: str) -> Optional[str]:
        """
        Get project for a specific file path.

        Args:
            file_path: Path to file

        Returns:
            Project name or None
        """
        return self._infer_project_from_file(file_path)

    def get_related_files(
        self,
        file_path: str,
        user_id: str,
        limit: int = 5
    ) -> List[str]:
        """
        Get files related to the given file based on access patterns.

        Files are related if they're:
        - In the same project
        - Accessed in the same session
        - Frequently accessed together

        Args:
            file_path: Reference file path
            user_id: User identifier
            limit: Maximum number of related files

        Returns:
            List of related file paths
        """
        related = []
        project = self._infer_project_from_file(file_path)

        # Get recent files from same project
        recent = self._get_recent_files(user_id, hours=24)
        for f in recent:
            if f != file_path:
                f_project = self._infer_project_from_file(f)
                if f_project == project:
                    related.append(f)
                    if len(related) >= limit:
                        break

        return related

    def clear_user_context(self, user_id: str):
        """
        Clear all context for a user.

        Args:
            user_id: User identifier
        """
        self._current_files.pop(user_id, None)
        self._access_history.pop(user_id, None)
        self._query_history.pop(user_id, None)
        self._file_access_counts.pop(user_id, None)

        logger.info(f"Cleared context for user: {user_id}")

    def get_stats(self) -> Dict[str, any]:
        """Get statistics about collected context"""
        return {
            "total_users": len(self._current_files),
            "total_accesses": sum(len(h) for h in self._access_history.values()),
            "total_queries": sum(len(h) for h in self._query_history.values()),
            "team_tracked_files": len(self._team_access_patterns),
        }
