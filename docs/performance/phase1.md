# Phase 1 Performance Benchmarks

This document summarizes lightweight performance checks for Phase 1 features and how to run them locally or in CI.

## Benchmarks

- Startup-time overhead (<10%): `benchmarks/startup_time_benchmark.py`
- Monitoring overhead (<10%): `benchmarks/monitoring_overhead_benchmark.py`
- Session memory (<100MB): `benchmarks/session_memory_check.py`
- Cache hit rate (>=90% baseline or >=20% improvement): `benchmarks/cache_hit_rate_benchmark.py`
- NLPAnalyzer throughput/memory (informational): `benchmarks/nlp_analyzer_perf.py`
- Deployment tool registration cost (informational): `benchmarks/deployment_tools_perf.py`

## How to run

```
python benchmarks/startup_time_benchmark.py
python benchmarks/monitoring_overhead_benchmark.py
python benchmarks/session_memory_check.py
python benchmarks/cache_hit_rate_benchmark.py
python benchmarks/nlp_analyzer_perf.py
python benchmarks/deployment_tools_perf.py
```

Notes:
- NLPAnalyzer requires spaCy and a model (default: `en_core_web_sm`).
  - Install: `python -m pip install spacy`
  - Download model: `python -m spacy download en_core_web_sm`
  - If spaCy or the model is missing, the NLP benchmark will skip gracefully.
- The deployment tools perf benchmark only measures the registration overhead of MCP tool wrappers; it does not perform any external deployments.

## Recent results (local sample)

- Startup-time overhead: PASS (<10%)
- Monitoring overhead: PASS (<10%)
- Session memory: PASS (<100MB)
- Cache hit rate: PASS (baseline high)
- NLPAnalyzer perf: model unavailable in this environment (skipped)
- Deployment tools registration: ~0.43 ms per registration; peak ~15 KB

## CI smoke (Docker Compose)

The workflow `.github/workflows/staging_compose_smoke.yml` builds the dev image and brings up a minimal stack (qdrant, redis, context-server), then performs a JSON-RPC initialize call to verify the server responds.

This workflow avoids GPU dependencies and does not start optional services like Ollama in CI.

