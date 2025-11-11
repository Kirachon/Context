# Phase 3 Features and Usage

Phase 3 adds templates, conversation context, and advanced caching.

## Components

- Template Expansion (common prompt/code templates)
- Conversation Context (multi-turn enhancements)
- Advanced Caching (predictive caching, cache warming)

## Feature Flags (settings.py)

- enable_predictive_caching: bool (default False)
- enable_cache_warming: bool (default False)
- enable_conversation_tracking: bool (default False)

In .env:

```
ENABLE_PREDICTIVE_CACHING=true
ENABLE_CACHE_WARMING=true
ENABLE_CONVERSATION_TRACKING=true
```

## Usage

- Predictive caching: warms cache for likely-next queries/files
- Conversation context: better ranking and tool selection using recent turns
- Templates: call template helpers or use MCP tools for generation

## Notes

- All features are opt-in and safe; defaults remain current prod behavior.
- Ensure Redis/Qdrant are running for caching features to have effect.

