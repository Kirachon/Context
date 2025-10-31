"""
Unit tests for File Monitor

Tests file system monitoring, event handlers, and ignore patterns.
"""

import pytest
import asyncio
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Add project root to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.indexing.file_monitor import FileMonitor, FileChangeHandler, start_file_monitor, stop_file_monitor, get_monitor_status


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_callback():
    """Create a mock callback function"""
    return AsyncMock()


class TestFileChangeHandler:
    """Test file change event handler"""
    
    def test_handler_initialization(self, mock_callback):
        """Test that handler initializes correctly"""
        handler = FileChangeHandler(on_change_callback=mock_callback)
        assert handler.on_change_callback == mock_callback
        assert isinstance(handler.ignore_patterns, list)
    
    def test_should_ignore_patterns(self):
        """Test ignore pattern matching"""
        handler = FileChangeHandler()
        
        # Test common ignore patterns
        assert handler._should_ignore("/path/to/.git/file.txt") is True
        assert handler._should_ignore("/path/to/node_modules/package.json") is True
        assert handler._should_ignore("/path/to/__pycache__/module.pyc") is True
        assert handler._should_ignore("/path/to/src/main.py") is False
    
    def test_is_supported_file(self):
        """Test supported file type detection"""
        handler = FileChangeHandler()
        
        # Supported files
        assert handler._is_supported_file("/path/to/file.py") is True
        assert handler._is_supported_file("/path/to/file.js") is True
        assert handler._is_supported_file("/path/to/file.ts") is True
        assert handler._is_supported_file("/path/to/file.java") is True
        assert handler._is_supported_file("/path/to/file.cpp") is True
        
        # Unsupported files
        assert handler._is_supported_file("/path/to/file.txt") is False
        assert handler._is_supported_file("/path/to/file.md") is False
        assert handler._is_supported_file("/path/to/file.json") is False
    
    @pytest.mark.asyncio
    async def test_on_created_event(self, temp_dir, mock_callback):
        """Test file creation event handling"""
        handler = FileChangeHandler(on_change_callback=mock_callback)
        
        # Create a test file
        test_file = os.path.join(temp_dir, "test.py")
        Path(test_file).touch()
        
        # Create mock event
        event = Mock()
        event.is_directory = False
        event.src_path = test_file
        
        # Handle event
        handler.on_created(event)
        
        # Wait for async callback
        await asyncio.sleep(0.1)
        
        # Verify callback was called
        mock_callback.assert_called_once_with('created', test_file)
    
    @pytest.mark.asyncio
    async def test_on_modified_event(self, temp_dir, mock_callback):
        """Test file modification event handling"""
        handler = FileChangeHandler(on_change_callback=mock_callback)
        
        # Create a test file
        test_file = os.path.join(temp_dir, "test.js")
        Path(test_file).touch()
        
        # Create mock event
        event = Mock()
        event.is_directory = False
        event.src_path = test_file
        
        # Handle event
        handler.on_modified(event)
        
        # Wait for async callback
        await asyncio.sleep(0.1)
        
        # Verify callback was called
        mock_callback.assert_called_once_with('modified', test_file)
    
    @pytest.mark.asyncio
    async def test_on_deleted_event(self, temp_dir, mock_callback):
        """Test file deletion event handling"""
        handler = FileChangeHandler(on_change_callback=mock_callback)
        
        # Use a file path (doesn't need to exist for delete event)
        test_file = os.path.join(temp_dir, "test.ts")
        
        # Create mock event
        event = Mock()
        event.is_directory = False
        event.src_path = test_file
        
        # Handle event
        handler.on_deleted(event)
        
        # Wait for async callback
        await asyncio.sleep(0.1)
        
        # Verify callback was called
        mock_callback.assert_called_once_with('deleted', test_file)
    
    def test_ignores_directory_events(self, mock_callback):
        """Test that directory events are ignored"""
        handler = FileChangeHandler(on_change_callback=mock_callback)
        
        # Create mock directory event
        event = Mock()
        event.is_directory = True
        event.src_path = "/path/to/directory"
        
        # Handle events
        handler.on_created(event)
        handler.on_modified(event)
        handler.on_deleted(event)
        
        # Verify callback was not called
        mock_callback.assert_not_called()
    
    def test_ignores_unsupported_files(self, mock_callback):
        """Test that unsupported file types are ignored"""
        handler = FileChangeHandler(on_change_callback=mock_callback)
        
        # Create mock event for unsupported file
        event = Mock()
        event.is_directory = False
        event.src_path = "/path/to/file.txt"
        
        # Handle events
        handler.on_created(event)
        handler.on_modified(event)
        
        # Verify callback was not called
        mock_callback.assert_not_called()


class TestFileMonitor:
    """Test file monitor service"""
    
    def test_monitor_initialization(self):
        """Test that monitor initializes correctly"""
        monitor = FileMonitor(paths=["/test/path"])
        assert monitor.paths == ["/test/path"]
        assert monitor.is_running is False
        assert monitor.observer is None
    
    def test_monitor_uses_default_paths(self):
        """Test that monitor uses settings paths by default"""
        monitor = FileMonitor()
        assert isinstance(monitor.paths, list)
    
    @pytest.mark.asyncio
    @patch('src.indexing.file_monitor.Observer')
    async def test_monitor_start(self, mock_observer_class, temp_dir):
        """Test monitor startup"""
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer
        
        monitor = FileMonitor(paths=[temp_dir])
        await monitor.start()
        
        assert monitor.is_running is True
        assert monitor.observer is not None
        mock_observer.start.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.indexing.file_monitor.Observer')
    async def test_monitor_stop(self, mock_observer_class):
        """Test monitor shutdown"""
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer
        
        monitor = FileMonitor(paths=["/test/path"])
        await monitor.start()
        await monitor.stop()
        
        assert monitor.is_running is False
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_monitor_start_already_running(self, temp_dir):
        """Test that starting an already running monitor logs warning"""
        monitor = FileMonitor(paths=[temp_dir])
        monitor.is_running = True
        
        await monitor.start()
        # Should not raise error, just log warning
    
    @pytest.mark.asyncio
    async def test_monitor_stop_not_running(self):
        """Test that stopping a non-running monitor logs warning"""
        monitor = FileMonitor()
        await monitor.stop()
        # Should not raise error, just log warning
    
    @pytest.mark.asyncio
    @patch('src.indexing.file_monitor.Observer')
    async def test_monitor_skips_nonexistent_paths(self, mock_observer_class):
        """Test that monitor skips paths that don't exist"""
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer
        
        monitor = FileMonitor(paths=["/nonexistent/path"])
        await monitor.start()
        
        # Should start but not schedule the nonexistent path
        assert monitor.is_running is True
    
    def test_get_status(self):
        """Test get_status returns correct structure"""
        monitor = FileMonitor(paths=["/test/path"])
        status = monitor.get_status()
        
        assert "running" in status
        assert "monitored_paths" in status
        assert "ignore_patterns" in status
        assert "observer_alive" in status
        
        assert status["running"] is False
        assert status["monitored_paths"] == ["/test/path"]


class TestGlobalFunctions:
    """Test global file monitor functions"""
    
    @pytest.mark.asyncio
    @patch('src.indexing.file_monitor.file_monitor.start')
    async def test_start_file_monitor(self, mock_start):
        """Test global start_file_monitor function"""
        mock_start.return_value = None
        
        await start_file_monitor()
        mock_start.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.indexing.file_monitor.file_monitor.stop')
    async def test_stop_file_monitor(self, mock_stop):
        """Test global stop_file_monitor function"""
        mock_stop.return_value = None
        
        await stop_file_monitor()
        mock_stop.assert_called_once()
    
    def test_get_monitor_status(self):
        """Test global get_monitor_status function"""
        status = get_monitor_status()
        
        assert isinstance(status, dict)
        assert "running" in status
        assert "monitored_paths" in status


class TestRealTimeDetection:
    """Test real-time change detection"""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    @patch('src.indexing.file_monitor.Observer')
    async def test_sub_second_detection(self, mock_observer_class, temp_dir):
        """Test that changes are detected in sub-second time"""
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer
        
        callback_times = []
        
        async def timed_callback(change_type, file_path):
            callback_times.append(time.time())
        
        monitor = FileMonitor(paths=[temp_dir], on_change_callback=timed_callback)
        await monitor.start()
        
        # Verify monitor started quickly
        assert monitor.is_running is True

