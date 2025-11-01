"""
Unit tests for Embedding Cache (Story 2-7)
"""
import pytest
from unittest.mock import MagicMock, patch

# Skip all tests if redis is not installed
pytest.importorskip("redis")

from src.search.embedding_cache import EmbeddingCache, get_embedding_cache


@pytest.fixture
def mock_redis():
    """Create a mock Redis client"""
    redis_mock = MagicMock()
    redis_mock.ping.return_value = True
    redis_mock.get.return_value = None
    redis_mock.setex.return_value = True
    redis_mock.delete.return_value = 1
    redis_mock.scan.return_value = (0, [])
    return redis_mock


@pytest.fixture
def embedding_cache(mock_redis):
    """Create embedding cache with mocked Redis"""
    with patch('redis.from_url', return_value=mock_redis):
        cache = EmbeddingCache(ttl_seconds=3600)
        return cache


def test_embedding_cache_initialization(embedding_cache):
    """Test embedding cache initialization"""
    assert embedding_cache.enabled is True
    assert embedding_cache.ttl_seconds == 3600
    assert embedding_cache.stats["hits"] == 0
    assert embedding_cache.stats["misses"] == 0


def test_cache_key_generation(embedding_cache):
    """Test cache key generation"""
    key1 = embedding_cache._get_cache_key("test text", "model1")
    key2 = embedding_cache._get_cache_key("test text", "model1")
    key3 = embedding_cache._get_cache_key("test text", "model2")
    
    assert key1 == key2  # Same text and model
    assert key1 != key3  # Different model


def test_cache_miss(embedding_cache):
    """Test cache miss"""
    result = embedding_cache.get("test text", "model1")
    
    assert result is None
    assert embedding_cache.stats["misses"] == 1
    assert embedding_cache.stats["hits"] == 0


def test_cache_set_and_get(embedding_cache, mock_redis):
    """Test setting and getting cached embedding"""
    import json
    
    embedding = [0.1, 0.2, 0.3]
    text = "test text"
    model = "model1"
    
    # Set embedding
    embedding_cache.set(text, embedding, model)
    assert embedding_cache.stats["sets"] == 1
    
    # Mock Redis to return the cached value
    cached_data = {
        "text": text,
        "embedding": embedding,
        "model": model,
        "cached_at": "2025-11-01T00:00:00",
        "hit_count": 0
    }
    mock_redis.get.return_value = json.dumps(cached_data)
    
    # Get embedding
    result = embedding_cache.get(text, model)
    
    assert result == embedding
    assert embedding_cache.stats["hits"] == 1


def test_cache_invalidate_model(embedding_cache, mock_redis):
    """Test model cache invalidation"""
    # Mock scan to return some keys
    mock_redis.scan.return_value = (0, ["embedding:model1:hash1", "embedding:model1:hash2"])
    
    embedding_cache.invalidate_model("model1")
    
    assert embedding_cache.stats["invalidations"] == 2
    mock_redis.delete.assert_called_once()


def test_cache_statistics(embedding_cache):
    """Test cache statistics"""
    # Simulate some cache activity
    embedding_cache.stats["hits"] = 80
    embedding_cache.stats["misses"] = 20
    embedding_cache.stats["sets"] = 100
    
    stats = embedding_cache.get_statistics()
    
    assert stats["hits"] == 80
    assert stats["misses"] == 20
    assert stats["sets"] == 100
    assert stats["hit_rate_percent"] == 80.0
    assert stats["total_requests"] == 100


def test_cache_disabled_on_redis_failure():
    """Test cache disables gracefully on Redis failure"""
    with patch('redis.from_url', side_effect=Exception("Connection failed")):
        cache = EmbeddingCache()
        
        assert cache.enabled is False
        assert cache.redis_client is None


def test_cache_operations_when_disabled():
    """Test cache operations when disabled"""
    with patch('redis.from_url', side_effect=Exception("Connection failed")):
        cache = EmbeddingCache()
        
        # Operations should not raise errors
        result = cache.get("test", "model")
        assert result is None
        
        cache.set("test", [0.1, 0.2], "model")
        cache.invalidate_model("model")
        
        stats = cache.get_statistics()
        assert stats["enabled"] is False


def test_get_embedding_cache_singleton():
    """Test global embedding cache singleton"""
    cache1 = get_embedding_cache()
    cache2 = get_embedding_cache()
    
    assert cache1 is cache2


def test_clear_statistics(embedding_cache):
    """Test clearing cache statistics"""
    embedding_cache.stats["hits"] = 100
    embedding_cache.stats["misses"] = 50
    
    embedding_cache.clear_statistics()
    
    assert embedding_cache.stats["hits"] == 0
    assert embedding_cache.stats["misses"] == 0


def test_cache_with_long_text(embedding_cache):
    """Test caching with long text (should truncate)"""
    long_text = "a" * 2000
    embedding = [0.1, 0.2, 0.3]
    
    embedding_cache.set(long_text, embedding, "model1")
    
    # Should not raise error
    assert embedding_cache.stats["sets"] == 1


def test_cache_error_handling(embedding_cache, mock_redis):
    """Test cache error handling"""
    # Simulate Redis error
    mock_redis.get.side_effect = Exception("Redis error")
    
    result = embedding_cache.get("test", "model")
    
    assert result is None
    assert embedding_cache.stats["errors"] == 1

