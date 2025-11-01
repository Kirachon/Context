"""
Tests for Real-time File Watcher (Story 2.2 AC1)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import time

from src.realtime.file_watcher import (
    RealTimeFileHandler,
    RealTimeFileWatcher,
    FileChangeEvent,
    start_real_time_watcher,
    get_watcher_status,
)


class TestFileChangeEvent:
    """Test FileChangeEvent dataclass."""

    def test_event_creation(self):
        """Test creating a file change event."""
        event = FileChangeEvent(
            event_type="modified", file_path="/test/file.py", timestamp=time.time()
        )

        assert event.event_type == "modified"
        assert event.file_path == "/test/file.py"
        assert event.timestamp > 0
        assert event.language is None
        assert event.content_hash is None
        assert event.is_debounced is False


class TestRealTimeFileHandler:
    """Test enhanced file handler with debouncing."""

    def test_handler_initialization(self):
        """Test handler initializes with correct defaults."""
        handler = RealTimeFileHandler()

        assert handler.debounce_delay == 0.5
        assert handler.max_events_per_second == 10
        assert handler.stats["events_processed"] == 0
        assert len(handler.debounce_states) == 0

    @patch("src.realtime.file_watcher.detect_language")
    def test_should_process_file(self, mock_detect):
        """Test file processing filter logic."""
        handler = RealTimeFileHandler()

        # Mock language detection
        mock_detect.return_value = None  # Unsupported file
        assert not handler._should_process_file("/test/file.txt")

        from src.parsing.parser import Language

        mock_detect.return_value = Language.PYTHON
        assert handler._should_process_file("/test/file.py")

    @patch("src.realtime.file_watcher.detect_language")
    @patch("builtins.open")
    def test_create_change_event(self, mock_open, mock_detect):
        """Test creating enhanced change events."""
        handler = RealTimeFileHandler()

        # Mock file operations
        from src.parsing.parser import Language

        mock_detect.return_value = Language.PYTHON
        mock_open.return_value.__enter__.return_value.read.return_value = (
            b"print('hello')"
        )

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.stat"
        ) as mock_stat:
            mock_stat.return_value.st_size = 100

            event = handler._create_change_event("modified", "/test/file.py")

            assert event.event_type == "modified"
            assert event.file_path == "/test/file.py"
            assert event.language == Language.PYTHON
            assert event.content_hash is not None
            assert event.file_size == 100

    def test_get_stats(self):
        """Test getting handler statistics."""
        handler = RealTimeFileHandler()
        stats = handler.get_stats()

        assert "events_processed" in stats
        assert "events_debounced" in stats
        assert "events_filtered" in stats
        assert "avg_processing_time" in stats
        assert "active_debounce_states" in stats
        assert "pending_tasks" in stats


class TestRealTimeFileWatcher:
    """Test enhanced file watcher."""

    def test_watcher_initialization(self):
        """Test watcher initializes correctly."""
        watcher = RealTimeFileWatcher(paths=["/test/path"])

        assert watcher.paths == ["/test/path"]
        assert watcher.is_running is False
        assert watcher.observer is None
        assert watcher.handler is None

    @pytest.mark.asyncio
    @patch("src.realtime.file_watcher.Observer")
    async def test_start_watcher(self, mock_observer_class):
        """Test starting the watcher."""
        mock_observer = MagicMock()
        mock_observer_class.return_value = mock_observer

        with tempfile.TemporaryDirectory() as temp_dir:
            watcher = RealTimeFileWatcher(paths=[temp_dir])

            await watcher.start()

            assert watcher.is_running is True
            assert watcher.observer is not None
            assert watcher.handler is not None
            mock_observer.start.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.realtime.file_watcher.Observer")
    async def test_stop_watcher(self, mock_observer_class):
        """Test stopping the watcher."""
        mock_observer = MagicMock()
        mock_observer_class.return_value = mock_observer

        with tempfile.TemporaryDirectory() as temp_dir:
            watcher = RealTimeFileWatcher(paths=[temp_dir])
            await watcher.start()
            await watcher.stop()

            assert watcher.is_running is False
            mock_observer.stop.assert_called_once()

    def test_get_status(self):
        """Test getting watcher status."""
        watcher = RealTimeFileWatcher(paths=["/test"])
        status = watcher.get_status()

        assert "running" in status
        assert "uptime_seconds" in status
        assert "monitored_paths" in status
        assert "observer_alive" in status
        assert status["monitored_paths"] == ["/test"]


class TestGlobalFunctions:
    """Test global watcher functions."""

    @pytest.mark.asyncio
    @patch("src.realtime.file_watcher.real_time_watcher")
    async def test_start_real_time_watcher(self, mock_watcher):
        """Test starting global watcher."""
        mock_watcher.start = AsyncMock()
        callback = AsyncMock()
        await start_real_time_watcher(callback)

        assert mock_watcher.on_change_callback == callback
        mock_watcher.start.assert_called_once()

    @patch("src.realtime.file_watcher.real_time_watcher")
    def test_get_watcher_status(self, mock_watcher):
        """Test getting global watcher status."""
        mock_watcher.get_status.return_value = {"running": True}

        status = get_watcher_status()
        assert status == {"running": True}
        mock_watcher.get_status.assert_called_once()
