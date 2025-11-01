"""
Context-Aware Prompt Enhancement (Story 3-3)

Builds a richer prompt using project context signals.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ContextEnhancer:
    """Compose an enhanced prompt using lightweight signals"""

    def __init__(self):
        pass

    def enhance(
        self,
        prompt: str,
        recent_files: Optional[List[str]] = None,
        active_branch: Optional[str] = None,
        related_symbols: Optional[List[str]] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ctx: Dict[str, Any] = {
            "recent_files": recent_files or [],
            "active_branch": active_branch or "unknown",
            "related_symbols": related_symbols or [],
        }
        if extra_context:
            ctx.update(extra_context)

        enhanced = (
            "Please answer precisely and concisely. Use the provided project "
            "context when relevant."
        )
        return {
            "enhanced_prompt": f"{enhanced}\n\nUser request:\n{prompt}",
            "context": ctx,
        }


# Singleton
_context_enhancer: ContextEnhancer = None


def get_context_enhancer() -> ContextEnhancer:
    global _context_enhancer
    if _context_enhancer is None:
        _context_enhancer = ContextEnhancer()
    return _context_enhancer
