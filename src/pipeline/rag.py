"""RAG pipeline — chunk, embed, index, retrieve, generate.

Reaproveita as funcoes do notebook 02. Voce vai preencher 3 TODOs aqui.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from openai import OpenAI


def _fallback_embedding(text: str, dimensions: int = 384) -> list[float]:
    vector = [0.0] * dimensions
    tokens = re.findall(r"\w+", text.lower(), flags=re.UNICODE)

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        vector[index] += 1.0

    norm = sum(value * value for value in vector) ** 0.5
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]


class _FallbackEmbeddingFunction:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def name(self) -> str:
        return self.model_name

    def __call__(self, input: list[str]) -> list[list[float]]:
        return [_fallback_embedding(text) for text in input]

    def embed_documents(self, input: list[str]) -> list[list[float]]:
        return self(input)

    def embed_query(self, input: str | list[str]) -> list[float]:
        if isinstance(input, list):
            input = input[0] if input else ""
        return [_fallback_embedding(input)]


def _make_client() -> tuple[OpenAI, str]:
    """Inicializa cliente OpenAI-compatible conforme provider escolhido no .env."""
    if "GROQ_API_KEY" in os.environ:
        client = OpenAI(
            api_key=os.environ["GROQ_API_KEY"],
            base_url="https://api.groq.com/openai/v1",
        )
        return client, "groq"
    if "GEMINI_API_KEY" in os.environ:
        client = OpenAI(
            api_key=os.environ["GEMINI_API_KEY"],
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        return client, "gemini"
    elif "OPENAI_API_KEY" in os.environ:
        client = OpenAI()
        return client, "openai"
    else:
        raise RuntimeError("Configure GROQ_API_KEY, GEMINI_API_KEY ou OPENAI_API_KEY no .env")


def _make_embedding_function(embed_model: str) -> Any:
    """Cria a função de embedding.

    Use embeddings locais por padrão para permitir demo com uma única chave
    do Groq. Se quiser embeddings remotos, defina EMBED_PROVIDER=remote.
    """
    provider = os.environ.get("EMBED_PROVIDER", "local").lower()
    if provider == "remote":
        if "GEMINI_API_KEY" in os.environ:
            embed_kwargs: dict[str, Any] = {
                "api_key": os.environ["GEMINI_API_KEY"],
                "model_name": embed_model,
                "api_base": "https://generativelanguage.googleapis.com/v1beta/openai/",
            }
            return OpenAIEmbeddingFunction(**embed_kwargs)
        if "OPENAI_API_KEY" in os.environ:
            return OpenAIEmbeddingFunction(
                api_key=os.environ["OPENAI_API_KEY"],
                model_name=embed_model,
            )
        raise RuntimeError("EMBED_PROVIDER=remote requer GEMINI_API_KEY ou OPENAI_API_KEY")

    try:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

        return SentenceTransformerEmbeddingFunction(model_name=os.environ.get("EMBED_MODEL_LOCAL", "all-MiniLM-L6-v2"))
    except Exception:
        return _FallbackEmbeddingFunction(os.environ.get("EMBED_MODEL_LOCAL", "fallback-hash-embedding"))


class RAGPipeline:
    """Pipeline RAG end-to-end com Chroma local."""

    def __init__(
        self,
        corpus_dir: str = "data/corpus",
        persist_dir: str = "data/chroma",
        collection_name: str = "docs",
        llm_model: str | None = None,
        embed_model: str | None = None,
    ) -> None:
        self.client, provider = _make_client()
        if provider == "groq":
            self.llm_model = llm_model or os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
        elif provider == "gemini":
            self.llm_model = llm_model or os.environ.get("LLM_MODEL", "gemini-2.5-flash-lite")
        else:
            self.llm_model = llm_model or os.environ.get("LLM_MODEL", "gpt-4o-mini")

        self.embed_model = embed_model or os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
        self.embed_fn = _make_embedding_function(self.embed_model)

        self.corpus_dir = Path(corpus_dir)
        self.persist_dir = persist_dir
        self.collection_name = collection_name

        chroma = chromadb.PersistentClient(path=persist_dir)
        self.collection = chroma.get_or_create_collection(
            name=collection_name, embedding_function=self.embed_fn
        )

    # ------------------------------------------------------------------ TODO 1
    def ingest_and_index(self) -> int:
        """Le arquivos de `corpus_dir`, faz chunking e indexa em Chroma.

        Retorna numero de chunks indexados.

        Ja deixei a estrutura do ciclo. Voce completa as 3 partes marcadas.
        """
        docs: list[dict] = []

        if not self.corpus_dir.exists():
            raise FileNotFoundError(f"Diretorio do corpus nao encontrado: {self.corpus_dir}")

        for corpus_path in sorted(self.corpus_dir.iterdir()):
            if not corpus_path.is_file():
                continue

            suffix = corpus_path.suffix.lower()
            if suffix == ".pdf":
                reader = PdfReader(str(corpus_path))
                for page_index, page in enumerate(reader.pages, start=1):
                    text = (page.extract_text() or "").strip()
                    if text:
                        docs.append({"text": text, "source": corpus_path.name, "page": page_index})
            elif suffix in {".md", ".txt"}:
                text = corpus_path.read_text(encoding="utf-8").strip()
                if text:
                    docs.append({"text": text, "source": corpus_path.name, "page": 1})

        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        chunks: list[dict] = []

        for doc in docs:
            for chunk_index, chunk_text in enumerate(splitter.split_text(doc["text"])):
                chunk_text = chunk_text.strip()
                if not chunk_text:
                    continue
                chunks.append(
                    {
                        "id": f"{doc['source']}-p{doc['page']}-c{chunk_index}",
                        "text": chunk_text,
                        "source": doc["source"],
                        "page": doc["page"],
                    }
                )

        if chunks:
            self.collection.add(
                ids=[chunk["id"] for chunk in chunks],
                documents=[chunk["text"] for chunk in chunks],
                metadatas=[{"source": chunk["source"], "page": chunk["page"]} for chunk in chunks],
            )

        return self.collection.count()

    # ------------------------------------------------------------------ TODO 2
    def retrieve(self, query: str, k: int = 5) -> list[dict]:
        """Busca top-k chunks similares a query."""
        result = self.collection.query(query_texts=[query], n_results=k)
        documents = result.get("documents", [[]])
        metadatas = result.get("metadatas", [[]])
        distances = result.get("distances", [[]])

        hits: list[dict] = []
        for index, text in enumerate(documents[0]):
            metadata = metadatas[0][index] if metadatas and metadatas[0] else {}
            distance = distances[0][index] if distances and distances[0] else None
            hits.append(
                {
                    "text": text,
                    "source": metadata.get("source", "unknown"),
                    "page": metadata.get("page", 0),
                    "distance": distance,
                }
            )

        return hits

    # ------------------------------------------------------------------ TODO 3
    def answer(self, question: str, k: int = 5) -> dict:
        """Pipeline completo: retrieve + augment + generate. Retorna {answer, sources}."""
        hits = self.retrieve(question, k=k)
        context = "\n\n---\n\n".join(
            f"[{hit['source']}:p{hit['page']}]\n{hit['text']}" for hit in hits
        )
        prompt = PROMPT_TEMPLATE.format(context=context, question=question)

        response = self.client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": "Voce responde apenas com base no contexto fornecido."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )

        answer_text = response.choices[0].message.content or ""
        return {"answer": answer_text, "sources": [(hit["source"], hit["page"]) for hit in hits]}


PROMPT_TEMPLATE = """Voce e um assistente tecnico. Responda APENAS com base no contexto abaixo.
Se a informacao nao estiver no contexto, diga "Nao encontrado no corpus".
Sempre cite a fonte usando o formato [arquivo:pagina].

CONTEXTO:
{context}

PERGUNTA: {question}

RESPOSTA:"""


def build_rag_pipeline(corpus_dir: str = "data/corpus") -> RAGPipeline:
    """Factory: cria pipeline e indexa corpus se ainda nao indexado."""
    pipeline = RAGPipeline(corpus_dir=corpus_dir)
    if pipeline.collection.count() == 0:
        pipeline.ingest_and_index()
    return pipeline
