"""
NLP Analyzer (spaCy-backed, optional)

Provides additive, non-breaking NLP capabilities for prompt and query analysis:
- Named Entity Recognition (NER)
- Keyword extraction (noun/proper-noun heuristics)
- Text similarity (spaCy vectors if available; Jaccard fallback)

Design goals:
- Lazy import and model loading (no hard dependency at import time)
- Graceful degradation if spaCy/model are not installed
- Backward compatible: never raises if NLP is unavailable
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

from src.config.settings import settings

logger = logging.getLogger(__name__)


class NLPAnalyzer:
    """Wrapper around spaCy pipeline with safe fallbacks."""

    def __init__(self, model_name: Optional[str] = None):
        self._spacy = None  # type: ignore
        self._nlp = None
        self._model_name = model_name or settings.nlp_model
        self._available: Optional[bool] = None

    def _import_spacy(self) -> bool:
        if self._spacy is not None:
            return True
        try:
            import spacy  # type: ignore

            self._spacy = spacy
            return True
        except Exception as e:  # pragma: no cover - environment dependent
            logger.info("spaCy not available: %s", e)
            self._spacy = None
            return False

    def _ensure_model(self) -> bool:
        if self._nlp is not None:
            return True
        if not self._import_spacy():
            self._available = False
            return False
        try:
            self._nlp = self._spacy.load(self._model_name)
            self._available = True
            return True
        except Exception as e:  # pragma: no cover - environment dependent
            logger.info("spaCy model '%s' not available: %s", self._model_name, e)
            self._nlp = None
            self._available = False
            return False

    @property
    def available(self) -> bool:
        if self._available is None:
            self._ensure_model()
        return bool(self._available)

    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze text and return NLP findings with safe fallbacks."""
        if not text:
            return {
                "available": self.available,
                "entities": [],
                "keywords": [],
                "num_tokens": 0,
            }

        if not self._ensure_model():
            # Fallback: basic keyword extraction via simple heuristics
            keywords = self._fallback_keywords(text)
            return {
                "available": False,
                "entities": [],
                "keywords": keywords,
                "num_tokens": len(text.split()),
            }

        # Protect performance with max length
        clipped = text[: settings.nlp_max_doc_length]
        doc = self._nlp(clipped)

        entities = [
            {
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
            }
            for ent in doc.ents
        ]

        # Heuristic keywords: unique nouns/proper nouns (lowercased), len>=3
        kw_set: Set[str] = set(
            t.lemma_.lower()
            for t in doc
            if (t.pos_ in {"NOUN", "PROPN"}) and len(t.lemma_) >= 3 and t.is_alpha and not t.is_stop
        )
        keywords = sorted(list(kw_set))[:25]

        return {
            "available": True,
            "entities": entities,
            "keywords": keywords,
            "num_tokens": len([t for t in doc if not t.is_space]),
        }

    def similarity(self, a: str, b: str) -> Optional[float]:
        """Compute similarity using spaCy vectors if available, else Jaccard."""
        if not a or not b:
            return None
        if self._ensure_model():
            try:
                da = self._nlp(a[: settings.nlp_max_doc_length])
                db = self._nlp(b[: settings.nlp_max_doc_length])
                # Some small models may not have vectors; spaCy returns 0.0 but valid
                return float(da.similarity(db))
            except Exception:  # pragma: no cover - spaCy internals
                pass
        # Fallback: Jaccard similarity over token sets
        set_a = {t.lower() for t in a.split() if len(t) >= 3}
        set_b = {t.lower() for t in b.split() if len(t) >= 3}
        if not set_a or not set_b:
            return 0.0
        inter = len(set_a & set_b)
        union = len(set_a | set_b)
        return inter / union if union else 0.0

    @staticmethod
    def _fallback_keywords(text: str) -> List[str]:
        words = [w.strip(".,:;!?") for w in text.split()]
        words = [w.lower() for w in words if len(w) >= 3 and w.isalpha()]
        seen: Set[str] = set()
        out: List[str] = []
        for w in words:
            if w not in seen:
                seen.add(w)
                out.append(w)
            if len(out) >= 25:
                break
        return out


# Singleton accessor
_nlp_analyzer: Optional[NLPAnalyzer] = None


def get_nlp_analyzer() -> NLPAnalyzer:
    global _nlp_analyzer
    if _nlp_analyzer is None:
        _nlp_analyzer = NLPAnalyzer()
    return _nlp_analyzer

