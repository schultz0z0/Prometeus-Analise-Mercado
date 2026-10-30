# Relatório de Conclusão da Fase 2 — Uso Correto da Apify e Aquisição por Pergunta

**Data:** 2026-10-30  
**Contexto:** Inteligência de Mercado Sênior Prometeus (Auditoria 2026-10-30)  
**Status:** CONCLUÍDA E VERIFICADA  

---

## 1. Objetivo da Fase 2

Sanar os defeitos estruturais de coleta, amostragem e recuperação de dados identificados nos achados P1 e P2 da auditoria (A05, A06, A07, A08 e A13):
1. **Reconciliação de capabilities e inputs efetivos**: contratos de limite por unidade (`per_video`, `per_query`, `retained_total`), eliminação de broadening silencioso e suporte integral às 27 UFs brasileiras.
2. **Amostragem estratificada e linhagem de entidades**: solução da regressão do YouTube (onde 15 itens de um vídeo consumiam toda a cota de 10 vídeos), diagnóstico explícito de truncamento de dataset e separação de `Capture` (observação pontual) e `Entity` (ativo canônico de mercado).
3. **Priorização e outcomes explícitos de URLs**: rankeamento determinístico de páginas para crawling com diversidade de domínio, `maxCrawlDepth=0` para confirmação de páginas alvo, proibição de 404 como oferta válida e rastreamento de documentos/PDFs.
4. **Recuperação causal e controle de ganho marginal**: classificação determinística das 7 causas de lacunas de pesquisa e garantia de que dados existentes nunca sejam recomprados na Apify para resolver falhas locais de normalização ou projeção.

---

## 2. Entregas Realizadas

### Tarefa 2.1 — Capability e Input Efetivo Reconciliados
- **Contratos e Unidades de Limite:** `src/prometeus/application/tool_capabilities.py`
  - Mapeadas as unidades canônicas em `CAPABILITY_LIMIT_UNITS`: `youtube_comments` -> `per_video`, `google_trends` -> `per_query`, demais -> `retained_total`.
  - Cada capability no `CAPABILITY_CONTRACTS` declara pergunta respondida, hashes, filtros traduzidos/indisponíveis e `effective_limit_explanation`.
- **Filtros e Broadening Controlado:** `src/prometeus/infrastructure/apify/registry.py`
  - Corrigido o broadening indevido no conector do LinkedIn: a query original é estritamente preservada a menos que o parâmetro `broaden_query=True` seja explicitamente fornecido.
- **Contrato Geográfico Completo (27 UFs):** `src/prometeus/application/research_scope.py` e `src/prometeus/application/evidence_features.py`
  - Inclusão das 27 UFs brasileiras (`BRAZILIAN_STATES`), cobrindo estados anteriormente omitidos (`AL`, `MA`, `MT`, `MS`, `SC`).
  - Resolução de ambiguidades (ex.: `PA` isolado como Pennsylvania vs. Pará).
  - Tratamento da variante `isPartial=[True]` em séries temporais.
- **Rastreabilidade de Execução:** `src/prometeus/application/collect_market_evidence.py`
  - Persistência obrigatória de `effective_actor_input` e `effective_scope` em `ToolRunModel.parameters`.
- **Testes de Contrato:** `tests/contract/market_sources/test_actor_effective_contracts.py` (6 testes passando).

### Tarefa 2.2 — Amostra e Paginação em Unidades Corretas
- **Linhagem Canônica de Entidades:** `src/prometeus/domain/market_entities.py`
  - Criados modelos `MarketCapture`, `MarketEntity` e o `EntityLineageTracker`.
  - Extração de chave canônica via `extract_canonical_entity_id`: `ad:{id}` (Meta Ads), `job:{id}` (LinkedIn Jobs), `comment:{cid}` (YouTube), `offer:{url}` (Web Crawler).
  - Múltiplas capturas do mesmo anúncio ou vaga preservam histórico e contradições/atualizações sem multiplicar a contagem de concorrentes no mercado.
- **Amostragem Estratificada por Vídeo:** `src/prometeus/application/collect_market_evidence.py`
  - Implementado particionamento estratificado em `_normalized_items`: quando múltiplos vídeos são consultados para comentários, a cota é distribuída equitativamente entre os vídeos (`per_video_quota`), evitando que um único vídeo monopolize a amostra.
- **Paginação e Diagnóstico de Truncamento:** `src/prometeus/infrastructure/apify/client.py` e `collect_market_evidence.py`
  - `ApifyClient.execute` consulta o dataset com cota proporcional ao número de alvos em capacidades `per_video` e itera paginação conforme necessário.
  - Método `_build_sampling_audit`: registra `sampling_strategy`, `dataset_total_items`, `items_read`, `items_retained`, `quota_per_video`, `distribution_per_video` e sinalizador `truncation_detected` com justificativa explicada.
  - Registro de resumo de entidades em `audit["entities"]`.
- **Testes de Integração:** `tests/integration/market_sources/test_sampling_and_lineage.py` (8 testes passando).

### Tarefa 2.3 — URLs Priorizadas e Arquivos com Outcome Explícito
- **Validação e Higienização de URLs:** `src/prometeus/application/collect_market_evidence.py`
  - Rejeição de URLs malformadas em `_is_usable_discovered_url` (ex.: host repetido no path como `https://securitariosp.org.br/curso/www.securitariosp.org.br`).
- **Rankeamento Determinístico e Diversidade de Domínio:** `_prioritize_crawler_urls`
  - Pontuação por relevância: cursos específicos (`+10`), tokens da consulta (`+3`), documentos/PDFs (`+5`), catálogos (`+2`), notícias genéricas (`-3`).
  - Teto de diversidade: no máximo 2 URLs por domínio em cada lote de crawling.
- **Confirmação de Páginas Alvo:** `src/prometeus/infrastructure/apify/registry.py`
  - Crawler configurado com `maxCrawlDepth=0` para confirmação de páginas selecionadas, evitando dispersão em páginas não planejadas.
- **Mapeamento de Outcomes Técnicos:** `collect_market_evidence.py`
  - Cada URL planejada recebe status explícito em `audit["url_outcomes"]`: `fetched`, `not_found`, `blocked`, `unsupported_type`, `budget_skipped`, `extraction_failed`.
  - Páginas 404 ou com indicativo de não encontrada são rejeitadas em `_item_rejection_reason` e jamais viram ofertas válidas.
  - Documentos PDF possuem MIME identificado (`application/pdf`) e rastreamento de recência.
- **Testes de Integração:** `tests/integration/market_sources/test_url_prioritization_and_outcomes.py` (6 testes passando).

### Tarefa 2.4 — Recuperação por Causa e Ganho Marginal
- **Classificador Causal de Lacunas:** `src/prometeus/application/research_sufficiency.py`
  - Criados enums `GapCause` (7 causas canônicas: `source_failure`, `unsupported_source`, `normalization_loss`, `context_projection_loss`, `qualification_uncertain`, `true_no_signal`, `missing_primary_data`) e `GapRecoveryAction`.
  - Função `classify_research_gaps`: inspeciona execuções e dados persistidos para identificar se o dado já existe e foi perdido na normalização ou projeção.
  - Regra de custo: se `reproducible_without_cost=True`, a ação orienta reparo local (`REPROCESS_LOCAL_DATA` ou `REPROJECT_CONTEXT`) sem efetuar nova chamada paga.
- **Deduplicação por Assinatura Efetiva:** `src/prometeus/application/plan_course_research.py`
  - Normalização léxica de assinaturas de consulta com remoção de stopwords (`query_sig`), impedindo que reformulações cosméticas de queries já realizadas gerem novas coletas redundantes.
- **Diagnósticos de Coleta:** `src/prometeus/application/collection_diagnostics.py`
  - `summarize_collection` enriquecido com métricas de `sampling`, `entities` e `url_outcomes`.
- **Testes de Integração:** `tests/integration/market_sources/test_gap_recovery_and_deduplication.py` (5 testes passando).

---

## 3. Matriz de Verificação

| Gate da Fase 2 | Verificação | Resultado |
|---|---|:---:|
| Contratos de Actor e inputs efetivos | `tests/contract/market_sources/test_actor_effective_contracts.py` (6 testes) | PASS |
| Quotas e estratificação YouTube (3 vídeos) | `test_youtube_stratified_sampling_across_three_eligible_videos` | PASS |
| Diagnóstico de truncamento de dataset | `test_dataset_truncation_diagnostic_is_recorded_in_audit` | PASS |
| Separação Captura vs Entidade | `test_entity_lineage_tracker_separates_captures_from_entities` | PASS |
| Teto financeiro e persistência de auditoria | `test_collect_service_persists_sampling_and_entities_audit` | PASS |
| Falha técnica parcial em múltiplos alvos | `test_partial_failure_in_multi_video_call` | PASS |
| Rejeição de URLs malformadas | `test_malformed_urls_are_rejected_before_crawl` | PASS |
| Diversidade de domínio em URLs (max 2/domínio) | `test_url_prioritization_and_domain_diversity` | PASS |
| Páginas 404 nunca viram oferta | `test_404_not_found_is_rejected_and_never_becomes_valid_offer` | PASS |
| Crawler maxCrawlDepth=0 em páginas alvo | `test_crawler_page_confirmation_sets_max_crawl_depth_zero` | PASS |
| Rastreamento explícito de outcome por URL | `test_audit_records_explicit_outcome_per_url` | PASS |
| Rastreamento e MIME de PDF | `test_pdf_prioritized_has_explicit_outcome_and_mime_tracking` | PASS |
| Classificação das 7 causas de lacunas | `test_gap_recovery_and_deduplication.py` (4 testes de causa) | PASS |
| Deduplicação de query por assinatura normalizada | `test_query_deduplication_via_normalized_effective_input` | PASS |
| Suíte Integral de Testes | `pytest tests/unit tests/contract tests/integration` (513 testes) | PASS |
| Verificação Estática de Tipos | `mypy src` (77 arquivos fonte) | PASS (0 erros) |
| Linting e Formatação | `ruff check src tests` | PASS (0 erros) |
| Verificação de Baseline do Estudo | `senior-market-intelligence-baseline-checks-2026-10-30.py` | PASS |
| Validador de Documentação | `scripts/validate_docs.py` (155 arquivos Markdown) | PASS |

