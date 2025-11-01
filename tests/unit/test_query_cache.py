"""
Unit tests for Query Cache (Story 5-1)
"""
from src.search.query_cache import QueryCache


def test_query_cache_set_get():
    qc = QueryCache(ttl_seconds=60)
    qc.set("foo", {"r": 1}, {"lang": "py"})
    assert qc.get("foo", {"lang": "py"}) == {"r": 1}
    assert qc.get("bar") is None

