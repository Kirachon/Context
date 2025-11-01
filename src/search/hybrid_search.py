"""
Hybrid Search (Story 5-5)

Combines lexical and semantic scores for improved ranking.
"""

from typing import List
from .models import SearchResult


def rerank(results: List[SearchResult], alpha: float = 0.7) -> List[SearchResult]:
    """
    Re-score results as: hybrid = alpha*semantic + (1-alpha)*lexical
    Assumes lexical score present in metadata['lexical_score'] if any.
    """
    rescored: List[SearchResult] = []
    for r in results:
        lex = r.metadata.get('lexical_score', r.similarity_score)  # fallback
        sem = r.similarity_score
        hybrid = alpha*sem + (1-alpha)*lex
        r.similarity_score = hybrid
        rescored.append(r)
    return sorted(rescored, key=lambda x: x.similarity_score, reverse=True)

