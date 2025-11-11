"""
Example Usage of Context-Aware Prompt Enhancement Engine

This file demonstrates how to use the prompt enhancement system
with real-world examples.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.prompt import enhance_prompt
from src.prompt.context_gatherer import UserContext


# ============================================================================
# Example 1: Debugging a Production Error
# ============================================================================


async def example_1_debug_error():
    """
    Example: Fix a TypeError in production

    User Prompt: "Fix the TypeError on line 45 in payment_processor.py"

    This demonstrates:
    - Intent classification (fix)
    - Entity extraction (file path, error type)
    - Context gathering (code, history, similar issues)
    - Token budget estimation (100k+ for fix intent)
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: Debugging a Production Error")
    print("="*80)

    user_context = UserContext(
        workspace_path=os.path.abspath("."),
        current_file="backend/payment_processor.py",
        selected_region={
            'text': "result = payment_gateway.charge(amount, method['type'])",
            'lines': (45, 45)
        }
    )

    result = await enhance_prompt(
        prompt="Fix the TypeError on line 45 in payment_processor.py",
        user_context=user_context
    )

    print(f"\nOriginal Prompt: {result.original}")
    print(f"Token Count: {result.token_count}")
    print(f"Intent: {result.metadata['intent']}")
    print(f"Entities Found: {result.metadata['entity_count']}")
    print(f"\nEnhanced Prompt Preview (first 500 chars):")
    print(result.enhanced[:500])
    print("...")


# ============================================================================
# Example 2: Understanding Complex Code
# ============================================================================


async def example_2_understand_caching():
    """
    Example: How does the caching system work?

    User Prompt: "How does the caching system work?"

    This demonstrates:
    - Intent classification (explain)
    - Context gathering (architecture, code, configs)
    - Hierarchical summarization
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: Understanding Complex Code")
    print("="*80)

    user_context = UserContext(
        workspace_path=os.path.abspath("."),
        current_file="src/caching/query_cache.py"
    )

    result = await enhance_prompt(
        prompt="How does the caching system work?",
        user_context=user_context
    )

    print(f"\nOriginal Prompt: {result.original}")
    print(f"Token Count: {result.token_count}")
    print(f"Context Sources:")
    for source, count in result.metadata['context_sources'].items():
        print(f"  - {source}: {count} items")

    print(f"\nEnhanced Prompt Preview (first 500 chars):")
    print(result.enhanced[:500])
    print("...")


# ============================================================================
# Example 3: Implementing a New Feature
# ============================================================================


async def example_3_implement_feature():
    """
    Example: Implement email validation

    User Prompt: "Implement email validation for user signup"

    This demonstrates:
    - Intent classification (implement)
    - Context gathering (patterns, architecture, examples)
    - Higher token budget (150k+)
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Implementing a New Feature")
    print("="*80)

    user_context = UserContext(
        workspace_path=os.path.abspath("."),
        current_file="backend/models/user.py"
    )

    result = await enhance_prompt(
        prompt="Implement email validation for user signup",
        user_context=user_context
    )

    print(f"\nOriginal Prompt: {result.original}")
    print(f"Token Count: {result.token_count}")
    print(f"Token Budget: {result.metadata['token_budget']}")
    print(f"Compression Ratio: {result.metadata['compression_ratio']:.2%}")

    print(f"\nEnhanced Prompt Preview (first 500 chars):")
    print(result.enhanced[:500])
    print("...")


# ============================================================================
# Example 4: Code Review Request
# ============================================================================


async def example_4_code_review():
    """
    Example: Review changes in a PR

    User Prompt: "Review the authentication changes"

    This demonstrates:
    - Intent classification (review/explain)
    - Context gathering (git history, recent commits)
    - Team context (code owners, experts)
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: Code Review Request")
    print("="*80)

    user_context = UserContext(
        workspace_path=os.path.abspath("."),
        current_file="backend/auth/jwt.py",
        open_files=[
            "backend/auth/jwt.py",
            "backend/auth/middleware.py",
            "tests/test_auth.py"
        ]
    )

    result = await enhance_prompt(
        prompt="Review the authentication changes",
        user_context=user_context
    )

    print(f"\nOriginal Prompt: {result.original}")
    print(f"Open Files: {len(user_context.open_files)}")
    print(f"Context Items: {result.metadata['total_context_items']}")

    print(f"\nEnhanced Prompt Preview (first 500 chars):")
    print(result.enhanced[:500])
    print("...")


# ============================================================================
# Example 5: CLI Usage
# ============================================================================


async def example_5_cli_usage():
    """
    Example: Using CLI command

    Command: context enhance-prompt "Fix authentication bug"

    This demonstrates:
    - CLI integration
    - Simple workspace context
    - Quick enhancement
    """
    print("\n" + "="*80)
    print("EXAMPLE 5: CLI Usage")
    print("="*80)

    from src.prompt.composer import enhance_prompt_cli

    result = await enhance_prompt_cli(
        prompt="Fix authentication bug",
        workspace_path=os.path.abspath("."),
        current_file="backend/auth.py"
    )

    print(f"\nCLI Command: context enhance-prompt 'Fix authentication bug'")
    print(f"\nResult:")
    print(f"  Token Count: {result.token_count}")
    print(f"  Intent: {result.metadata['intent']}")
    print(f"  Entities: {result.metadata['entity_count']}")


# ============================================================================
# Example 6: MCP Tool Usage
# ============================================================================


async def example_6_mcp_usage():
    """
    Example: Using MCP tool for IDE integration

    This demonstrates:
    - MCP tool integration
    - IDE context (selected region, open files)
    - Structured response
    """
    print("\n" + "="*80)
    print("EXAMPLE 6: MCP Tool Usage (IDE Integration)")
    print("="*80)

    from src.prompt.composer import enhance_prompt_mcp

    context = {
        'workspace_path': os.path.abspath("."),
        'current_file': 'src/prompt/analyzer.py',
        'selected_region': {
            'text': 'def classify(self, prompt: str) -> Intent:',
            'lines': (50, 60)
        },
        'open_files': [
            'src/prompt/analyzer.py',
            'src/prompt/context_gatherer.py'
        ]
    }

    result = await enhance_prompt_mcp(
        prompt="Explain this function",
        context=context
    )

    print(f"\nMCP Tool Response:")
    print(f"  Original: {result['original_prompt']}")
    print(f"  Token Count: {result['token_count']}")
    print(f"  Metadata: {len(result['metadata'])} fields")


# ============================================================================
# Example 7: REST API Usage
# ============================================================================


async def example_7_api_usage():
    """
    Example: Using REST API endpoint

    POST /api/v1/prompts/enhance

    This demonstrates:
    - REST API integration
    - Performance metrics
    - Structured request/response
    """
    print("\n" + "="*80)
    print("EXAMPLE 7: REST API Usage")
    print("="*80)

    from src.prompt.composer import enhance_prompt_api

    request_data = {
        'prompt': 'Fix the authentication bug in login.py',
        'user_context': {
            'workspace_path': os.path.abspath("."),
            'current_file': 'backend/login.py'
        },
        'options': {
            'token_budget': 200000,
            'include_external': False
        }
    }

    result = await enhance_prompt_api(request_data)

    print(f"\nAPI Request:")
    print(f"  POST /api/v1/prompts/enhance")
    print(f"\nAPI Response:")
    print(f"  Token Count: {result['token_count']}")
    print(f"  Latency: {result['latency_ms']}ms")
    print(f"  Success: ✓")


# ============================================================================
# Example 8: Custom Template
# ============================================================================


async def example_8_custom_template():
    """
    Example: Using custom Jinja2 template

    This demonstrates:
    - Custom template support
    - Template customization
    - Flexible output formatting
    """
    print("\n" + "="*80)
    print("EXAMPLE 8: Custom Template")
    print("="*80)

    from src.prompt.composer import PromptComposer
    from src.prompt.analyzer import PromptAnalyzer
    from src.prompt.context_gatherer import ContextGatherer
    from src.prompt.ranker import ContextRanker
    from src.prompt.summarizer import HierarchicalSummarizer

    # Custom template
    custom_template = """
TASK: {{ original_prompt }}

CONTEXT:
{% for item in current_items %}
- {{ item.original.type }}: {{ item.original.metadata.get('path', 'N/A') }}
{% endfor %}

PROCEED.
    """.strip()

    # Create composer with custom template
    composer = PromptComposer(custom_template=custom_template)

    # Analyze
    analyzer = PromptAnalyzer()
    user_context = UserContext(workspace_path=os.path.abspath("."))
    prompt_intent = await analyzer.analyze("Fix bug", user_context)

    # Gather
    gatherer = ContextGatherer()
    raw_context = await gatherer.gather(prompt_intent, user_context)

    # Rank
    ranker = ContextRanker()
    ranked = await ranker.rank(raw_context, prompt_intent, user_context)

    # Summarize
    summarizer = HierarchicalSummarizer()
    summarized = await summarizer.summarize(ranked, prompt_intent.token_budget)

    # Compose
    result = composer.compose("Fix bug", summarized, prompt_intent)

    print(f"\nCustom Template Output:")
    print(result.enhanced[:300])


# ============================================================================
# Main: Run all examples
# ============================================================================


async def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("Context-Aware Prompt Enhancement Engine - Examples")
    print("Version 3.0.0")
    print("="*80)

    examples = [
        ("Debugging a Production Error", example_1_debug_error),
        ("Understanding Complex Code", example_2_understand_caching),
        ("Implementing a New Feature", example_3_implement_feature),
        ("Code Review Request", example_4_code_review),
        ("CLI Usage", example_5_cli_usage),
        ("MCP Tool Usage", example_6_mcp_usage),
        ("REST API Usage", example_7_api_usage),
        ("Custom Template", example_8_custom_template),
    ]

    for i, (name, example_func) in enumerate(examples, 1):
        try:
            await example_func()
        except Exception as e:
            print(f"\nExample {i} ({name}) failed: {e}")

    print("\n" + "="*80)
    print("All examples completed!")
    print("="*80)


if __name__ == '__main__':
    # Run examples
    asyncio.run(main())
