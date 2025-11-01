"""
Incremental Indexer (Story 2.2 AC2)

Smart incremental indexing with content-hash change detection, dependency tracking,
and batched vector DB updates. Integrates with RealTimeFileWatcher and Story 1.3 queue.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import contextlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Callable

from src.parsing.parser import get_parser, detect_language
from src.parsing.models import ParseResult, ImportInfo

logger = logging.getLogger(__name__)


@dataclass
class FileState:
    mtime: float
    content_hash: str


class IncrementalIndexer:
    """
    Incremental indexing engine.
    - Tracks file hashes & mtimes to avoid redundant work
    - Maintains a lightweight dependency graph (imports -> dependents)
    - Batches vector DB upserts for efficiency
    """

    def __init__(
        self,
        batch_max: int = 32,
        batch_window_ms: int = 500,
        embedding_service: Optional[Any] = None,
        vector_store: Optional[Any] = None,
        on_indexed: Optional[Callable[[List[str]], None]] = None,
    ):
        self._states: Dict[str, FileState] = {}
        # dependency: file_path -> set(relative_import_key)
        self._imports_by_file: Dict[str, Set[str]] = {}
        # reverse dependency: import_key -> set(file_paths_that_depend_on_it)
        self._dependents_by_import: Dict[str, Set[str]] = {}
        self._queue: asyncio.Queue[Tuple[str, str]] = asyncio.Queue()
        self._processor_task: Optional[asyncio.Task] = None
        self._stopped = True
        self._batch_max = batch_max
        self._batch_window_ms = batch_window_ms
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._on_indexed = on_indexed
        # Optional integration points to avoid hard deps in tests
        self._index_file_func: Optional[Callable[[str], Any]] = None
        self._remove_file_func: Optional[Callable[[str], Any]] = None

    async def start(self):
        if self._processor_task and not self._processor_task.done():
            return
        self._stopped = False
        self._processor_task = asyncio.create_task(self._processor_loop())
        logger.info("IncrementalIndexer started")

    async def stop(self):
        self._stopped = True
        if self._processor_task:
            self._processor_task.cancel()
            with contextlib.suppress(Exception):
                await self._processor_task
        logger.info("IncrementalIndexer stopped")

    async def enqueue_event(self, event) -> None:
        """Accepts RealTimeFileWatcher FileChangeEvent or (change_type, file_path)."""
        if isinstance(event, tuple) and len(event) == 2:
            change_type, file_path = event
        else:
            change_type = getattr(event, "event_type", "modified")
            file_path = getattr(event, "file_path", None)
        if not file_path:
            return
        await self._queue.put((change_type, str(Path(file_path).resolve())))

    async def _processor_loop(self):
        """Batch events and process incrementally."""
        while not self._stopped:
            try:
                # First item (wait indefinitely)
                change_type, file_path = await self._queue.get()
                batch: List[Tuple[str, str]] = [(change_type, file_path)]
                t0 = time.time()
                # Drain up to batch_max or until window elapsed
                while len(batch) < self._batch_max:
                    timeout = max(0, self._batch_window_ms / 1000 - (time.time() - t0))
                    try:
                        item = await asyncio.wait_for(self._queue.get(), timeout=timeout)
                        batch.append(item)
                    except asyncio.TimeoutError:
                        break
                await self._process_batch(batch)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Incremental batch processing error: {e}", exc_info=True)

    async def _process_batch(self, batch: List[Tuple[str, str]]):
        # Deduplicate by file (last event wins)
        latest: Dict[str, str] = {}
        for change_type, file_path in batch:
            latest[file_path] = change_type
        changed_files: List[str] = []
        removed_files: List[str] = []

        # Determine actual changes via mtime+hash
        for file_path, change_type in latest.items():
            p = Path(file_path)
            if change_type == "deleted" or not p.exists():
                removed_files.append(file_path)
                continue
            if not self._is_supported(file_path):
                continue
            if self._has_changed(file_path):
                changed_files.append(file_path)

        # Include dependents of changed files
        dependents: Set[str] = set()
        for fp in changed_files:
            for dep in self._get_dependents_for_file(fp):
                if Path(dep).exists() and self._is_supported(dep):
                    dependents.add(dep)
        to_index = list(dict.fromkeys(changed_files + list(dependents)))

        # Apply removals first
        for fp in removed_files:
            await self._call_remove_file(fp)
            self._remove_file_from_graph(fp)
            self._states.pop(fp, None)

        # Parse, update graph, and index (batched vectors)
        if not to_index:
            return
        parser = get_parser()
        parse_results: Dict[str, ParseResult] = {}
        file_texts: Dict[str, str] = {}
        for fp in to_index:
            pr = parser.parse(Path(fp))
            parse_results[fp] = pr
            self._update_dependency_graph(fp, pr.imports)
            # Update hash state now that we'll index
            self._update_file_state(fp)
            # Read content for embeddings
            try:
                file_texts[fp] = Path(fp).read_text(encoding="utf-8", errors="ignore")
            except Exception:
                file_texts[fp] = ""
            # Update DB metadata + single-file vector as fallback
            await self._call_index_file(fp)

        # Optimize vector ops: batch upserts if possible
        try:
            await self._batch_upsert_vectors(file_texts, parse_results)
        except Exception as e:
            logger.warning(f"Batch vector upsert failed, continuing: {e}")

        if self._on_indexed:
            with contextlib.suppress(Exception):
                self._on_indexed(to_index)

    def _has_changed(self, file_path: str) -> bool:
        p = Path(file_path)
        try:
            mtime = p.stat().st_mtime
            content = p.read_bytes()
            h = hashlib.sha256(content).hexdigest()
        except Exception:
            return False
        prev = self._states.get(file_path)
        return (prev is None) or (prev.mtime != mtime) or (prev.content_hash != h)

    def _update_file_state(self, file_path: str):
        p = Path(file_path)
        try:
            st = p.stat()
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            self._states[file_path] = FileState(mtime=st.st_mtime, content_hash=h)
        except Exception:
            pass

    def _import_key_from_path(self, file_path: str) -> str:
        # Normalize to module-like key (relative path without extension)
        rel = str(Path(file_path).with_suffix("").as_posix())
        return rel.lower()

    def _normalize_import(self, imp: ImportInfo) -> str:
        # Use module string, normalize path-like modules
        mod = (getattr(imp, "module", "") or "").strip()
        if mod.startswith("./") or mod.startswith("../") or "/" in mod or "\\" in mod:
            mod = mod.replace("\\", "/")
            if mod.endswith(".py") or mod.endswith(".ts") or mod.endswith(".js"):
                mod = mod.rsplit(".", 1)[0]
        return mod.lower()

    def _is_supported(self, file_path: str) -> bool:
        try:
            return detect_language(Path(file_path)) is not None
        except Exception:
            return False

    async def _call_index_file(self, file_path: str):
        if self._index_file_func:
            return await self._index_file_func(file_path)
        # Lazy import to avoid heavy deps in tests
        from src.indexing.file_indexer import file_indexer as _fx
        return await _fx.index_file(file_path)

    async def _call_remove_file(self, file_path: str):
        if self._remove_file_func:
            return await self._remove_file_func(file_path)
        from src.indexing.file_indexer import file_indexer as _fx
        return await _fx.remove_file(file_path)

    def set_index_ops(self, index_file_func: Callable[[str], Any], remove_file_func: Callable[[str], Any]):
        self._index_file_func = index_file_func
        self._remove_file_func = remove_file_func

    def _update_dependency_graph(self, file_path: str, imports: List[ImportInfo]):
        old = self._imports_by_file.get(file_path, set())
        new: Set[str] = set(self._normalize_import(imp) for imp in imports or [])
        self._imports_by_file[file_path] = new
        # Update reverse index
        for key in old - new:
            if key in self._dependents_by_import:
                self._dependents_by_import[key].discard(file_path)
                if not self._dependents_by_import[key]:
                    self._dependents_by_import.pop(key, None)
        for key in new - old:
            self._dependents_by_import.setdefault(key, set()).add(file_path)

    def _remove_file_from_graph(self, file_path: str):
        keys = self._imports_by_file.pop(file_path, set())
        for key in keys:
            if key in self._dependents_by_import:
                self._dependents_by_import[key].discard(file_path)
                if not self._dependents_by_import[key]:
                    self._dependents_by_import.pop(key, None)

    def _get_dependents_for_file(self, file_path: str) -> Set[str]:
        key = self._import_key_from_path(file_path)
        return set(self._dependents_by_import.get(key, set()))

    async def _batch_upsert_vectors(self, file_texts: Dict[str, str], parse_results: Dict[str, ParseResult]):
        """Batch-generate embeddings and upsert vectors to Qdrant when possible."""
        # Lazy imports only when needed to allow test-time injection
        if self._embedding_service is None:
            from src.vector_db.embeddings import get_embedding_service
            svc = get_embedding_service()
        else:
            svc = self._embedding_service
        if self._vector_store is None:
            from src.vector_db.vector_store import get_vector_store
            store = get_vector_store()
        else:
            store = self._vector_store

        # Initialize model lazily if needed
        if getattr(svc, "model", None) is None and hasattr(svc, "initialize"):
            try:
                await svc.initialize()  # may be mocked in tests
            except Exception:
                logger.warning("EmbeddingService initialize failed; continuing with per-file fallback")

        ids: List[str] = []
        texts: List[str] = []
        payloads: List[Dict[str, Any]] = []
        for fp, code in file_texts.items():
            pr = parse_results.get(fp)
            lang = pr.language.value if pr and pr.language else ""
            file_name = Path(fp).name
            # Compose text with light context (same as EmbeddingService.generate_code_embedding)
            prefix = " | ".join([p for p in [f"Language: {lang}" if lang else "", f"File: {file_name}"] if p])
            texts.append((prefix + "\n\n" + code) if prefix else code)
            ids.append(str(Path(fp).resolve()))
            payloads.append({
                "file_path": str(Path(fp).resolve()),
                "file_name": file_name,
                "file_type": lang,
                "indexed_time": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            })

        if not texts:
            return

        try:
            embeddings = await svc.generate_batch_embeddings(texts)
        except Exception as e:
            logger.warning(f"Batch embedding failed: {e}")
            embeddings = [None] * len(texts)

        vectors: List[Dict[str, Any]] = []
        for i, emb in enumerate(embeddings):
            if emb is None:
                continue
            vectors.append({"id": ids[i], "vector": emb, "payload": payloads[i]})

        if vectors:
            await store.upsert_batch(vectors)


# Global instance
_incremental_indexer: Optional[IncrementalIndexer] = None



def attach_watcher(watcher: Any, indexer: Optional[IncrementalIndexer] = None):
    """Attach incremental indexer to a RealTimeFileWatcher instance.
    The watcher should expose `on_change_callback` attribute.
    """
    idx = indexer or get_incremental_indexer()
    watcher.on_change_callback = idx.enqueue_event
    return idx


def get_incremental_indexer() -> IncrementalIndexer:
    global _incremental_indexer
    if _incremental_indexer is None:
        _incremental_indexer = IncrementalIndexer()
    return _incremental_indexer

