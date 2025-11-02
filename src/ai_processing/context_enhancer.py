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

    def enhance_with_code_context(
        self,
        prompt: str,
        code_snippets: List[Dict[str, Any]],
        git_context: Optional[Dict[str, Any]] = None,
        recent_files: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Enhance prompt with code snippets and optional git/recent files context.
        Returns a dict with enhanced_prompt and context metadata.
        """
        parts: List[str] = []

        # Code snippets section
        if code_snippets:
            parts.append("=== Relevant Code from Codebase ===\n")
            for i, snip in enumerate(code_snippets, 1):
                fp = snip.get("file_path", "")
                ls = snip.get("line_start", 1)
                le = snip.get("line_end", ls)
                lang = snip.get("language", "text")
                content = snip.get("content", "")
                parts.append(
                    f"\n[{i}] File: {fp} (lines {ls}-{le})\n"  # header
                )
                parts.append(f"```{lang}\n{content}\n```\n")

        # Git context
        if git_context and git_context.get("recent_commits"):
            parts.append("\n=== Recent Changes ===\n")
            for c in git_context.get("recent_commits", [])[:3]:
                subj = c.get("subject") or c.get("message") or "(no message)"
                author = c.get("author", "unknown")
                parts.append(f"- {subj} ({author})\n")

        # Recently modified files
        if recent_files:
            parts.append("\n=== Recently Modified Files ===\n")
            for f in recent_files[:5]:
                parts.append(f"- {f}\n")

        context_text = "".join(parts)

        enhanced_prompt = (
            f"{context_text}\n\n=== User Question ===\n{prompt}\n\n"
            "=== Instructions ===\n"
            "Please answer the user's question based on the code context provided above.\n"
            "Reference specific files and line numbers when relevant. Be concise and accurate.\n"
        )

        return {
            "enhanced_prompt": enhanced_prompt,
            "context": {
                "code_snippets_count": len(code_snippets or []),
                "files_referenced": [s.get("file_path") for s in (code_snippets or []) if s.get("file_path")],
                "git_commits_count": len(git_context.get("recent_commits", [])) if git_context else 0,
                "recent_files_count": len(recent_files or []),
            },
        }



# Singleton
_context_enhancer: ContextEnhancer = None


def get_context_enhancer() -> ContextEnhancer:
    global _context_enhancer
    if _context_enhancer is None:
        _context_enhancer = ContextEnhancer()
    return _context_enhancer
