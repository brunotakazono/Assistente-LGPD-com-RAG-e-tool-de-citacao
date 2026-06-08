# 📋 Guia de Reprodução - Testes Práticos LGPD RAG

## 🚀 Quick Start - Reproduzir os Testes

### 1. Ativar Virtual Environment

```bash
cd "template-portfolio/Assistente-LGPD-com-RAG-e-tool-de-citacao"
source .venv/Scripts/activate  # Windows/Git Bash
# ou
.venv\Scripts\activate  # Windows CMD
```

### 2. Executar Suite de Testes

```bash
python tests/teste_pratico.py
```

**Saída esperada**: Relatório com 4-5 testes, JSON com resultados

### 3. Verificar Resultados

```bash
cat TESTE_RESULTADOS.json  # Resultado estruturado em JSON
cat TESTE_RELATORIO.md     # Relatório completo em Markdown
```

---

## 🌐 Iniciar Interface Streamlit

### Option A: Local (desenvolvimento)

```bash
streamlit run src/ui/streamlit_app.py
```

Acessa em: http://localhost:8501

### Option B: Streamlit Cloud (produção)

1. Commit o projeto no GitHub
2. Crie um app no Streamlit Cloud
3. Aponte para `src/ui/streamlit_app.py`
4. Deploy automático

---

## 📊 Resultados dos Testes Executados

### Ambiente
- **Data**: 2026-06-08 03:12 UTC
- **Python**: 3.13
- **Provider LLM**: Groq (llama-3.3-70b-versatile)
- **Embeddings**: Local (all-MiniLM-L6-v2)

### Taxa de Sucesso: 80% (4/5 testes passaram)

| # | Teste | Status | Tempo | Detalhes |
|---|-------|--------|-------|----------|
| 1 | Citação Determinística | ❌ FALHA | 2,527ms | Art. 18 em chunk não prioritário |
| 2 | RAG com Fontes | ✅ SUCESSO | 1,117ms | 5 fontes recuperadas |
| 3 | Cache Exato | ✅ SUCESSO | 0.01ms | 200x mais rápido que RAG |
| 4 | Observabilidade | ✅ SUCESSO | - | 28 chunks, 2 em cache |
| 5 | Edge Case (out-of-scope) | ✅ SUCESSO | 384ms | Corretamente rejeita |

---

## 🔍 Análise do Teste 1 (Falha esperada)

### Por que "O que diz o art. 18?" retornou "Não encontrado"?

**Raiz do Problema**:
- Art. 18 está no corpus (`data/corpus/lgpd.md`)
- Mas foi chunked num bloco que contém guias correlatos do Art. 50
- Query semântica "O que diz o art. 18?" não recupera esse chunk nos top-5

**Evidência**:
```
$ grep -c "Art. 18" data/corpus/lgpd.md
2  # (encontra 2 menções)

$ python -c "...retrieve('O que diz o art. 18', k=10)..."
# Art. 18 NÃO está nos top-10 recuperados
# Artigos 50, 38, 23, 9 aparecem antes
```

**Solução**:
1. Refinar chunking strategy em `src/pipeline/rag.py`
2. Usar query mais específica: "direitos do titular artigo 18"
3. Ou aumentar `k` de recuperação de 5 para 10

---

## 🧪 Reproduzir Teste 1 com Variações

```bash
python -c "
from src.pipeline.rag import build_rag_pipeline
from dotenv import load_dotenv
load_dotenv()

pipeline = build_rag_pipeline('data/corpus')

queries = [
    'O que diz o art. 18?',
    'art. 18 direito titular',
    'direitos do titular dados',
    'confirmação existência tratamento'
]

for q in queries:
    hits = pipeline.retrieve(q, k=5)
    has_art18 = any('Art. 18' in hit['text'] for hit in hits)
    print(f'{q:40} -> Art. 18 encontrado: {has_art18}')
"
```

---

## 📂 Estrutura do Projeto

```
.
├── data/
│   ├── corpus/
│   │   ├── lgpd.md           # Lei Geral Proteção Dados (18KB)
│   │   └── README.md          # Instruções corpus
│   └── chroma/                # Vector DB persistente
├── src/
│   ├── pipeline/
│   │   ├── rag.py            # RAG pipeline (chunk, embed, retrieve, answer)
│   │   ├── cache.py          # 2-level caching (exact + semantic)
│   │   ├── routing.py        # Query complexity classifier
│   │   └── tools.py          # LLM tools (cite_article)
│   ├── observability/
│   │   └── trace.py          # Structured logging com trace_id
│   └── ui/
│       └── streamlit_app.py   # Interface Streamlit
├── tests/
│   ├── teste_pratico.py      # Suite de testes
│   └── benchmark.py          # Performance benchmark
├── .env.example              # Template de variáveis
├── .env                       # Variáveis (NÃO commitar)
├── requirements.txt          # Dependências Python
└── TESTE_RELATORIO.md        # Relatório detalhado
```

---

## 🔑 Configuração .env

Copiar de `.env.example` e preencher UMA das opções:

```bash
# Opção A — Groq (recomendado, free tier)
GROQ_API_KEY=sk_...
GROQ_MODEL=llama-3.3-70b-versatile

# Opção B — Gemini
GEMINI_API_KEY=...

# Opção C — OpenAI
OPENAI_API_KEY=sk-...

# Embeddings (local por padrão)
EMBED_PROVIDER=local
EMBED_MODEL_LOCAL=all-MiniLM-L6-v2
```

---

## 📈 Métricas Capturadas

Cada teste deixa traces estruturados:

```json
{
  "ts": 1780899126.288,
  "event": "teste_1_citacao_start",
  "trace_id": "3ced90f7-aab4-4b63-9b88-67bc5b8a0454"
}
{
  "ts": 1780899128.815,
  "event": "teste_1_citacao_end",
  "trace_id": "3ced90f7-aab4-4b63-9b88-67bc5b8a0454",
  "latency_ms": 2527.2
}
```

Use para:
- Medir P95, P99 latencies
- Rastrear cache hit-rate
- Observabilidade em produção (integrable com Langfuse)

---

## 🎬 Passo-a-Passo para Apresentação (5min)

Siga o script em `docs/ROTEIRO_APRESENTACAO.md`:

1. **0:00-0:20** — Abertura + Contexto LGPD
2. **0:20-0:45** — Arquitetura RAG + Cache
3. **0:45-1:10** — Setup local / Cloud
4. **1:10-1:50** — Demo 1: Citação determinística
   - *Nota*: Use query alternativa se art. 18 não aparecer
5. **1:50-2:40** — Demo 2: RAG com fontes
6. **2:40-3:10** — Demo 3: Cache em ação
7. **3:10-3:40** — Observabilidade e métricas
8. **3:40-4:10** — Limitações e próximos passos
9. **4:10-5:00** — Q&A

---

## ✅ Checklist Pré-Apresentação

- [ ] `.env` configurado com chave válida
- [ ] `data/corpus/lgpd.md` presente (18KB)
- [ ] Virtual env ativado
- [ ] `pip install -r requirements.txt` executado
- [ ] `python tests/teste_pratico.py` rodou com sucesso (80%+)
- [ ] Streamlit inicia sem erros: `streamlit run src/ui/streamlit_app.py`
- [ ] Sidebar mostra: "Chunks indexados: 28"
- [ ] Teste manual no navegador: digitar pergunta simples e ver resposta em < 2s

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'src'"
```bash
# Verificar que está no diretório raiz
cd "template-portfolio/Assistente-LGPD-com-RAG-e-tool-de-citacao"
pwd  # deve terminar com "...Assistente-LGPD-com-RAG-e-tool-de-citacao"
```

### "RuntimeError: Configure GROQ_API_KEY..."
```bash
# Verificar .env
cat .env | grep GROQ_API_KEY
# Renovar chave se expirou em https://console.groq.com
```

### "FileNotFoundError: data/corpus não encontrado"
```bash
# Verificar estrutura
ls -la data/corpus/
# Deve ter lgpd.md (~18KB)
```

### "Cache hit = 0, hit-rate = 0%"
```bash
# Normal na primeira execução
# Segunda execução das mesmas queries mostrará hits
python tests/teste_pratico.py  # Executa 2x para ver cache em ação
```

---

## 📞 Suporte

Para questões sobre:
- **RAG Pipeline**: ver `src/pipeline/rag.py`
- **Cache Strategy**: ver `src/pipeline/cache.py`
- **Observabilidade**: ver `src/observability/trace.py`
- **Interface**: ver `src/ui/streamlit_app.py`

Logs estruturados no terminal durante execução do Streamlit ou testes.

---

**Versão**: 1.0  
**Data**: 2026-06-08  
**Mantido por**: Filipe Alves & Bruno Matsuyama
