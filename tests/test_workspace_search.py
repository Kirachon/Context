"""
Tests for Workspace Search

Comprehensive tests for cross-project semantic search functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.search.workspace_search import (
    WorkspaceSearch,
    SearchScope,
    EnhancedSearchResult,
    ProjectSearchContext,
    SearchMetrics
)
from src.search.filters import SearchFilters
from src.workspace.relationship_graph import ProjectRelationshipGraph, RelationshipType


class TestSearchScope:
    """Test SearchScope enum"""

    def test_search_scope_values(self):
        """Test search scope enum values"""
        assert SearchScope.PROJECT.value == "project"
        assert SearchScope.DEPENDENCIES.value == "dependencies"
        assert SearchScope.WORKSPACE.value == "workspace"
        assert SearchScope.RELATED.value == "related"


class TestEnhancedSearchResult:
    """Test EnhancedSearchResult dataclass"""

    def test_enhanced_search_result_creation(self):
        """Test creating enhanced search result"""
        result = EnhancedSearchResult(
            file_path="/path/to/file.py",
            file_name="file.py",
            file_type="python",
            similarity_score=0.85,
            confidence_score=0.90,
            file_size=1024,
            snippet="def hello():\n    pass",
            metadata={"indexed_time": "2024-01-01T00:00:00Z"},
            project_id="backend",
            project_name="Backend API",
            relationship_context=["frontend", "shared"]
        )

        assert result.project_id == "backend"
        assert result.project_name == "Backend API"
        assert result.relationship_context == ["frontend", "shared"]
        assert result.similarity_score == 0.85

    def test_enhanced_result_defaults(self):
        """Test default values for enhanced fields"""
        result = EnhancedSearchResult(
            file_path="/path/to/file.py",
            file_name="file.py",
            file_type="python",
            similarity_score=0.85,
            confidence_score=0.90,
            file_size=1024
        )

        assert result.project_id == ""
        assert result.project_name == ""
        assert result.relationship_context is None


class TestProjectSearchContext:
    """Test ProjectSearchContext dataclass"""

    def test_project_context_creation(self):
        """Test creating project search context"""
        ctx = ProjectSearchContext(
            project_id="backend",
            project_name="Backend API",
            collection_name="project_backend_vectors",
            priority="high",
            priority_weight=1.2,
            is_target_project=True,
            relationship_distance=0
        )

        assert ctx.project_id == "backend"
        assert ctx.priority == "high"
        assert ctx.is_target_project is True


class TestWorkspaceSearch:
    """Test WorkspaceSearch class"""

    @pytest.fixture
    def workspace_search(self):
        """Create workspace search instance"""
        return WorkspaceSearch()

    @pytest.fixture
    def relationship_graph(self):
        """Create relationship graph with test data"""
        graph = ProjectRelationshipGraph()
        graph.add_project("frontend")
        graph.add_project("backend")
        graph.add_project("shared")

        graph.add_relationship(
            "frontend",
            "backend",
            RelationshipType.API_CLIENT
        )
        graph.add_relationship(
            "frontend",
            "shared",
            RelationshipType.IMPORTS
        )

        return graph

    def test_workspace_search_initialization(self, workspace_search):
        """Test workspace search initialization"""
        assert workspace_search.workspace_manager is None
        assert workspace_search.vector_store is None
        assert workspace_search.relationship_graph is None

        # Check default weights
        assert workspace_search.vector_similarity_weight == 1.0
        assert workspace_search.project_priority_weight == 0.3
        assert workspace_search.relationship_boost_weight == 0.2
        assert workspace_search.recency_boost_weight == 0.1
        assert workspace_search.exact_match_boost_weight == 0.5

    def test_priority_multipliers(self, workspace_search):
        """Test project priority multipliers"""
        assert workspace_search.priority_multipliers["critical"] == 1.5
        assert workspace_search.priority_multipliers["high"] == 1.2
        assert workspace_search.priority_multipliers["normal"] == 1.0
        assert workspace_search.priority_multipliers["low"] == 0.7

    @pytest.mark.asyncio
    async def test_search_requires_project_id_for_project_scope(self, workspace_search):
        """Test that PROJECT scope requires project_id"""
        with pytest.raises(ValueError, match="project_id is required"):
            await workspace_search.search(
                query="test query",
                scope=SearchScope.PROJECT,
                project_id=None
            )

    @pytest.mark.asyncio
    async def test_search_requires_project_id_for_dependencies_scope(self, workspace_search):
        """Test that DEPENDENCIES scope requires project_id"""
        with pytest.raises(ValueError, match="project_id is required"):
            await workspace_search.search(
                query="test query",
                scope=SearchScope.DEPENDENCIES,
                project_id=None
            )

    @pytest.mark.asyncio
    async def test_search_requires_project_id_for_related_scope(self, workspace_search):
        """Test that RELATED scope requires project_id"""
        with pytest.raises(ValueError, match="project_id is required"):
            await workspace_search.search(
                query="test query",
                scope=SearchScope.RELATED,
                project_id=None
            )

    def test_compute_keyword_score(self, workspace_search):
        """Test keyword score computation"""
        # Exact match
        score = workspace_search._compute_keyword_score(
            "authentication login",
            "This file contains authentication and login logic"
        )
        assert score > 0.5

        # Partial match
        score = workspace_search._compute_keyword_score(
            "authentication",
            "This file has auth logic"
        )
        assert score < 1.0

        # No match
        score = workspace_search._compute_keyword_score(
            "authentication",
            "No matching content here"
        )
        assert score == 0.0

        # Empty inputs
        score = workspace_search._compute_keyword_score("", "text")
        assert score == 0.0

        score = workspace_search._compute_keyword_score("text", "")
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_get_project_context_fallback(self, workspace_search):
        """Test getting project context in fallback mode"""
        ctx = await workspace_search._get_project_context("test_project")

        assert ctx.project_id == "default"
        assert ctx.project_name == "Default Project"
        assert ctx.collection_name == "context_vectors"
        assert ctx.priority == "normal"

    @pytest.mark.asyncio
    async def test_search_metrics_tracking(self, workspace_search):
        """Test that search metrics are populated"""
        # Mock embedding generation
        with patch('src.search.workspace_search.generate_embedding') as mock_embed:
            mock_embed.return_value = [0.1] * 384

            # Mock vector search
            with patch('src.vector_db.vector_store.search_vectors') as mock_search:
                mock_search.return_value = []

                results, metrics = await workspace_search.search(
                    query="test query",
                    scope=SearchScope.WORKSPACE,
                    limit=10
                )

                # Check metrics are populated
                assert isinstance(metrics, SearchMetrics)
                assert metrics.total_time_ms > 0
                assert metrics.projects_searched >= 0
                assert metrics.total_results_after_merge == 0

    @pytest.mark.asyncio
    async def test_search_dependencies_without_graph(self, workspace_search):
        """Test dependency search without relationship graph"""
        with patch('src.search.workspace_search.generate_embedding') as mock_embed:
            mock_embed.return_value = [0.1] * 384

            with patch('src.vector_db.vector_store.search_vectors') as mock_search:
                mock_search.return_value = []

                results = await workspace_search.search_dependencies(
                    project_id="test_project",
                    query="test query",
                    include_dependencies=True,
                    limit=10
                )

                # Should only search the target project (no dependencies found)
                assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_dependencies_with_graph(self, relationship_graph):
        """Test dependency search with relationship graph"""
        search = WorkspaceSearch(relationship_graph=relationship_graph)

        with patch('src.search.workspace_search.generate_embedding') as mock_embed:
            mock_embed.return_value = [0.1] * 384

            with patch('src.vector_db.vector_store.search_vectors') as mock_search:
                mock_search.return_value = []

                results = await search.search_dependencies(
                    project_id="frontend",
                    query="test query",
                    include_dependencies=True,
                    limit=10
                )

                # Should search frontend + backend + shared
                assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_related_projects(self, relationship_graph):
        """Test searching related projects"""
        search = WorkspaceSearch(relationship_graph=relationship_graph)

        with patch('src.search.workspace_search.generate_embedding') as mock_embed:
            mock_embed.return_value = [0.1] * 384

            with patch('src.vector_db.vector_store.search_vectors') as mock_search:
                mock_search.return_value = []

                results = await search.search_related(
                    project_id="frontend",
                    query="test query",
                    similarity_threshold=0.7,
                    limit=10
                )

                assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_rank_cross_project_results(self, workspace_search):
        """Test cross-project ranking algorithm"""
        # Create test results
        results = [
            EnhancedSearchResult(
                file_path="/path1/file1.py",
                file_name="file1.py",
                file_type="python",
                similarity_score=0.80,
                confidence_score=0.80,
                file_size=1024,
                metadata={
                    "project_priority": "high",
                    "keyword_score": 0.5,
                    "modified_time": datetime.now(timezone.utc).isoformat()
                },
                project_id="backend",
                project_name="Backend"
            ),
            EnhancedSearchResult(
                file_path="/path2/file2.py",
                file_name="file2.py",
                file_type="python",
                similarity_score=0.85,
                confidence_score=0.85,
                file_size=2048,
                metadata={
                    "project_priority": "normal",
                    "keyword_score": 0.3,
                },
                project_id="frontend",
                project_name="Frontend"
            )
        ]

        ranked = await workspace_search._rank_cross_project_results(
            results,
            query="test query",
            target_project_id="backend"
        )

        # Check that results are sorted by confidence_score
        assert len(ranked) == 2
        assert all(r.confidence_score > 0 for r in ranked)
        assert ranked[0].confidence_score >= ranked[1].confidence_score

    @pytest.mark.asyncio
    async def test_merge_and_rank_deduplicates(self, workspace_search):
        """Test that merge and rank removes duplicates"""
        # Create duplicate results
        results = [
            EnhancedSearchResult(
                file_path="/same/file.py",
                file_name="file.py",
                file_type="python",
                similarity_score=0.80,
                confidence_score=0.80,
                file_size=1024,
                metadata={},
                project_id="project1",
                project_name="Project 1"
            ),
            EnhancedSearchResult(
                file_path="/same/file.py",  # Duplicate
                file_name="file.py",
                file_type="python",
                similarity_score=0.90,  # Higher score
                confidence_score=0.90,
                file_size=1024,
                metadata={},
                project_id="project2",
                project_name="Project 2"
            )
        ]

        merged = await workspace_search._merge_and_rank_results(
            results,
            query="test",
            target_project_id=None,
            limit=10
        )

        # Should keep only the higher-scoring duplicate
        assert len(merged) == 1
        assert merged[0].similarity_score == 0.90

    @pytest.mark.asyncio
    async def test_streaming_search(self, workspace_search):
        """Test streaming search results"""
        with patch('src.search.workspace_search.generate_embedding') as mock_embed:
            mock_embed.return_value = [0.1] * 384

            with patch('src.vector_db.vector_store.search_vectors') as mock_search:
                # Return some mock results
                mock_search.return_value = [
                    {
                        "id": "1",
                        "score": 0.9,
                        "payload": {
                            "file_path": "/test/file1.py",
                            "file_name": "file1.py",
                            "file_type": "python",
                            "size": 1024,
                            "content": "test content"
                        }
                    }
                ]

                count = 0
                async for result in workspace_search.search_streaming(
                    query="test",
                    scope=SearchScope.WORKSPACE,
                    limit=5
                ):
                    count += 1
                    assert isinstance(result, EnhancedSearchResult)

                assert count == 1


class TestSearchMetrics:
    """Test SearchMetrics dataclass"""

    def test_search_metrics_creation(self):
        """Test creating search metrics"""
        metrics = SearchMetrics(
            total_time_ms=123.45,
            projects_searched=3,
            total_results_before_merge=50,
            total_results_after_merge=45,
            deduplicated_count=5,
            projects_searched_list=["frontend", "backend", "shared"],
            embedding_time_ms=10.5,
            search_time_ms=100.0,
            ranking_time_ms=12.95
        )

        assert metrics.total_time_ms == 123.45
        assert metrics.projects_searched == 3
        assert metrics.deduplicated_count == 5
        assert len(metrics.projects_searched_list) == 3


class TestIntegration:
    """Integration tests for workspace search"""

    @pytest.mark.asyncio
    async def test_end_to_end_workspace_search(self):
        """Test complete workspace search flow"""
        # Create relationship graph
        graph = ProjectRelationshipGraph()
        graph.add_project("project1")
        graph.add_project("project2")
        graph.add_relationship("project1", "project2", RelationshipType.IMPORTS)

        # Create workspace search
        search = WorkspaceSearch(relationship_graph=graph)

        # Mock dependencies
        with patch('src.search.workspace_search.generate_embedding') as mock_embed:
            mock_embed.return_value = [0.1] * 384

            with patch('src.vector_db.vector_store.search_vectors') as mock_search:
                mock_search.return_value = []

                # Execute search
                results, metrics = await search.search(
                    query="test query",
                    scope=SearchScope.WORKSPACE,
                    limit=10
                )

                # Verify results
                assert isinstance(results, list)
                assert isinstance(metrics, SearchMetrics)
                assert metrics.total_time_ms > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
