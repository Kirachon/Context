"""
Unit tests for Cursor-Based Pagination (Story 2-7, Phase 3)
"""
import pytest
from src.search.pagination import (
    PaginationCursor,
    CursorPaginator,
    StreamingPaginator,
    PaginatedResult
)


@pytest.fixture
def sample_items():
    """Create sample items for pagination"""
    return [{"id": i, "name": f"item_{i}"} for i in range(100)]


@pytest.fixture
def paginator():
    """Create a cursor paginator"""
    return CursorPaginator(page_size=10, max_page_size=50)


def test_cursor_encoding_decoding():
    """Test cursor encoding and decoding"""
    cursor = PaginationCursor(offset=20, timestamp="2025-11-01T00:00:00", hash="abc123")
    
    encoded = cursor.encode()
    decoded = PaginationCursor.decode(encoded)
    
    assert decoded.offset == 20
    assert decoded.timestamp == "2025-11-01T00:00:00"
    assert decoded.hash == "abc123"


def test_cursor_invalid_decoding():
    """Test decoding invalid cursor"""
    decoded = PaginationCursor.decode("invalid_cursor")
    assert decoded is None


def test_paginate_first_page(paginator, sample_items):
    """Test paginating first page"""
    result = paginator.paginate(sample_items)
    
    assert len(result.items) == 10
    assert result.total_count == 100
    assert result.current_offset == 0
    assert result.has_next is True
    assert result.has_previous is False


def test_paginate_middle_page(paginator, sample_items):
    """Test paginating middle page"""
    # Get first page to get next cursor
    first_result = paginator.paginate(sample_items)
    
    # Use next cursor
    second_result = paginator.paginate(sample_items, first_result.next_cursor)
    
    assert second_result.current_offset == 10
    assert len(second_result.items) == 10
    assert second_result.has_previous is True


def test_paginate_last_page(paginator, sample_items):
    """Test paginating last page"""
    # Navigate to last page
    cursor = None
    result = None
    while True:
        result = paginator.paginate(sample_items, cursor)
        if not result.has_next:
            break
        cursor = result.next_cursor
    
    assert result.has_next is False
    assert len(result.items) == 10  # Last 10 items


def test_paginate_custom_page_size(paginator, sample_items):
    """Test pagination with custom page size"""
    result = paginator.paginate(sample_items, page_size=25)
    
    assert len(result.items) == 25
    assert result.page_size == 25


def test_paginate_exceeds_max_page_size(paginator, sample_items):
    """Test page size capped at max"""
    result = paginator.paginate(sample_items, page_size=200)
    
    assert result.page_size == 50  # max_page_size


def test_paginated_result_to_dict(paginator, sample_items):
    """Test converting paginated result to dict"""
    result = paginator.paginate(sample_items)
    result_dict = result.to_dict()
    
    assert "items" in result_dict
    assert "total_count" in result_dict
    assert "has_next" in result_dict


def test_streaming_paginator(sample_items):
    """Test streaming paginator"""
    streamer = StreamingPaginator(chunk_size=20)
    
    chunks = list(streamer.stream(sample_items))
    
    assert len(chunks) == 5  # 100 items / 20 per chunk
    assert chunks[0]["chunk_size"] == 20
    assert chunks[-1]["chunk_size"] == 20


def test_streaming_with_progress(sample_items):
    """Test streaming with progress"""
    streamer = StreamingPaginator(chunk_size=25)
    
    chunks = list(streamer.stream_with_progress(sample_items))
    
    assert chunks[0]["progress_percent"] == 25.0
    assert chunks[-1]["progress_percent"] == 100.0
    assert chunks[-1]["is_last"] is True


def test_streaming_uneven_chunks():
    """Test streaming with uneven chunk distribution"""
    items = list(range(55))
    streamer = StreamingPaginator(chunk_size=20)
    
    chunks = list(streamer.stream(items))
    
    assert len(chunks) == 3
    assert chunks[0]["chunk_size"] == 20
    assert chunks[1]["chunk_size"] == 20
    assert chunks[2]["chunk_size"] == 15


def test_backward_navigation(paginator, sample_items):
    """Test backward navigation with previous cursor"""
    # Get to page 3
    cursor = None
    for _ in range(2):
        result = paginator.paginate(sample_items, cursor)
        cursor = result.next_cursor
    
    # Now go back
    result = paginator.paginate(sample_items, cursor)
    prev_result = paginator.paginate(sample_items, result.previous_cursor)
    
    assert prev_result.current_offset == 10


def test_empty_items_pagination(paginator):
    """Test pagination with empty items"""
    result = paginator.paginate([])
    
    assert len(result.items) == 0
    assert result.total_count == 0
    assert result.has_next is False
    assert result.has_previous is False


def test_single_item_pagination(paginator):
    """Test pagination with single item"""
    result = paginator.paginate([{"id": 1}])
    
    assert len(result.items) == 1
    assert result.total_count == 1
    assert result.has_next is False

