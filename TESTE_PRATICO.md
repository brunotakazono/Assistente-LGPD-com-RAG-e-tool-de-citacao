# Teste Prático - Assistente LGPD com RAG e Ferramenta de Citação

**Data**: 2026-06-08  
**Objetivo**: Validar funcionalidade da interface no navegador conforme script de apresentação

---

##  Testes Executados

### Teste 1: Citação Determinística (T=1:10 do script)
**Pergunta**: "O que diz o art. 18?"

**Resultado esperado**: Resposta com texto exato do artigo + nota de guia correlato  
**Status**: ⏳ Pendente

**Observações**:
- [ ] Resposta gerada em < 5s
- [ ] Texto do artigo presente
- [ ] Sem alucinações jurídicas
- [ ] Cache hit exato (primeira vez = miss, segunda = hit)

---

### Teste 2: RAG com Fontes (T=1:50 do script)
**Pergunta**: "Quais são os deveres do controlador segundo a LGPD?"

**Resultado esperado**: Trechos relevantes do corpus + fontes em formato `[arquivo:pagina]`  
**Status**: ⏳ Pendente

**Observações**:
- [ ] Múltiplas fontes identificadas
- [ ] Fontes verificáveis
- [ ] Resposta ancorada no corpus

---

### Teste 3: Cache Exato em Ação (T=2:40 do script)
**Pergunta**: Repetir "O que diz o art. 18?"

**Resultado esperado**: Status = "Cache hit (exact)", latência < 100ms  
**Status**: ⏳ Pendente

**Observações**:
- [ ] Indicador de cache visível
- [ ] Resposta idêntica à primeira
- [ ] Latência reduzida

---

### Teste 4: Observabilidade e Métricas (T=3:10 do script)

**Sidebar deve mostrar**:
- [ ] Chunks indexados: > 0
- [ ] Exact cache size: aumenta após testes
- [ ] Semantic cache size: aumenta após testes

**Terminal deve mostrar**:
- [ ] Logs estruturados com `trace_id`
- [ ] Latência por requisição

---

### Teste 5: Limitações e Edge Cases

**Pergunta que não está no corpus**: "Qual é a capital do Brasil?"

**Resultado esperado**: Resposta clara indicando que a pergunta está fora do escopo  
**Status**: ⏳ Pendente

---

##  Resumo de Evidências

| Teste | Pergunta | Status | Cache | Latência | Fontes |
|-------|----------|--------|-------|----------|--------|
| 1 | O que diz o art. 18? |  |  →  (2ª) | - | 1 |
| 2 | Deveres do controlador? |  | - | - | N/A |
| 3 | Repetir art. 18 |  |  hit | < 100ms | 1 |
| 4 | Observabilidade |  | - | - | - |
| 5 | Fora do escopo |  | - | - | 0 |

---

##  Configuração Utilizada

- **Python**: 3.10+
- **Streamlit**: 1.30+
- **LLM Provider**: Groq (llama-3.3-70b-versatile)
- **Embeddings**: local (all-MiniLM-L6-v2)
- **Corpus**: data/corpus/lgpd.md
- **Chroma**: data/chroma/

---

##  Notas do Teste

(Preenchidas durante execução)

---

##  Conclusão

(Preenchida ao fim dos testes)
