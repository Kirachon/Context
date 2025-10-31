"""
Unit tests for File Indexer

Tests file type detection, metadata extraction, and indexing operations.
"""

import pytest
import os
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, AsyncMock

# Add project root to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.indexing.file_indexer import FileIndexer, index_file, remove_file, get_indexer_stats


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def indexer():
    """Create a fresh file indexer instance"""
    return FileIndexer()


class TestFileTypeDetection:
    """Test file type detection"""
    
    @pytest.mark.asyncio
    async def test_detect_python_files(self, indexer):
        """Test Python file detection"""
        language = await indexer.detect_file_type("/path/to/file.py")
        assert language == "python"
    
    @pytest.mark.asyncio
    async def test_detect_javascript_files(self, indexer):
        """Test JavaScript file detection"""
        assert await indexer.detect_file_type("/path/to/file.js") == "javascript"
        assert await indexer.detect_file_type("/path/to/file.jsx") == "javascript"
    
    @pytest.mark.asyncio
    async def test_detect_typescript_files(self, indexer):
        """Test TypeScript file detection"""
        assert await indexer.detect_file_type("/path/to/file.ts") == "typescript"
        assert await indexer.detect_file_type("/path/to/file.tsx") == "typescript"
    
    @pytest.mark.asyncio
    async def test_detect_java_files(self, indexer):
        """Test Java file detection"""
        language = await indexer.detect_file_type("/path/to/File.java")
        assert language == "java"
    
    @pytest.mark.asyncio
    async def test_detect_cpp_files(self, indexer):
        """Test C++ file detection"""
        assert await indexer.detect_file_type("/path/to/file.cpp") == "cpp"
        assert await indexer.detect_file_type("/path/to/file.hpp") == "cpp"
        assert await indexer.detect_file_type("/path/to/file.h") == "cpp"
        assert await indexer.detect_file_type("/path/to/file.cc") == "cpp"
    
    @pytest.mark.asyncio
    async def test_unsupported_file_types(self, indexer):
        """Test unsupported file types return None"""
        assert await indexer.detect_file_type("/path/to/file.txt") is None
        assert await indexer.detect_file_type("/path/to/file.md") is None
        assert await indexer.detect_file_type("/path/to/file.json") is None
    
    def test_is_supported(self, indexer):
        """Test is_supported method"""
        assert indexer.is_supported("/path/to/file.py") is True
        assert indexer.is_supported("/path/to/file.js") is True
        assert indexer.is_supported("/path/to/file.txt") is False


class TestMetadataExtraction:
    """Test metadata extraction"""
    
    @pytest.mark.asyncio
    async def test_extract_metadata_success(self, indexer, temp_dir):
        """Test successful metadata extraction"""
        # Create test file
        test_file = os.path.join(temp_dir, "test.py")
        Path(test_file).write_text("print('hello')")
        
        metadata = await indexer.extract_metadata(test_file)
        
        assert metadata is not None
        assert "file_path" in metadata
        assert "file_name" in metadata
        assert "file_type" in metadata
        assert "size" in metadata
        assert "modified_time" in metadata
        assert "created_time" in metadata
        assert "extension" in metadata
        
        assert metadata["file_name"] == "test.py"
        assert metadata["file_type"] == "python"
        assert metadata["extension"] == ".py"
        assert metadata["size"] > 0
        assert isinstance(metadata["modified_time"], datetime)
    
    @pytest.mark.asyncio
    async def test_extract_metadata_nonexistent_file(self, indexer):
        """Test metadata extraction for nonexistent file"""
        metadata = await indexer.extract_metadata("/nonexistent/file.py")
        assert metadata is None
    
    @pytest.mark.asyncio
    async def test_extract_metadata_unsupported_file(self, indexer, temp_dir):
        """Test metadata extraction for unsupported file type"""
        # Create unsupported file
        test_file = os.path.join(temp_dir, "test.txt")
        Path(test_file).write_text("hello")
        
        metadata = await indexer.extract_metadata(test_file)
        assert metadata is None


class TestFileIndexing:
    """Test file indexing operations"""
    
    @pytest.mark.asyncio
    @patch('src.indexing.file_indexer.create_file_metadata')
    @patch('src.indexing.file_indexer.get_file_metadata')
    async def test_index_file_success(self, mock_get, mock_create, indexer, temp_dir):
        """Test successful file indexing"""
        # Create test file
        test_file = os.path.join(temp_dir, "test.js")
        Path(test_file).write_text("console.log('hello');")
        
        # Mock database operations
        mock_get.return_value = None  # File doesn't exist in DB
        mock_create.return_value = None
        
        metadata = await indexer.index_file(test_file)
        
        assert metadata is not None
        assert metadata["file_type"] == "javascript"
        assert metadata["status"] == "indexed"
        assert "indexed_time" in metadata
        
        # Verify database was called
        mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.indexing.file_indexer.update_file_metadata')
    @patch('src.indexing.file_indexer.get_file_metadata')
    async def test_index_file_update_existing(self, mock_get, mock_update, indexer, temp_dir):
        """Test updating existing file in index"""
        # Create test file
        test_file = os.path.join(temp_dir, "test.ts")
        Path(test_file).write_text("const x = 1;")
        
        # Mock database operations - file exists
        mock_get.return_value = {"file_path": test_file}
        mock_update.return_value = None
        
        metadata = await indexer.index_file(test_file)
        
        assert metadata is not None
        
        # Verify update was called instead of create
        mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_index_file_nonexistent(self, indexer):
        """Test indexing nonexistent file"""
        metadata = await indexer.index_file("/nonexistent/file.py")
        assert metadata is None
    
    @pytest.mark.asyncio
    async def test_index_file_unsupported(self, indexer, temp_dir):
        """Test indexing unsupported file type"""
        # Create unsupported file
        test_file = os.path.join(temp_dir, "test.txt")
        Path(test_file).write_text("hello")
        
        metadata = await indexer.index_file(test_file)
        assert metadata is None
    
    @pytest.mark.asyncio
    @patch('src.indexing.file_indexer.delete_file_metadata')
    async def test_remove_file_success(self, mock_delete, indexer):
        """Test successful file removal"""
        mock_delete.return_value = True
        
        success = await indexer.remove_file("/path/to/file.py")
        
        assert success is True
        mock_delete.assert_called_once_with("/path/to/file.py")
    
    @pytest.mark.asyncio
    @patch('src.indexing.file_indexer.delete_file_metadata')
    async def test_remove_file_not_found(self, mock_delete, indexer):
        """Test removing file not in index"""
        mock_delete.return_value = False
        
        success = await indexer.remove_file("/path/to/file.py")
        
        assert success is False


class TestIndexerStatistics:
    """Test indexer statistics"""
    
    @pytest.mark.asyncio
    @patch('src.indexing.file_indexer.create_file_metadata')
    @patch('src.indexing.file_indexer.get_file_metadata')
    async def test_stats_tracking(self, mock_get, mock_create, indexer, temp_dir):
        """Test that statistics are tracked correctly"""
        # Create test files
        py_file = os.path.join(temp_dir, "test.py")
        js_file = os.path.join(temp_dir, "test.js")
        Path(py_file).write_text("print('hello')")
        Path(js_file).write_text("console.log('hello');")
        
        # Mock database
        mock_get.return_value = None
        mock_create.return_value = None
        
        # Index files
        await indexer.index_file(py_file)
        await indexer.index_file(js_file)
        
        stats = indexer.get_stats()
        
        assert stats["total_indexed"] == 2
        assert stats["total_errors"] == 0
        assert "python" in stats["by_language"]
        assert "javascript" in stats["by_language"]
        assert stats["by_language"]["python"] == 1
        assert stats["by_language"]["javascript"] == 1
    
    def test_get_stats_structure(self, indexer):
        """Test get_stats returns correct structure"""
        stats = indexer.get_stats()
        
        assert "total_indexed" in stats
        assert "total_errors" in stats
        assert "by_language" in stats
        assert "supported_languages" in stats
        
        assert isinstance(stats["supported_languages"], list)
        assert "python" in stats["supported_languages"]
        assert "javascript" in stats["supported_languages"]


class TestGlobalFunctions:
    """Test global indexer functions"""
    
    @pytest.mark.asyncio
    @patch('src.indexing.file_indexer.file_indexer.index_file')
    async def test_index_file_function(self, mock_index):
        """Test global index_file function"""
        mock_index.return_value = {"file_path": "/test/file.py"}
        
        result = await index_file("/test/file.py")
        
        mock_index.assert_called_once_with("/test/file.py")
        assert result is not None
    
    @pytest.mark.asyncio
    @patch('src.indexing.file_indexer.file_indexer.remove_file')
    async def test_remove_file_function(self, mock_remove):
        """Test global remove_file function"""
        mock_remove.return_value = True
        
        result = await remove_file("/test/file.py")
        
        mock_remove.assert_called_once_with("/test/file.py")
        assert result is True
    
    def test_get_indexer_stats_function(self):
        """Test global get_indexer_stats function"""
        stats = get_indexer_stats()
        
        assert isinstance(stats, dict)
        assert "total_indexed" in stats
        assert "supported_languages" in stats

