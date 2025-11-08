# Phase 2 Features and Usage

Phase 2 focuses on developer experience and intelligent assistance.

## Components

- Interactive CLI (Rich UI), shortcuts and prompts
- Semantic File Matching (context-aware file suggestions)
- Real-Time Code Monitoring (quality/security metrics)
- AI-Powered Code Generation (safe local templates by default)

## Feature Flags (settings.py)

- enable_realtime_monitoring: bool (default False)
- enable_code_generation: bool (default False)
- enable_query_refinement: bool (default False)
- enable_conversation_tracking: bool (default False)

In .env:

```
ENABLE_REALTIME_MONITORING=true
ENABLE_CODE_GENERATION=true
ENABLE_QUERY_REFINEMENT=true
```

## Usage

- Code generation (local provider):
  - MCP tool: `generate_code`, `generate_tests`, `generate_docs`
  - Library: `from src.ai_processing.code_generator import CodeGenerator`
  - Returns deterministic skeletons (no external APIs)

- Real-time monitoring:
  - Metrics exported via Prometheus when enabled
  - Low-overhead hooks around MCP tools and key services

- Semantic file matching:
  - Integrated into indexing/search; boosts relevant files in results

## Notes

- Ollama-backed code generation is not implemented; local provider is deterministic and safe.
- All features degrade gracefully when flags are disabled.

