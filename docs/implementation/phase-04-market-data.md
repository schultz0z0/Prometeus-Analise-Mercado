# Fase 04 — Dados externos de mercado

**Atualização de 2026-10-28:** falhas de ferramentas são lacunas individuais: a análise continua com evidências válidas, informa a fonte indisponível e reduz cobertura/recomendação conforme as regras determinísticas. `required` representa prioridade de pesquisa, sem bloquear por falha de execução. O intake extrai PDF/DOCX/TXT; preço parcelado é calculado em código, independentemente da duração acadêmica.

## Objetivo

Coletar e normalizar evidências externas com custo, quota, proveniência e comportamento de falha conhecidos. Implementa as etapas 04 (keywords), 05 (research plan), 07 (mercado) e 08 (higienização) do [workflow](../agent/workflow.md).

## Gate de release relacionado

[Gate B — Data ready](../roadmap/release-gates.md#gate-b--data-ready) (fontes externas).

## Arquivos principais previstos

- `src/prometeus/domain/ports/market_sources.py`
- `src/prometeus/domain/ports/generative_model.py`
- `src/prometeus/application/keywords.py`
- `src/prometeus/application/research_plan.py`
- `src/prometeus/infrastructure/llm/`
- `src/prometeus/infrastructure/apify/`
- `src/prometeus/infrastructure/google_ads/`
- `src/prometeus/infrastructure/youtube/`
- `src/prometeus/infrastructure/trends/`
- `config/prompts/keyword-candidates-v1.yaml`
- `tests/contract/market_sources/`

## Tarefas

1. Definir contratos de trends, search metrics, ads, offers, jobs e social voice.
2. Criar a porta `GenerativeModel` com adapter fake e o provider escolhido (reutilizada na Fase 06).
3. Implementar TOOL-01/TOOL-02: candidatos de keywords pela LLM, relevância pelo JEV (`keyword_relevance_v1`) e seleção final por regra em código (`KeywordSet`).
4. Implementar o research plan (etapa 05) a partir da taxonomia JEV, das features habilitadas no tenant e do orçamento.
5. Implementar orçamento por análise e cache key canônica.
6. Avaliar e pinar Actors por schema, custo, manutenção e termos.
7. Implementar adapter Apify e acompanhamento assíncrono de runs.
8. Implementar Google Ads Keyword Planning quando o acesso estiver aprovado.
9. Implementar YouTube com cálculo explícito de quota.
10. Implementar provider de Trends selecionado na Fase 00.
11. Normalizar, deduplicar e registrar proveniência.
12. Simular timeout, 429, schema drift, resultado vazio e custo excedido.
13. Validar amostras manualmente com analista de marketing.

## Verificação

```bash
pytest tests/contract/market_sources -q
pytest tests/integration/market_sources -q
```

## Gate

Cada fonte possui contrato, termos revisados, teto de custo, métricas de qualidade e fallback/status parcial definido.

## Reabertura de 2026-10-28

Implementadas as correções de sanitização recursiva, dependências, proveniência, normalização de SERPs, metadados sociais, contagem, deduplicação por entidade e comparação de preços com periodicidade. O catálogo agora descreve somente fontes configuradas e uma rodada complementar é limitada ao orçamento restante. O julgamento de pertinência usa a mesma porta nos modos tradicional e híbrido. Ver [relatório da reabertura](reports/market-dossier-improvements-2026-10-28.md). Schemas antigos pinados e qualidade de novas coletas reais ainda exigem homologação operacional; testes com fixtures não substituem essa avaliação.
