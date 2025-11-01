"""
Semantic Search Service

Core semantic search functionality using vector embeddings.
"""

import asyncio
from src.logging.manager import get_logger
import os
import sys
import time
import re
from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.search.models import SearchRequest, SearchResponse, SearchResult, SearchStats
from src.search.filters import SearchFilters, apply_filters
from src.search.ranking import RankingService, get_ranking_service
from src.vector_db.embeddings import generate_embedding
from src.vector_db.vector_store import search_vectors
from src.search.query_cache import get_query_cache
from src.analytics.usage import usage
from src.monitoring.metrics import metrics
# Lazy import inside search() to avoid heavy dependencies during import time
# from src.indexing.models import get_file_metadata

logger = get_logger(__name__)


class SemanticSearchService:
    """
    Semantic Search Service

    Provides natural language search capabilities for code using vector embeddings.
    """

    def __init__(self):
        """Initialize semantic search service"""
        self.ranking_service = get_ranking_service()
        self.cache: Dict[str, SearchResponse] = {}
        self.cache_ttl = 300  # 5 minutes
        self.stats = {
            "total_searches": 0,
            "total_results": 0,
            "cache_hits": 0,
            "errors": 0,
            "response_times": [],
            "popular_queries": {}
        }

        logger.info("SemanticSearchService initialized")

    def _get_cache_key(self, request: SearchRequest) -> str:
        """Generate cache key for search request"""
        request_str = f"{request.query}|{request.limit}|{request.file_types}|{request.directories}|{request.exclude_patterns}|{request.min_score}"
        return hashlib.md5(request_str.encode()).hexdigest()

    def _is_cache_valid(self, cached_response: SearchResponse) -> bool:
        """Check if cached response is still valid"""
        try:
            cached_time = datetime.fromisoformat(cached_response.timestamp)
            current_time = datetime.utcnow()
            age_seconds = (current_time - cached_time).total_seconds()
            return age_seconds < self.cache_ttl
        except Exception:
            return False

    async def _extract_code_snippet(self, file_path: str, max_lines: int = 10) -> Optional[str]:
        """
        Extract code snippet from file

        Args:
            file_path: Path to file
            max_lines: Maximum lines to include

        Returns:
            Code snippet or None if error
        """
        try:
            if not os.path.exists(file_path):
                return None

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # Take first max_lines or all lines if fewer
            snippet_lines = lines[:max_lines]
            snippet = ''.join(snippet_lines)

            # Add ellipsis if truncated
            if len(lines) > max_lines:
                snippet += "\n... (truncated)"

            return snippet.strip()

        except Exception as e:
            logger.error(f"Error extracting snippet from {file_path}: {e}")
            return None
    def _compute_keyword_score(self, query: str, text: Optional[str]) -> float:
        """Compute simple keyword match score between query and text (0-1)."""
        if not query or not text:
            return 0.0
        # Tokenize on non-alphanumeric, lowercase, length >= 3
        def tokenize(s: str) -> set:
            tokens = re.split(r"[^a-zA-Z0-9_]+", s.lower())
            return {t for t in tokens if len(t) >= 3}
        q_tokens = tokenize(query)
        t_tokens = tokenize(text)
        if not q_tokens or not t_tokens:
            return 0.0
        overlap = q_tokens.intersection(t_tokens)
        # Jaccard-like score weighted towards query coverage
        return min(1.0, len(overlap) / max(1, len(q_tokens)))


    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Perform semantic search

        Args:
            request: Search request

        Returns:
            Search response with results
        """
        start_time = time.time()

        try:
            logger.info(f"Performing semantic search: '{request.query}'")
            usage().incr("semantic_search_requests")
            c_req = metrics.counter("search_requests_total", "Search requests", ("status",))
            c_cache = metrics.counter("search_cache_hits_total", "Search cache hits")
            h_req = metrics.histogram("search_request_seconds", "Search latency")

            # Build filters for cache keying
            applied_filters = self._get_applied_filters(request)

            # Global query cache (shared across workers) behind feature flag
            use_global_cache = False
            try:
                from src.config.settings import settings as _settings
                use_global_cache = bool(getattr(_settings, "query_cache_redis_enabled", False))
            except Exception:
                use_global_cache = False
            qc = get_query_cache() if use_global_cache else None
            cached_payload = qc.get(request.query, applied_filters) if qc else None
            if cached_payload:
                try:
                    # Rehydrate SearchResponse from cached dict
                    cached_response = SearchResponse(**cached_payload)
                    self.stats["cache_hits"] += 1
                    usage().incr("semantic_search_cache_hits")
                    try:
                        c_cache.labels().inc() if hasattr(c_cache, "labels") else c_cache.inc()  # type: ignore
                        h_req.labels().observe(time.time() - start_time)
                        c_req.labels("hit").inc()
                    except Exception:
                        pass
                    logger.debug("Returning cached search results (global cache)")
                    return cached_response
                except Exception:
                    pass

            # Local in-process cache (legacy)
            cache_key = self._get_cache_key(request)
            if cache_key in self.cache:
                cached_response = self.cache[cache_key]
                if self._is_cache_valid(cached_response):
                    self.stats["cache_hits"] += 1
                    usage().incr("semantic_search_cache_hits")
                    try:
                        c_cache.labels().inc() if hasattr(c_cache, "labels") else c_cache.inc()  # type: ignore
                        h_req.labels().observe(time.time() - start_time)
                        c_req.labels("hit").inc()
                    except Exception:
                        pass
                    logger.debug("Returning cached search results (local cache)")
                    return cached_response
                else:
                    # Remove expired cache entry
                    del self.cache[cache_key]

            # Generate embedding for query
            query_embedding = await generate_embedding(request.query)

            if not query_embedding:
                raise ValueError("Failed to generate embedding for query")

            # Search vectors
            vector_results = await search_vectors(
                query_vector=query_embedding,
                limit=request.limit * 2  # Get more results for filtering
            )

            if not vector_results:
                # Return empty results
                try:
                    h_req.labels().observe(time.time() - start_time)
                    c_req.labels("ok").inc()
                except Exception:
                    pass
                response = SearchResponse(
                    query=request.query,
                    results=[],
                    total_results=0,
                    search_time_ms=(time.time() - start_time) * 1000,
                    filters_applied=applied_filters,
                    timestamp=datetime.utcnow().isoformat()
                )

                # Cache empty results too
                if qc:
                    try:
                        qc.set(request.query, response.model_dump(), applied_filters)
                    except Exception:
                        pass
                self.cache[cache_key] = response
                return response

            # Convert vector results to search results
            search_results = []

            for vector_result in vector_results:
                try:
                    payload = vector_result["payload"]
                    file_path = payload.get("file_path")

                    if not file_path:
                        continue

                    # Extract code snippet
                    snippet = await self._extract_code_snippet(file_path)

                    # Compute keyword score (hybrid component)
                    keyword_source = f"{payload.get('file_name', os.path.basename(file_path))} {snippet or ''}"
                    keyword_score = self._compute_keyword_score(request.query, keyword_source)

                    # Attempt to enrich metadata with file modified_time
                    modified_time_iso = None
                    try:
                        # Lazy import to avoid heavy dependency at module import time
                        from src.indexing.models import get_file_metadata  # type: ignore
                        file_meta = await get_file_metadata(file_path)
                        if file_meta and getattr(file_meta, 'modified_time', None):
                            modified_time_iso = file_meta.modified_time.isoformat()
                    except Exception:
                        modified_time_iso = None

                    # Create search result
                    search_result = SearchResult(
                        file_path=file_path,
                        file_name=payload.get("file_name", os.path.basename(file_path)),
                        file_type=payload.get("file_type", "unknown"),
                        similarity_score=vector_result["score"],
                        confidence_score=self.ranking_service.calculate_confidence_score(
                            vector_result["score"],
                            payload.get("size", 0)
                        ),
                        file_size=payload.get("size", 0),
                        snippet=snippet,
                        metadata={
                            "indexed_time": payload.get("indexed_time"),
                            "modified_time": modified_time_iso,
                            "vector_id": vector_result["id"],
                            "author": payload.get("author"),
                            "keyword_score": keyword_score
                        }
                    )

                    search_results.append(search_result)

                except Exception as e:
                    logger.error(f"Error processing vector result: {e}")
                    continue

            # Apply filters (including advanced filters)
            filtered_results = apply_filters(search_results, SearchFilters(
                file_types=request.file_types,
                directories=request.directories,
                exclude_patterns=request.exclude_patterns,
                min_score=request.min_score,
                authors=getattr(request, 'authors', None),
                modified_after=getattr(request, 'modified_after', None),
                modified_before=getattr(request, 'modified_before', None)
            ))

            # Rank and limit results
            ranked_results = self.ranking_service.rank_results(filtered_results)
            final_results = ranked_results[:request.limit]

            # Create response
            search_time_ms = (time.time() - start_time) * 1000

            response = SearchResponse(
                query=request.query,
                results=final_results,
                total_results=len(filtered_results),
                search_time_ms=search_time_ms,
                filters_applied=applied_filters,
                timestamp=datetime.utcnow().isoformat()
            )

            # Cache response (global + local)
            if qc:
                try:
                    qc.set(request.query, response.model_dump(), applied_filters)
                except Exception:
                    pass
            self.cache[cache_key] = response

            # Update stats
            self.stats["total_searches"] += 1
            self.stats["total_results"] += len(final_results)
            self.stats["response_times"].append(search_time_ms)
            try:
                h_req.labels().observe(time.time() - start_time)
                c_req.labels("ok").inc()
            except Exception:
                pass

            # Track popular queries
            query_lower = request.query.lower()
            self.stats["popular_queries"][query_lower] = self.stats["popular_queries"].get(query_lower, 0) + 1

            logger.info(f"Search completed: {len(final_results)} results in {search_time_ms:.2f}ms")
            return response

        except Exception as e:
            self.stats["errors"] += 1
            try:
                h_req.labels().observe(time.time() - start_time)
                c_req.labels("error").inc()
            except Exception:
                pass
            logger.error(f"Error during semantic search: {e}", exc_info=True)
            raise

    def _get_applied_filters(self, request: SearchRequest) -> Dict[str, Any]:
        """Get dictionary of applied filters"""
        filters = {}

        if request.file_types:
            filters["file_types"] = request.file_types
        if request.directories:
            filters["directories"] = request.directories
        if request.exclude_patterns:
            filters["exclude_patterns"] = request.exclude_patterns
        if request.min_score > 0.0:
            filters["min_score"] = request.min_score
        # Advanced filters (Story 2.4)
        if getattr(request, "authors", None):
            filters["authors"] = request.authors
        if getattr(request, "modified_after", None):
            filters["modified_after"] = request.modified_after
        if getattr(request, "modified_before", None):
            filters["modified_before"] = request.modified_before

        return filters

    def get_stats(self) -> SearchStats:
        """
        Get search statistics

        Returns:
            Search statistics
        """
        # Calculate averages
        avg_response_time = 0.0
        if self.stats["response_times"]:
            avg_response_time = sum(self.stats["response_times"]) / len(self.stats["response_times"])

        # Calculate cache hit rate
        cache_hit_rate = 0.0
        if self.stats["total_searches"] > 0:
            cache_hit_rate = self.stats["cache_hits"] / self.stats["total_searches"]

        # Calculate error rate
        error_rate = 0.0
        total_requests = self.stats["total_searches"] + self.stats["errors"]
        if total_requests > 0:
            error_rate = self.stats["errors"] / total_requests

        # Get popular queries (top 10)
        popular_queries = sorted(
            self.stats["popular_queries"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        popular_queries = [query for query, count in popular_queries]

        return SearchStats(
            total_searches=self.stats["total_searches"],
            average_response_time_ms=avg_response_time,
            cache_hit_rate=cache_hit_rate,
            popular_queries=popular_queries,
            error_rate=error_rate,
            timestamp=datetime.utcnow().isoformat()
        )

    def clear_cache(self):
        """Clear search cache"""
        self.cache.clear()
        logger.info("Search cache cleared")


# Global search service instance
search_service = SemanticSearchService()


async def search_code(request: SearchRequest) -> SearchResponse:
    """Search code (entry point for integration)"""
    return await search_service.search(request)


def get_search_service() -> SemanticSearchService:
    """Get search service instance"""
    return search_service


def get_search_stats() -> SearchStats:
    """Get search statistics (entry point for status endpoints)"""
    return search_service.get_stats()
