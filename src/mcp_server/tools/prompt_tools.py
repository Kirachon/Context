"""
Prompt MCP Tools (Epic 3)

Analyze, enhance, and generate responses for prompts.
"""

import sys
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP
from src.ai_processing.prompt_analyzer import get_prompt_analyzer
from src.ai_processing.context_enhancer import get_context_enhancer
from src.ai_processing.response_generator import get_response_generator
from src.ai_processing.model_manager import get_model_manager
from src.git.history import get_recent_commits, summarize_changes

logger = logging.getLogger(__name__)


def register_prompt_tools(mcp: FastMCP):
    """Register prompt tools with MCP server"""

    @mcp.tool()
    async def prompt_analyze(prompt: str) -> Dict[str, Any]:
        """Analyze prompt intent and needs"""
        analyzer = get_prompt_analyzer()
        result = analyzer.analyze(prompt)
        return {
            "success": True,
            "analysis": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @mcp.tool()
    async def prompt_enhance(
        prompt: str,
        include_git_summary: bool = True
    ) -> Dict[str, Any]:
        """Enhance prompt with context signals"""
        enhancer = get_context_enhancer()
        extra_ctx = {}
        if include_git_summary:
            extra_ctx["recent_commits"] = get_recent_commits(5)
            extra_ctx["change_summary"] = summarize_changes()
        enhanced = enhancer.enhance(prompt, extra_context=extra_ctx)
        return {
            "success": True,
            **enhanced,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @mcp.tool()
    async def prompt_generate(
        prompt: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate response using Ollama"""
        manager = get_model_manager()
        model_name = model or manager.get_default_model()
        generator = get_response_generator()
        text = await generator.generate(prompt, model=model_name)
        return {
            "success": True,
            "model": model_name,
            "response": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @mcp.tool()
    async def prompt_set_model(model: str) -> Dict[str, Any]:
        """Set default model"""
        manager = get_model_manager()
        manager.set_default_model(model)
        return {
            "success": True,
            "default_model": manager.get_default_model(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

