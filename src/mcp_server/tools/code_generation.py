from __future__ import annotations

from typing import Any, Dict, Optional
from src.mcp_server.tools.instrumentation import instrument_tool
from fastmcp import FastMCP


def register_code_generation_tools(mcp: FastMCP) -> None:
    """Register AI-assisted code generation MCP tools.

    All tools are deterministic and safe by default, producing skeletons/templates
    without external API calls. Advanced providers can be added later behind flags.
    """

    @mcp.tool()
    @instrument_tool("generate_code")
    async def generate_code(spec: str, language: str = "python", max_lines: int = 200) -> Dict[str, Any]:
        from src.ai_processing.code_generator import CodeGenerator, GenerationOptions

        gen = CodeGenerator()
        res = gen.generate_code(spec, GenerationOptions(language=language, max_lines=max_lines))
        return {"success": True, **res}

    @mcp.tool()
    @instrument_tool("generate_tests")
    async def generate_tests(module: str, target: str, language: str = "python") -> Dict[str, Any]:
        from src.ai_processing.test_generator import TestGenerator

        tg = TestGenerator()
        res = tg.generate_tests(module, target, language)
        return {"success": True, **res}

    @mcp.tool()
    @instrument_tool("generate_docs")
    async def generate_docs(title: str, description: str) -> Dict[str, Any]:
        from src.ai_processing.doc_generator import DocGenerator

        dg = DocGenerator()
        res = dg.generate_docs(title, description)
        return {"success": True, **res}

