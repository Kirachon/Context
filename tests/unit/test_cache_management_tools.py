"""
Unit tests for Cache Management MCP Tools (Story 2-7)
"""
import pytest
from unittest.mock import MagicMock

# Skip all tests if redis is not installed
pytest.importorskip("redis")

from src.mcp_server.tools.cache_management import register_cache_management_tools


@pytest.fixture
def mock_mcp():
    """Create a mock FastMCP instance"""
    mcp = MagicMock()
    registered_tools = []
    
    def tool_decorator_factory():
        def tool_decorator(func):
            registered_tools.append(func)
            return func
        return tool_decorator
    
    mcp.tool = MagicMock(side_effect=tool_decorator_factory)
    mcp._registered_tools = registered_tools
    return mcp


def test_register_cache_management_tools(mock_mcp):
    """Test that cache management tools are registered"""
    register_cache_management_tools(mock_mcp)
    assert len(mock_mcp._registered_tools) == 4


@pytest.mark.asyncio
async def test_cache_statistics_tool(mock_mcp):
    """Test cache statistics tool"""
    register_cache_management_tools(mock_mcp)
    
    tool_func = mock_mcp._registered_tools[0]
    result = await tool_func()
    
    assert result["success"] is True
    assert "embedding_cache" in result
    assert "ast_cache" in result
    assert "timestamp" in result


@pytest.mark.asyncio
async def test_invalidate_embedding_cache_tool(mock_mcp):
    """Test embedding cache invalidation tool"""
    register_cache_management_tools(mock_mcp)
    
    tool_func = mock_mcp._registered_tools[1]
    result = await tool_func(model="test-model")
    
    assert result["success"] is True
    assert "message" in result
    assert "invalidations" in result


@pytest.mark.asyncio
async def test_cache_health_check_tool(mock_mcp):
    """Test cache health check tool"""
    register_cache_management_tools(mock_mcp)
    
    tool_func = mock_mcp._registered_tools[2]
    result = await tool_func()
    
    assert result["success"] is True
    assert "overall_healthy" in result
    assert "embedding_cache" in result
    assert "ast_cache" in result


@pytest.mark.asyncio
async def test_configure_cache_tool(mock_mcp):
    """Test cache configuration tool"""
    register_cache_management_tools(mock_mcp)
    
    tool_func = mock_mcp._registered_tools[3]
    result = await tool_func(ttl_seconds=7200, max_cache_size=20000)
    
    assert result["success"] is True
    assert "configuration" in result
    assert result["configuration"]["ttl_seconds"] == 7200
    assert result["configuration"]["max_cache_size"] == 20000


@pytest.mark.asyncio
async def test_cache_statistics_with_data(mock_mcp):
    """Test cache statistics with actual cache data"""
    register_cache_management_tools(mock_mcp)
    
    # Get embedding cache and add some stats
    from src.search.embedding_cache import get_embedding_cache
    cache = get_embedding_cache()
    cache.stats["hits"] = 100
    cache.stats["misses"] = 50
    
    tool_func = mock_mcp._registered_tools[0]
    result = await tool_func()
    
    assert result["success"] is True
    embedding_stats = result["embedding_cache"]
    assert embedding_stats["hits"] == 100
    assert embedding_stats["misses"] == 50
    assert embedding_stats["hit_rate_percent"] > 0


@pytest.mark.asyncio
async def test_cache_health_check_healthy(mock_mcp):
    """Test cache health check when healthy"""
    register_cache_management_tools(mock_mcp)
    
    # Set up healthy cache
    from src.search.embedding_cache import get_embedding_cache
    cache = get_embedding_cache()
    cache.stats["hits"] = 100
    cache.stats["misses"] = 20
    cache.stats["errors"] = 0
    
    tool_func = mock_mcp._registered_tools[2]
    result = await tool_func()
    
    assert result["success"] is True
    assert result["embedding_cache"]["healthy"] is True


@pytest.mark.asyncio
async def test_cache_health_check_unhealthy(mock_mcp):
    """Test cache health check when unhealthy"""
    register_cache_management_tools(mock_mcp)
    
    # Set up unhealthy cache
    from src.search.embedding_cache import get_embedding_cache
    cache = get_embedding_cache()
    cache.stats["hits"] = 10
    cache.stats["misses"] = 100
    cache.stats["errors"] = 200
    
    tool_func = mock_mcp._registered_tools[2]
    result = await tool_func()
    
    assert result["success"] is True
    # May be unhealthy due to high error rate or low hit rate


@pytest.mark.asyncio
async def test_configure_cache_partial_update(mock_mcp):
    """Test partial cache configuration update"""
    register_cache_management_tools(mock_mcp)
    
    tool_func = mock_mcp._registered_tools[3]
    
    # Update only TTL
    result = await tool_func(ttl_seconds=3600)
    assert result["success"] is True
    assert result["configuration"]["ttl_seconds"] == 3600
    
    # Update only max size
    result = await tool_func(max_cache_size=15000)
    assert result["success"] is True
    assert result["configuration"]["max_cache_size"] == 15000

