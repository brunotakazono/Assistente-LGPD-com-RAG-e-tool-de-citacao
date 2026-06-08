"""Cache em 2 niveis: exact-match (SHA256) + semantic (cosine similarity).

Reaproveita o notebook 05. Voce vai preencher 1 TODO aqui.
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import Any

import numpy as np
from openai import OpenAI


def _fallback_embedding(text: str, dimensions: int = 384) -> np.ndarray:
    vector = np.zeros(dimensions, dtype=float)
    tokens = re.findall(r"\w+", text.lower(), flags=re.UNICODE)

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        vector[index] += 1.0

    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        return vector
    return vector / norm


class ExactCache:
    """Cache por hash SHA256 da query. Captura replays exatos (~10-15% das queries)."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    @staticmethod
    def _key(query: str) -> str:
        return hashlib.sha256(query.encode()).hexdigest()

    def get(self, query: str) -> str | None:
        return self._store.get(self._key(query))

    def put(self, query: str, answer: str) -> None:
        self._store[self._key(query)] = answer

    def stats(self) -> dict[str, int]:
        return {"size": len(self._store)}


class SemanticCache:
    """Cache por similaridade de embedding. Captura parafrases (~20% adicional)."""

    def __init__(self, threshold: float = 0.93) -> None:
        self.threshold = threshold
        self._queries: list[str] = []
        self._embeddings: list[np.ndarray] = []
        self._answers: list[str] = []
        self._local_model: Any | None = None

        # Inicializa cliente para embeddings (mesmo provider do RAG)
        if os.environ.get("EMBED_PROVIDER", "local").lower() == "local":
            self._client = None
            self._embed_model = os.environ.get("EMBED_MODEL_LOCAL", "all-MiniLM-L6-v2")
            return

        if "GEMINI_API_KEY" in os.environ:
            self._client = OpenAI(
                api_key=os.environ["GEMINI_API_KEY"],
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )
            self._embed_model = os.environ.get("EMBED_MODEL", "gemini-embedding-001")
        else:
            self._client = OpenAI()
            self._embed_model = "text-embedding-3-small"

    def _embed(self, text: str) -> np.ndarray:
        if self._client is None:
            if self._local_model is None:
                try:
                    from sentence_transformers import SentenceTransformer

                    self._local_model = SentenceTransformer(self._embed_model)
                except Exception:
                    self._local_model = False
            if self._local_model:
                return np.array(self._local_model.encode(text, normalize_embeddings=True))
            return _fallback_embedding(text)

        r = self._client.embeddings.create(model=self._embed_model, input=text)
        return np.array(r.data[0].embedding)

    # ------------------------------------------------------------------ TODO 5
    def get(self, query: str) -> str | None:
        """Retorna resposta cacheada se similar a query alguma anterior, OU None."""
        if not self._queries:
            return None

        query_embedding = self._embed(query)
        similarities: list[float] = []

        for cached_embedding in self._embeddings:
            denominator = float(np.linalg.norm(query_embedding) * np.linalg.norm(cached_embedding))
            if denominator == 0.0:
                similarities.append(-1.0)
                continue
            similarities.append(float(np.dot(query_embedding, cached_embedding) / denominator))

        if not similarities:
            return None

        best_index = int(np.argmax(similarities))
        if similarities[best_index] >= self.threshold:
            return self._answers[best_index]
        return None

    def put(self, query: str, answer: str) -> None:
        self._queries.append(query)
        self._embeddings.append(self._embed(query))
        self._answers.append(answer)

    def stats(self) -> dict[str, Any]:
        return {"size": len(self._queries), "threshold": self.threshold}
