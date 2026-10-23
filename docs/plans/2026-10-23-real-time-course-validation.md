# Real-Time Course Validation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fazer o Prometeus compreender uma proposta, planejar e executar pesquisa real multi-fonte em tempo real e produzir um dossiê totalmente rastreável, mantendo apenas o histórico passado da ENS como dado sintético de teste.

**Architecture:** Um orquestrador assíncrono de 15 etapas coordena LLM tradicional ou modo híbrido, registry de ferramentas Apify, persistência de runs/evidências, extração determinística de features, scoring e síntese verificada. A LLM propõe entendimento e plano; código valida e executa ferramentas permitidas, bloqueando o job quando uma fonte obrigatória falha.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, PostgreSQL, Redis/Celery, httpx, OpenAI-compatible LLM, TypeSafe JEV opcional, Apify API, pytest, Ruff, mypy, JavaScript modular e Docker Compose.

---

### Task 1: Congelar a regressão fictícia e validar pré-condições

**Files:**
- Create: `tests/unit/workers/test_no_synthetic_runtime_fallbacks.py`
- Create: `tests/integration/test_runtime_preflight.py`
- Modify: `src/prometeus/domain/configuration.py`

**Steps:**

1. Escrever testes que rejeitam valores e textos estáticos de mercado no worker e exigem credenciais/Actor IDs não vazios para fontes habilitadas.
2. Executar `pytest tests/unit/workers/test_no_synthetic_runtime_fallbacks.py tests/integration/test_runtime_preflight.py -q` e confirmar falha pelos fallbacks atuais e pela ausência de preflight.
3. Adicionar settings tipadas para Actors, egress, modo de decisão e fontes obrigatórias; criar `RuntimePreflight` que retorna falhas estruturadas sem revelar segredos.
4. Executar os testes isolados até passarem.
5. Commit: `test: guard against synthetic market fallbacks`.

### Task 2: Modelar entendimento, plano e execução de ferramentas

**Files:**
- Create: `src/prometeus/domain/research.py`
- Create: `tests/unit/domain/test_research_models.py`
- Modify: `src/prometeus/domain/ports/market_sources.py`
- Modify: `src/prometeus/infrastructure/db/models.py`
- Create: `migrations/versions/0008_create_tool_runs_and_research_snapshots.py`

**Steps:**

1. Escrever testes para `CourseUnderstanding`, `ResearchQuestion`, `PlannedToolCall`, `ResearchPlan`, `ToolRun` e regras de fonte obrigatória.
2. Confirmar RED com `pytest tests/unit/domain/test_research_models.py -q`.
3. Implementar contratos versionados, estados `PLANNED/RUNNING/SUCCEEDED/EMPTY/FAILED`, critérios de suficiência e hashes canônicos.
4. Persistir snapshots de entendimento/plano e runs com Actor, run ID, dataset ID, consulta, contagens, custo, timestamps e erro sanitizado.
5. Rodar teste unitário e compilação DDL PostgreSQL.
6. Commit: `feat: model research plans and tool runs`.

### Task 3: Garantir o modo LLM tradicional real e compatibilidade JEV

**Files:**
- Create: `tests/unit/domain/test_ai_provider_factory.py`
- Modify: `src/prometeus/infrastructure/factory.py`
- Modify: `src/prometeus/infrastructure/llm/decision_adapter.py`
- Modify: `src/prometeus/application/decision_service.py`
- Modify: `src/prometeus/domain/configuration.py`

**Steps:**

1. Escrever testes provando que ausência de `TYPESAFE_API_KEY` seleciona `LLMDecisionAdapter` real e que nenhuma factory de runtime retorna adaptador fake.
2. Confirmar RED no caso de LLM sem credencial e de provider não suportado.
3. Implementar `AI_MODE=traditional|hybrid|auto`, validação de credencial e decisões estruturadas pela LLM com o mesmo contrato dos decision packs.
4. Fazer indisponibilidade da LLM bloquear a etapa, sem resposta determinística inventada.
5. Rodar testes de factory, contratos JEV e LLM.
6. Commit: `feat: enforce real traditional and hybrid ai modes`.

### Task 4: Criar e registrar skills genéricas de inteligência educacional

**Files:**
- Create: `skills/understanding-course-proposals/SKILL.md`
- Create: `skills/planning-market-research/SKILL.md`
- Create: `skills/reviewing-market-evidence/SKILL.md`
- Create: `skills/auditing-course-curriculum/SKILL.md`
- Create: `skills/building-course-offers/SKILL.md`
- Create: `src/prometeus/application/skill_registry.py`
- Create: `tests/unit/application/test_skill_registry.py`
- Modify: `docs/agent/skills-strategy.md`

**Steps:**

1. Para cada skill, criar primeiro um caso de comportamento que demonstre a falha sem as instruções: números sem fonte, ferramenta não autorizada, confusão entre ausência de dado e sinal negativo ou conclusão além da evidência.
2. Criar uma skill por vez, validar com o `quick_validate.py` da skill-creator e só então avançar para a próxima.
3. Escrever teste RED do registry exigindo allowlist, versão, hash e seleção por estágio/domínio sem caminhos arbitrários.
4. Implementar carregamento seguro dos snapshots das skills e persistir metadados no plano.
5. Rodar `pytest tests/unit/application/test_skill_registry.py -q` e validação de todas as skills.
6. Commit: `feat: add domain skills for course intelligence`.

### Task 5: Compreender o curso e gerar o plano antes da coleta

**Files:**
- Create: `src/prometeus/application/course_understanding.py`
- Create: `src/prometeus/application/plan_course_research.py`
- Create: `config/prompts/course-understanding-v1.yaml`
- Create: `config/prompts/research-plan-v1.yaml`
- Create: `tests/integration/market_sources/test_course_understanding.py`
- Create: `tests/integration/market_sources/test_dynamic_research_plan.py`

**Steps:**

1. Escrever testes com propostas distintas e anexos, exigindo planos distintos, queries específicas e critérios de suficiência.
2. Confirmar RED porque o worker atual deriva apenas duas strings fixas.
3. Implementar chamadas estruturadas à LLM, sanitização de anexos e validação determinística do plano contra registry, orçamento e fontes obrigatórias.
4. Integrar geração de keywords com `KeywordPipeline`; no modo tradicional, usar o adaptador de decisão LLM real.
5. Rodar testes de entendimento, keywords e research plan.
6. Commit: `feat: plan research from proposal context`.

### Task 6: Transformar o Apify em registry multi-fonte real

**Files:**
- Create: `src/prometeus/infrastructure/apify/registry.py`
- Create: `src/prometeus/infrastructure/apify/schemas.py`
- Modify: `src/prometeus/infrastructure/apify/client.py`
- Modify: `.env.example`
- Create: `tests/contract/market_sources/test_apify_registry.py`
- Create: `tests/contract/market_sources/test_apify_live_schemas.py`

**Steps:**

1. Revalidar a documentação oficial da API Apify e os schemas dos Actors configurados para Google Search, crawler, Meta Ads Library, LinkedIn, LinkedIn Jobs/Google Jobs e redes sociais.
2. Escrever testes RED para URLs corretas, versão configurada, polling terminal, dataset vazio, schema drift, timeout, custo e metadados de run.
3. Implementar registry configurável, inputs por capacidade e normalizadores separados por fonte; remover Actor defaults inventados e rótulos incorretos.
4. Permitir capacidades adicionais configuradas via Apify, como Trends/Analytics, sem aceitar Actor fora da allowlist.
5. Rodar testes contratuais com `MockTransport`; executar smoke test real somente quando preflight autorizar.
6. Commit: `feat: execute configured Apify research tools`.

### Task 7: Coletar, sanitizar e persistir somente evidência real

**Files:**
- Create: `src/prometeus/application/collect_market_evidence.py`
- Create: `src/prometeus/application/evidence_features.py`
- Create: `tests/integration/market_sources/test_real_collection_orchestrator.py`
- Modify: `src/prometeus/application/sanitization.py`

**Steps:**

1. Escrever testes RED para execução de chamadas planejadas, checkpoints, deduplicação, resultado vazio e bloqueio de fonte obrigatória.
2. Implementar o executor com dependências injetadas, sem `except Exception: continue` para fontes obrigatórias.
3. Persistir `MarketEvidenceModel` somente a partir de resultados retornados pelo fornecedor e vincular cada evidência ao `ToolRun`.
4. Implementar extração determinística de features para concorrência, busca, preço, vagas e voz social.
5. Rodar testes de coleta, sanitização e persistência.
6. Commit: `feat: persist source-backed market evidence`.

### Task 8: Conectar julgamentos, scoring e quality gates reais

**Files:**
- Create: `tests/integration/scoring/test_evidence_backed_scoring.py`
- Modify: `src/prometeus/application/scoring_service.py`
- Modify: `src/prometeus/domain/scoring/calculator.py`
- Modify: `src/prometeus/domain/scoring/quality_gates.py`

**Steps:**

1. Escrever teste RED no qual duas coleções diferentes produzem scores diferentes e uma fonte ausente reduz cobertura/recomendação.
2. Mapear somente features verificadas aos pilares configurados; preservar IDs de evidência nas features.
3. Calcular score, confiança e cobertura pelo `ScoringService`, sem constantes no worker.
4. Garantir `INSUFFICIENT_EVIDENCE` abaixo da cobertura e `BLOCKED` antes do scoring quando fonte obrigatória falhar.
5. Rodar testes unitários e de integração de scoring.
6. Commit: `feat: score verified real-time evidence`.

### Task 9: Remover o dossiê fallback e exigir claims rastreáveis

**Files:**
- Create: `tests/integration/dossiers/test_no_dossier_fallback.py`
- Modify: `src/prometeus/application/synthesize_dossier.py`
- Modify: `src/prometeus/application/dossier_verifier.py`
- Modify: `src/prometeus/infrastructure/llm/client.py`
- Modify: `config/prompts/dossier-v1.yaml`

**Steps:**

1. Escrever testes RED exigindo falha/bloqueio da síntese quando a LLM falha e rejeição de qualquer claim sem evidência existente.
2. Incluir entendimento, plano, evidências, score, limitações e contraprovas em `DossierFacts`.
3. Remover integralmente o dossiê determinístico estático.
4. Validar JSON estruturado, números, URLs e `evidence_ids` antes de persistir.
5. Rodar unitários, integração e avaliação do Gate C.
6. Commit: `fix: require source-backed generated dossiers`.

### Task 10: Substituir o worker de quatro passos pelo workflow canônico

**Files:**
- Rewrite: `src/prometeus/workers/tasks.py`
- Create: `src/prometeus/application/run_course_analysis.py`
- Create: `tests/e2e/test_real_time_course_analysis.py`
- Modify: `tests/e2e/test_foundation_flow.py`

**Steps:**

1. Escrever E2E RED que exige os 15 checkpoints, plano persistido, runs reais/injetados, score derivado e dossiê verificado.
2. Implementar um caso de uso independente do Celery; deixar a task apenas abrir transação e chamá-lo.
3. Aplicar transições `WAITING_FOR_INPUT`, `BLOCKED`, `COMPLETED` e `FAILED` conforme contratos.
4. Garantir retomada idempotente sem repetir runs concluídas ou custo.
5. Rodar E2E e testes operacionais de falhas.
6. Commit: `feat: orchestrate full course intelligence workflow`.

### Task 11: Tornar configuração e rede Docker realmente operacionais

**Files:**
- Modify: `compose.yaml`
- Modify: `src/prometeus/entrypoints/rest/app.py`
- Modify: `web/js/views/settings-view.js`
- Modify: `web/js/store.js`
- Modify: `docs/operations/configuration.md`
- Modify: `docs/operations/staging-and-pilot-deployment.md`
- Create: `tests/operational/test_external_egress_and_settings.py`

**Steps:**

1. Escrever testes RED comprovando que credenciais salvas ficam disponíveis ao worker e que o worker possui egress sem expor PostgreSQL/Redis.
2. Separar rede de dados interna da rede de egress do worker; corrigir healthcheck que hoje mascara falhas.
3. Tornar atualização de settings explícita sobre restart/reload e validar Actor IDs obrigatórios.
4. Remover tokens e estados falsos de `mock-data.js`; a UI deve refletir somente `/v1/settings`.
5. Rodar testes operacionais e `docker compose config --quiet`.
6. Commit: `fix: propagate integration settings and worker egress`.

### Task 12: Exibir progresso e dossiê reais na interface

**Files:**
- Modify: `web/js/store.js`
- Modify: `web/js/views/live-view.js`
- Modify: `web/js/views/dossier-view.js`
- Modify: `web/js/mock-data.js`
- Create: `tests/contract/api/test_analysis_progress.py`

**Steps:**

1. Escrever contrato RED para progresso contendo estágio, ferramenta, consulta, run ID, contagens, custo e bloqueio.
2. Expor snapshots do workflow pela API sem payload bruto sensível.
3. Remover `simulateLivePipeline`, `finishJobWithFallback` e fallback de evidências/dossiê no navegador.
4. Renderizar as etapas e evidências retornadas pela API; estado vazio deve ser explícito.
5. Rodar contratos REST e smoke test da UI.
6. Commit: `fix: render real analysis progress and evidence`.

### Task 13: Verificação ao vivo, documentação e changelog

**Files:**
- Modify: `docs/agent/workflow.md`
- Modify: `docs/agent/tools-catalog.md`
- Modify: `docs/integrations/external-sources.md`
- Modify: `docs/implementation/phase-04-market-data.md`
- Modify: `docs/implementation/phase-06-dossier.md`
- Modify: `docs/implementation/reports/phase-04-report.md`
- Modify: `docs/implementation/reports/phase-06-report.md`
- Modify: `docs/operations/pilot-operation-report.md`

**Steps:**

1. Atualizar documentação e corrigir relatórios que declaram integrações completas sem evidência de execução real.
2. Executar `ruff check .`, `ruff format --check .`, `mypy src` e `pytest -q`.
3. Reconstruir Docker e executar preflight sem imprimir segredos.
4. Criar uma análise nova com proposta inédita e observar runs externos reais até o dossiê.
5. Auditar amostra de claims contra run IDs/datasets; provocar falha de fonte obrigatória e confirmar `BLOCKED`.
6. Registrar custos, duração, fontes, cobertura e limitações no relatório do piloto.
7. Commit: `docs: record verified real-time analysis workflow`.

## Verificação final

```bash
ruff check .
ruff format --check .
mypy src
pytest -q
python scripts/validate_docs.py
docker compose config --quiet
docker compose up -d --build
```

O trabalho só está concluído quando uma proposta inédita gerar pesquisa externa real, score derivado e dossiê rastreável, e quando a indisponibilidade de uma fonte obrigatória bloquear o fluxo sem inserir qualquer dado substituto.
