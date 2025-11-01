"""
Unit tests for Security MCP Tools (Epic 4)
"""

import pytest
from unittest.mock import MagicMock
from src.mcp_server.tools.security_tools import register_security_tools


@pytest.fixture
def mock_mcp():
    mcp = MagicMock()
    regs = []

    def deco_factory():
        def dec(fn):
            regs.append(fn)
            return fn

        return dec

    mcp.tool = MagicMock(side_effect=deco_factory)
    mcp._tools = regs
    return mcp


def test_register_security_tools(mock_mcp):
    register_security_tools(mock_mcp)
    assert len(mock_mcp._tools) == 3


@pytest.mark.asyncio
async def test_set_and_get_role(mock_mcp):
    register_security_tools(mock_mcp)
    set_role_fn = mock_mcp._tools[0]
    get_role_fn = mock_mcp._tools[1]

    res = await set_role_fn("admin")
    assert res["success"]
    res2 = await get_role_fn()
    assert res2["role"] == "admin"
