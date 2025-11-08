"""
Cache Warmer (feature-flagged)

Warms a small set of representative texts on startup to reduce first-request
latency. Safe, additive, and completely optional.
"""
from __future__ import annotations

from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


def get_default_warm_texts() -> List[str]:
    """Return a small set of texts to warm embeddings for.

    Uses template bodies if available; falls back to generic strings.
    """
    try:
        from src.ai_processing.template_library import TEMPLATES  # type: ignore
        # Use up to 5 templates to keep warm-up fast
        return [TEMPLATES[name] for name in list(TEMPLATES.keys())[:5]]
    except Exception:
        return [
            "Search README for setup instructions",
            "Implement CRUD API with FastAPI and SQLAlchemy",
            "Write pytest unit tests for a service function",
            "Optimize database query using an index",
            "Add logging and metrics to the HTTP server",
        ]


class CacheWarmer:
    async def warm_common_texts(self, *, embedder, cache, model: str, texts: Optional[List[str]] = None) -> int:
        """Warm embeddings for provided or default texts. Returns warmed count."""
        data = texts or get_default_warm_texts()
        if not data:
            return 0
        try:
            # Prefer batch embedding for efficiency
            if hasattr(embedder, "generate_batch_embeddings"):
                embeddings = await embedder.generate_batch_embeddings(data)
                warmed = 0
                for t, emb in zip(data, embeddings):
                    if emb is not None:
                        try:
                            cache.set(t, emb, model)
                            warmed += 1
                        except Exception as e:
                            logger.debug(f"Cache set failed during warming: {e}")
                return warmed
            else:
                warmed = 0
                for t in data:
                    emb = await embedder.generate_embedding(t)
                    if emb is not None:
                        try:
                            cache.set(t, emb, model)
                            warmed += 1
                        except Exception as e:
                            logger.debug(f"Cache set failed during warming: {e}")
                return warmed
        except Exception as e:
            logger.warning(f"Cache warm failed: {e}")
            return 0


async def run_on_startup() -> int:
    """Convenience entry point used by server startup."""
    try:
        from src.vector_db.embeddings import get_embedding_service
        from src.search.embedding_cache import get_embedding_cache

        svc = get_embedding_service()
        cache = get_embedding_cache()
        model = getattr(svc, "model_name", "unknown")
        warmer = CacheWarmer()
        warmed = await warmer.warm_common_texts(embedder=svc, cache=cache, model=model)
        logger.info(f"Cache warming completed: warmed={warmed}")
        return warmed
    except Exception as e:
        logger.error(f"Cache warming failed: {e}")
        return 0

