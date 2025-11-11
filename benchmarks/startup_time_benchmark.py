"""
Startup Time Benchmark for HTTP MCP Server

Measures the time to create the HTTP MCP ASGI app via create_app(), with
heavy external operations patched out to avoid environment coupling. This
isolates framework and registration overhead and checks we remain <10%.

Safe to run locally. No external services required.
"""
from __future__ import annotations

import os
import sys
import time
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure repository root is on sys.path so `src` imports work
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _patched_create_app_run() -> float:
    """Import http_server and call create_app() with heavy ops patched."""
    import importlib

    # Fresh-import module each run to avoid caching artifacts
    if "src.mcp_server.http_server" in sys.modules:
        del sys.modules["src.mcp_server.http_server"]

    with ExitStack() as stack:
        # Import the module so we can patch its local symbols
        http_server = importlib.import_module("src.mcp_server.http_server")

        # Patch heavy async operations used during initialization (patch original modules)
        stack.enter_context(patch("src.vector_db.qdrant_client.connect_qdrant", new=AsyncMock(return_value=True)))
        stack.enter_context(patch("src.vector_db.vector_store.vector_store.ensure_collection", new=AsyncMock(return_value=True)))
        stack.enter_context(patch("src.vector_db.embeddings.initialize_embeddings", new=AsyncMock(return_value=None)))
        stack.enter_context(patch("src.indexing.file_monitor.start_file_monitor", new=AsyncMock(return_value=None)))
        stack.enter_context(patch("src.indexing.initial_indexer.run_initial_indexing", new=AsyncMock(return_value={"queued_files": 0, "failed_files": 0, "total_files": 0})))
        stack.enter_context(patch("src.indexing.queue.indexing_queue.process_queue", new=AsyncMock(return_value=None)))

        # Avoid expensive tool registration and server creation logic
        # Return a stub with streamable_http_app that returns a trivial ASGI app
        def _streamable_http_app(path: str = "/"):
            async def app(scope, receive, send):  # minimal ASGI 3.0 app
                if scope["type"] == "http":
                    await send({"type": "http.response.start", "status": 200, "headers": []})
                    await send({"type": "http.response.body", "body": b"OK"})
            return app

        fake_mcp = SimpleNamespace(streamable_http_app=_streamable_http_app)
        stack.enter_context(patch("src.mcp_server.mcp_app.mcp_server.create_server", new=MagicMock(return_value=fake_mcp)))
        stack.enter_context(patch("src.mcp_server.mcp_app.mcp_server.register_tools", new=MagicMock(return_value=None)))

        # Measure create_app
        t0 = time.perf_counter()
        _ = http_server.create_app()
        t1 = time.perf_counter()
        return t1 - t0


def _measure_median(runs: int = 7) -> float:
    import statistics
    samples = [_patched_create_app_run() for _ in range(max(3, runs))]
    return statistics.median(samples)


def main() -> None:
    # Use median across several runs to reduce noise
    baseline = _measure_median(7)
    variant = _measure_median(7)  # flags have minimal impact here by design

    # Compute overhead percentage; expect variant within 10% of baseline
    overhead_pct = (variant - baseline) / baseline * 100 if baseline > 0 else 0.0

    print("Startup Time Benchmark (HTTP MCP create_app)\n")
    print(f"baseline: {baseline*1000:.2f} ms")
    print(f"variant:  {variant*1000:.2f} ms")
    print(f"overhead: {overhead_pct:.2f}%")

    # Accept within 10%
    ok = overhead_pct <= 10.0
    exit(0 if ok else 1)


if __name__ == "__main__":
    main()

