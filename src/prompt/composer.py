"""
Prompt Composer - Epic 4

Composes final enhanced prompt from summarized context using Jinja2 templates.

Components:
- PromptComposer: Main composer class
- EnhancedPrompt: Result dataclass
- Template engine integration (Jinja2)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from jinja2 import Template

from src.prompt.summarizer import count_tokens


@dataclass
class EnhancedPrompt:
    """Enhanced prompt with metadata"""
    original: str
    enhanced: str
    token_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class PromptComposer:
    """
    Compose final enhanced prompt from summarized context

    Uses Jinja2 templates to structure the enhanced prompt with:
    - Original user request
    - Current context
    - Related code
    - Architecture
    - Recent changes
    - Team knowledge
    """

    def __init__(self, custom_template: Optional[str] = None):
        """
        Initialize prompt composer

        Args:
            custom_template: Optional custom Jinja2 template
        """
        self.template = self._load_template(custom_template)

    def compose(self, original_prompt: str, summarized_context, prompt_intent) -> EnhancedPrompt:
        """
        Compose structured enhanced prompt

        Args:
            original_prompt: User's original prompt
            summarized_context: SummarizedContext after ranking/compression
            prompt_intent: Analyzed prompt intent

        Returns:
            EnhancedPrompt with original and enhanced versions
        """
        # Group context by source
        current_items = summarized_context.get_by_source('current')
        code_items = summarized_context.get_by_source('code')
        arch_items = summarized_context.get_by_source('architecture')
        history_items = summarized_context.get_by_source('history')
        team_items = summarized_context.get_by_source('team')
        external_items = summarized_context.get_by_source('external')

        # Render template
        enhanced_prompt = self.template.render(
            original_prompt=original_prompt,
            intent=prompt_intent.intent.type.value,
            current_items=current_items,
            code_items=code_items,
            arch_items=arch_items,
            history_items=history_items,
            team_items=team_items,
            external_items=external_items,
            total_items=len(summarized_context.items),
            format_item=self._format_item,
            format_score=lambda x: f"{x:.2f}",
        )

        # Count tokens
        token_count = count_tokens(enhanced_prompt)

        # Extract metadata
        metadata = self._extract_metadata(
            summarized_context,
            prompt_intent,
            current_items,
            code_items,
            arch_items,
            history_items,
            team_items
        )

        return EnhancedPrompt(
            original=original_prompt,
            enhanced=enhanced_prompt,
            token_count=token_count,
            metadata=metadata
        )

    def _load_template(self, custom_template: Optional[str] = None) -> Template:
        """Load Jinja2 template"""
        if custom_template:
            return Template(custom_template)

        # Default template
        template_str = """
# USER REQUEST
{{ original_prompt }}

**Intent:** {{ intent }}
**Total Context Items:** {{ total_items }}

{% if current_items %}
# CURRENT CONTEXT

{% for item in current_items %}
{{ format_item(item) }}
{% endfor %}
{% endif %}

{% if code_items %}
# RELATED CODE

{% for item in code_items|sort(attribute='original.priority', reverse=True) %}
## {{ item.original.metadata.get('path', 'Unknown') }}
{% if item.original.priority > 0 %}
**Priority:** {{ format_score(item.original.priority) }}
{% endif %}
{% if item.compression == 'none' %}
```
{{ item.original.content }}
```
{% elif item.summary %}
```
{{ item.summary }}
```
{% else %}
```
{{ item.original.content }}
```
{% endif %}

{% endfor %}
{% endif %}

{% if arch_items %}
# ARCHITECTURE

{% for item in arch_items %}
## {{ item.original.type }}: {{ item.original.metadata.get('path', 'System') }}
{% if item.compression == 'none' %}
```
{{ item.original.content }}
```
{% elif item.summary %}
{{ item.summary }}
{% else %}
{{ item.original.content }}
{% endif %}

{% endfor %}
{% endif %}

{% if history_items %}
# RECENT CHANGES

{% for item in history_items %}
{% if item.original.type == 'recent_commit' %}
- **Commit {{ item.original.metadata.get('commit_hash', '')[:7] }}** by @{{ item.original.metadata.get('author', 'unknown') }}
  {{ item.original.metadata.get('message', '') }}
{% elif item.original.type == 'git_blame' %}
- **Git Blame** for {{ item.original.metadata.get('path', 'file') }}
  (See commit history above)
{% endif %}
{% endfor %}
{% endif %}

{% if team_items %}
# TEAM KNOWLEDGE

{% for item in team_items %}
{% if item.original.type == 'codeowners' %}
## Code Owners
{{ item.summary if item.summary else item.original.content }}
{% elif item.original.type == 'experts' %}
## Experts for {{ item.original.metadata.get('path', 'this file') }}
{% if item.original.content %}
{% for expert in item.original.content %}
- {{ expert.get('name', 'Unknown') }} ({{ expert.get('commits', 0) }} commits)
{% endfor %}
{% endif %}
{% endif %}
{% endfor %}
{% endif %}

{% if external_items %}
# EXTERNAL CONTEXT

{% for item in external_items %}
- {{ format_item(item) }}
{% endfor %}
{% endif %}

---
*Enhanced by Context Workspace v3.0*
*Token count: {{ token_count }} tokens*
        """.strip()

        return Template(template_str)

    def _format_item(self, item) -> str:
        """Format a context item for display"""
        item_type = item.original.type
        path = item.original.metadata.get('path', '')
        priority = item.original.priority

        # Get content
        if item.summary:
            content = item.summary
        else:
            content = str(item.original.content)

        # Truncate if too long
        if len(content) > 500:
            content = content[:500] + '...'

        # Format based on type
        if item_type == 'file':
            return f"**File:** {path}\n```\n{content}\n```"
        elif item_type == 'selection':
            lines = item.original.metadata.get('lines', (0, 0))
            return f"**Selected:** Lines {lines[0]}-{lines[1]}\n```\n{content}\n```"
        elif item_type in ['dependency', 'test']:
            return f"**{item_type.title()}:** {path}\n```\n{content}\n```"
        else:
            return f"**{item_type.title()}:** {content}"

    def _extract_metadata(self, summarized_context, prompt_intent, current_items,
                         code_items, arch_items, history_items, team_items) -> Dict[str, Any]:
        """Extract metadata about the enhancement"""
        return {
            'intent': prompt_intent.intent.type.value,
            'intent_confidence': prompt_intent.intent.confidence,
            'entity_count': len(prompt_intent.entities),
            'entities': [
                {
                    'text': e.text,
                    'type': e.type.value if hasattr(e.type, 'value') else str(e.type),
                    'confidence': e.confidence
                }
                for e in prompt_intent.entities
            ],
            'context_sources': {
                'current': len(current_items),
                'code': len(code_items),
                'architecture': len(arch_items),
                'history': len(history_items),
                'team': len(team_items),
            },
            'total_context_items': len(summarized_context.items),
            'token_budget': prompt_intent.token_budget,
            'actual_tokens': summarized_context.total_tokens,
            'compression_ratio': (
                summarized_context.total_tokens / prompt_intent.token_budget
                if prompt_intent.token_budget > 0 else 0
            ),
        }


# CLI Integration
async def enhance_prompt_cli(prompt: str, workspace_path: str, current_file: Optional[str] = None):
    """
    CLI command for prompt enhancement

    Usage:
        context enhance-prompt "Fix the authentication bug"
        context enhance-prompt "Fix the authentication bug" --file backend/auth.py
    """
    from src.prompt import enhance_prompt
    from src.prompt.context_gatherer import UserContext

    # Create user context
    user_context = UserContext(
        workspace_path=workspace_path,
        current_file=current_file
    )

    # Enhance prompt
    result = await enhance_prompt(prompt, user_context)

    return result


# MCP Tool Integration
async def enhance_prompt_mcp(prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    MCP tool for IDE integration

    Args:
        prompt: User's prompt
        context: User context dict with keys:
            - workspace_path: str
            - current_file: Optional[str]
            - selected_region: Optional[dict]
            - open_files: Optional[List[str]]

    Returns:
        Dict with enhanced prompt and metadata
    """
    from src.prompt import enhance_prompt
    from src.prompt.context_gatherer import UserContext

    # Create user context from dict
    user_context = UserContext(
        workspace_path=context.get('workspace_path', '.'),
        current_file=context.get('current_file'),
        selected_region=context.get('selected_region'),
        open_files=context.get('open_files', [])
    )

    # Enhance prompt
    result = await enhance_prompt(prompt, user_context)

    # Return as dict for MCP
    return {
        'original_prompt': result.original,
        'enhanced_prompt': result.enhanced,
        'token_count': result.token_count,
        'metadata': result.metadata
    }


# REST API Integration
async def enhance_prompt_api(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    REST API endpoint for prompt enhancement

    POST /api/v1/prompts/enhance
    Body:
    {
        "prompt": "Fix the authentication bug",
        "user_context": {
            "workspace_path": "/path/to/workspace",
            "current_file": "backend/auth.py"
        },
        "options": {
            "token_budget": 200000,
            "include_external": false
        }
    }

    Returns:
    {
        "enhanced_prompt": "...",
        "token_count": 150234,
        "latency_ms": 1523,
        "metadata": {...}
    }
    """
    import time
    from src.prompt import enhance_prompt
    from src.prompt.context_gatherer import UserContext

    start_time = time.time()

    # Parse request
    prompt = request_data.get('prompt')
    user_context_data = request_data.get('user_context', {})
    options = request_data.get('options', {})

    # Create user context
    user_context = UserContext(
        workspace_path=user_context_data.get('workspace_path', '.'),
        current_file=user_context_data.get('current_file'),
        selected_region=user_context_data.get('selected_region'),
        open_files=user_context_data.get('open_files', [])
    )

    # Enhance prompt
    result = await enhance_prompt(prompt, user_context)

    # Calculate latency
    latency_ms = int((time.time() - start_time) * 1000)

    # Return response
    return {
        'enhanced_prompt': result.enhanced,
        'token_count': result.token_count,
        'latency_ms': latency_ms,
        'metadata': result.metadata
    }
