"""
Cursor-Based Pagination (Story 2-7, Phase 3)

Implements efficient cursor-based pagination for large result sets.
"""

import logging
import base64
import json
from typing import List, Optional, Dict, Any, TypeVar, Generic
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class PaginationCursor:
    """Cursor for pagination"""

    offset: int
    timestamp: str
    hash: str

    def encode(self) -> str:
        """Encode cursor to string"""
        data = json.dumps(asdict(self))
        return base64.b64encode(data.encode()).decode()

    @staticmethod
    def decode(cursor_str: str) -> "PaginationCursor":
        """Decode cursor from string"""
        try:
            data = base64.b64decode(cursor_str.encode()).decode()
            obj = json.loads(data)
            return PaginationCursor(**obj)
        except Exception as e:
            logger.warning(f"Failed to decode cursor: {e}")
            return None


@dataclass
class PaginatedResult(Generic[T]):
    """Paginated result set"""

    items: List[T]
    total_count: int
    page_size: int
    current_offset: int
    has_next: bool
    has_previous: bool
    next_cursor: Optional[str] = None
    previous_cursor: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "items": self.items,
            "total_count": self.total_count,
            "page_size": self.page_size,
            "current_offset": self.current_offset,
            "has_next": self.has_next,
            "has_previous": self.has_previous,
            "next_cursor": self.next_cursor,
            "previous_cursor": self.previous_cursor,
        }


class CursorPaginator:
    """
    Cursor-based paginator for efficient pagination

    Features:
    - Stateless cursor-based pagination
    - Efficient offset calculation
    - Cursor validation
    - Support for forward and backward navigation
    """

    def __init__(self, page_size: int = 20, max_page_size: int = 100):
        """
        Initialize paginator

        Args:
            page_size: Default page size
            max_page_size: Maximum allowed page size
        """
        self.page_size = page_size
        self.max_page_size = max_page_size

    def paginate(
        self,
        items: List[T],
        cursor: Optional[str] = None,
        page_size: Optional[int] = None,
    ) -> PaginatedResult[T]:
        """
        Paginate items using cursor

        Args:
            items: List of items to paginate
            cursor: Pagination cursor (optional)
            page_size: Page size (optional, uses default if not specified)

        Returns:
            PaginatedResult with paginated items
        """
        if page_size is None:
            page_size = self.page_size
        else:
            page_size = min(page_size, self.max_page_size)

        # Determine offset
        offset = 0
        if cursor:
            decoded = PaginationCursor.decode(cursor)
            if decoded:
                offset = decoded.offset

        # Get items for current page
        start = offset
        end = start + page_size
        page_items = items[start:end]

        # Calculate pagination info
        total_count = len(items)
        has_next = end < total_count
        has_previous = offset > 0

        # Generate cursors
        next_cursor = None
        if has_next:
            next_cursor = PaginationCursor(
                offset=end,
                timestamp=datetime.now(timezone.utc).isoformat(),
                hash=self._hash_items(items[end : end + page_size]),
            ).encode()

        previous_cursor = None
        if has_previous:
            prev_offset = max(0, offset - page_size)
            previous_cursor = PaginationCursor(
                offset=prev_offset,
                timestamp=datetime.now(timezone.utc).isoformat(),
                hash=self._hash_items(items[prev_offset : prev_offset + page_size]),
            ).encode()

        return PaginatedResult(
            items=page_items,
            total_count=total_count,
            page_size=page_size,
            current_offset=offset,
            has_next=has_next,
            has_previous=has_previous,
            next_cursor=next_cursor,
            previous_cursor=previous_cursor,
        )

    def _hash_items(self, items: List[T]) -> str:
        """Generate hash for items"""
        try:
            import hashlib

            data = json.dumps([str(item) for item in items[:5]])  # Hash first 5 items
            return hashlib.sha256(data.encode()).hexdigest()[:16]
        except Exception as e:
            logger.warning(f"Failed to hash items: {e}")
            return "unknown"


class StreamingPaginator:
    """
    Streaming paginator for large result sets

    Yields results in chunks for memory efficiency.
    """

    def __init__(self, chunk_size: int = 50):
        """
        Initialize streaming paginator

        Args:
            chunk_size: Size of each chunk
        """
        self.chunk_size = chunk_size

    def stream(self, items: List[T]):
        """
        Stream items in chunks

        Args:
            items: List of items to stream

        Yields:
            Chunks of items
        """
        for i in range(0, len(items), self.chunk_size):
            chunk = items[i : i + self.chunk_size]
            yield {
                "items": chunk,
                "chunk_index": i // self.chunk_size,
                "chunk_size": len(chunk),
                "total_processed": i + len(chunk),
            }

    def stream_with_progress(self, items: List[T]):
        """
        Stream items with progress information

        Args:
            items: List of items to stream

        Yields:
            Chunks with progress info
        """
        total = len(items)
        for i, chunk_data in enumerate(self.stream(items)):
            progress_percent = (
                (chunk_data["total_processed"] / total * 100) if total > 0 else 0
            )
            chunk_data["progress_percent"] = round(progress_percent, 2)
            chunk_data["is_last"] = chunk_data["total_processed"] >= total
            yield chunk_data


# Module-level stub function for MCP tool integration
def paginate(results: list, page: int = 1, page_size: int = 10) -> Dict:
    """
    Paginate search results.

    Stub implementation for MCP tool integration.

    Args:
        results: List of results to paginate
        page: Page number (1-indexed)
        page_size: Number of results per page

    Returns:
        Dict with status and paginated results
    """
    logger.warning(f"CursorPaginator stub called with {len(results)} results, page={page}, page_size={page_size}")
    return {
        "status": "NOT_IMPLEMENTED",
        "message": "paginate is a stub implementation",
        "results": [],
        "total_count": len(results),
        "page": page,
        "page_size": page_size,
        "data": {}
    }
