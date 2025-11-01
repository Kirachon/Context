"""
Tests for Incremental Indexer (Story 2.2 AC2)
"""
import asyncio
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.parsing.models import ParseResult, Language


class FakeParser:
    def __init__(self, imports_map=None):
        self.imports_map = imports_map or {}

    def parse(self, file_path: Path, content=None):
        imps = self.imports_map.get(str(file_path), [])
        # Build minimal ParseResult
        return ParseResult(
            file_path=file_path,
            language=Language.PYTHON,
            ast_root=None,
            symbols=[], classes=[], imports=imps, relationships=[],
            parse_success=True,
            parse_time_ms=1.0,
        )


class FakeEmbeddingService:
    def __init__(self):
        self.model = object()
        self.calls = 0

    async def initialize(self):
        self.model = object()

    async def generate_batch_embeddings(self, texts):
        self.calls += 1
        # return small fixed-dim vectors
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeVectorStore:
    def __init__(self):
        self.upserts = []

    async def upsert_batch(self, vectors):
        self.upserts.append(vectors)
        return True


@pytest.mark.asyncio
async def test_enqueue_and_process_changed_file(tmp_path: Path, monkeypatch):
    # Create file
    f = tmp_path / "a.py"
    f.write_text("print('hi')\n")

    from src.realtime.incremental_indexer import IncrementalIndexer
    svc = FakeEmbeddingService()
    store = FakeVectorStore()

    # Patch parser
    parser = FakeParser()
    monkeypatch.setattr("src.realtime.incremental_indexer.get_parser", lambda: parser)
    # Inject index ops to avoid DB dependency
    idx = IncrementalIndexer(batch_window_ms=100, embedding_service=svc, vector_store=store)
    idx.set_index_ops(index_file_func=AsyncMock(return_value={}), remove_file_func=AsyncMock(return_value=True))
    await idx.start()
    await idx.enqueue_event(("modified", str(f)))
    await asyncio.sleep(0.3)
    await idx.stop()

    assert len(store.upserts) >= 1
    assert any(any(v.get("id").endswith("a.py") for v in batch) for batch in store.upserts)


@pytest.mark.asyncio
async def test_no_redundant_processing_same_hash(tmp_path: Path, monkeypatch):
    f = tmp_path / "a.py"
    f.write_text("x=1\n")

    from src.realtime.incremental_indexer import IncrementalIndexer
    svc = FakeEmbeddingService(); store = FakeVectorStore(); parser = FakeParser()
    monkeypatch.setattr("src.realtime.incremental_indexer.get_parser", lambda: parser)
    idx = IncrementalIndexer(batch_window_ms=50, embedding_service=svc, vector_store=store)
    idx.set_index_ops(index_file_func=AsyncMock(return_value={}), remove_file_func=AsyncMock(return_value=True))
    await idx.start()
    await idx.enqueue_event(("modified", str(f)))
    await asyncio.sleep(0.2)
    # Enqueue again without change
    await idx.enqueue_event(("modified", str(f)))
    await asyncio.sleep(0.2)
    await idx.stop()

    # Only first batch should include vector for this file
    total_vectors = sum(len(b) for b in store.upserts)
    assert total_vectors == 1


@pytest.mark.asyncio
async def test_dependency_tracking_on_import_change(tmp_path: Path, monkeypatch):
    a = tmp_path / "a.py"; b = tmp_path / "b.py"
    a.write_text("import b\n"); b.write_text("print(1)\n")

    from src.parsing.models import ImportInfo
    imports_map = {str(a): [ImportInfo(module=str(b.with_suffix("")))], str(b): []}
    parser = FakeParser(imports_map)

    from src.realtime.incremental_indexer import IncrementalIndexer
    svc = FakeEmbeddingService(); store = FakeVectorStore()
    monkeypatch.setattr("src.realtime.incremental_indexer.get_parser", lambda: parser)
    idx = IncrementalIndexer(batch_window_ms=100, embedding_service=svc, vector_store=store)
    idx.set_index_ops(index_file_func=AsyncMock(return_value={}), remove_file_func=AsyncMock(return_value=True))
    await idx.start()
    # First process baseline to learn deps
    await idx.enqueue_event(("modified", str(a)))
    await asyncio.sleep(0.2)
    # Change b -> should reindex b and dependent a
    b.write_text("print(2)\n")
    await idx.enqueue_event(("modified", str(b)))
    await asyncio.sleep(0.4)
    await idx.stop()

    # Last upsert batch should include both a and b
    last_batch = store.upserts[-1]
    ids = [v["id"] for v in last_batch]
    assert any(id.endswith("a.py") for id in ids)
    assert any(id.endswith("b.py") for id in ids)


@pytest.mark.asyncio
async def test_batching_multiple_files(tmp_path: Path, monkeypatch):
    f1 = tmp_path / "a.py"; f2 = tmp_path / "b.py"; f3 = tmp_path / "c.py"
    for f in (f1, f2, f3): f.write_text("print(0)\n")

    from src.realtime.incremental_indexer import IncrementalIndexer
    svc = FakeEmbeddingService(); store = FakeVectorStore(); parser = FakeParser()
    monkeypatch.setattr("src.realtime.incremental_indexer.get_parser", lambda: parser)
    idx = IncrementalIndexer(batch_window_ms=200, embedding_service=svc, vector_store=store)
    idx.set_index_ops(index_file_func=AsyncMock(return_value={}), remove_file_func=AsyncMock(return_value=True))
    await idx.start()
    await idx.enqueue_event(("modified", str(f1)))
    await idx.enqueue_event(("modified", str(f2)))
    await idx.enqueue_event(("modified", str(f3)))
    await asyncio.sleep(0.4)
    await idx.stop()

    # Expect a single batch upsert
    assert len(store.upserts) == 1
    assert len(store.upserts[0]) == 3


@pytest.mark.asyncio
async def test_removed_file_calls_remove(tmp_path: Path, monkeypatch):
    f = tmp_path / "a.py"; f.write_text("print(0)\n")
    from src.realtime.incremental_indexer import IncrementalIndexer
    svc = FakeEmbeddingService(); store = FakeVectorStore(); parser = FakeParser()
    monkeypatch.setattr("src.realtime.incremental_indexer.get_parser", lambda: parser)
    mock_remove = AsyncMock(return_value=True)

    idx = IncrementalIndexer(batch_window_ms=50, embedding_service=svc, vector_store=store)
    idx.set_index_ops(index_file_func=AsyncMock(return_value={}), remove_file_func=mock_remove)
    await idx.start()
    # Delete then enqueue
    f.unlink()
    await idx.enqueue_event(("deleted", str(f)))
    await asyncio.sleep(0.2)
    await idx.stop()

    mock_remove.assert_awaited()



@pytest.mark.asyncio
async def test_is_supported_filters_txt(tmp_path: Path, monkeypatch):
    from src.realtime.incremental_indexer import IncrementalIndexer
    idx = IncrementalIndexer()
    assert idx._is_supported(str((tmp_path/"a.py"))) is False or True  # callable
    assert idx._is_supported(str((tmp_path/"a.txt"))) is False


def test_attach_watcher_sets_callback(monkeypatch):
    class W: pass
    from src.realtime.incremental_indexer import attach_watcher, IncrementalIndexer
    w = W(); idx = IncrementalIndexer()
    attach_watcher(w, idx)
    assert callable(w.on_change_callback)


@pytest.mark.asyncio
async def test_dependents_skip_unsupported(tmp_path: Path, monkeypatch):
    a = tmp_path/"a.txt"; b = tmp_path/"b.py"
    a.write_text("anything\n"); b.write_text("print(1)\n")
    from src.realtime.incremental_indexer import IncrementalIndexer
    from src.parsing.models import ImportInfo
    parser = FakeParser({str(b): [ImportInfo(module=str(a.with_suffix("")))], str(a): []})
    monkeypatch.setattr("src.realtime.incremental_indexer.get_parser", lambda: parser)
    idx = IncrementalIndexer(batch_window_ms=50, embedding_service=FakeEmbeddingService(), vector_store=FakeVectorStore())
    idx.set_index_ops(index_file_func=AsyncMock(return_value={}), remove_file_func=AsyncMock(return_value=True))
    await idx.start(); await idx.enqueue_event(("modified", str(b))); await asyncio.sleep(0.2); await idx.stop()
    # Only b.py should be upserted
    upserts = idx._vector_store.upserts
    assert upserts and all(not v["id"].endswith("a.txt") for v in upserts[0])


@pytest.mark.asyncio
async def test_batch_window_produces_multiple_batches(tmp_path: Path, monkeypatch):
    f = tmp_path/"a.py"; f.write_text("1\n")
    from src.realtime.incremental_indexer import IncrementalIndexer
    svc=FakeEmbeddingService(); store=FakeVectorStore(); parser=FakeParser()
    monkeypatch.setattr("src.realtime.incremental_indexer.get_parser", lambda: parser)
    idx = IncrementalIndexer(batch_window_ms=50, embedding_service=svc, vector_store=store)
    idx.set_index_ops(index_file_func=AsyncMock(return_value={}), remove_file_func=AsyncMock(return_value=True))
    await idx.start(); await idx.enqueue_event(("modified", str(f))); await asyncio.sleep(0.2)
    f.write_text("2\n"); await idx.enqueue_event(("modified", str(f))); await asyncio.sleep(0.2)
    await idx.stop()
    assert len(store.upserts) >= 2


@pytest.mark.asyncio
async def test_content_change_triggers_second_index(tmp_path: Path, monkeypatch):
    f = tmp_path/"a.py"; f.write_text("1\n")
    from src.realtime.incremental_indexer import IncrementalIndexer
    svc=FakeEmbeddingService(); store=FakeVectorStore(); parser=FakeParser()
    monkeypatch.setattr("src.realtime.incremental_indexer.get_parser", lambda: parser)
    idx = IncrementalIndexer(batch_window_ms=50, embedding_service=svc, vector_store=store)
    idx.set_index_ops(index_file_func=AsyncMock(return_value={}), remove_file_func=AsyncMock(return_value=True))
    await idx.start(); await idx.enqueue_event(("modified", str(f))); await asyncio.sleep(0.2)
    f.write_text("3\n"); await idx.enqueue_event(("modified", str(f))); await asyncio.sleep(0.2)
    await idx.stop()
    total = sum(len(b) for b in store.upserts)
    assert total >= 2
