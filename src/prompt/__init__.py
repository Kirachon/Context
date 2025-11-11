"""
Context-Aware Prompt Enhancement Engine for Context Workspace v3.0

This package provides intelligent prompt enhancement by automatically injecting
relevant context from code, history, team patterns, and external sources.

Main Components:
- analyzer: Analyzes user prompts to determine intent, entities, and context requirements
- context_gatherer: Gathers context from 6 sources in parallel
- ranker: Ranks context by relevance using 10-factor scoring
- summarizer: Compresses context using hierarchical summarization
- composer: Composes final enhanced prompt with structured sections

Usage:
    from src.prompt import enhance_prompt

    result = await enhance_prompt(
        prompt="Fix the authentication bug",
        user_context=UserContext(current_file="backend/auth.py")
    )
    print(result.enhanced_prompt)
"""

from src.prompt.analyzer import PromptAnalyzer, Intent, Entity, PromptIntent
from src.prompt.context_gatherer import ContextGatherer, UserContext
from src.prompt.composer import PromptComposer, EnhancedPrompt

__version__ = "3.0.0"
__all__ = [
    "PromptAnalyzer",
    "ContextGatherer",
    "PromptComposer",
    "Intent",
    "Entity",
    "PromptIntent",
    "UserContext",
    "EnhancedPrompt",
    "enhance_prompt",
]


async def enhance_prompt(prompt: str, user_context: UserContext) -> EnhancedPrompt:
    """
    Main entry point for prompt enhancement.

    Args:
        prompt: User's original prompt
        user_context: Current user context (file, workspace, etc.)

    Returns:
        EnhancedPrompt with original prompt and enhanced version
    """
    # Step 1: Analyze prompt
    analyzer = PromptAnalyzer()
    prompt_intent = await analyzer.analyze(prompt, user_context)

    # Step 2: Gather context
    gatherer = ContextGatherer()
    raw_context = await gatherer.gather(prompt_intent, user_context)

    # Step 3: Rank and summarize context
    from src.prompt.ranker import ContextRanker
    from src.prompt.summarizer import HierarchicalSummarizer

    ranker = ContextRanker()
    ranked_context = await ranker.rank(raw_context, prompt_intent, user_context)

    summarizer = HierarchicalSummarizer()
    summarized_context = await summarizer.summarize(ranked_context, prompt_intent.token_budget)

    # Step 4: Compose enhanced prompt
    composer = PromptComposer()
    enhanced_prompt = composer.compose(prompt, summarized_context, prompt_intent)

    return enhanced_prompt
