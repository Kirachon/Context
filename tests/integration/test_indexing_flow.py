"""
Integration tests for Indexing Flow

Tests end-to-end file monitoring, indexing, and status reporting.
"""

import pytest
import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

# Add project root to path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def client():
    """Create FastAPI test client"""
    from src.mcp_server.server import app

    return TestClient(app)


class TestEndToEndIndexingFlow:
    """Test complete indexing flow from file change to database"""

    @pytest.mark.asyncio
    @patch("src.indexing.models.create_file_metadata")
    @patch("src.indexing.models.get_file_metadata")
    async def test_file_creation_flow(self, mock_get, mock_create, temp_dir):
        """Test complete flow for file creation"""
        from src.indexing.queue import queue_file_change, indexing_queue

        # Create test file
        test_file = os.path.join(temp_dir, "test.py")
        Path(test_file).write_text("print('hello')")

        # Mock database
        mock_get.return_value = None
        mock_create.return_value = None

        # Queue file change
        await queue_file_change("created", test_file)

        # Wait for processing
        await asyncio.sleep(0.5)

        # Verify file was processed
        stats = indexing_queue.get_status()
        assert stats["stats"]["total_processed"] >= 1

    @pytest.mark.asyncio
    @patch("src.indexing.models.update_file_metadata")
    @patch("src.indexing.models.get_file_metadata")
    async def test_file_modification_flow(self, mock_get, mock_update, temp_dir):
        """Test complete flow for file modification"""
        from src.indexing.queue import queue_file_change, indexing_queue

        # Create test file
        test_file = os.path.join(temp_dir, "test.js")
        Path(test_file).write_text("console.log('hello');")

        # Mock database - file exists
        mock_get.return_value = {"file_path": test_file}
        mock_update.return_value = None

        # Queue file change
        await queue_file_change("modified", test_file)

        # Wait for processing
        await asyncio.sleep(0.5)

        # Verify file was processed
        stats = indexing_queue.get_status()
        assert stats["stats"]["total_processed"] >= 1

    @pytest.mark.asyncio
    @patch("src.indexing.models.delete_file_metadata")
    async def test_file_deletion_flow(self, mock_delete):
        """Test complete flow for file deletion"""
        from src.indexing.queue import queue_file_change, indexing_queue

        test_file = "/path/to/deleted/file.py"

        # Mock database
        mock_delete.return_value = True

        # Queue file change
        await queue_file_change("deleted", test_file)

        # Wait for processing
        await asyncio.sleep(0.5)

        # Verify file was processed
        stats = indexing_queue.get_status()
        assert stats["stats"]["total_processed"] >= 1


class TestIncrementalIndexing:
    """Test incremental indexing behavior"""

    @pytest.mark.asyncio
    @patch("src.indexing.models.create_file_metadata")
    @patch("src.indexing.models.update_file_metadata")
    @patch("src.indexing.models.get_file_metadata")
    async def test_incremental_updates(
        self, mock_get, mock_update, mock_create, temp_dir
    ):
        """Test that only changed files are reindexed"""
        from src.indexing.file_indexer import file_indexer

        # Create test file
        test_file = os.path.join(temp_dir, "test.py")
        Path(test_file).write_text("print('hello')")

        # First index - file doesn't exist
        mock_get.return_value = None
        mock_create.return_value = None

        await file_indexer.index_file(test_file)

        # Verify create was called
        assert mock_create.call_count == 1

        # Second index - file exists
        mock_get.return_value = {"file_path": test_file}
        mock_update.return_value = None

        await file_indexer.index_file(test_file)

        # Verify update was called instead of create
        assert mock_update.call_count == 1
        assert mock_create.call_count == 1  # Still 1, not 2

    @pytest.mark.asyncio
    @patch("src.indexing.models.create_file_metadata")
    @patch("src.indexing.models.get_file_metadata")
    async def test_no_full_reindex(self, mock_get, mock_create, temp_dir):
        """Test that unchanged files are not reprocessed"""
        from src.indexing.file_indexer import file_indexer

        # Create multiple test files
        files = []
        for i in range(3):
            test_file = os.path.join(temp_dir, f"test{i}.py")
            Path(test_file).write_text(f"print({i})")
            files.append(test_file)

        # Mock database
        mock_get.return_value = None
        mock_create.return_value = None

        # Index all files
        for file in files:
            await file_indexer.index_file(file)

        # Verify each file was indexed once
        assert mock_create.call_count == 3


class TestIndexingStatusEndpoint:
    """Test indexing status endpoint"""

    def test_indexing_status_endpoint_structure(self, client):
        """Test /indexing/status endpoint returns correct structure"""
        response = client.get("/indexing/status")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "file_monitor" in data
        assert "indexing_queue" in data
        assert "indexer" in data
        assert "database" in data
        assert "timestamp" in data

        # Verify file monitor structure
        assert "running" in data["file_monitor"]
        assert "monitored_paths" in data["file_monitor"]
        assert "ignore_patterns" in data["file_monitor"]

        # Verify queue structure
        assert "processing" in data["indexing_queue"]
        assert "queue_size" in data["indexing_queue"]
        assert "stats" in data["indexing_queue"]

        # Verify indexer structure
        assert "total_indexed" in data["indexer"]
        assert "supported_languages" in data["indexer"]

    def test_indexing_status_includes_statistics(self, client):
        """Test that status endpoint includes statistics"""
        response = client.get("/indexing/status")

        assert response.status_code == 200
        data = response.json()

        # Verify statistics are present
        assert "total_indexed" in data["indexer"]
        assert "total_errors" in data["indexer"]
        assert "by_language" in data["indexer"]


class TestFileMonitorIntegration:
    """Test file monitor integration with indexing queue"""

    @pytest.mark.asyncio
    @patch("src.indexing.file_monitor.Observer")
    @patch("src.indexing.models.create_file_metadata")
    @patch("src.indexing.models.get_file_metadata")
    async def test_monitor_queues_changes(
        self, mock_get, mock_create, mock_observer_class, temp_dir
    ):
        """Test that file monitor queues changes for processing"""
        from src.indexing.file_monitor import FileMonitor
        from src.indexing.queue import queue_file_change

        # Mock observer
        mock_observer = AsyncMock()
        mock_observer_class.return_value = mock_observer

        # Mock database
        mock_get.return_value = None
        mock_create.return_value = None

        # Start monitor with queue callback
        monitor = FileMonitor(paths=[temp_dir], on_change_callback=queue_file_change)
        await monitor.start()

        # Verify monitor is running
        assert monitor.is_running is True

        # Stop monitor
        await monitor.stop()


class TestMCPIndexingTools:
    """Test MCP indexing tools"""

    @pytest.mark.asyncio
    @patch("src.indexing.file_monitor.file_monitor.start")
    async def test_start_monitoring_tool(self, mock_start):
        """Test start_monitoring MCP tool"""
        from src.mcp_server.tools.indexing import register_indexing_tools
        from unittest.mock import Mock

        # Create mock MCP
        mcp = Mock()
        registered_tools = []

        def mock_tool_decorator():
            def decorator(func):
                registered_tools.append(func)
                return func

            return decorator

        mcp.tool = mock_tool_decorator
        register_indexing_tools(mcp)

        # Find start_monitoring tool
        start_monitoring = next(
            (t for t in registered_tools if t.__name__ == "start_monitoring"), None
        )
        assert start_monitoring is not None

        # Call tool
        mock_start.return_value = None
        result = await start_monitoring()

        assert "success" in result
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_indexing_status_tool(self):
        """Test indexing_status MCP tool"""
        from src.mcp_server.tools.indexing import register_indexing_tools
        from unittest.mock import Mock

        # Create mock MCP
        mcp = Mock()
        registered_tools = []

        def mock_tool_decorator():
            def decorator(func):
                registered_tools.append(func)
                return func

            return decorator

        mcp.tool = mock_tool_decorator
        register_indexing_tools(mcp)

        # Find indexing_status tool
        indexing_status = next(
            (t for t in registered_tools if t.__name__ == "indexing_status"), None
        )
        assert indexing_status is not None

        # Call tool
        result = await indexing_status()

        assert "file_monitor" in result
        assert "indexing_queue" in result
        assert "indexer" in result


class TestPerformance:
    """Test indexing performance"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    @patch("src.indexing.models.create_file_metadata")
    @patch("src.indexing.models.get_file_metadata")
    async def test_indexing_throughput(self, mock_get, mock_create, temp_dir):
        """Test that indexing meets throughput requirements (1000+ files/minute)"""
        import time
        from src.indexing.file_indexer import file_indexer

        # Create test files
        num_files = 100
        files = []
        for i in range(num_files):
            test_file = os.path.join(temp_dir, f"test{i}.py")
            Path(test_file).write_text(f"print({i})")
            files.append(test_file)

        # Mock database
        mock_get.return_value = None
        mock_create.return_value = None

        # Measure indexing time
        start_time = time.time()

        for file in files:
            await file_indexer.index_file(file)

        end_time = time.time()
        duration = end_time - start_time

        # Calculate throughput (files per minute)
        throughput = (num_files / duration) * 60

        # Should achieve at least 1000 files/minute
        # For 100 files, should complete in < 6 seconds
        assert (
            duration < 6.0
        ), f"Indexing took {duration}s, should be < 6s for {num_files} files"
        assert (
            throughput > 1000
        ), f"Throughput {throughput:.0f} files/min, should be > 1000"
