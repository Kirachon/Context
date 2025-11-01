"""
Lightweight Metrics (Enterprise-grade foundation)

Provides simple counters and timers with optional Prometheus integration.
Falls back to in-process storage if prometheus_client is unavailable.
"""

from __future__ import annotations

import time
import threading
from typing import Dict, Tuple, Callable

try:  # Optional dependency
    from prometheus_client import Counter as PCounter, Histogram as PHistogram  # type: ignore
except Exception:  # pragma: no cover
    PCounter = None  # type: ignore
    PHistogram = None  # type: ignore


class _InProcCounter:
    def __init__(self, name: str, documentation: str, labelnames: Tuple[str, ...] = ()):
        self.name = name
        self.doc = documentation
        self.labelnames = labelnames
        self._lock = threading.Lock()
        self._values: Dict[Tuple[str, ...], float] = {}

    def labels(self, *labelvalues: str):
        key = tuple(labelvalues)
        counter = self

        class _Child:
            def inc(self, amount: float = 1.0):
                with counter._lock:
                    counter._values[key] = counter._values.get(key, 0.0) + amount

        return _Child()


class _InProcHistogram:
    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Tuple[str, ...] = (),
        buckets: Tuple[float, ...] = (0.1, 0.5, 1, 2, 5, 10),
    ):
        self.name = name
        self.doc = documentation
        self.labelnames = labelnames
        self.buckets = buckets
        self._lock = threading.Lock()
        self._observations: Dict[Tuple[str, ...], list] = {}

    def labels(self, *labelvalues: str):
        key = tuple(labelvalues)
        hist = self

        class _Child:
            def observe(self, value: float):
                with hist._lock:
                    hist._observations.setdefault(key, []).append(value)

        return _Child()


class Metrics:
    def __init__(self):
        self._counters: Dict[str, object] = {}
        self._hists: Dict[str, object] = {}

    def counter(self, name: str, doc: str, labelnames: Tuple[str, ...] = ()):
        if name not in self._counters:
            if PCounter is not None:
                self._counters[name] = PCounter(name, doc, labelnames)
            else:
                self._counters[name] = _InProcCounter(name, doc, labelnames)
        return self._counters[name]

    def histogram(
        self,
        name: str,
        doc: str,
        labelnames: Tuple[str, ...] = (),
        buckets: Tuple[float, ...] = (0.1, 0.5, 1, 2, 5, 10),
    ):
        if name not in self._hists:
            if PHistogram is not None:
                self._hists[name] = PHistogram(name, doc, labelnames, buckets=buckets)
            else:
                self._hists[name] = _InProcHistogram(name, doc, labelnames, buckets)
        return self._hists[name]

    def timed(
        self, name: str, doc: str = "", labelnames: Tuple[str, ...] = ()
    ):  # decorator
        hist = self.histogram(name, doc, labelnames)

        def decorator(fn: Callable):
            def wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    return fn(*args, **kwargs)
                finally:
                    dur = time.perf_counter() - start
                    try:
                        hist.labels().observe(dur)
                    except Exception:
                        pass

            return wrapper

        return decorator


metrics = Metrics()
