"""Testes de avaliação da qualidade do RAG usando a biblioteca Ragas.

Uso: `uv run pytest tests/test_eval.py -v -s`

Para destravar este teste, voce precisa de:
- TODOs 1-3 implementados em src/pipeline/rag.py
- Corpus em data/corpus/ com pelo menos 1 arquivo MD da LGPD
- .env configurado com API key
"""

from __future__ import annotations

import os
from pathlib import Path

import nest_asyncio
import pytest
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import Faithfulness, AnswerRelevancy, ContextPrecision
from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceEmbeddings

nest_asyncio.apply()


@pytest.fixture(scope="module")
def pipeline():
    """Inicializa pipeline RAG com corpus de teste."""
    pytest.importorskip("dotenv")
    from dotenv import load_dotenv

    load_dotenv()

    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("GROQ_API_KEY")):
        pytest.skip("API key nao configurada em .env")

    corpus_dir = Path("data/corpus")
    # ATENÇÃO: Mudamos de *.pdf para *.md aqui!
    if not corpus_dir.exists() or not list(corpus_dir.glob("*.md")):
        pytest.skip("data/corpus/ vazio — adicione pelo menos 1 arquivo MD")

    from src.pipeline.rag import build_rag_pipeline

    return build_rag_pipeline(corpus_dir=str(corpus_dir))


def test_ragas_metrics_quality(pipeline):
    """
    Avalia a qualidade das respostas do RAG (Fidelidade, Relevância e Precisão do Contexto).
    Gera as respostas dinamicamente usando a fixture do pipeline e avalia com RAGAS.
    """
    perguntas = [
        "Quais são os direitos do titular dos dados descritos no artigo 18?",
        "Quando o consentimento pode ser revogado segundo a LGPD?"
    ]
    gabaritos = [
        "O artigo 18 trata dos direitos do titular dos dados, como confirmação, acesso, correção e anonimização.",
        "O consentimento pode ser revogado a qualquer momento mediante manifestação expressa do titular, de forma gratuita."
    ]

    respostas_geradas = []
    contextos_recuperados = []

    for p in perguntas:
        resultado = pipeline.answer(p)
        respostas_geradas.append(resultado["answer"])
        
        textos_fonte = [doc for doc, page in resultado.get("sources", [])]
        if not textos_fonte:
            textos_fonte = ["Nenhum contexto recuperado pelo retriever."]
        contextos_recuperados.append(textos_fonte)

    data = {
        "question": perguntas,
        "answer": respostas_geradas,
        "contexts": contextos_recuperados,
        "ground_truth": gabaritos
    }
    dataset = Dataset.from_dict(data)

    juiz_llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0)
    juiz_embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    resultado_ragas = evaluate(
        dataset=dataset,
        metrics=[Faithfulness(), AnswerRelevancy(), ContextPrecision()],
        llm=juiz_llm,
        embeddings=juiz_embeddings,
    )

    df = resultado_ragas.to_pandas()

    notas = {
        "faithfulness": df["faithfulness"].mean(),
        "answer_relevancy": df["answer_relevancy"].mean(),
        "context_precision": df["context_precision"].mean(),
    }

    f_score = float(notas.get("faithfulness", 0.0))
    a_score = float(notas.get("answer_relevancy", 0.0))
    cp_score = float(notas.get("context_precision", 0.0))

    assert 0.0 <= f_score <= 1.0, f"Faithfulness fora do range esperado: {f_score}"
    assert 0.0 <= a_score <= 1.0, f"Answer Relevancy fora do range esperado: {a_score}"
    assert 0.0 <= cp_score <= 1.0, f"Context Precision fora do range esperado: {cp_score}"

    assert a_score >= 0.60, f"O RAG falhou no SLA de relevância. Nota atual: {a_score:.2f}"