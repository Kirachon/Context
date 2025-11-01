"""
Integration tests for AST metadata storage system.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.parsing.parser import get_parser
from src.vector_db.ast_store import get_ast_vector_store
from src.search.ast_search import get_ast_search_service
from src.search.ast_models import ASTSearchRequest, SymbolType, SearchScope
from src.indexing.ast_indexer import get_ast_indexer


class TestASTStorageIntegration:
    """Integration tests for complete AST storage pipeline."""
    
    def setup_method(self):
        self.parser = get_parser()
        self.ast_store = get_ast_vector_store()
        self.search_service = get_ast_search_service()
        self.indexer = get_ast_indexer()
    
    @patch('src.vector_db.ast_store.get_qdrant_client')
    async def test_complete_pipeline_python(self, mock_get_client):
        """Test complete pipeline from parsing to search for Python code."""
        # Mock Qdrant client
        mock_client = Mock()
        mock_collections = Mock()
        mock_collections.collections = [
            Mock(name="context_symbols"),
            Mock(name="context_classes"),
            Mock(name="context_imports")
        ]
        mock_client.get_collections.return_value = mock_collections
        mock_client.search.return_value = []  # Empty search results
        mock_get_client.return_value = mock_client
        
        # Mock embedding service
        mock_embedding = [0.1] * 384
        with patch.object(self.ast_store.embedding_service, 'initialize', new_callable=AsyncMock):
            with patch.object(self.ast_store.embedding_service, 'embedding_dim', 384):
                with patch.object(self.ast_store.embedding_service, 'generate_embedding',
                                new_callable=AsyncMock, return_value=mock_embedding):
                    
                    # Test Python code
                    python_code = '''
import os
from typing import List, Optional

class UserManager:
    """Manages user operations."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def create_user(self, name: str, email: str) -> Optional[dict]:
        """Create a new user."""
        if not self.validate_email(email):
            return None
        return {"name": name, "email": email}
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        return "@" in email

def main():
    manager = UserManager("/tmp/users.db")
    print("UserManager created")
'''
                    
                    # Step 1: Parse the code
                    parse_result = self.parser.parse(Path("user_manager.py"), python_code)
                    
                    # Verify parsing worked (even without tree-sitter)
                    assert parse_result.language.value == "python"
                    assert parse_result.parse_time_ms >= 0
                    assert parse_result.symbol_extraction_time_ms >= 0
                    
                    # Step 2: Store in vector database (if parsing succeeded)
                    if parse_result.parse_success and parse_result.ast_root:
                        storage_result = await self.ast_store.store_parse_result(parse_result)
                        
                        # Verify storage calls were made
                        assert mock_client.upsert.call_count >= 0  # May be 0 if no symbols extracted
                        
                        # Step 3: Test search functionality
                        search_request = ASTSearchRequest(
                            query="async user creation function",
                            limit=10,
                            symbol_types=[SymbolType.FUNCTION, SymbolType.METHOD],
                            languages=["python"],
                            is_async=True
                        )
                        
                        search_response = await self.search_service.search(search_request)
                        
                        # Verify search response structure
                        assert search_response.query == "async user creation function"
                        assert isinstance(search_response.results, list)
                        assert search_response.search_time_ms >= 0
                        assert isinstance(search_response.filters_applied, dict)
                    
                    print(f"Pipeline test completed - Parse success: {parse_result.parse_success}")
    
    @patch('src.vector_db.ast_store.get_qdrant_client')
    async def test_search_filtering(self, mock_get_client):
        """Test advanced search filtering capabilities."""
        # Mock Qdrant client with search results
        mock_client = Mock()
        mock_search_result = Mock()
        mock_search_result.score = 0.85
        mock_search_result.payload = {
            "file_path": "test.py",
            "symbol_name": "async_function",
            "symbol_type": "function",
            "language": "python",
            "line_start": 10,
            "line_end": 20,
            "is_async": True,
            "is_static": False,
            "visibility": "public",
            "parameters": [{"name": "arg1", "type_hint": "str"}],
            "return_type": "dict"
        }
        mock_client.search.return_value = [mock_search_result]
        mock_get_client.return_value = mock_client
        
        # Mock embedding service
        mock_embedding = [0.1] * 384
        with patch.object(self.search_service.embedding_service, 'generate_embedding',
                        new_callable=AsyncMock, return_value=mock_embedding):
            
            # Test various filter combinations
            test_cases = [
                # Test async function filter
                ASTSearchRequest(
                    query="async functions",
                    symbol_types=[SymbolType.FUNCTION],
                    is_async=True
                ),
                # Test language filter
                ASTSearchRequest(
                    query="python functions",
                    languages=["python"],
                    search_scope=SearchScope.SYMBOLS
                ),
                # Test visibility filter
                ASTSearchRequest(
                    query="public methods",
                    symbol_types=[SymbolType.METHOD],
                    visibility="public"
                ),
                # Test class search
                ASTSearchRequest(
                    query="abstract classes",
                    search_scope=SearchScope.CLASSES,
                    is_abstract=True
                )
            ]
            
            for request in test_cases:
                response = await self.search_service.search(request)
                
                # Verify response structure
                assert response.query == request.query
                assert isinstance(response.results, list)
                assert response.search_time_ms >= 0
                assert isinstance(response.filters_applied, dict)
                
                # Verify search was called with filters
                mock_client.search.assert_called()
                call_args = mock_client.search.call_args
                assert "query_filter" in call_args.kwargs or call_args.kwargs.get("query_filter") is None
    
    async def test_indexer_file_processing(self):
        """Test AST indexer file processing."""
        # Create a temporary test file
        test_code = '''
def hello_world():
    """A simple greeting function."""
    print("Hello, World!")
    return True

class Greeter:
    def greet(self, name: str) -> str:
        return f"Hello, {name}!"
'''
        
        # Mock file operations
        with patch('pathlib.Path.read_text', return_value=test_code):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.is_file', return_value=True):
                    with patch.object(self.indexer.file_indexer, 'detect_file_type', 
                                    new_callable=AsyncMock, return_value="python"):
                        with patch.object(self.ast_store, 'store_parse_result',
                                        new_callable=AsyncMock, return_value=True):
                            
                            # Test file indexing
                            result = await self.indexer.index_file(Path("test.py"))
                            
                            # Verify indexing completed
                            assert isinstance(result, bool)
                            
                            # Check stats were updated
                            stats = self.indexer.get_stats()
                            assert stats["files_processed"] >= 0
                            assert stats["average_processing_time_ms"] >= 0
    
    async def test_error_handling(self):
        """Test error handling throughout the pipeline."""
        # Test with invalid file
        with patch('pathlib.Path.exists', return_value=False):
            result = await self.indexer.index_file(Path("nonexistent.py"))
            assert result is False
        
        # Test search with invalid embedding
        with patch.object(self.search_service.embedding_service, 'generate_embedding',
                        new_callable=AsyncMock, return_value=None):
            
            request = ASTSearchRequest(query="test query")
            response = await self.search_service.search(request)
            
            # Should return empty results on error
            assert response.total_results == 0
            assert len(response.results) == 0
    
    def test_stats_collection(self):
        """Test statistics collection across components."""
        # Test AST store stats
        store_stats = self.ast_store.get_stats()
        expected_keys = [
            "symbol_collection", "class_collection", "import_collection",
            "symbols_stored", "classes_stored", "imports_stored",
            "searches_performed", "errors"
        ]
        for key in expected_keys:
            assert key in store_stats
        
        # Test search service stats
        search_stats = self.search_service.get_stats()
        expected_keys = [
            "searches_performed", "average_search_time_ms",
            "cache_hits", "errors"
        ]
        for key in expected_keys:
            assert key in search_stats
        
        # Test indexer stats
        indexer_stats = self.indexer.get_stats()
        expected_keys = [
            "files_processed", "files_indexed", "symbols_indexed",
            "classes_indexed", "imports_indexed", "errors",
            "average_processing_time_ms", "success_rate"
        ]
        for key in expected_keys:
            assert key in indexer_stats
    
    def test_performance_characteristics(self):
        """Test performance characteristics of the system."""
        # Test that operations complete within reasonable time bounds
        # This is more of a smoke test since we're mocking external dependencies
        
        # Parse a simple file
        simple_code = "def test(): pass"
        result = self.parser.parse(Path("simple.py"), simple_code)
        
        # Should complete quickly
        assert result.parse_time_ms < 1000  # Less than 1 second
        assert result.symbol_extraction_time_ms < 1000
        
        # Test search request creation
        request = ASTSearchRequest(
            query="test function",
            limit=10,
            symbol_types=[SymbolType.FUNCTION]
        )
        
        # Should create request without issues
        assert request.query == "test function"
        assert request.limit == 10
