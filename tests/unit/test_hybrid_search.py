"""
Unit tests for Hybrid Search (Story 5-5)
"""
from src.search.models import SearchResult
from src.search.hybrid_search import rerank


def make_result(path: str, sem: float, lex: float):
    return SearchResult(
        file_path=path,
        file_name=path.split('/')[-1],
        file_type=path.split('.')[-1] if '.' in path else 'txt',
        similarity_score=sem,
        confidence_score=sem,
        file_size=123,
        snippet=None,
        line_numbers=None,
        metadata={"lexical_score": lex},
    )


def test_rerank_hybrid_scores():
    results = [
        make_result("a.py", sem=0.9, lex=0.2),
        make_result("b.py", sem=0.4, lex=0.9),
    ]
    out = rerank(results, alpha=0.5)
    # hybrid = average of sem and lex; b.py gets 0.65, a.py gets 0.55 -> b first
    assert out[0].file_name == "b.py"

