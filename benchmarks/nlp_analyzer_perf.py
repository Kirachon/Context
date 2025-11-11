import time
import tracemalloc
import random
from typing import List
import os
import sys

# Ensure project root on sys.path
sys.path.insert(0, os.path.abspath("."))

from src.ai_processing.nlp_analyzer import NLPAnalyzer


def make_samples(n: int = 200) -> List[str]:
    phrases = [
        "Implement a REST API for user login and JWT refresh.",
        "Refactor the parser to support TypeScript generics.",
        "Google moved its HQ from Mountain View to a new campus.",
        "Create a Docker Compose file with Redis, Postgres, and Qdrant.",
        "Fix race condition in async file monitor when deleting files.",
        "Add integration tests for the MCP HTTP endpoint /prompt.generate.",
        "Optimize vector search top_k=10 and re-rank by BM25.",
        "Kubernetes deployment needs liveness/readiness probes.",
        "Document feature flags enable_code_generation and enable_realtime_monitoring.",
        "Investigate memory leak reported in session manager cleanup.",
    ]
    out = []
    for _ in range(n):
        s = random.choice(phrases)
        out.append(s)
    return out


def run_benchmark() -> None:
    analyzer = NLPAnalyzer()
    if not analyzer.available:
        print("NLPAnalyzer not available (spaCy/model missing). Skipping perf run.")
        return

    samples = make_samples(200)

    # Warm-up
    for _ in range(5):
        analyzer.analyze_text(samples[_])

    tracemalloc.start()
    t0 = time.perf_counter()
    for s in samples:
        analyzer.analyze_text(s)
    t1 = time.perf_counter()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    per_doc_ms = (t1 - t0) * 1000.0 / len(samples)
    print("NLPAnalyzer Performance\n")
    print(f"docs:      {len(samples)}")
    print(f"avg/doc:   {per_doc_ms:.2f} ms")
    print(f"peak mem:  {peak/1024/1024:.2f} MB")


if __name__ == "__main__":
    run_benchmark()

