from __future__ import annotations

from pathlib import Path

import numpy as np

from src.pipeline.cache import SemanticCache
from src.pipeline.rag import RAGPipeline
from src.pipeline.routing import classify_complexity
from src.pipeline.tools import cite_article


def test_cite_article_returns_expected_article() -> None:
    result = cite_article(18)
    assert result.startswith("Art. 18:")
    assert "direito a obter do controlador" in result
    assert "Guia correlato:" in result


def test_classify_complexity_rules() -> None:
    simple = classify_complexity("O que diz o art. 18?")
    complex_case = classify_complexity("Explique e compare os fundamentos da LGPD com exemplos práticos.")

    assert simple.complexity == "simple"
    assert simple.model
    assert complex_case.complexity == "complex"
    assert complex_case.model


def test_semantic_cache_get_matches_similar_query(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    cache = SemanticCache(threshold=0.8)
    cache._queries = ["pergunta original"]
    cache._embeddings = [np.array([1.0, 0.0, 0.0])]
    cache._answers = ["resposta cacheada"]
    monkeypatch.setattr(cache, "_embed", lambda text: np.array([0.9, 0.1, 0.0]))

    assert cache.get("pergunta parecida") == "resposta cacheada"


def test_rag_pipeline_ingest_retrieve_and_answer(monkeypatch, tmp_path) -> None:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "lgpd.md").write_text("# corpus\ntexto de teste", encoding="utf-8")

    class FakePage:
        def extract_text(self) -> str:
            return "Texto da pagina 1"

    class FakePdfReader:
        def __init__(self, path: str) -> None:
            self.pages = [FakePage()]

    class FakeSplitter:
        def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap

        def split_text(self, text: str) -> list[str]:
            return [text]

    class FakeCollection:
        def __init__(self) -> None:
            self.docs: list[str] = []

        def add(self, ids, documents, metadatas) -> None:
            self.docs.extend(documents)

        def count(self) -> int:
            return len(self.docs)

        def query(self, query_texts, n_results):
            return {
                "documents": [["Trecho relevante"]],
                "metadatas": [[{"source": "lgpd.md", "page": 1}]],
                "distances": [[0.05]],
            }

    class FakeChatCompletions:
        def create(self, model, messages, temperature):
            return type(
                "Response",
                (),
                {"choices": [type("Choice", (), {"message": type("Message", (), {"content": "Resposta final"})()})()]},
            )()

    class FakeClient:
        def __init__(self) -> None:
            self.chat = type("Chat", (), {"completions": FakeChatCompletions()})()

    monkeypatch.setattr("src.pipeline.rag.PdfReader", FakePdfReader)
    monkeypatch.setattr("src.pipeline.rag.RecursiveCharacterTextSplitter", FakeSplitter)

    pipeline = object.__new__(RAGPipeline)
    pipeline.client = FakeClient()
    pipeline.llm_model = "fake-model"
    pipeline.collection = FakeCollection()
    pipeline.corpus_dir = Path(corpus_dir)

    count = pipeline.ingest_and_index()
    assert count == 1

    hits = pipeline.retrieve("O que tem no corpus?", k=1)
    assert hits[0]["source"] == "lgpd.md"

    result = pipeline.answer("O que tem no corpus?", k=1)
    assert result["answer"] == "Resposta final"
    assert result["sources"] == [("lgpd.md", 1)]