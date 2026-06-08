#!/usr/bin/env python
"""Script de teste prático — simula os 5 testes do roteiro de apresentação.

Executa:
1. Teste 1: Citação determinística (O que diz o art. 18?)
2. Teste 2: RAG com fontes (Deveres do controlador)
3. Teste 3: Cache exato (repetir art. 18)
4. Teste 4: Observabilidade e métricas
5. Teste 5: Pergunta fora do escopo (Capital do Brasil)
"""

import json
import sys
from pathlib import Path
from datetime import datetime

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv()

from src.pipeline.rag import build_rag_pipeline
from src.pipeline.cache import ExactCache, SemanticCache
from src.pipeline.routing import classify_complexity
from src.observability.trace import trace, log_event


def run_tests():
    """Executa os 5 testes e registra resultados."""

    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": [],
        "metrics": {}
    }

    print("=" * 80)
    print("TESTES PRÁTICOS - Assistente LGPD com RAG e Ferramenta de Citação")
    print("=" * 80)
    print()

    # Inicializa pipeline e caches
    print("[SETUP] Inicializando pipeline e caches...")
    with trace("setup") as ctx:
        pipeline = build_rag_pipeline("data/corpus")
        exact_cache = ExactCache()
        semantic_cache = SemanticCache(threshold=0.93)

        print(f"  [OK] Pipeline iniciado")
        print(f"  [OK] Chunks indexados: {pipeline.collection.count()}")
        print(f"  [OK] Caches inicializados")
    print()

    # Teste 1: Citação Determinística
    print("-" * 80)
    print("TESTE 1: Citação Determinística (T=1:10 do script)")
    print("-" * 80)
    pergunta_1 = "O que diz o art. 18?"
    print(f"Pergunta: {pergunta_1}")
    print()

    with trace("teste_1_citacao") as ctx:
        # Verifica cache exato
        cached = exact_cache.get(pergunta_1)
        if cached:
            print("  [CACHE HIT] Exact cache hit")
            resposta = cached
            cache_status = "exact_hit"
        else:
            print("  [CACHE MISS] Recuperando via RAG...")
            resposta_dict = pipeline.answer(pergunta_1, k=1)
            resposta = resposta_dict["answer"]
            sources = resposta_dict["sources"]
            exact_cache.put(pergunta_1, resposta)
            cache_status = "miss"

        print(f"\nResposta (primeiras 200 chars):")
        print(f"  {resposta[:200]}...")

        test_result = {
            "numero": 1,
            "titulo": "Citação Determinística",
            "pergunta": pergunta_1,
            "cache_status": cache_status,
            "resposta_length": len(resposta),
            "sucesso": len(resposta) > 50 and "art" in resposta.lower()
        }
        results["tests"].append(test_result)
    print()

    # Teste 2: RAG com Fontes
    print("-" * 80)
    print("TESTE 2: RAG com Fontes (T=1:50 do script)")
    print("-" * 80)
    pergunta_2 = "Quais são os deveres do controlador segundo a LGPD?"
    print(f"Pergunta: {pergunta_2}")
    print()

    with trace("teste_2_rag") as ctx:
        cached = exact_cache.get(pergunta_2)
        if cached:
            print("  [CACHE HIT] Exact cache hit")
            resposta = cached
            cache_status = "exact_hit"
        else:
            print("  [RAG QUERY] Consultando corpus...")
            resposta_dict = pipeline.answer(pergunta_2, k=5)
            resposta = resposta_dict["answer"]
            sources = resposta_dict["sources"]
            exact_cache.put(pergunta_2, resposta)

            print(f"  [OK] Fontes recuperadas: {len(sources)}")
            for source, page in sources[:3]:
                print(f"    - {source}:p{page}")
            cache_status = "miss"

        print(f"\nResposta (primeiras 250 chars):")
        print(f"  {resposta[:250]}...")

        test_result = {
            "numero": 2,
            "titulo": "RAG com Fontes",
            "pergunta": pergunta_2,
            "cache_status": cache_status,
            "resposta_length": len(resposta),
            "fontes_count": len(sources) if not cached else "N/A",
            "sucesso": len(resposta) > 50 and "controlador" in resposta.lower()
        }
        results["tests"].append(test_result)
    print()

    # Teste 3: Cache Exato em Ação
    print("-" * 80)
    print("TESTE 3: Cache Exato em Ação (T=2:40 do script)")
    print("-" * 80)
    pergunta_3 = "O que diz o art. 18?"  # Mesma do teste 1
    print(f"Pergunta: {pergunta_3}")
    print()

    with trace("teste_3_cache_exact") as ctx:
        import time
        start = time.time()

        cached = exact_cache.get(pergunta_3)
        if cached:
            latencia_ms = (time.time() - start) * 1000
            print(f"  [OK] [CACHE HIT] Exact cache hit")
            print(f"  [OK] Latência: {latencia_ms:.1f}ms")
            resposta = cached
            cache_status = "exact_hit"
        else:
            print("  [ERRO] Erro: esperava cache hit mas obteve miss")
            cache_status = "unexpected_miss"
            latencia_ms = None
            resposta = None

        test_result = {
            "numero": 3,
            "titulo": "Cache Exato em Ação",
            "pergunta": pergunta_3,
            "cache_status": cache_status,
            "latencia_ms": latencia_ms,
            "sucesso": cache_status == "exact_hit" and (latencia_ms or 0) < 100
        }
        results["tests"].append(test_result)
    print()

    # Teste 4: Observabilidade e Métricas
    print("-" * 80)
    print("TESTE 4: Observabilidade e Métricas (T=3:10 do script)")
    print("-" * 80)

    exact_stats = exact_cache.stats()
    semantic_stats = semantic_cache.stats()

    print(f"  Chunks indexados: {pipeline.collection.count()}")
    print(f"  Exact cache size: {exact_stats['size']}")
    print(f"  Semantic cache size: {semantic_stats['size']}")
    print(f"  Semantic cache threshold: {semantic_stats['threshold']}")

    test_result = {
        "numero": 4,
        "titulo": "Observabilidade e Métricas",
        "chunks_indexados": pipeline.collection.count(),
        "exact_cache_size": exact_stats['size'],
        "semantic_cache_size": semantic_stats['size'],
        "sucesso": pipeline.collection.count() > 0 and exact_stats['size'] >= 2
    }
    results["tests"].append(test_result)
    results["metrics"] = {
        "chunks_indexed": pipeline.collection.count(),
        "exact_cache_stats": exact_stats,
        "semantic_cache_stats": semantic_stats
    }
    print()

    # Teste 5: Pergunta fora do escopo
    print("-" * 80)
    print("TESTE 5: Pergunta fora do escopo (Edge Case)")
    print("-" * 80)
    pergunta_5 = "Qual é a capital do Brasil?"
    print(f"Pergunta: {pergunta_5}")
    print()

    with trace("teste_5_out_of_scope") as ctx:
        cached = exact_cache.get(pergunta_5)
        if cached:
            print("  [CACHE HIT] Exact cache hit")
            resposta = cached
            cache_status = "exact_hit"
        else:
            print("  [RAG QUERY] Consultando corpus...")
            resposta_dict = pipeline.answer(pergunta_5, k=3)
            resposta = resposta_dict["answer"]
            exact_cache.put(pergunta_5, resposta)
            cache_status = "miss"

        print(f"\nResposta:")
        print(f"  {resposta}")

        # Verifica se indicou que não está no corpus
        out_of_scope = "não encontrado" in resposta.lower() or "corpus" in resposta.lower() or "no encontrado" in resposta.lower()

        test_result = {
            "numero": 5,
            "titulo": "Pergunta fora do escopo",
            "pergunta": pergunta_5,
            "cache_status": cache_status,
            "resposta_length": len(resposta),
            "out_of_scope": out_of_scope,
            "sucesso": out_of_scope
        }
        results["tests"].append(test_result)
    print()

    # Resumo final
    print("=" * 80)
    print("RESUMO FINAL")
    print("=" * 80)

    total_testes = len(results["tests"])
    testes_sucesso = sum(1 for t in results["tests"] if t["sucesso"])

    for test in results["tests"]:
        status_icon = "[OK]" if test["sucesso"] else "[ERRO]"
        print(f"{status_icon} Teste {test['numero']}: {test['titulo']}")

    print()
    print(f"Total: {testes_sucesso}/{total_testes} testes passaram")
    print()

    # Salva resultados em JSON
    output_file = Path("TESTE_RESULTADOS.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Resultados salvos em: {output_file}")
    print("=" * 80)

    return testes_sucesso == total_testes


if __name__ == "__main__":
    sucesso = run_tests()
    sys.exit(0 if sucesso else 1)
