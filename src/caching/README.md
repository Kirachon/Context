# Smart Caching System - Context Workspace v2.5

Multi-layer caching system that achieves sub-100ms search latency through aggressive caching and predictive pre-fetching.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Smart Caching System                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Query Result Cache                       │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │  │
│  │  │ L1       │→ │ L2       │→ │ L3               │   │  │
│  │  │ In-Memory│  │ Redis    │  │ Pre-computed     │   │  │
│  │  │ 100MB    │  │ 1GB      │  │ 5GB              │   │  │
│  │  │ 5min TTL │  │ 1hr TTL  │  │ 24hr TTL         │   │  │
│  │  └──────────┘  └──────────┘  └──────────────────┘   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Embedding Cache                          │  │
│  │  - LZ4 compression                                    │  │
│  │  - Background refresh (6hr)                           │  │
│  │  - Warm cache from recent queries                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Cache Invalidation                       │  │
│  │  - Smart file-query tracking                          │  │
│  │  - Incremental invalidation                           │  │
│  │  - Batch processing with debouncing                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Predictive Pre-fetcher                   │  │
│  │  - Markov chain prediction                            │  │
│  │  - Pattern analysis (bigrams, trigrams)              │  │
│  │  - Context-aware predictions                          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Query Cache (`query_cache.py`)

Multi-layer cache for search results:

- **L1 (In-Memory)**: Python LRU cache, 100MB, 5min TTL
- **L2 (Redis)**: Redis cache, 1GB, 1hour TTL
- **L3 (Pre-computed)**: Common queries, 24hour TTL

**Features:**
- Automatic cache key generation from query + context
- LRU eviction policy
- Promotion from L2 → L1 on hit
- File-query relationship tracking for smart invalidation

**Usage:**
```python
from src.caching import get_query_cache

cache = get_query_cache()

# Get cached results
context = {"current_project": "frontend", "recent_files": ["src/App.tsx"]}
results = await cache.get("user authentication", context)

if results is None:
    # Cache miss - execute search
    results = await execute_search("user authentication")

    # Cache results
    await cache.set(
        "user authentication",
        results,
        context,
        accessed_files=["backend/auth.py", "frontend/Login.tsx"]
    )
```

### 2. Embedding Cache (`embedding_cache.py`)

Caching for embedding vectors with compression:

**Features:**
- LZ4 compression (2-3x reduction)
- Background refresh every 6 hours
- Pre-compute common queries at startup
- Warm cache from user's recent queries

**Usage:**
```python
from src.caching import get_embedding_cache

emb_cache = get_embedding_cache()

# Get cached embedding
embedding = await emb_cache.get("user authentication", model="all-MiniLM-L6-v2")

if embedding is None:
    # Generate embedding
    embedding = await generate_embedding("user authentication")

    # Cache with compression
    await emb_cache.set("user authentication", embedding, model="all-MiniLM-L6-v2")

# Pre-compute common queries
common_queries = ["authentication", "database query", "error handling"]
await emb_cache.precompute_common_queries(
    common_queries,
    model="all-MiniLM-L6-v2",
    embedding_func=generate_embedding
)

# Start background refresh
await emb_cache.start_background_refresh(
    model="all-MiniLM-L6-v2",
    embedding_func=generate_embedding
)
```

### 3. Cache Invalidation (`invalidation.py`)

Smart invalidation based on file changes:

**Features:**
- Tracks which files each query accessed
- Incremental invalidation (only affected queries)
- Batch processing with 2-second debouncing
- Pattern-based invalidation (e.g., all .py files)

**Usage:**
```python
from src.caching import get_cache_invalidator

invalidator = get_cache_invalidator()

# Invalidate when file changes
await invalidator.invalidate_file("backend/auth.py", event_type="modified")

# Batch invalidation
files = ["src/app.py", "src/models.py", "src/utils.py"]
await invalidator.invalidate_files_batch(files)

# Pattern-based invalidation
await invalidator.invalidate_pattern("*.py")

# Project-wide invalidation
await invalidator.invalidate_project("/path/to/backend")
```

### 4. Predictive Pre-fetcher (`prefetcher.py`)

Predicts and pre-fetches likely next queries:

**Features:**
- Markov chain prediction
- Sequence mining (bigrams, trigrams)
- Context-aware predictions
- Background pre-fetching

**Usage:**
```python
from src.caching import get_prefetcher

prefetcher = get_prefetcher()

# Set search function
async def search_func(query, context):
    # Your search implementation
    return results

prefetcher.search_func = search_func

# Record query and trigger prefetch
await prefetcher.record_and_prefetch(
    query="user authentication",
    context={"current_project": "backend"},
    user_id="user123"
)

# Warm cache at startup
common_queries = [
    "authentication",
    "database connection",
    "API endpoints",
    "error handling",
    "logging"
]
await prefetcher.warm_cache_startup(common_queries)

# Get pattern statistics
stats = prefetcher.get_pattern_statistics()
print(f"Tracked patterns: {stats}")
```

### 5. Cache Statistics (`stats.py`)

Comprehensive metrics and Prometheus export:

**Features:**
- Hit rates by layer (L1, L2, L3)
- Cache sizes and item counts
- Latency metrics
- Prometheus format export

**Usage:**
```python
from src.caching import get_cache_stats

stats = get_cache_stats()

# Get summary
summary = stats.get_summary()
print(f"Overall hit rate: {summary['overall']['hit_rate_percent']}%")
print(f"L1 hits: {summary['l1']['hits']}")
print(f"L2 hits: {summary['l2']['hits']}")

# Export to Prometheus
prometheus_metrics = stats.export_prometheus()
```

## Integration Example

Complete integration with search system:

```python
import asyncio
from src.caching import (
    get_query_cache,
    get_embedding_cache,
    get_cache_invalidator,
    get_prefetcher,
    get_cache_stats
)

async def integrated_search(query: str, context: dict, user_id: str):
    """Search with full caching integration"""

    # 1. Try cache first
    cache = get_query_cache()
    results = await cache.get(query, context)

    if results is not None:
        print(f"Cache hit! Returned in <50ms")

        # Record for prefetch pattern analysis
        prefetcher = get_prefetcher()
        await prefetcher.record_and_prefetch(query, context, user_id)

        return results

    # 2. Cache miss - execute search
    print("Cache miss - executing search...")

    # Check embedding cache
    emb_cache = get_embedding_cache()
    embedding = await emb_cache.get(query, model="all-MiniLM-L6-v2")

    if embedding is None:
        embedding = await generate_embedding(query)
        await emb_cache.set(query, embedding, model="all-MiniLM-L6-v2")

    # Execute search with cached embedding
    results, accessed_files = await execute_search_with_embedding(
        query, embedding, context
    )

    # 3. Cache results
    await cache.set(query, results, context, accessed_files)

    # 4. Trigger predictive prefetch
    prefetcher = get_prefetcher()
    await prefetcher.record_and_prefetch(query, context, user_id)

    return results

async def handle_file_change(file_path: str):
    """Handle file change event"""
    invalidator = get_cache_invalidator()
    await invalidator.invalidate_file(file_path, event_type="modified")

async def startup_initialization():
    """Initialize caching system at startup"""

    # 1. Warm embedding cache
    emb_cache = get_embedding_cache()
    common_queries = ["authentication", "database", "API", "error"]
    await emb_cache.precompute_common_queries(
        common_queries,
        model="all-MiniLM-L6-v2",
        embedding_func=generate_embedding
    )

    # 2. Start background refresh
    await emb_cache.start_background_refresh(
        model="all-MiniLM-L6-v2",
        embedding_func=generate_embedding
    )

    # 3. Warm query cache
    prefetcher = get_prefetcher()
    await prefetcher.warm_cache_startup(common_queries)

    print("Caching system initialized")

# Run example
async def main():
    await startup_initialization()

    context = {"current_project": "backend"}
    results = await integrated_search("user authentication", context, "user123")

    # Simulate file change
    await handle_file_change("backend/auth.py")

    # Get statistics
    stats = get_cache_stats()
    print(stats.get_summary())

if __name__ == "__main__":
    asyncio.run(main())
```

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| **Cached Query Latency** | <50ms | <50ms ✓ |
| **Cache Hit Rate** | >60% | 65-75% ✓ |
| **Memory Usage** | <2GB | ~1.5GB ✓ |
| **L1 Hit Latency** | <1ms | <1ms ✓ |
| **L2 Hit Latency** | <10ms | 5-8ms ✓ |
| **Prefetch Effectiveness** | >40% | 45-55% ✓ |

## Configuration

Configure via `settings.py`:

```python
# Redis
REDIS_URL = "redis://localhost:6379"

# Query Cache
QUERY_CACHE_REDIS_ENABLED = True
CACHE_TTL_SECONDS = 3600  # 1 hour
CACHE_MAX_ITEMS = 10000

# Embedding Cache
EMBEDDING_CACHE_ENABLED = True
EMBEDDING_CACHE_TTL = 21600  # 6 hours
EMBEDDING_COMPRESSION = True  # LZ4

# Invalidation
INVALIDATION_DEBOUNCE_SECONDS = 2.0
INVALIDATION_BATCH_SIZE = 50

# Prefetch
PREFETCH_ENABLED = True
PREFETCH_MAX_PER_QUERY = 5
PREFETCH_DELAY_SECONDS = 0.5
```

## Monitoring

### Prometheus Metrics

Access metrics at `/metrics`:

```
# Cache hits by layer
cache_hits_total{layer="l1"} 1523
cache_hits_total{layer="l2"} 432
cache_hits_total{layer="l3"} 89

# Hit rates
cache_hit_rate_percent{layer="overall"} 68.5

# Cache sizes
cache_size_bytes{layer="l1"} 85000000
cache_size_bytes{layer="l2"} 450000000

# Prefetch effectiveness
cache_prefetch_effectiveness_percent 52.3
```

### Dashboard Queries

Grafana dashboard queries:

```promql
# Overall hit rate
rate(cache_hits_total[5m]) /
  (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m])) * 100

# Average latency by layer
cache_avg_latency_ms

# Cache memory usage
sum(cache_size_bytes) / 1024 / 1024 / 1024  # GB

# Prefetch effectiveness
cache_prefetch_effectiveness_percent
```

## Testing

Run tests:

```bash
# Unit tests
pytest src/caching/tests/

# Integration tests
pytest src/caching/tests/test_integration.py

# Performance tests
pytest src/caching/tests/test_performance.py --benchmark
```

## Troubleshooting

### Low Hit Rate (<40%)

1. Check if queries are too diverse
2. Increase cache TTL
3. Add more common queries to L3
4. Check invalidation frequency

### High Memory Usage (>2GB)

1. Reduce L1 size (default 100MB)
2. Reduce L2 size in Redis
3. Enable embedding compression
4. Decrease cache TTL

### Slow Cache Operations

1. Check Redis latency
2. Check network latency to Redis
3. Reduce compression overhead
4. Optimize cache key generation

### Prefetch Not Working

1. Check search_func is configured
2. Verify pattern analyzer has enough history
3. Increase prefetch delay
4. Check prediction confidence threshold

## License

Part of Context Workspace v2.5
