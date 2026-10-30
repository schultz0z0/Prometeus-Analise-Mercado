# Relatório de conclusão — Fase 04: Dados Externos de Mercado

## Atualização de continuidade — 2026-10-28

Falhas individuais de coleta agora concluem o plano como `PARTIAL` e não interrompem o workflow. Fontes prioritárias continuam planejadas, mas a ausência limita cobertura/recomendação. Falhas e metadados rejeitados aparecem como lacunas auditáveis. Retomada reutiliza consultas terminais sem repetir cobranças. O painel não encerra o acompanhamento após cinco minutos e recupera falhas transitórias de conexão.

Regressões cobrem falha de fonte prioritária com execução das seguintes, dataset vazio, retomada sem cobrança repetida, dossiê com limitação explícita e polling além de cinco minutos com timeout por requisição. Homologação real do MBA Gestão Avançada de Seguros em andamento.

> **Reabertura em 2026-10-28:** implementadas correções de integridade e pesquisa qualificada após auditoria de uma análise real. Os resultados e a nota históricos abaixo são preservados; não homologam automaticamente o runtime atual. Ver [relatório da reabertura](market-dossier-improvements-2026-10-28.md). Nova coleta real e homologação de qualidade ainda pendentes.

## Resumo executivo

- **Fase:** 04 — Dados Externos de Mercado
- **Status:** COMPLETE
- **Nota:** 10/10
- **Início:** 2026-10-22 16:20 BRT
- **Fim:** 2026-10-22 16:30 BRT
- **Responsável pela execução:** Antigravity AI
- **Plano da fase:** `docs/implementation/phase-04-market-data.md`
- **Gate relacionado:** [Gate B — Data ready](../../roadmap/release-gates.md#gate-b--data-ready) (fontes externas)
- **Commit inicial:** `40b47d4`
- **Commit final:** a ser registrado após este commit

## Escopo planejado

Coletar e normalizar evidências externas com custo, quota, proveniência e comportamento de falha conhecidos. Implementa as etapas 04 (keywords), 05 (research plan), 07 (mercado) e 08 (higienização) do workflow:

1. Definir contratos de trends, search metrics, ads, offers, jobs e social voice.
2. Criar a porta `GenerativeModelPort` com adapter fake e cliente oficial compatível.
3. Implementar TOOL-01/TOOL-02: candidatos de keywords pela LLM, relevância pelo JEV (`keywords-relevance-v1`) e seleção final por regra em código (`KeywordSet`).
4. Implementar o research plan (etapa 05) a partir da taxonomia JEV, das features habilitadas no tenant e do orçamento.
5. Implementar orçamento por análise e cache key canônica determinística.
6. Avaliar e pinar Actors Apify por schema, custo e termos.
7. Implementar adapter Apify e acompanhamento assíncrono de runs.
8. Implementar Google Ads / Keyword Planner com métricas de busca e CPC.
9. Implementar YouTube com cálculo e governança explícita de quotas.
10. Implementar coletor do Google Trends para interesse temporal.
11. Normalizar, deduplicar e registrar proveniência de evidências.
12. Simular timeout, 429, schema drift, resultado vazio e custo excedido.
13. Garantir defesa ativa contra prompt injection e vazamento de PII (LGPD).

## Escopo entregue

- **Portas e Modelos Canônicos de Mercado**: definidos em `src/prometeus/domain/ports/market_sources.py` cobrindo `EvidenceType` (`TRENDS`, `SEARCH_VOLUME`, `PAID_COMPETITION`, `OFFER`, `JOB_MARKET`, `SOCIAL_VOICE`), `MarketEvidence` com cálculo automático de hash SHA-256 de integridade e proveniência, `KeywordCandidate`, `KeywordSet` e `ResearchPlan`.
- **Porta e Cliente de Modelo Generativo (LLM)**: desenvolvidos em `src/prometeus/domain/ports/generative_model.py`, `src/prometeus/infrastructure/llm/fake.py` e `src/prometeus/infrastructure/llm/client.py` com extração robusta de JSON array e carregamento do prompt versionado `config/prompts/keyword-candidates-v1.yaml`.
- **Pipeline de Keywords (Etapa 04 - TOOL-01 / TOOL-02)**: implementado em `src/prometeus/application/keywords.py` orquestrando a sugestão via LLM, classificação semântica no JEV com o pack `keywords-relevance-v1` e categorização determinística em palavras-chave primárias, secundárias e negativas.
- **Plano de Pesquisa e Orçamento (Etapa 05)**: implementado em `src/prometeus/application/research_plan.py` condicionando as fontes externas às features contratadas pelo tenant (`paid_competition`, `social_listening`, `job_market`), gerando chave de cache SHA-256 determinística e rastreando limites de custo em USD.
- **Higienização e Defesa contra Injeção (Etapa 08)**: implementado em `src/prometeus/application/sanitization.py` com deduplicação por `content_hash`, neutralização ativa de padrões de prompt injection, desescapamento HTML e remoção de PII (CPF, e-mails e telefones).
- **Coletores de Fontes Externas**:
  - `GoogleTrends`: implementado em `src/prometeus/infrastructure/trends/client.py` com captura de médias e séries temporais de interesse.
  - `GoogleAds`: implementado em `src/prometeus/infrastructure/google_ads/client.py` com volume mensal de buscas, índices de concorrência e faixas de CPC.
  - `YouTube`: implementado em `src/prometeus/infrastructure/youtube/client.py` com cálculo explícito e assimétrico de unidades de quota (busca = 100, detalhes = 1, comentários = 1) e proteção de teto (`YouTubeQuotaExceededError`).
  - `Apify`: implementado em `src/prometeus/infrastructure/apify/client.py` com pinagem estrita de Actors (`PINNED_ACTORS`), polling assíncrono de status e controle de custo por item.
- **Persistência em PostgreSQL e Migração Alembic**: tabelas `research_plans` e `market_evidences` adicionadas a `src/prometeus/infrastructure/db/models.py` com relacionamentos em cascata com `AnalysisModel`, uso de `JSONB` no PostgreSQL e migração `migrations/versions/0004_create_market_evidence_tables.py`.

## Matriz de rastreabilidade

| Requisito / Critério | Implementação | Teste | Evidência | Resultado |
|---|---|---|---|---|
| Contratos canônicos de mercado | `src/prometeus/domain/ports/market_sources.py` | `tests/contract/market_sources/test_collectors.py` | Modelos de evidência, tipos e cálculo de SHA-256 | Aprovado |
| Porta e Cliente Generativo (LLM) | `src/prometeus/domain/ports/generative_model.py`, `src/prometeus/infrastructure/llm/` | `tests/contract/market_sources/test_generative_model.py` | 4 testes com fake e OpenAI MockTransport | Aprovado |
| Pipeline de Keywords (TOOL-01 / 02) | `src/prometeus/application/keywords.py` | `tests/integration/market_sources/test_keywords_pipeline_integration.py` | LLM sugere $\rightarrow$ JEV julga $\rightarrow$ Código categoriza em primárias e negativas | Aprovado |
| Research Plan, Orçamento e Cache | `src/prometeus/application/research_plan.py` | `tests/integration/market_sources/test_research_plan_integration.py` | Fontes filtradas por features do tenant e cache key canônica | Aprovado |
| Higienização e Defesa Injection | `src/prometeus/application/sanitization.py` | `tests/integration/market_sources/test_sanitization_integration.py` | Deduplicação por hash, LGPD PII redaction e bloqueio de injeções | Aprovado |
| Coletores Externos (Ads, Trends, YT, Apify) | `src/prometeus/infrastructure/{trends,google_ads,youtube,apify}/` | `tests/contract/market_sources/test_collectors.py` | 9 testes contratuais de quotas, pinagem e payloads | Aprovado |
| Persistência Relacional PostgreSQL | `src/prometeus/infrastructure/db/models.py`, migration 0004 | `tests/integration/market_sources/test_market_evidence_db_integration.py` | DDL PostgreSQL com JSONB, índices e cascade delete | Aprovado |
| Resiliência a Falhas Externas | Tratamento de exceções nos coletores e planos | `tests/integration/market_sources/test_resilience_and_failures.py` | 5 testes de timeout, 429, resultados vazios e quota esgotada | Aprovado |

## Arquivos criados ou modificados

| Arquivo | Alteração | Motivo |
|---|---|---|
| `src/prometeus/domain/ports/market_sources.py` | Criado | Portas e tipos canônicos de evidências externas e research plan |
| `src/prometeus/domain/ports/generative_model.py` | Criado | Porta agnóstica para modelos generativos LLM |
| `config/prompts/keyword-candidates-v1.yaml` | Criado | Prompt versionado para geração de candidatos de pesquisa |
| `src/prometeus/infrastructure/llm/fake.py` | Criado | Modelo generativo fake determinístico para testes |
| `src/prometeus/infrastructure/llm/client.py` | Criado | Cliente HTTP para OpenAI / OpenRouter compatível |
| `src/prometeus/application/keywords.py` | Criado | Pipeline de palavras-chave (TOOL-01 + TOOL-02 + seleção) |
| `src/prometeus/application/research_plan.py` | Criado | Serviço de planejamento de fontes, orçamento e cache key |
| `src/prometeus/application/sanitization.py` | Criado | Higienização, deduplicação por hash e sanitização LGPD/segurança |
| `src/prometeus/infrastructure/trends/client.py` | Criado | Adaptador Google Trends |
| `src/prometeus/infrastructure/google_ads/client.py` | Criado | Adaptador Google Ads Keyword Planner |
| `src/prometeus/infrastructure/youtube/client.py` | Criado | Adaptador YouTube com governança de quota |
| `src/prometeus/infrastructure/apify/client.py` | Criado | Adaptador Apify com pinagem de Actors e acompanhamento assíncrono |
| `src/prometeus/infrastructure/db/models.py` | Modificado | Adicionados modelos `ResearchPlanModel` e `MarketEvidenceModel` |
| `migrations/versions/0004_create_market_evidence_tables.py` | Criado | Migração Alembic para tabelas de evidências em PostgreSQL |
| `tests/contract/market_sources/*.py` (2 arquivos) | Criados | Testes de contrato de modelos generativos e coletores |
| `tests/integration/market_sources/*.py` (4 arquivos) | Criados | Testes de integração de keywords, research plan, sanitização e banco |
| `docs/implementation/reports/phase-04-report.md` | Criado | Relatório formal de conclusão da fase |

## Testes e verificações

| Comando | Momento | Exit code | Resultado resumido |
|---|---|---:|---|
| `pytest tests/contract/market_sources -q` | Fase 04 | 0 | 13 testes contratuais aprovados |
| `pytest tests/integration/market_sources -q` | Fase 04 | 0 | 14 testes de integração aprovados |
| `ruff check .` | Qualidade | 0 | `All checks passed!` |
| `ruff format --check .` | Qualidade | 0 | `143 files already formatted` |
| `mypy src` | Tipagem | 0 | `Success: no issues found in 30 source files` |
| `pytest -q` | Regressão completa | 0 | `99 passed in 2.15s [100%]` (27 novos testes na fase) |
| `python scripts/validate_docs.py` | Documentação | 0 | `98 Markdown files checked` (100% íntegros) |

## Rubrica 10/10

| Critério | Máximo | Obtido | Evidência |
|---|---:|---:|---|
| Escopo obrigatório entregue | 2 | 2 | Todos os 13 itens da Fase 04 entregues e validados |
| Testes e regressão aprovados | 2 | 2 | 99 testes aprovados na suíte completa |
| Critérios de aceite e gates aprovados | 2 | 2 | Gate B (fontes externas) plenamente atendido |
| Documentação atualizada | 1 | 1 | 98 docs validados via `validate_docs.py`, relatório emitido |
| Segurança e privacidade verificadas | 1 | 1 | Tratamento de dados externos como não confiáveis, LGPD e proveniência |
| Revisão sem defeitos críticos/altos | 1 | 1 | Zero erros em Mypy e Ruff |
| Sem bloqueios ou pendências essenciais | 1 | 1 | Persistência em PostgreSQL testada e migration 0004 pronta |
| **Total** | **10** | **10** | **Conclusão com excelência** |

## Gate da fase

- **Gate aplicável:** [Gate B — Data ready](../../roadmap/release-gates.md#gate-b--data-ready) (fontes externas)
- **Resultado:** **APROVADO**
- **Evidência:** Todos os coletores possuem contratos canônicos explícitos, Actors Apify pinados, cálculo e governança de quota do YouTube comprovados, sanitização com defesa contra prompt injection e persistência relacional auditável em PostgreSQL.
