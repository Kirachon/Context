"""
Cross-Project Semantic Search

Workspace-aware search system that provides semantic search across multiple projects
with relationship-aware ranking and intelligent result merging.
"""

import asyncio
import logging
import time
import re
from enum import Enum
from typing import List, Optional, Dict, Any, AsyncGenerator, Tuple, Set
from datetime import datetime, timezone
from dataclasses import dataclass, field

from src.search.models import SearchResult as BaseSearchResult
from src.search.filters import SearchFilters, apply_filters
from src.vector_db.embeddings import generate_embedding

logger = logging.getLogger(__name__)


class SearchScope(Enum):
    """Search scope modes for workspace-aware search"""

    PROJECT = "project"  # Search within one project only
    DEPENDENCIES = "dependencies"  # Search project + its dependencies
    WORKSPACE = "workspace"  # Search all projects in workspace
    RELATED = "related"  # Search semantically related projects


@dataclass
class EnhancedSearchResult(BaseSearchResult):
    """
    Enhanced search result with project-awareness

    Extends base SearchResult with project identification and relationship context
    """

    project_id: str = ""
    project_name: str = ""
    relationship_context: Optional[List[str]] = None

    class Config:
        arbitrary_types_allowed = True


@dataclass
class ProjectSearchContext:
    """Context information for a project during search operations"""

    project_id: str
    project_name: str
    collection_name: str
    priority: str = "normal"  # critical, high, normal, low
    priority_weight: float = 1.0
    is_target_project: bool = False
    relationship_distance: int = 0  # 0 = target, 1 = direct dependency, 2 = transitive


@dataclass
class SearchMetrics:
    """Metrics collected during workspace search"""

    total_time_ms: float = 0.0
    projects_searched: int = 0
    total_results_before_merge: int = 0
    total_results_after_merge: int = 0
    deduplicated_count: int = 0
    projects_searched_list: List[str] = field(default_factory=list)
    embedding_time_ms: float = 0.0
    search_time_ms: float = 0.0
    ranking_time_ms: float = 0.0


class WorkspaceSearch:
    """
    Workspace-aware semantic search system

    Provides cross-project search with relationship-aware ranking, intelligent
    result merging, and multiple search scope modes.
    """

    def __init__(
        self,
        workspace_manager=None,
        vector_store=None,
        relationship_graph=None
    ):
        """
        Initialize workspace search

        Args:
            workspace_manager: WorkspaceManager instance (optional, for multi-project mode)
            vector_store: VectorStore instance (for single-project fallback)
            relationship_graph: ProjectRelationshipGraph instance (optional)
        """
        self.workspace_manager = workspace_manager
        self.vector_store = vector_store
        self.relationship_graph = relationship_graph

        # Ranking configuration
        self.vector_similarity_weight = 1.0
        self.project_priority_weight = 0.3
        self.relationship_boost_weight = 0.2
        self.recency_boost_weight = 0.1
        self.exact_match_boost_weight = 0.5

        # Project priority mappings
        self.priority_multipliers = {
            "critical": 1.5,
            "high": 1.2,
            "normal": 1.0,
            "low": 0.7
        }

        # Performance settings
        self.early_termination_threshold = 0.95  # Stop if we have high-scoring results
        self.parallel_search_enabled = True
        self.max_concurrent_searches = 10

        logger.info("WorkspaceSearch initialized")

    async def search(
        self,
        query: str,
        scope: SearchScope = SearchScope.WORKSPACE,
        project_id: Optional[str] = None,
        include_dependencies: bool = True,
        limit: int = 50,
        filters: Optional[SearchFilters] = None,
        similarity_threshold: float = 0.7
    ) -> Tuple[List[EnhancedSearchResult], SearchMetrics]:
        """
        Unified search interface with multiple scope modes

        Args:
            query: Natural language search query
            scope: Search scope mode
            project_id: Target project ID (required for PROJECT, DEPENDENCIES, RELATED scopes)
            include_dependencies: Include dependencies in search (for DEPENDENCIES scope)
            limit: Maximum number of results to return
            filters: Optional search filters
            similarity_threshold: Minimum similarity for RELATED scope

        Returns:
            Tuple of (search results, metrics)
        """
        start_time = time.time()
        metrics = SearchMetrics()

        logger.info(f"Starting workspace search: query='{query}', scope={scope.value}, project={project_id}")

        try:
            # Validate scope-specific requirements
            if scope in [SearchScope.PROJECT, SearchScope.DEPENDENCIES, SearchScope.RELATED]:
                if not project_id:
                    raise ValueError(f"project_id is required for scope={scope.value}")

            # Route to appropriate search method
            if scope == SearchScope.PROJECT:
                results = await self.search_project(project_id, query, limit, filters)
                metrics.projects_searched = 1
                metrics.projects_searched_list = [project_id]

            elif scope == SearchScope.DEPENDENCIES:
                results = await self.search_dependencies(
                    project_id, query, include_dependencies, limit, filters
                )

            elif scope == SearchScope.WORKSPACE:
                results = await self.search_workspace(query, limit, filters)

            elif scope == SearchScope.RELATED:
                results = await self.search_related(
                    project_id, query, similarity_threshold, limit, filters
                )

            else:
                raise ValueError(f"Unsupported search scope: {scope}")

            metrics.total_time_ms = (time.time() - start_time) * 1000
            metrics.total_results_after_merge = len(results)

            logger.info(
                f"Workspace search completed: {len(results)} results in {metrics.total_time_ms:.2f}ms "
                f"(searched {metrics.projects_searched} projects)"
            )

            return results, metrics

        except Exception as e:
            logger.error(f"Error during workspace search: {e}", exc_info=True)
            raise

    async def search_project(
        self,
        project_id: str,
        query: str,
        limit: int = 50,
        filters: Optional[SearchFilters] = None
    ) -> List[EnhancedSearchResult]:
        """
        Search within a single project only

        Args:
            project_id: Project ID to search
            query: Search query
            limit: Maximum results
            filters: Optional filters

        Returns:
            List of enhanced search results
        """
        logger.debug(f"Searching project: {project_id}")

        # Generate embedding
        query_embedding = await generate_embedding(query)
        if not query_embedding:
            logger.error("Failed to generate query embedding")
            return []

        # Get project context
        project_context = await self._get_project_context(project_id)

        # Search project collection
        results = await self._search_project_collection(
            project_context,
            query_embedding,
            query,
            limit * 2,  # Get more for filtering
            filters
        )

        # Apply filters if provided
        if filters:
            results = self._apply_filters_to_enhanced_results(results, filters)

        # Limit results
        return results[:limit]

    async def search_dependencies(
        self,
        project_id: str,
        query: str,
        include_dependencies: bool = True,
        limit: int = 50,
        filters: Optional[SearchFilters] = None
    ) -> List[EnhancedSearchResult]:
        """
        Search project and its dependencies

        Args:
            project_id: Target project ID
            query: Search query
            include_dependencies: Whether to include dependencies (if False, same as search_project)
            limit: Maximum results
            filters: Optional filters

        Returns:
            List of enhanced search results with relationship context
        """
        logger.debug(f"Searching project {project_id} with dependencies")

        # Build list of projects to search
        projects_to_search = [project_id]

        if include_dependencies and self.relationship_graph:
            dependencies = self.relationship_graph.get_dependencies(project_id)
            projects_to_search.extend(dependencies)
            logger.debug(f"Including {len(dependencies)} dependencies: {dependencies}")

        # Generate embedding once
        query_embedding = await generate_embedding(query)
        if not query_embedding:
            logger.error("Failed to generate query embedding")
            return []

        # Search all projects in parallel
        results = await self._parallel_search_projects(
            projects_to_search,
            query_embedding,
            query,
            limit,
            filters,
            target_project_id=project_id
        )

        return results

    async def search_workspace(
        self,
        query: str,
        limit: int = 50,
        filters: Optional[SearchFilters] = None
    ) -> List[EnhancedSearchResult]:
        """
        Search across all projects in workspace

        Args:
            query: Search query
            limit: Maximum results
            filters: Optional filters

        Returns:
            List of enhanced search results from all projects
        """
        logger.debug("Searching entire workspace")

        # Get all projects in workspace
        if self.workspace_manager:
            all_projects = list(self.workspace_manager.projects.keys())
        else:
            # Fallback: single project mode
            all_projects = ["default"]

        logger.debug(f"Searching {len(all_projects)} projects in workspace")

        # Generate embedding once
        query_embedding = await generate_embedding(query)
        if not query_embedding:
            logger.error("Failed to generate query embedding")
            return []

        # Search all projects in parallel
        results = await self._parallel_search_projects(
            all_projects,
            query_embedding,
            query,
            limit,
            filters
        )

        return results

    async def search_related(
        self,
        project_id: str,
        query: str,
        similarity_threshold: float = 0.7,
        limit: int = 50,
        filters: Optional[SearchFilters] = None
    ) -> List[EnhancedSearchResult]:
        """
        Search semantically related projects

        Args:
            project_id: Target project ID
            query: Search query
            similarity_threshold: Minimum project similarity score (0-1)
            limit: Maximum results
            filters: Optional filters

        Returns:
            List of enhanced search results from related projects
        """
        logger.debug(f"Searching projects related to {project_id} (threshold={similarity_threshold})")

        # Get related projects
        related_projects = [project_id]  # Always include target project

        if self.relationship_graph:
            related = await self.relationship_graph.get_related_projects(
                project_id, threshold=similarity_threshold
            )
            related_project_ids = [proj_id for proj_id, score in related]
            related_projects.extend(related_project_ids)
            logger.debug(f"Found {len(related_project_ids)} related projects: {related_project_ids}")

        # Generate embedding once
        query_embedding = await generate_embedding(query)
        if not query_embedding:
            logger.error("Failed to generate query embedding")
            return []

        # Search related projects
        results = await self._parallel_search_projects(
            related_projects,
            query_embedding,
            query,
            limit,
            filters,
            target_project_id=project_id
        )

        return results

    async def search_streaming(
        self,
        query: str,
        scope: SearchScope = SearchScope.WORKSPACE,
        project_id: Optional[str] = None,
        limit: int = 50
    ) -> AsyncGenerator[EnhancedSearchResult, None]:
        """
        Stream search results as they become available

        Useful for large result sets or real-time UI updates

        Args:
            query: Search query
            scope: Search scope
            project_id: Target project (if applicable)
            limit: Maximum results

        Yields:
            Enhanced search results one at a time
        """
        logger.debug(f"Starting streaming search: scope={scope.value}")

        # Perform regular search
        results, _ = await self.search(query, scope, project_id, limit=limit)

        # Stream results
        for result in results:
            yield result

    async def _parallel_search_projects(
        self,
        project_ids: List[str],
        query_embedding: List[float],
        query: str,
        limit: int,
        filters: Optional[SearchFilters] = None,
        target_project_id: Optional[str] = None
    ) -> List[EnhancedSearchResult]:
        """
        Search multiple projects in parallel and merge results

        Args:
            project_ids: List of project IDs to search
            query_embedding: Pre-generated query embedding
            query: Original query string
            limit: Maximum results to return
            filters: Optional search filters
            target_project_id: Target project ID (for relationship boosting)

        Returns:
            Merged and ranked search results
        """
        start_time = time.time()

        # Get project contexts
        project_contexts = await asyncio.gather(
            *[self._get_project_context(pid) for pid in project_ids],
            return_exceptions=True
        )

        # Filter out errors
        valid_contexts = [
            ctx for ctx in project_contexts
            if not isinstance(ctx, Exception)
        ]

        if not valid_contexts:
            logger.warning("No valid project contexts found")
            return []

        # Mark target project
        if target_project_id:
            for ctx in valid_contexts:
                ctx.is_target_project = (ctx.project_id == target_project_id)

        # Search all projects in parallel (with concurrency limit)
        semaphore = asyncio.Semaphore(self.max_concurrent_searches)

        async def search_with_semaphore(ctx):
            async with semaphore:
                return await self._search_project_collection(
                    ctx, query_embedding, query, limit, filters
                )

        all_results_nested = await asyncio.gather(
            *[search_with_semaphore(ctx) for ctx in valid_contexts],
            return_exceptions=True
        )

        # Flatten results
        all_results = []
        for results in all_results_nested:
            if isinstance(results, Exception):
                logger.error(f"Search error: {results}")
                continue
            all_results.extend(results)

        logger.debug(f"Parallel search completed: {len(all_results)} total results from {len(valid_contexts)} projects")

        # Merge and rank results
        merged_results = await self._merge_and_rank_results(
            all_results,
            query,
            target_project_id,
            limit
        )

        search_time_ms = (time.time() - start_time) * 1000
        logger.debug(f"Merge and rank completed in {search_time_ms:.2f}ms")

        return merged_results

    async def _search_project_collection(
        self,
        project_context: ProjectSearchContext,
        query_embedding: List[float],
        query: str,
        limit: int,
        filters: Optional[SearchFilters]
    ) -> List[EnhancedSearchResult]:
        """
        Search a single project's vector collection

        Args:
            project_context: Project context information
            query_embedding: Query vector
            query: Original query string
            limit: Maximum results
            filters: Optional filters

        Returns:
            List of search results for this project
        """
        try:
            # Import here to avoid circular dependency
            from src.vector_db.vector_store import search_vectors

            # Search the project's collection
            vector_results = await search_vectors(
                query_vector=query_embedding,
                limit=limit,
                collection_name=project_context.collection_name
            )

            if not vector_results:
                return []

            # Convert to enhanced search results
            enhanced_results = []

            for vector_result in vector_results:
                try:
                    payload = vector_result.get("payload", {})
                    file_path = payload.get("file_path")

                    if not file_path:
                        continue

                    # Extract code snippet (simplified)
                    snippet = payload.get("content", "")[:500]  # First 500 chars

                    # Compute keyword score for exact match boost
                    keyword_score = self._compute_keyword_score(query, snippet)

                    # Create enhanced result
                    result = EnhancedSearchResult(
                        file_path=file_path,
                        file_name=payload.get("file_name", ""),
                        file_type=payload.get("file_type", "unknown"),
                        similarity_score=vector_result.get("score", 0.0),
                        confidence_score=vector_result.get("score", 0.0),  # Will be recalculated
                        file_size=payload.get("size", 0),
                        snippet=snippet,
                        metadata={
                            "indexed_time": payload.get("indexed_time"),
                            "modified_time": payload.get("modified_time"),
                            "vector_id": vector_result.get("id"),
                            "keyword_score": keyword_score,
                            "project_priority": project_context.priority
                        },
                        project_id=project_context.project_id,
                        project_name=project_context.project_name,
                        relationship_context=None  # Will be populated during ranking
                    )

                    enhanced_results.append(result)

                except Exception as e:
                    logger.error(f"Error converting vector result: {e}")
                    continue

            logger.debug(f"Project {project_context.project_id}: {len(enhanced_results)} results")
            return enhanced_results

        except Exception as e:
            logger.error(f"Error searching project {project_context.project_id}: {e}")
            return []

    async def _merge_and_rank_results(
        self,
        results: List[EnhancedSearchResult],
        query: str,
        target_project_id: Optional[str],
        limit: int
    ) -> List[EnhancedSearchResult]:
        """
        Merge results from multiple projects and apply cross-project ranking

        Args:
            results: All results from all projects
            query: Original query
            target_project_id: Target project for relationship boosting
            limit: Maximum results to return

        Returns:
            Merged, deduplicated, and ranked results
        """
        if not results:
            return []

        # Deduplicate by file path (keep highest scoring)
        dedup_map: Dict[str, EnhancedSearchResult] = {}

        for result in results:
            key = result.file_path
            if key not in dedup_map or result.similarity_score > dedup_map[key].similarity_score:
                dedup_map[key] = result

        deduplicated_results = list(dedup_map.values())
        logger.debug(f"Deduplicated: {len(results)} -> {len(deduplicated_results)} results")

        # Apply cross-project ranking
        ranked_results = await self._rank_cross_project_results(
            deduplicated_results,
            query,
            target_project_id
        )

        # Return top N
        return ranked_results[:limit]

    async def _rank_cross_project_results(
        self,
        results: List[EnhancedSearchResult],
        query: str,
        target_project_id: Optional[str]
    ) -> List[EnhancedSearchResult]:
        """
        Re-rank results considering cross-project factors

        Ranking formula:
        final_score = (
            vector_similarity * 1.0 +
            project_priority_weight * 0.3 +
            relationship_boost * 0.2 +
            recency_boost * 0.1 +
            exact_match_boost * 0.5
        )

        Args:
            results: Results to rank
            query: Original query
            target_project_id: Target project for relationship boosting

        Returns:
            Ranked results
        """
        for result in results:
            # Base score: vector similarity
            vector_score = result.similarity_score * self.vector_similarity_weight

            # Project priority boost
            priority = result.metadata.get("project_priority", "normal")
            priority_multiplier = self.priority_multipliers.get(priority, 1.0)
            priority_score = (priority_multiplier - 1.0) * self.project_priority_weight

            # Relationship boost (if from target project or related)
            relationship_score = 0.0
            if target_project_id and self.relationship_graph:
                if result.project_id == target_project_id:
                    # Target project itself gets max boost
                    relationship_score = 1.0 * self.relationship_boost_weight
                else:
                    # Check if related to target project
                    is_related = self.relationship_graph.has_relationship(
                        target_project_id, result.project_id
                    )
                    if is_related:
                        relationship_score = 0.5 * self.relationship_boost_weight
                        # Add relationship context
                        if not result.relationship_context:
                            result.relationship_context = []
                        result.relationship_context.append(target_project_id)

            # Recency boost (prefer recently modified files)
            recency_score = 0.0
            modified_time = result.metadata.get("modified_time")
            if modified_time:
                try:
                    modified_dt = datetime.fromisoformat(modified_time.replace("Z", "+00:00"))
                    age_days = (datetime.now(timezone.utc) - modified_dt).days
                    # Linear decay: 1.0 for today, 0.0 for 30+ days old
                    recency_factor = max(0.0, 1.0 - (age_days / 30.0))
                    recency_score = recency_factor * self.recency_boost_weight
                except Exception:
                    pass

            # Exact match boost (keyword matching)
            keyword_score = result.metadata.get("keyword_score", 0.0)
            exact_match_score = keyword_score * self.exact_match_boost_weight

            # Calculate final score
            final_score = (
                vector_score +
                priority_score +
                relationship_score +
                recency_score +
                exact_match_score
            )

            # Update confidence score with final ranking score
            result.confidence_score = min(1.0, final_score)

        # Sort by confidence score
        ranked_results = sorted(results, key=lambda r: r.confidence_score, reverse=True)

        logger.debug(f"Ranked {len(ranked_results)} results with cross-project factors")
        return ranked_results

    async def _get_project_context(self, project_id: str) -> ProjectSearchContext:
        """
        Get project context information

        Args:
            project_id: Project ID

        Returns:
            Project context
        """
        if self.workspace_manager:
            project = self.workspace_manager.get_project(project_id)

            return ProjectSearchContext(
                project_id=project.id,
                project_name=project.name,
                collection_name=f"project_{project.id}_vectors",
                priority=project.config.indexing.get("priority", "normal"),
                priority_weight=self.priority_multipliers.get(
                    project.config.indexing.get("priority", "normal"),
                    1.0
                )
            )
        else:
            # Fallback for single-project mode
            return ProjectSearchContext(
                project_id="default",
                project_name="Default Project",
                collection_name="context_vectors",  # Default collection name
                priority="normal",
                priority_weight=1.0
            )

    def _compute_keyword_score(self, query: str, text: Optional[str]) -> float:
        """
        Compute simple keyword match score between query and text

        Args:
            query: Search query
            text: Text to match against

        Returns:
            Keyword score (0-1)
        """
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

    def _apply_filters_to_enhanced_results(
        self,
        results: List[EnhancedSearchResult],
        filters: SearchFilters
    ) -> List[EnhancedSearchResult]:
        """
        Apply search filters to enhanced results

        Args:
            results: Enhanced search results
            filters: Filters to apply

        Returns:
            Filtered results
        """
        # Convert enhanced results to base results for filtering
        base_results = [
            BaseSearchResult(
                file_path=r.file_path,
                file_name=r.file_name,
                file_type=r.file_type,
                similarity_score=r.similarity_score,
                confidence_score=r.confidence_score,
                file_size=r.file_size,
                snippet=r.snippet,
                line_numbers=r.line_numbers,
                metadata=r.metadata
            )
            for r in results
        ]

        # Apply filters
        filtered_base = apply_filters(base_results, filters)

        # Map back to enhanced results
        filtered_paths = {r.file_path for r in filtered_base}
        filtered_enhanced = [r for r in results if r.file_path in filtered_paths]

        return filtered_enhanced


# Global workspace search instance (will be initialized by workspace manager)
_workspace_search: Optional[WorkspaceSearch] = None


def get_workspace_search() -> WorkspaceSearch:
    """
    Get global workspace search instance

    Returns:
        WorkspaceSearch instance
    """
    global _workspace_search

    if _workspace_search is None:
        # Initialize with fallback mode (single-project)
        _workspace_search = WorkspaceSearch()

    return _workspace_search


def initialize_workspace_search(
    workspace_manager=None,
    vector_store=None,
    relationship_graph=None
):
    """
    Initialize global workspace search with dependencies

    Args:
        workspace_manager: WorkspaceManager instance
        vector_store: VectorStore instance
        relationship_graph: ProjectRelationshipGraph instance
    """
    global _workspace_search

    _workspace_search = WorkspaceSearch(
        workspace_manager=workspace_manager,
        vector_store=vector_store,
        relationship_graph=relationship_graph
    )

    logger.info("Workspace search initialized with workspace manager")
