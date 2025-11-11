"""
Predictive Pre-fetcher with Pattern Analysis

Features:
- Analyze user query patterns
- Predict likely next query using Markov chains
- Pre-fetch and cache results in background
- Usage pattern analysis (sequence mining)
- Context-aware predictions
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple, Set, Any, Callable
from collections import defaultdict, deque
from dataclasses import dataclass, field
import threading

logger = logging.getLogger(__name__)


@dataclass
class QueryPattern:
    """Represents a query pattern"""

    query: str
    timestamp: float
    context: Optional[Dict[str, Any]] = None
    next_queries: List[str] = field(default_factory=list)


@dataclass
class MarkovState:
    """Markov chain state for query prediction"""

    current_query: str
    next_queries: Dict[str, float]  # query -> probability
    transition_count: int = 0


class PatternAnalyzer:
    """
    Analyzes user query patterns using Markov chains and sequence mining

    Tracks:
    - Query sequences (what follows what)
    - Temporal patterns (queries at specific times)
    - Context patterns (queries in specific contexts)
    - User-specific patterns
    """

    def __init__(self, history_size: int = 1000, min_confidence: float = 0.1):
        """
        Initialize pattern analyzer

        Args:
            history_size: Maximum query history to maintain
            min_confidence: Minimum confidence for predictions
        """
        self.history_size = history_size
        self.min_confidence = min_confidence

        # Query history (recent queries)
        self._query_history: deque = deque(maxlen=history_size)
        self._history_lock = threading.Lock()

        # Markov chain: query -> next queries with counts
        self._transitions: Dict[str, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )

        # Context-based patterns
        self._context_patterns: Dict[str, List[str]] = defaultdict(list)

        # Frequent sequences (2-gram, 3-gram)
        self._bigrams: Dict[Tuple[str, str], int] = defaultdict(int)
        self._trigrams: Dict[Tuple[str, str, str], int] = defaultdict(int)

        logger.info("Pattern analyzer initialized")

    def record_query(
        self, query: str, context: Optional[Dict[str, Any]] = None, user_id: str = None
    ):
        """
        Record a query for pattern analysis

        Args:
            query: Search query
            context: Query context
            user_id: User ID
        """
        with self._history_lock:
            pattern = QueryPattern(
                query=query, timestamp=time.time(), context=context
            )

            # Add to history
            self._query_history.append(pattern)

            # Update Markov chain
            if len(self._query_history) >= 2:
                prev_query = self._query_history[-2].query
                self._transitions[prev_query][query] += 1

                # Update bigram
                self._bigrams[(prev_query, query)] += 1

            # Update trigram
            if len(self._query_history) >= 3:
                query1 = self._query_history[-3].query
                query2 = self._query_history[-2].query
                self._trigrams[(query1, query2, query)] += 1

            # Update context patterns
            if context and "current_project" in context:
                project = context["current_project"]
                self._context_patterns[project].append(query)

    def predict_next_queries(
        self,
        current_query: str,
        context: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """
        Predict likely next queries

        Args:
            current_query: Current query
            context: Current context
            top_k: Number of predictions to return

        Returns:
            List of (query, probability) tuples
        """
        predictions: Dict[str, float] = defaultdict(float)

        # Markov chain predictions
        if current_query in self._transitions:
            next_queries = self._transitions[current_query]
            total_count = sum(next_queries.values())

            for next_query, count in next_queries.items():
                probability = count / total_count
                if probability >= self.min_confidence:
                    predictions[next_query] += probability * 0.6  # 60% weight

        # Context-based predictions
        if context and "current_project" in context:
            project = context["current_project"]
            if project in self._context_patterns:
                # Find similar patterns
                similar = self._find_similar_queries(
                    current_query, self._context_patterns[project]
                )
                for similar_query in similar[:3]:
                    predictions[similar_query] += 0.2  # 20% weight

        # Trigram predictions (if we have recent context)
        with self._history_lock:
            if len(self._query_history) >= 1:
                prev_query = self._query_history[-1].query
                trigram_key = (prev_query, current_query)

                # Find trigrams starting with these two queries
                for (q1, q2, q3), count in self._trigrams.items():
                    if (q1, q2) == trigram_key:
                        predictions[q3] += 0.2  # 20% weight

        # Sort by probability
        sorted_predictions = sorted(
            predictions.items(), key=lambda x: x[1], reverse=True
        )

        return sorted_predictions[:top_k]

    def _find_similar_queries(
        self, query: str, candidate_queries: List[str], top_k: int = 5
    ) -> List[str]:
        """
        Find queries similar to the given query

        Args:
            query: Query to match
            candidate_queries: List of candidate queries
            top_k: Number of similar queries to return

        Returns:
            List of similar queries
        """
        # Simple word-based similarity
        query_words = set(query.lower().split())

        similarities = []
        for candidate in candidate_queries:
            candidate_words = set(candidate.lower().split())
            # Jaccard similarity
            intersection = len(query_words & candidate_words)
            union = len(query_words | candidate_words)
            similarity = intersection / union if union > 0 else 0.0
            if similarity > 0:
                similarities.append((candidate, similarity))

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        return [q for q, _ in similarities[:top_k]]

    def get_frequent_sequences(self, min_count: int = 3) -> List[Tuple[Tuple, int]]:
        """
        Get frequent query sequences

        Args:
            min_count: Minimum occurrence count

        Returns:
            List of (sequence, count) tuples
        """
        frequent = []

        # Bigrams
        for bigram, count in self._bigrams.items():
            if count >= min_count:
                frequent.append((bigram, count))

        # Trigrams
        for trigram, count in self._trigrams.items():
            if count >= min_count:
                frequent.append((trigram, count))

        # Sort by count
        frequent.sort(key=lambda x: x[1], reverse=True)
        return frequent

    def get_statistics(self) -> Dict[str, Any]:
        """Get pattern analysis statistics"""
        return {
            "query_history_size": len(self._query_history),
            "markov_states": len(self._transitions),
            "bigrams": len(self._bigrams),
            "trigrams": len(self._trigrams),
            "context_patterns": len(self._context_patterns),
        }


class PredictivePrefetcher:
    """
    Predictive pre-fetching system with pattern analysis

    Predicts likely next queries and pre-fetches results in background
    """

    def __init__(
        self,
        query_cache=None,
        search_func: Optional[Callable] = None,
        max_prefetch_per_query: int = 5,
        prefetch_delay: float = 0.5,
        stats=None,
    ):
        """
        Initialize prefetcher

        Args:
            query_cache: QueryCache instance
            search_func: Async function to execute searches
            max_prefetch_per_query: Max queries to prefetch
            prefetch_delay: Delay before prefetching (seconds)
            stats: CacheStats instance
        """
        self.query_cache = query_cache
        self.search_func = search_func
        self.max_prefetch_per_query = max_prefetch_per_query
        self.prefetch_delay = prefetch_delay

        # Pattern analyzer
        self.pattern_analyzer = PatternAnalyzer()

        # Stats
        from .stats import get_cache_stats

        self.stats = stats or get_cache_stats()

        # Active prefetch tasks
        self._prefetch_tasks: Set[asyncio.Task] = set()
        self._task_lock = threading.Lock()

        logger.info("Predictive prefetcher initialized")

    def get_query_cache(self):
        """Lazy load query cache"""
        if self.query_cache is None:
            from .query_cache import get_query_cache

            self.query_cache = get_query_cache()
        return self.query_cache

    async def record_and_prefetch(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ):
        """
        Record query and trigger predictive prefetch

        Args:
            query: Search query
            context: Search context
            user_id: User ID
        """
        # Record query for pattern analysis
        self.pattern_analyzer.record_query(query, context, user_id)

        # Trigger prefetch (after delay)
        asyncio.create_task(self._delayed_prefetch(query, context))

    async def _delayed_prefetch(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ):
        """
        Prefetch after delay (to avoid interfering with current query)

        Args:
            query: Current query
            context: Current context
        """
        await asyncio.sleep(self.prefetch_delay)
        await self.prefetch(query, context)

    async def prefetch(
        self, current_query: str, context: Optional[Dict[str, Any]] = None
    ):
        """
        Predict and prefetch likely next queries

        Args:
            current_query: Current query
            context: Current context
        """
        # Predict next queries
        predictions = self.pattern_analyzer.predict_next_queries(
            current_query, context, top_k=self.max_prefetch_per_query
        )

        if not predictions:
            logger.debug("No predictions for prefetch")
            return

        logger.debug(
            f"Prefetching {len(predictions)} predicted queries after '{current_query}'"
        )

        # Prefetch in background
        for predicted_query, probability in predictions:
            # Check if already cached
            query_cache = self.get_query_cache()
            cached = await query_cache.get(predicted_query, context)

            if cached is not None:
                # Already cached, record as prefetch hit
                self.stats.record_prefetch(hit=True)
                continue

            # Prefetch
            task = asyncio.create_task(
                self._prefetch_query(predicted_query, context, probability)
            )

            with self._task_lock:
                self._prefetch_tasks.add(task)
                task.add_done_callback(self._prefetch_tasks.discard)

    async def _prefetch_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]],
        probability: float,
    ):
        """
        Prefetch a single query

        Args:
            query: Query to prefetch
            context: Search context
            probability: Prediction probability
        """
        if self.search_func is None:
            logger.warning("No search function configured for prefetch")
            return

        try:
            logger.debug(
                f"Prefetching: '{query}' (probability: {probability:.2f})"
            )

            # Execute search
            results = await self.search_func(query, context)

            # Cache results
            query_cache = self.get_query_cache()
            await query_cache.set(query, results, context)

            # Record prefetch
            self.stats.record_prefetch(hit=False)

            logger.debug(
                f"Prefetch complete: '{query}' ({len(results)} results)"
            )

        except Exception as e:
            logger.warning(f"Prefetch failed for '{query}': {e}")

    async def warm_cache_startup(
        self,
        common_queries: List[str],
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Warm cache with common queries at startup

        Args:
            common_queries: List of common queries to precompute
            context: Default context
        """
        if self.search_func is None:
            logger.warning("No search function configured for cache warming")
            return

        logger.info(f"Warming cache with {len(common_queries)} common queries")

        query_cache = self.get_query_cache()

        for query in common_queries:
            # Check if already cached
            cached = await query_cache.get(query, context)
            if cached is not None:
                continue

            try:
                # Execute search
                results = await self.search_func(query, context)

                # Cache with longer TTL (24 hours for pre-computed)
                await query_cache.precompute_query(query, results, ttl=86400)

                logger.debug(f"Warmed cache: '{query}' ({len(results)} results)")

                # Rate limiting
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.warning(f"Failed to warm cache for '{query}': {e}")

        logger.info("Cache warming complete")

    def get_active_prefetch_count(self) -> int:
        """Get number of active prefetch tasks"""
        with self._task_lock:
            return len(self._prefetch_tasks)

    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get pattern analysis statistics"""
        return self.pattern_analyzer.get_statistics()

    def get_frequent_patterns(self, min_count: int = 3) -> List:
        """Get frequent query patterns"""
        return self.pattern_analyzer.get_frequent_sequences(min_count)

    def get_statistics(self) -> Dict[str, Any]:
        """Get prefetcher statistics"""
        return {
            "max_prefetch_per_query": self.max_prefetch_per_query,
            "prefetch_delay": self.prefetch_delay,
            "active_prefetch_tasks": self.get_active_prefetch_count(),
            "pattern_analysis": self.get_pattern_statistics(),
        }


# Global prefetcher instance
_prefetcher: Optional[PredictivePrefetcher] = None
_prefetcher_lock = threading.Lock()


def get_prefetcher() -> PredictivePrefetcher:
    """Get global prefetcher instance"""
    global _prefetcher
    if _prefetcher is None:
        with _prefetcher_lock:
            if _prefetcher is None:
                _prefetcher = PredictivePrefetcher()
    return _prefetcher
