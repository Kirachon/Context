"""
Unit tests for Prompt MCP Tools (Epic 3)
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.mcp_server.tools.prompt_tools import register_prompt_tools


@pytest.fixture
def mock_mcp():
    mcp = MagicMock()
    registered = []
    def decorator_factory():
        def dec(func):
            registered.append(func)
            return func
        return dec
    mcp.tool = MagicMock(side_effect=decorator_factory)
    mcp._tools = registered
    return mcp


def test_register_prompt_tools(mock_mcp):
    register_prompt_tools(mock_mcp)
    # We registered 4 tools
    assert len(mock_mcp._tools) == 4


@pytest.mark.asyncio
async def test_prompt_analyze_tool(mock_mcp):
    register_prompt_tools(mock_mcp)
    fn = mock_mcp._tools[0]
    result = await fn("Explain this code")
    assert result["success"] is True
    assert "analysis" in result


@pytest.mark.asyncio
async def test_prompt_generate_tool(mock_mcp):
    register_prompt_tools(mock_mcp)
    fn = mock_mcp._tools[2]
    with patch('src.ai_processing.ollama_client.OllamaClient.generate_response', new=AsyncMock(return_value='ok')):
        result = await fn("hello", model="llama3")
    assert result["success"] is True
    assert result["response"] == "ok"

