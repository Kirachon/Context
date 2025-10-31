"""
Unit tests for Semantic Search

Tests search service, ranking, and filtering functionality.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock, mock_open
from datetime import datetime

# Add project root to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.search.semantic_search import SemanticSearchService
from src.search.models import SearchRequest, SearchResult
from src.search.filters import SearchFilters, apply_filters
from src.search.ranking import RankingService


class TestSemanticSearchService:
    """Test semantic search service"""
    
    @pytest.fixture
    def search_service(self):
        """Create search service instance"""
        return SemanticSearchService()
    
    @pytest.mark.asyncio
    @patch('src.search.semantic_search.generate_embedding')
    @patch('src.search.semantic_search.search_vectors')
    async def test_search_success(self, mock_search_vectors, mock_generate_embedding, search_service):
        """Test successful search"""
        # Mock embedding generation
        mock_generate_embedding.return_value = [0.1, 0.2, 0.3]
        
        # Mock vector search results
        mock_search_vectors.return_value = [
            {
                "id": "file1.py",
                "score": 0.95,
                "payload": {
                    "file_path": "/test/file1.py",
                    "file_name": "file1.py",
                    "file_type": "python",
                    "size": 1024,
                    "indexed_time": datetime.utcnow().isoformat()
                }
            }
        ]
        
        # Mock file reading
        with patch('builtins.open', mock_open(read_data="print('hello')")):
            with patch('os.path.exists', return_value=True):
                request = SearchRequest(query="test query", limit=10)
                response = await search_service.search(request)
        
        assert response.query == "test query"
        assert len(response.results) == 1
        assert response.results[0].file_path == "/test/file1.py"
        assert response.results[0].similarity_score == 0.95
        assert response.search_time_ms > 0
    
    @pytest.mark.asyncio
    @patch('src.search.semantic_search.generate_embedding')
    async def test_search_no_embedding(self, mock_generate_embedding, search_service):
        """Test search with embedding generation failure"""
        mock_generate_embedding.return_value = None
        
        request = SearchRequest(query="test query", limit=10)
        
        with pytest.raises(ValueError, match="Failed to generate embedding"):
            await search_service.search(request)
    
    @pytest.mark.asyncio
    @patch('src.search.semantic_search.generate_embedding')
    @patch('src.search.semantic_search.search_vectors')
    async def test_search_empty_results(self, mock_search_vectors, mock_generate_embedding, search_service):
        """Test search with no results"""
        mock_generate_embedding.return_value = [0.1, 0.2, 0.3]
        mock_search_vectors.return_value = []
        
        request = SearchRequest(query="test query", limit=10)
        response = await search_service.search(request)
        
        assert response.total_results == 0
        assert len(response.results) == 0
    
    @pytest.mark.asyncio
    @patch('src.search.semantic_search.generate_embedding')
    @patch('src.search.semantic_search.search_vectors')
    async def test_search_caching(self, mock_search_vectors, mock_generate_embedding, search_service):
        """Test search result caching"""
        mock_generate_embedding.return_value = [0.1, 0.2, 0.3]
        mock_search_vectors.return_value = []
        
        request = SearchRequest(query="cached query", limit=10)
        
        # First search
        response1 = await search_service.search(request)
        
        # Second search (should be cached)
        response2 = await search_service.search(request)
        
        # Embedding should only be generated once
        assert mock_generate_embedding.call_count == 1
        assert search_service.stats["cache_hits"] == 1
    
    def test_get_stats(self, search_service):
        """Test getting search statistics"""
        stats = search_service.get_stats()
        
        assert stats.total_searches >= 0
        assert 0.0 <= stats.cache_hit_rate <= 1.0
        assert 0.0 <= stats.error_rate <= 1.0
        assert isinstance(stats.popular_queries, list)


class TestSearchFilters:
    """Test search filtering"""
    
    def test_filter_by_file_types(self):
        """Test filtering by file types"""
        results = [
            SearchResult(
                file_path="/test/file1.py",
                file_name="file1.py",
                file_type="python",
                similarity_score=0.9,
                confidence_score=0.9,
                file_size=1024
            ),
            SearchResult(
                file_path="/test/file2.js",
                file_name="file2.js",
                file_type="javascript",
                similarity_score=0.8,
                confidence_score=0.8,
                file_size=2048
            )
        ]
        
        filters = SearchFilters(file_types=[".py"])
        filtered = apply_filters(results, filters)
        
        assert len(filtered) == 1
        assert filtered[0].file_path == "/test/file1.py"
    
    def test_filter_by_directories(self):
        """Test filtering by directories"""
        results = [
            SearchResult(
                file_path="/src/module/file1.py",
                file_name="file1.py",
                file_type="python",
                similarity_score=0.9,
                confidence_score=0.9,
                file_size=1024
            ),
            SearchResult(
                file_path="/tests/test_file.py",
                file_name="test_file.py",
                file_type="python",
                similarity_score=0.8,
                confidence_score=0.8,
                file_size=2048
            )
        ]
        
        filters = SearchFilters(directories=["src"])
        filtered = apply_filters(results, filters)
        
        assert len(filtered) == 1
        assert "src" in filtered[0].file_path
    
    def test_filter_by_exclude_patterns(self):
        """Test filtering by exclude patterns"""
        results = [
            SearchResult(
                file_path="/src/file1.py",
                file_name="file1.py",
                file_type="python",
                similarity_score=0.9,
                confidence_score=0.9,
                file_size=1024
            ),
            SearchResult(
                file_path="/tests/test_file.py",
                file_name="test_file.py",
                file_type="python",
                similarity_score=0.8,
                confidence_score=0.8,
                file_size=2048
            )
        ]
        
        filters = SearchFilters(exclude_patterns=["test"])
        filtered = apply_filters(results, filters)
        
        assert len(filtered) == 1
        assert "test" not in filtered[0].file_path.lower()
    
    def test_filter_by_min_score(self):
        """Test filtering by minimum score"""
        results = [
            SearchResult(
                file_path="/test/file1.py",
                file_name="file1.py",
                file_type="python",
                similarity_score=0.9,
                confidence_score=0.9,
                file_size=1024
            ),
            SearchResult(
                file_path="/test/file2.py",
                file_name="file2.py",
                file_type="python",
                similarity_score=0.5,
                confidence_score=0.5,
                file_size=2048
            )
        ]
        
        filters = SearchFilters(min_score=0.7)
        filtered = apply_filters(results, filters)
        
        assert len(filtered) == 1
        assert filtered[0].similarity_score >= 0.7


class TestRankingService:
    """Test ranking service"""
    
    @pytest.fixture
    def ranking_service(self):
        """Create ranking service instance"""
        return RankingService()
    
    def test_rank_results(self, ranking_service):
        """Test result ranking"""
        results = [
            SearchResult(
                file_path="/test/file1.py",
                file_name="file1.py",
                file_type="python",
                similarity_score=0.8,
                confidence_score=0.0,
                file_size=5000,
                metadata={"indexed_time": datetime.utcnow().isoformat()}
            ),
            SearchResult(
                file_path="/test/file2.py",
                file_name="file2.py",
                file_type="python",
                similarity_score=0.9,
                confidence_score=0.0,
                file_size=10000,
                metadata={"indexed_time": datetime.utcnow().isoformat()}
            )
        ]
        
        ranked = ranking_service.rank_results(results)
        
        assert len(ranked) == 2
        # Higher similarity should rank higher
        assert ranked[0].similarity_score >= ranked[1].similarity_score
    
    def test_calculate_confidence_score(self, ranking_service):
        """Test confidence score calculation"""
        score = ranking_service.calculate_confidence_score(0.9, 10000)
        
        assert 0.0 <= score <= 1.0
    
    def test_deduplicate_results(self, ranking_service):
        """Test result deduplication"""
        results = [
            SearchResult(
                file_path="/test/file1.py",
                file_name="file1.py",
                file_type="python",
                similarity_score=0.9,
                confidence_score=0.9,
                file_size=1024
            ),
            SearchResult(
                file_path="/test/file1.py",  # Duplicate
                file_name="file1.py",
                file_type="python",
                similarity_score=0.8,
                confidence_score=0.8,
                file_size=1024
            )
        ]
        
        ranked = ranking_service.rank_results(results)
        
        assert len(ranked) == 1  # Duplicate removed


class TestSearchModels:
    """Test search models"""
    
    def test_search_request_validation(self):
        """Test search request validation"""
        # Valid request
        request = SearchRequest(query="test", limit=10)
        assert request.query == "test"
        assert request.limit == 10
        
        # Invalid limit (too high)
        with pytest.raises(Exception):
            SearchRequest(query="test", limit=200)
        
        # Invalid query (too short)
        with pytest.raises(Exception):
            SearchRequest(query="", limit=10)
    
    def test_search_result_model(self):
        """Test search result model"""
        result = SearchResult(
            file_path="/test/file.py",
            file_name="file.py",
            file_type="python",
            similarity_score=0.95,
            confidence_score=0.90,
            file_size=1024
        )
        
        assert result.file_path == "/test/file.py"
        assert 0.0 <= result.similarity_score <= 1.0
        assert 0.0 <= result.confidence_score <= 1.0

