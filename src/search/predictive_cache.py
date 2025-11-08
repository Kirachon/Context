"""
Predictive Cache (feature-flagged)

Lightweight, in-memory predictor for next-likely embedding requests based on
recent query frequency. Designed to be safe, additive, and inexpensive.

- No external dependencies
- Thread-safe enough for typical asyncio usage (single-process server)
- Graceful no-op if not enabled
"""
from __future__ import annotations

from collections import Counter, deque
from typing import Deque, Dict, List, Optional, Iterable
import asyncio
import logging

logger = logging.getLogger(__name__)


class PredictiveCache:
    """Simple frequency-based predictor with bounded history.

    Records recently-embedded texts and returns top-N most frequent other texts
    as next-likely predictions.
    """

    def __init__(self, max_history: int = 1000) -> None:
        self._history: Deque[str] = deque(maxlen=max_history)
        self._freq: Counter[str] = Counter()

    def record(self, text: str) -> None:
        if not text:
            return
        self._history.append(text)
        self._freq[text] += 1

    def get_predictions(self, current_text: str, top_n: int = 3) -> List[str]:
        """Return top-N frequent texts seen recently (excluding current).

        Very simple heuristic; can be extended to session-aware or token-aware later.
        """
        preds: List[str] = []
        for item, _count in self._freq.most_common():
            if item and item != current_text:
                preds.append(item)
            if len(preds) >= top_n:
                break
        return preds

    async def prefetch_async(
        self,
        texts: Iterable[str],
        *,
        embedder,  # EmbeddingService instance (expects generate_batch_embeddings)
        cache,     # EmbeddingCache instance (expects set(text, embedding, model))
        model: str,
    ) -> None:
        """Prefetch embeddings for texts and populate EmbeddingCache.

        This runs as a background task; errors are logged but never raised.
        """
        try:
            batch = [t for t in texts if t and t.strip()]
            if not batch:
                return
            # Prefer batch operation if available
            if hasattr(embedder, "generate_batch_embeddings"):
                embeddings = await embedder.generate_batch_embeddings(batch)  # type: ignore[attr-defined]
                for t, emb in zip(batch, embeddings):
                    if emb is not None:
                        try:
                            cache.set(t, emb, model)
                        except Exception as e:
                            logger.debug(f"Cache set failed during prefetch: {e}")
            else:
                # Fallback to sequential
                for t in batch:
                    emb = await embedder.generate_embedding(t)
                    if emb is not None:
                        try:
                            cache.set(t, emb, model)
                        except Exception as e:
                            logger.debug(f"Cache set failed during prefetch: {e}")
        except Exception as e:
            logger.debug(f"Predictive prefetch encountered error: {e}")


# Singleton accessor
_predictive_cache: Optional[PredictiveCache] = None


def get_predictive_cache() -> PredictiveCache:
    global _predictive_cache
    if _predictive_cache is None:
        _predictive_cache = PredictiveCache()
    return _predictive_cache

