"""Model routing cheap-first com fallback.

Reaproveita o notebook 05. Voce vai preencher 1 TODO aqui.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from openai import OpenAI


@dataclass(frozen=True)
class RouteDecision:
    model: str
    complexity: str  # "simple" | "complex"
    reason: str


# ------------------------------------------------------------------ TODO 6
def classify_complexity(query: str) -> RouteDecision:
    """Classifica complexidade da query para escolher modelo (cheap vs premium).

    Estrategia heuristica simples. Em producao, evoluiria para classifier treinado.
    """
    cheap_model = os.environ.get("CHEAP_MODEL", "gemini-2.5-flash-lite")
    premium_model = os.environ.get("PREMIUM_MODEL", "gemini-2.5-pro")

    normalized_query = query.strip().lower()
    complex_markers = (
        "explique",
        "compare",
        "analise",
        "analise",
        "projet",
        "arquitet",
        "estruture",
        "avali",
        "justifique",
        "por que",
    )

    if any(marker in normalized_query for marker in complex_markers):
        return RouteDecision(
            model=premium_model,
            complexity="complex",
            reason="A query contem termos que pedem analise, comparacao ou decisao arquitetural.",
        )

    if len(normalized_query) < 60 and normalized_query.endswith("?"):
        return RouteDecision(
            model=cheap_model,
            complexity="simple",
            reason="A query e curta e objetiva, entao o modelo barato deve bastar.",
        )

    if len(normalized_query) > 140:
        return RouteDecision(
            model=premium_model,
            complexity="complex",
            reason="A query e longa e tende a precisar de mais contexto e raciocinio.",
        )

    return RouteDecision(
        model=cheap_model,
        complexity="simple",
        reason="Nao houve sinal forte de complexidade, entao usei o caminho cheap-first.",
    )


def make_client() -> OpenAI:
    """Cliente OpenAI-compatible para o provider configurado."""
    if "GEMINI_API_KEY" in os.environ:
        return OpenAI(
            api_key=os.environ["GEMINI_API_KEY"],
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    return OpenAI()
