"""Function-calling / tool-use — registro de tools usadas pelo agente.

Reaproveita o LAB-001. Esta versao implementa uma tool real para a LGPD,
baseada em um corpus Markdown local em `data/corpus/lgpd.md`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable


LGPD_CORPUS_PATH = Path("data/corpus/lgpd.md")
ARTICLE_HEADER_RE = re.compile(r"^##\s*Art\.\s*(\d+)")


def _load_lgpd_articles() -> dict[int, tuple[str, str]]:
    """Carrega artigos e guias correlatos a partir do corpus Markdown."""
    if not LGPD_CORPUS_PATH.exists():
        return {}

    articles: dict[int, tuple[str, str]] = {}
    current_article: int | None = None
    article_lines: list[str] = []
    guide_lines: list[str] = []
    in_guide = False

    def flush_current() -> None:
        nonlocal current_article, article_lines, guide_lines, in_guide
        if current_article is not None:
            articles[current_article] = (
                "\n".join(article_lines).strip(),
                "\n".join(guide_lines).strip(),
            )
        current_article = None
        article_lines = []
        guide_lines = []
        in_guide = False

    for raw_line in LGPD_CORPUS_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()

        match = ARTICLE_HEADER_RE.match(line)
        if match:
            flush_current()
            current_article = int(match.group(1))
            continue

        if current_article is None:
            continue

        if line.strip() == "### Guia correlato":
            in_guide = True
            continue

        if in_guide:
            guide_lines.append(line)
        else:
            article_lines.append(line)

    flush_current()
    return articles


def cite_article(article_number: int) -> str:
    """Retorna o artigo informado da LGPD e uma nota de guia correlato."""
    articles = _load_lgpd_articles()
    if not articles:
        return (
            "ERROR: corpus LGPD nao encontrado em data/corpus/lgpd.md. "
            "Adicione o arquivo com os artigos em Markdown e tente novamente."
        )

    if article_number not in articles:
        available = ", ".join(str(number) for number in sorted(articles))
        return f"ERROR: artigo {article_number} nao encontrado. Artigos disponiveis: {available}"

    article_text, guide_note = articles[article_number]
    parts = [f"Art. {article_number}:", article_text]
    if guide_note:
        parts.extend(["", "Guia correlato:", guide_note])
    return "\n".join(parts).strip()


TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "cite_article",
            "description": "Retorna o texto do artigo informado da LGPD e uma nota de guia correlato em Markdown.",
            "parameters": {
                "type": "object",
                "properties": {
                    "article_number": {
                        "type": "integer",
                        "description": "Numero do artigo da LGPD a citar, por exemplo 6, 7, 8 ou 18.",
                    }
                },
                "required": ["article_number"],
                "additionalProperties": False,
            },
        },
    },
]


TOOL_REGISTRY: dict[str, Callable[..., str]] = {
    "cite_article": cite_article,
}


def run_tool_call(name: str, arguments_json: str) -> str:
    """Executa uma tool call e retorna o resultado como string."""
    if name not in TOOL_REGISTRY:
        return f"ERROR: tool '{name}' nao registrada"
    try:
        kwargs = json.loads(arguments_json)
        return TOOL_REGISTRY[name](**kwargs)
    except Exception as e:
        return f"ERROR ao executar {name}: {e}"
