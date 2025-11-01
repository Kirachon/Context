import importlib
import sys


def test_query_cache_fallback_to_memory(monkeypatch):
    # Force feature flag enabled and redis import to fail
    from src.search import query_cache as qc_mod
    import src.config.settings as settings_mod

    # Enable redis feature but make import fail
    monkeypatch.setattr(settings_mod.settings, "query_cache_redis_enabled", True)
    monkeypatch.setattr(settings_mod.settings, "redis_url", "redis://localhost:6379/0")

    # Ensure 'redis' import fails
    sys.modules.pop("redis", None)
    monkeypatch.setitem(sys.modules, "redis", None)

    importlib.reload(qc_mod)
    qc = qc_mod.get_query_cache()
    # Should be in-memory QueryCache
    assert qc.__class__.__name__ == "QueryCache"


def test_query_cache_in_memory_basic(monkeypatch):
    from src.search.query_cache import QueryCache

    qc = QueryCache(ttl_seconds=1, max_items=2)
    qc.set("q1", {"a": 1}, filters={"f": 1})
    assert qc.get("q1", {"f": 1}) == {"a": 1}
