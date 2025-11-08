# Phase 1 Features and Usage

Phase 1 introduces safe, additive capabilities that are feature-flagged and backward compatible.

## Components

- Advanced NLP (spaCy-backed) via `NLPAnalyzer`
- Multi-Platform Deployment Tools (Vercel, Render, Railway, Supabase) as MCP tools
- Advanced Query Understanding (conversation context, refinements)
- Performance Profiling & Optimization tooling
- Security & Compliance Analysis tools

## Feature Flags (settings.py)

- enable_nlp_analysis: bool (default False)
- enable_deployment_integrations: bool (default False)
- enable_conversation_tracking: bool (default False)
- enable_performance_profiling: bool (default False)
- profiling_sample_rate: float (default 0.1)
- profiling_store_results: bool (default False)
- enable_security_scanning: bool (default False)
- security_scan_on_index: bool (default False)

In .env:

```
ENABLE_NLP_ANALYSIS=true
ENABLE_DEPLOYMENT_INTEGRATIONS=true
ENABLE_CONVERSATION_TRACKING=true
ENABLE_PERFORMANCE_PROFILING=false
ENABLE_SECURITY_SCANNING=false
```

## Usage

- NLP analysis (optional):
  - `from src.ai_processing.nlp_analyzer import get_nlp_analyzer`
  - Analyzer is lazy-loaded and gracefully degrades when spaCy/model unavailable

- Deployment tools (MCP):
  - `deploy_to_vercel`, `deploy_to_render`, `deploy_to_railway`, `deploy_to_supabase`
  - Return structured JSON, mock-safe unless SDKs installed and wired

- Query understanding tools (MCP):
  - `query:refine`, `query:resolve_ambiguity` (feature-flagged)

- Profiling tools (MCP):
  - `profile_operation`, `get_performance_stats`, `identify_bottlenecks`

- Security tools (MCP):
  - `scan_security`, `check_dependencies`, `generate_compliance_report`

## Benchmarks and Limits

- Startup-time overhead: <10% (passing)
- Monitoring overhead: <10% (passing)
- Session memory: <100MB (passing)
- NLPAnalyzer perf: informational (skips if spaCy/model missing)

See also: docs/performance/phase1.md

