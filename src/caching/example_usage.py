"""
Example Usage of Smart Caching System

Demonstrates complete integration of all caching components.
"""

import asyncio
import random
import time
from typing import List, Dict, Any

# Import caching components
from src.caching import (
    get_query_cache,
    get_embedding_cache,
    get_cache_invalidator,
    get_prefetcher,
    get_cache_stats,
)


# Mock functions (replace with actual implementations)
async def mock_generate_embedding(text: str) -> List[float]:
    """Mock embedding generation"""
    await asyncio.sleep(0.05)  # Simulate API call
    # Generate fake embedding
    return [random.random() for _ in range(384)]


async def mock_search(query: str, context: Dict[str, Any] = None) -> List[Dict]:
    """Mock search execution"""
    await asyncio.sleep(0.1)  # Simulate search latency
    # Return mock results
    return [
        {
            "file": f"file_{i}.py",
            "content": f"Content related to {query}",
            "score": random.random(),
        }
        for i in range(10)
    ]


async def demo_basic_caching():
    """Demonstrate basic cache operations"""
    print("\n=== Demo 1: Basic Cache Operations ===\n")

    cache = get_query_cache()
    stats = get_cache_stats()

    query = "user authentication"
    context = {"current_project": "backend", "recent_files": ["auth.py"]}

    # First request - cache miss
    print(f"Query: '{query}'")
    start = time.time()
    results = await cache.get(query, context)
    if results is None:
        print("❌ Cache MISS - executing search...")
        results = await mock_search(query, context)
        await cache.set(
            query, results, context, accessed_files=["backend/auth.py", "models/user.py"]
        )
    latency = (time.time() - start) * 1000
    print(f"✓ First request: {latency:.2f}ms (cache miss)\n")

    # Second request - cache hit
    start = time.time()
    results = await cache.get(query, context)
    latency = (time.time() - start) * 1000
    print(f"✓ Second request: {latency:.2f}ms (cache hit from L1)")
    print(f"  Results: {len(results)} items\n")

    # Show stats
    summary = stats.get_summary()
    print(f"Cache Stats:")
    print(f"  L1 Hit Rate: {summary['l1']['hit_rate_percent']}%")
    print(f"  L1 Items: {summary['l1']['item_count']}")
    print(f"  L1 Size: {summary['l1']['size_bytes'] / 1024:.2f} KB")


async def demo_embedding_cache():
    """Demonstrate embedding cache with compression"""
    print("\n=== Demo 2: Embedding Cache with Compression ===\n")

    emb_cache = get_embedding_cache()

    queries = ["authentication", "database query", "error handling", "API endpoint"]

    print("Pre-computing embeddings for common queries...")
    await emb_cache.precompute_common_queries(
        queries, model="all-MiniLM-L6-v2", embedding_func=mock_generate_embedding
    )

    # Test cache hits
    print("\nTesting cache hits:")
    for query in queries[:2]:
        start = time.time()
        embedding = await emb_cache.get(query, model="all-MiniLM-L6-v2")
        latency = (time.time() - start) * 1000

        if embedding:
            print(
                f"✓ '{query}': {latency:.2f}ms (cached, {len(embedding)} dimensions)"
            )
        else:
            print(f"❌ '{query}': Not cached")

    # Get statistics
    emb_stats = emb_cache.get_statistics()
    print(f"\nEmbedding Cache Stats:")
    print(f"  Compression: {emb_stats['compression_enabled']}")
    print(f"  Cached embeddings: {emb_stats.get('cached_embeddings_count', 'N/A')}")


async def demo_invalidation():
    """Demonstrate smart cache invalidation"""
    print("\n=== Demo 3: Smart Cache Invalidation ===\n")

    cache = get_query_cache()
    invalidator = get_cache_invalidator()

    # Cache multiple queries
    queries = [
        ("find auth logic", {"current_project": "backend"}),
        ("search user model", {"current_project": "backend"}),
        ("api endpoints", {"current_project": "backend"}),
    ]

    print("Caching queries...")
    for query, context in queries:
        results = await mock_search(query, context)
        await cache.set(
            query, results, context, accessed_files=["backend/auth.py", "models/user.py"]
        )
        print(f"  ✓ Cached: '{query}'")

    # Simulate file change
    print("\n🔄 File changed: backend/auth.py")
    await invalidator.invalidate_file("backend/auth.py", event_type="modified")

    # Wait for debouncing
    await asyncio.sleep(2.5)

    # Check cache
    print("\nChecking cache after invalidation:")
    for query, context in queries:
        results = await cache.get(query, context)
        status = "❌ Invalidated" if results is None else "✓ Still cached"
        print(f"  {status}: '{query}'")

    # Get invalidation stats
    inv_stats = invalidator.get_statistics()
    print(f"\nInvalidation Stats:")
    print(f"  Tracked files: {inv_stats['tracked_files']}")
    print(f"  Tracked queries: {inv_stats['tracked_queries']}")


async def demo_predictive_prefetch():
    """Demonstrate predictive pre-fetching"""
    print("\n=== Demo 4: Predictive Pre-fetching ===\n")

    prefetcher = get_prefetcher()
    prefetcher.search_func = mock_search

    # Simulate query sequence
    query_sequence = [
        ("user login", {"current_project": "auth"}),
        ("authentication flow", {"current_project": "auth"}),
        ("password validation", {"current_project": "auth"}),
        ("user login", {"current_project": "auth"}),  # Repeat
        ("authentication flow", {"current_project": "auth"}),  # Repeat
    ]

    print("Recording query sequence for pattern learning...")
    for i, (query, context) in enumerate(query_sequence, 1):
        print(f"  {i}. '{query}'")
        await prefetcher.record_and_prefetch(query, context, user_id="user123")
        await asyncio.sleep(0.2)

    # Test prediction
    print("\n🔮 Predicting next queries after 'user login':")
    predictions = prefetcher.pattern_analyzer.predict_next_queries(
        "user login", {"current_project": "auth"}, top_k=3
    )

    for predicted_query, probability in predictions:
        print(f"  • '{predicted_query}' (probability: {probability:.2f})")

    # Get pattern stats
    pattern_stats = prefetcher.get_pattern_statistics()
    print(f"\nPattern Analysis Stats:")
    print(f"  Query history: {pattern_stats['query_history_size']}")
    print(f"  Markov states: {pattern_stats['markov_states']}")
    print(f"  Bigrams: {pattern_stats['bigrams']}")
    print(f"  Trigrams: {pattern_stats['trigrams']}")


async def demo_complete_integration():
    """Demonstrate complete integration"""
    print("\n=== Demo 5: Complete Integration ===\n")

    cache = get_query_cache()
    emb_cache = get_embedding_cache()
    prefetcher = get_prefetcher()
    stats = get_cache_stats()

    prefetcher.search_func = mock_search

    # Integrated search function
    async def integrated_search(query: str, context: dict, user_id: str):
        """Search with full caching integration"""
        start_time = time.time()

        # 1. Try query cache
        results = await cache.get(query, context)
        if results is not None:
            latency = (time.time() - start_time) * 1000
            print(f"  ⚡ Cache hit: {latency:.2f}ms")
            await prefetcher.record_and_prefetch(query, context, user_id)
            return results, latency

        # 2. Try embedding cache
        embedding = await emb_cache.get(query, model="all-MiniLM-L6-v2")
        if embedding is None:
            embedding = await mock_generate_embedding(query)
            await emb_cache.set(query, embedding, model="all-MiniLM-L6-v2")

        # 3. Execute search
        results = await mock_search(query, context)

        # 4. Cache results
        await cache.set(query, results, context, accessed_files=["file1.py", "file2.py"])

        # 5. Record for prefetch
        await prefetcher.record_and_prefetch(query, context, user_id)

        latency = (time.time() - start_time) * 1000
        print(f"  🔍 Cache miss: {latency:.2f}ms")
        return results, latency

    # Execute searches
    queries = [
        "user authentication",
        "database connection",
        "API endpoints",
        "user authentication",  # Cached hit
        "error handling",
    ]

    print("Executing integrated searches:\n")
    latencies = []
    for query in queries:
        print(f"Query: '{query}'")
        results, latency = await integrated_search(
            query, {"current_project": "backend"}, "user123"
        )
        latencies.append(latency)
        await asyncio.sleep(0.1)

    # Summary
    print(f"\n📊 Performance Summary:")
    print(f"  Queries: {len(queries)}")
    print(f"  Avg latency: {sum(latencies) / len(latencies):.2f}ms")
    print(f"  Min latency: {min(latencies):.2f}ms")
    print(f"  Max latency: {max(latencies):.2f}ms")

    # Cache statistics
    summary = stats.get_summary()
    print(f"\n📈 Cache Statistics:")
    print(f"  Overall hit rate: {summary['overall']['hit_rate_percent']}%")
    print(f"  L1 hit rate: {summary['l1']['hit_rate_percent']}%")
    print(f"  L2 hit rate: {summary['l2']['hit_rate_percent']}%")
    print(f"  Prefetch effectiveness: {summary['overall']['prefetch_effectiveness_percent']}%")


async def demo_prometheus_export():
    """Demonstrate Prometheus metrics export"""
    print("\n=== Demo 6: Prometheus Metrics Export ===\n")

    stats = get_cache_stats()

    # Generate some activity first
    cache = get_query_cache()
    for i in range(10):
        query = f"test query {i % 3}"  # Create some cache hits
        results = await cache.get(query)
        if results is None:
            results = await mock_search(query)
            await cache.set(query, results)

    # Export metrics
    print("Prometheus metrics:\n")
    metrics = stats.export_prometheus()
    print(metrics[:800] + "\n..." if len(metrics) > 800 else metrics)


async def main():
    """Run all demos"""
    print("=" * 60)
    print("Smart Caching System - Example Usage")
    print("=" * 60)

    try:
        await demo_basic_caching()
        await asyncio.sleep(1)

        await demo_embedding_cache()
        await asyncio.sleep(1)

        await demo_invalidation()
        await asyncio.sleep(1)

        await demo_predictive_prefetch()
        await asyncio.sleep(1)

        await demo_complete_integration()
        await asyncio.sleep(1)

        await demo_prometheus_export()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
