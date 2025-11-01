"""
Unit tests for MCP Query Understanding Tools (Story 2.6)
"""
import pytest
from unittest.mock import MagicMock

from src.mcp_server.tools.query_understanding import register_query_tools


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


def test_register_query_tools(mock_mcp):
    """Test that query tools are registered"""
    register_query_tools(mock_mcp)
    # Verify 6 tools were registered
    assert len(mock_mcp._registered_tools) == 6


@pytest.mark.asyncio
async def test_query_classify(mock_mcp):
    """Test query classification tool"""
    register_query_tools(mock_mcp)
    
    # Get the registered function (first tool: query_classify)
    tool_func = mock_mcp._registered_tools[0]
    
    result = await tool_func("find all authentication functions")
    assert result["success"] is True
    assert "intent" in result
    assert result["intent"] == "search"
    assert "confidence" in result
    assert "entities" in result


@pytest.mark.asyncio
async def test_query_enhance(mock_mcp):
    """Test query enhancement tool"""
    register_query_tools(mock_mcp)
    
    # Get the registered function (second tool: query_enhance)
    tool_func = mock_mcp._registered_tools[1]
    
    result = await tool_func("find authentication code", recent_files=["src/auth.py"])
    assert result["success"] is True
    assert "enhanced_query" in result
    assert len(result["enhanced_query"]) > 0
    assert "context_additions" in result


@pytest.mark.asyncio
async def test_query_followup(mock_mcp):
    """Test follow-up question generation"""
    register_query_tools(mock_mcp)
    
    # Get the registered function (third tool: query_followup)
    tool_func = mock_mcp._registered_tools[2]
    
    result = await tool_func("find database queries")
    assert result["success"] is True
    assert "follow_up_questions" in result
    assert len(result["follow_up_questions"]) > 0


@pytest.mark.asyncio
async def test_query_history_add(mock_mcp):
    """Test adding query to history"""
    register_query_tools(mock_mcp)
    
    # Get the registered function (fourth tool: query_history_add)
    tool_func = mock_mcp._registered_tools[3]
    
    result = await tool_func("find functions", "search", 5, tags=["important"])
    assert result["success"] is True
    assert "total_in_history" in result
    assert result["total_in_history"] >= 1


@pytest.mark.asyncio
async def test_query_history_get(mock_mcp):
    """Test retrieving query history"""
    register_query_tools(mock_mcp)
    
    # Add some queries first
    add_tool = mock_mcp._registered_tools[3]
    await add_tool("query 1", "search", 5)
    await add_tool("query 2", "debug", 3)
    
    # Get the registered function (fifth tool: query_history_get)
    get_tool = mock_mcp._registered_tools[4]
    
    result = await get_tool(limit=10)
    assert result["success"] is True
    assert "queries" in result
    assert result["count"] >= 2


@pytest.mark.asyncio
async def test_query_analytics(mock_mcp):
    """Test query analytics"""
    register_query_tools(mock_mcp)

    # Add some queries first
    add_tool = mock_mcp._registered_tools[3]
    await add_tool("query 1", "search", 5)
    await add_tool("query 2", "search", 3)
    await add_tool("query 3", "debug", 2)

    # Get the registered function (sixth tool: query_analytics)
    analytics_tool = mock_mcp._registered_tools[5]

    result = await analytics_tool()
    assert result["success"] is True
    assert "statistics" in result
    assert "total_queries" in result["statistics"]


@pytest.mark.asyncio
async def test_query_classify_multiple_intents(mock_mcp):
    """Test classification of different query intents"""
    register_query_tools(mock_mcp)
    tool_func = mock_mcp._registered_tools[0]

    # Test refactor intent
    result = await tool_func("refactor this code to improve readability")
    assert result["success"] is True
    assert result["intent"] == "refactor"

    # Test optimize intent
    result = await tool_func("optimize this loop for better performance")
    assert result["success"] is True
    assert result["intent"] == "optimize"


@pytest.mark.asyncio
async def test_query_enhance_confidence(mock_mcp):
    """Test query enhancement confidence scoring"""
    register_query_tools(mock_mcp)
    tool_func = mock_mcp._registered_tools[1]

    result = await tool_func("find code")
    assert result["success"] is True
    assert "confidence" in result
    assert 0.0 <= result["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_query_followup_refactor(mock_mcp):
    """Test follow-up questions for refactor intent"""
    register_query_tools(mock_mcp)
    tool_func = mock_mcp._registered_tools[2]

    result = await tool_func("refactor this code")
    assert result["success"] is True
    assert result["intent"] == "refactor"
    assert len(result["follow_up_questions"]) > 0


@pytest.mark.asyncio
async def test_query_history_multiple_adds(mock_mcp):
    """Test adding multiple queries to history"""
    register_query_tools(mock_mcp)
    add_tool = mock_mcp._registered_tools[3]

    for i in range(5):
        result = await add_tool(f"query {i}", "search", i)
        assert result["success"] is True
        assert result["total_in_history"] >= i + 1  # Allow for previous test queries


@pytest.mark.asyncio
async def test_query_analytics_intent_distribution(mock_mcp):
    """Test analytics with multiple intents"""
    register_query_tools(mock_mcp)

    add_tool = mock_mcp._registered_tools[3]
    await add_tool("find code", "search", 5)
    await add_tool("find code 2", "search", 3)
    await add_tool("debug issue", "debug", 2)
    await add_tool("optimize code", "optimize", 1)

    analytics_tool = mock_mcp._registered_tools[5]
    result = await analytics_tool()

    stats = result["statistics"]
    # Check that intents are present and have expected counts (allow for previous test queries)
    assert "search" in stats["intent_distribution"]
    assert stats["intent_distribution"]["search"] >= 2
    assert "debug" in stats["intent_distribution"]
    assert stats["intent_distribution"]["debug"] >= 1
    assert "optimize" in stats["intent_distribution"]
    assert stats["intent_distribution"]["optimize"] >= 1


@pytest.mark.asyncio
async def test_query_tools_workflow(mock_mcp):
    """Test complete workflow of query tools"""
    register_query_tools(mock_mcp)

    classify_tool = mock_mcp._registered_tools[0]
    enhance_tool = mock_mcp._registered_tools[1]
    followup_tool = mock_mcp._registered_tools[2]
    add_tool = mock_mcp._registered_tools[3]
    get_tool = mock_mcp._registered_tools[4]

    query = "find authentication functions"

    # Step 1: Classify
    classify_result = await classify_tool(query)
    assert classify_result["success"] is True
    intent = classify_result["intent"]

    # Step 2: Enhance
    enhance_result = await enhance_tool(query)
    assert enhance_result["success"] is True

    # Step 3: Get follow-up questions
    followup_result = await followup_tool(query)
    assert followup_result["success"] is True

    # Step 4: Add to history
    add_result = await add_tool(query, intent, 5)
    assert add_result["success"] is True

    # Step 5: Retrieve from history
    get_result = await get_tool(limit=10)
    assert get_result["success"] is True
    assert get_result["count"] >= 1

