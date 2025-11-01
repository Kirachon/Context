"""
AST Search Service

Advanced search service for AST metadata with semantic search and filtering.
"""

import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from qdrant_client.http import models
import src.vector_db.ast_store as ast_store
from src.vector_db.embeddings import EmbeddingService
from src.vector_db.ast_store import get_ast_vector_store
from src.search.ast_models import (
    ASTSearchRequest,
    ASTSearchResponse,
    ASTSearchResult,
    SymbolType,
    SearchScope,
)

logger = logging.getLogger(__name__)


class ASTSearchService:
    """
    AST Search Service

    Provides advanced semantic search over AST metadata with comprehensive
    filtering by symbol types, languages, and code structure.
    """

    def __init__(self):
        """Initialize AST search service."""
        self.embedding_service = EmbeddingService()
        self.ast_store = get_ast_vector_store()

        self.stats = {
            "searches_performed": 0,
            "total_search_time_ms": 0.0,
            "cache_hits": 0,
            "errors": 0,
        }

        logger.info("ASTSearchService initialized")

    async def search(self, request: ASTSearchRequest) -> ASTSearchResponse:
        """
        Perform advanced AST search.

        Args:
            request: AST search request with query and filters

        Returns:
            ASTSearchResponse with results and metadata
        """
        start_time = time.time()

        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(
                request.query
            )
            if not query_embedding:
                raise ValueError("Failed to generate query embedding")

            # Perform searches based on scope
            results = []
            symbols_found = 0
            classes_found = 0
            imports_found = 0

            if request.search_scope in [SearchScope.ALL, SearchScope.SYMBOLS]:
                symbol_results = await self._search_symbols(query_embedding, request)
                results.extend(symbol_results)
                symbols_found = len(symbol_results)

            if request.search_scope in [SearchScope.ALL, SearchScope.CLASSES]:
                class_results = await self._search_classes(query_embedding, request)
                results.extend(class_results)
                classes_found = len(class_results)

            if request.search_scope in [SearchScope.ALL, SearchScope.IMPORTS]:
                import_results = await self._search_imports(query_embedding, request)
                results.extend(import_results)
                imports_found = len(import_results)

            # Sort by similarity score
            results.sort(key=lambda x: x.similarity_score, reverse=True)

            # Apply limit
            results = results[: request.limit]

            # Calculate search time
            search_time_ms = (time.time() - start_time) * 1000

            # Update statistics
            self.stats["searches_performed"] += 1
            self.stats["total_search_time_ms"] += search_time_ms

            # Build response
            response = ASTSearchResponse(
                query=request.query,
                results=results,
                total_results=len(results),
                search_time_ms=search_time_ms,
                symbols_found=symbols_found,
                classes_found=classes_found,
                imports_found=imports_found,
                filters_applied=self._get_applied_filters(request),
                languages_searched=request.languages or [],
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            logger.info(
                f"AST search completed: {len(results)} results in {search_time_ms:.2f}ms"
            )
            return response

        except Exception as e:
            logger.error(f"AST search failed: {e}", exc_info=True)
            self.stats["errors"] += 1

            # Return empty response on error
            return ASTSearchResponse(
                query=request.query,
                results=[],
                total_results=0,
                search_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    async def _search_symbols(
        self, query_embedding: List[float], request: ASTSearchRequest
    ) -> List[ASTSearchResult]:
        """Search symbols collection."""
        client = ast_store.get_qdrant_client()
        if not client:
            return []

        try:
            # Build search filters
            search_filter = self._build_symbol_filter(request)

            # Perform search
            search_results = client.search(
                collection_name=self.ast_store.symbol_collection,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=request.limit,
                score_threshold=request.min_score,
            )

            # Convert to ASTSearchResult
            results = []
            for result in search_results:
                ast_result = self._convert_symbol_result(result)
                if ast_result:
                    results.append(ast_result)

            return results

        except Exception as e:
            logger.error(f"Symbol search failed: {e}", exc_info=True)
            return []

    async def _search_classes(
        self, query_embedding: List[float], request: ASTSearchRequest
    ) -> List[ASTSearchResult]:
        """Search classes collection."""
        client = ast_store.get_qdrant_client()
        if not client:
            return []

        try:
            # Build search filters
            search_filter = self._build_class_filter(request)

            # Perform search
            search_results = client.search(
                collection_name=self.ast_store.class_collection,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=request.limit,
                score_threshold=request.min_score,
            )

            # Convert to ASTSearchResult
            results = []
            for result in search_results:
                ast_result = self._convert_class_result(result)
                if ast_result:
                    results.append(ast_result)

            return results

        except Exception as e:
            logger.error(f"Class search failed: {e}", exc_info=True)
            return []

    async def _search_imports(
        self, query_embedding: List[float], request: ASTSearchRequest
    ) -> List[ASTSearchResult]:
        """Search imports collection."""
        client = ast_store.get_qdrant_client()
        if not client:
            return []

        try:
            # Build search filters
            search_filter = self._build_import_filter(request)

            # Perform search
            search_results = client.search(
                collection_name=self.ast_store.import_collection,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=request.limit,
                score_threshold=request.min_score,
            )

            # Convert to ASTSearchResult
            results = []
            for result in search_results:
                ast_result = self._convert_import_result(result)
                if ast_result:
                    results.append(ast_result)

            return results

        except Exception as e:
            logger.error(f"Import search failed: {e}", exc_info=True)
            return []

    def _build_symbol_filter(
        self, request: ASTSearchRequest
    ) -> Optional[models.Filter]:
        """Build Qdrant filter for symbol search."""
        conditions = []

        # Language filter
        if request.languages:
            conditions.append(
                models.FieldCondition(
                    key="language", match=models.MatchAny(any=request.languages)
                )
            )

        # Symbol type filter
        if request.symbol_types:
            symbol_type_values = [st.value for st in request.symbol_types]
            conditions.append(
                models.FieldCondition(
                    key="symbol_type", match=models.MatchAny(any=symbol_type_values)
                )
            )

        # Boolean filters
        if request.is_async is not None:
            conditions.append(
                models.FieldCondition(
                    key="is_async", match=models.MatchValue(value=request.is_async)
                )
            )

        if request.is_static is not None:
            conditions.append(
                models.FieldCondition(
                    key="is_static", match=models.MatchValue(value=request.is_static)
                )
            )

        if request.visibility:
            conditions.append(
                models.FieldCondition(
                    key="visibility", match=models.MatchValue(value=request.visibility)
                )
            )

        return models.Filter(must=conditions) if conditions else None

    def _build_class_filter(self, request: ASTSearchRequest) -> Optional[models.Filter]:
        """Build Qdrant filter for class search."""
        conditions = []

        # Language filter
        if request.languages:
            conditions.append(
                models.FieldCondition(
                    key="language", match=models.MatchAny(any=request.languages)
                )
            )

        # Boolean filters
        if request.is_abstract is not None:
            conditions.append(
                models.FieldCondition(
                    key="is_abstract",
                    match=models.MatchValue(value=request.is_abstract),
                )
            )

        return models.Filter(must=conditions) if conditions else None

    def _build_import_filter(
        self, request: ASTSearchRequest
    ) -> Optional[models.Filter]:
        """Build Qdrant filter for import search."""
        conditions = []

        # Language filter
        if request.languages:
            conditions.append(
                models.FieldCondition(
                    key="language", match=models.MatchAny(any=request.languages)
                )
            )

        return models.Filter(must=conditions) if conditions else None

    def _convert_symbol_result(self, result) -> Optional[ASTSearchResult]:
        """Convert Qdrant search result to ASTSearchResult for symbols."""
        try:
            payload = result.payload

            return ASTSearchResult(
                file_path=payload.get("file_path", ""),
                file_name=payload.get("file_path", "").split("/")[-1],
                language=payload.get("language", ""),
                similarity_score=result.score,
                symbol_name=payload.get("symbol_name"),
                symbol_type=SymbolType(payload.get("symbol_type", "function")),
                line_start=payload.get("line_start"),
                line_end=payload.get("line_end"),
                signature=payload.get("signature"),
                docstring=payload.get("docstring"),
                parameters=payload.get("parameters", []),
                return_type=payload.get("return_type"),
                decorators=payload.get("decorators", []),
                visibility=payload.get("visibility"),
                is_static=payload.get("is_static", False),
                is_abstract=payload.get("is_abstract", False),
                is_async=payload.get("is_async", False),
                metadata={"parent_class": payload.get("parent_class")},
            )

        except Exception as e:
            logger.warning(f"Failed to convert symbol result: {e}")
            return None

    def _convert_class_result(self, result) -> Optional[ASTSearchResult]:
        """Convert Qdrant search result to ASTSearchResult for classes."""
        try:
            payload = result.payload

            return ASTSearchResult(
                file_path=payload.get("file_path", ""),
                file_name=payload.get("file_path", "").split("/")[-1],
                language=payload.get("language", ""),
                similarity_score=result.score,
                symbol_name=payload.get("class_name"),
                symbol_type=(
                    SymbolType.INTERFACE
                    if payload.get("is_interface")
                    else SymbolType.CLASS
                ),
                line_start=payload.get("line_start"),
                line_end=payload.get("line_end"),
                docstring=payload.get("docstring"),
                base_classes=payload.get("base_classes", []),
                interfaces=payload.get("interfaces", []),
                decorators=payload.get("decorators", []),
                visibility=payload.get("visibility"),
                is_abstract=payload.get("is_abstract", False),
                metadata={
                    "methods": payload.get("methods", []),
                    "fields": payload.get("fields", []),
                    "generic_params": payload.get("generic_params", []),
                },
            )

        except Exception as e:
            logger.warning(f"Failed to convert class result: {e}")
            return None

    def _convert_import_result(self, result) -> Optional[ASTSearchResult]:
        """Convert Qdrant search result to ASTSearchResult for imports."""
        try:
            payload = result.payload

            return ASTSearchResult(
                file_path=payload.get("file_path", ""),
                file_name=payload.get("file_path", "").split("/")[-1],
                language=payload.get("language", ""),
                similarity_score=result.score,
                symbol_name=payload.get("module"),
                symbol_type=SymbolType.VARIABLE,  # Use variable for imports
                line_start=payload.get("line"),
                line_end=payload.get("line"),
                metadata={
                    "import_type": payload.get("import_type"),
                    "alias": payload.get("alias"),
                    "items": payload.get("items", []),
                    "is_wildcard": payload.get("is_wildcard", False),
                },
            )

        except Exception as e:
            logger.warning(f"Failed to convert import result: {e}")
            return None

    def _get_applied_filters(self, request: ASTSearchRequest) -> Dict[str, Any]:
        """Get dictionary of applied filters for response."""
        filters = {}

        if request.symbol_types:
            filters["symbol_types"] = [st.value for st in request.symbol_types]
        if request.languages:
            filters["languages"] = request.languages
        if request.file_types:
            filters["file_types"] = request.file_types
        if request.directories:
            filters["directories"] = request.directories
        if request.exclude_patterns:
            filters["exclude_patterns"] = request.exclude_patterns
        if request.min_score > 0:
            filters["min_score"] = request.min_score
        if request.search_scope != SearchScope.ALL:
            filters["search_scope"] = request.search_scope.value

        # Boolean filters
        if request.has_parameters is not None:
            filters["has_parameters"] = request.has_parameters
        if request.has_return_type is not None:
            filters["has_return_type"] = request.has_return_type
        if request.is_async is not None:
            filters["is_async"] = request.is_async
        if request.is_static is not None:
            filters["is_static"] = request.is_static
        if request.is_abstract is not None:
            filters["is_abstract"] = request.is_abstract
        if request.visibility:
            filters["visibility"] = request.visibility
        if request.has_inheritance is not None:
            filters["has_inheritance"] = request.has_inheritance
        if request.implements_interface is not None:
            filters["implements_interface"] = request.implements_interface

        return filters

    def get_stats(self) -> Dict[str, Any]:
        """Get AST search service statistics."""
        avg_search_time = 0.0
        if self.stats["searches_performed"] > 0:
            avg_search_time = (
                self.stats["total_search_time_ms"] / self.stats["searches_performed"]
            )

        return {
            "searches_performed": self.stats["searches_performed"],
            "average_search_time_ms": avg_search_time,
            "cache_hits": self.stats["cache_hits"],
            "errors": self.stats["errors"],
        }


# Global AST search service instance
_global_ast_search: Optional[ASTSearchService] = None


def get_ast_search_service() -> ASTSearchService:
    """Get the global AST search service instance."""
    global _global_ast_search
    if _global_ast_search is None:
        _global_ast_search = ASTSearchService()
    return _global_ast_search
