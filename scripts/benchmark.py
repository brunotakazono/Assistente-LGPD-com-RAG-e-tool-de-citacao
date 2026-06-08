from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from dotenv import load_dotenv

from src.pipeline.cache import ExactCache, SemanticCache
from src.pipeline.rag import build_rag_pipeline
from src.pipeline.routing import classify_complexity


DEFAULT_QUERIES = [
    "O que diz o art. 18 da LGPD?",
    "Quando o consentimento pode ser revogado?",
    "Explique os princípios do art. 6 da LGPD.",
    "Quais bases legais permitem tratamento de dados pessoais?",
    "Qual a obrigação sobre incidente de seguranca no art. 48?",
]


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, int(round((percentile / 100.0) * (len(ordered) - 1)))))
    return ordered[rank]


def run_benchmark() -> dict:
    load_dotenv()
    corpus_dir = Path("data/corpus")
    pipeline = build_rag_pipeline(corpus_dir=str(corpus_dir))
    exact_cache = ExactCache()
    semantic_cache = SemanticCache(threshold=0.93)

    latencies: list[float] = []
    cache_hits = {"exact": 0, "semantic": 0}
    route_counts = {"simple": 0, "complex": 0}

    queries = list(DEFAULT_QUERIES)
    queries.extend([DEFAULT_QUERIES[0], DEFAULT_QUERIES[0].replace("art. 18", "artigo 18")])

    for query in queries:
        start = time.perf_counter()

        cached = exact_cache.get(query)
        if cached is not None:
            cache_hits["exact"] += 1
            latencies.append((time.perf_counter() - start) * 1000)
            continue

        cached = semantic_cache.get(query)
        if cached is not None:
            cache_hits["semantic"] += 1
            latencies.append((time.perf_counter() - start) * 1000)
            exact_cache.put(query, cached)
            continue

        decision = classify_complexity(query)
        route_counts[decision.complexity] += 1
        result = pipeline.answer(query)
        exact_cache.put(query, result["answer"])
        semantic_cache.put(query, result["answer"])
        latencies.append((time.perf_counter() - start) * 1000)

    report = {
        "queries": len(queries),
        "cache_hits": cache_hits,
        "route_counts": route_counts,
        "latency_ms": {
            "mean": round(statistics.fmean(latencies), 2),
            "p95": round(_percentile(latencies, 95), 2),
            "min": round(min(latencies), 2),
            "max": round(max(latencies), 2),
        },
    }
    return report


if __name__ == "__main__":
    result = run_benchmark()
    print(json.dumps(result, indent=2, ensure_ascii=False))