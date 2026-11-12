# Codex CLI + Scrapling — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Substituir progressivamente a execução semântica por Codex CLI e o provider de navegação web por Scrapling, preservando Apify, o workflow, o acervo e o dossiê CMS do Prometeus.

**Architecture:** O backend mantém estado, tentativas, autorização, dados e cálculos. Um runner Codex isolado solicita ferramentas por gateway e retorna contratos estruturados; Scrapling e Apify implementam aquisição com proveniência própria. A implantação muda defaults apenas para novas análises e mantém caminho de reversão.

**Tech Stack:** Python/FastAPI, SQLAlchemy/PostgreSQL, Celery/Redis, Docker, Codex CLI, Scrapling/browser, MCP, pytest e frontend atual.

---

**Data:** 12/11/2026. **Estado:** plano para desenvolvimento; nenhum passo abaixo foi executado por esta entrega documental. A autorização atual cobre documentação, commit e push. Arquivos de código e testes indicados como novos ainda não existem; seus comandos somente devem rodar após criação. Não marcar testes planejados como resultados.

## Leitura e limites obrigatórios

**Progresso após autorização para CS-00:** tarefa 1 parcialmente implementada; retenção/diagnóstico corrigidos, recuperação da mesma run validada, causa exata do mismatch original ainda pendente. Ver [relatório](../implementation/reports/cs-00-baseline-and-reconciliation.md). As declarações de entrega documental acima descrevem a publicação inicial do plano; não invalidam a autorização posterior para iniciar CS-00. Tarefas 2–12 não foram iniciadas.

Ler [ADR-0012](../architecture/adr/0012-codex-cli-and-provider-neutral-collection.md), [contratos](../integrations/codex-scrapling-contracts.md), [fases CS](../implementation/codex-scrapling/README.md) e [runbook planejado](../operations/codex-scrapling-rollout.md). A [avaliação inicial](2026-11-11-codex-cli-scrapling-assessment.md) contém os acoplamentos existentes. Consultar documentação oficial vigente antes de instalar/fixar versões. Nenhum conteúdo coletado pode instruir o runner a mudar permissões, código de produção ou publicação.

Aplicar `@test-driven-development` e `@systematic-debugging` aos bugs; `@verification-before-completion` antes de alegar conclusão. Revisão de código antes de integrar cada marco. Não há instrução para abrir novas conversas ou delegar automaticamente. Desenvolver mudanças de runtime em checkout isolado quando houver trabalho concorrente, preservando commits do usuário; integração final na `main` por merge normal, sem force push.

## Procedimento de cada tarefa

Cada tarefa abaixo é executada em ações curtas: criar o teste do comportamento, observar RED pela causa esperada, implementar o mínimo, observar GREEN e regressões relevantes, atualizar a fase/relatório e fazer commit restrito aos arquivos da tarefa. Se o teste já passar, registrar que não reproduziu o problema e investigar antes de editar o runtime. Resultado de mock não substitui gate live.

Commits sugeridos são rótulos de escopo, não autorização para publicar segredos ou incluir arquivos privados. Scripts live devem exigir opt-in e produzir artefatos em `var/diagnostics/` ou diretório privado equivalente.

### Tarefa 1 — Reproduzir a reconciliação Google Search (CS-00)

**Arquivos:** alterar `src/prometeus/infrastructure/apify/client.py` e `src/prometeus/application/recover_market_collection.py` somente após reproduzir; criar `tests/contract/market_sources/test_apify_dataset_reconciliation.py` e `tests/integration/market_sources/test_existing_run_reconciliation.py`.

1. Capturar baseline privado e respostas do dataset já pago, com parâmetros/headers/corpo e estado remoto. Não assumir que página curta significa inconsistência sem comparar o request real.
2. Criar um teste reproduzindo a divergência, outro de dataset realmente incompleto e um contador de POST. O primeiro deve falhar antes do fix; o segundo deve continuar exigindo reconciliação.
3. Corrigir a causa no cliente ou na política de retomada, sem omitir contagem ou reduzir retenção.
4. Rodar os dois testes novos e as regressões existentes:

```powershell
rtk proxy .venv/Scripts/python.exe -m pytest tests/contract/market_sources/test_apify_dataset_reconciliation.py tests/integration/market_sources/test_existing_run_reconciliation.py tests/integration/market_sources/test_complete_collection_retention.py tests/integration/market_sources/test_apify_recovery_policy.py -q -o addopts=
```

5. Reconciliar a mesma run em ambiente controlado, conferir hashes e registrar `cs-00-baseline-and-reconciliation.md`. Commit sugerido: `fix: reconcile existing Apify datasets without duplicate runs`.

### Tarefa 2 — Introduzir contrato de aquisição neutro (CS-01)

**Criar:** `src/prometeus/domain/collection_results.py`, `src/prometeus/domain/ports/research_tools.py`, `tests/unit/application/test_research_router.py`. **Modificar:** `src/prometeus/application/collect_market_evidence.py`.

1. Escrever testes de provider local com IDs remotos ausentes e Apify com IDs reais; custo inválido e artefato alheio são recusados.
2. Executar `rtk proxy .venv/Scripts/python.exe -m pytest tests/unit/application/test_research_router.py -q -o addopts=` e observar RED no contrato novo.
3. Implementar os tipos definidos nos contratos e validação de domínio; manter adaptador compatível com `ApifyExecutionResult` no limite da infraestrutura.
4. Reexecutar testes e verificar que a origem real chega a `OfferObservation`/`PageAcquisition` e à auditoria.
5. Commit sugerido: `refactor: separate research capability from collection provider`.

### Tarefa 3 — Roteamento e recuperação por interface (CS-01)

**Criar:** `src/prometeus/infrastructure/research/router.py`, `src/prometeus/infrastructure/research/apify_adapter.py`, `tests/integration/market_sources/test_provider_neutral_recovery.py`. **Modificar:** `application/recover_market_collection.py`, `workers/tasks.py`, `entrypoints/rest/app.py`, `entrypoints/cli/main.py`, `application/runtime_preflight.py` sob `src/prometeus/`.

1. Testar dois executores, operação iniciada antes de queda e retomada do ID correto. O router não pode perder a capacidade de reconciliação por não ser `ApifyClient`.
2. Observar RED com `rtk proxy .venv/Scripts/python.exe -m pytest tests/integration/market_sources/test_provider_neutral_recovery.py -q -o addopts=`.
3. Trocar verificações de classe concreta por interface; persistir callback de início e reutilizar contador da tarefa. Preflight valida provider selecionado, não Actor para toda capability.
4. Provar cancelamento, execução incerta e zero POST adicional na leitura da run; exercitar worker, CLI e REST.
5. Commit sugerido: `refactor: route research execution and recovery by provider`.

### Tarefa 4 — Persistência e snapshots retrocompatíveis (CS-01)

**Modificar:** `src/prometeus/infrastructure/db/models.py`, `src/prometeus/domain/configuration.py`, `src/prometeus/application/create_analysis.py`. **Criar:** próxima migração aditiva em `migrations/versions/` após conferir heads; `tests/operational/test_research_provider_migration.py`.

1. Testar cópia de registros legados, arquivo v1 e nova execução local. Preservar hashes e renderização de dossiês anteriores.
2. Observar RED no teste novo, depois implementar campos/relações necessários sem copiar payloads em massa.
3. Congelar provider, políticas, versões e identidade de runtime em novas análises. Não converter snapshots existentes para novos defaults.
4. Verificar upgrade, leitura pelo código compatível e uma head; ensaiar reversão em cópia do PostgreSQL.
5. Commit sugerido: `feat: persist research provider and artifact provenance`. Gate CS-01 exige as tarefas 2–4 completas.

### Tarefa 5 — Transporte Codex CLI (CS-02)

**Criar:** `src/prometeus/infrastructure/codex/runner.py`, `src/prometeus/infrastructure/llm/codex_cli.py`, `tests/contract/llm/test_codex_cli_transport.py`. **Modificar:** `src/prometeus/infrastructure/factory.py` e `src/prometeus/domain/configuration.py`.

1. Criar um pequeno executável de teste que emite JSONL controlado e lê stdin, sem chamar LLM paga. Cobrir saída final válida, erro de processo, ausência de evento final, stdout parcial e JSON fora do schema.
2. Rodar `rtk proxy .venv/Scripts/python.exe -m pytest tests/contract/llm/test_codex_cli_transport.py -q -o addopts=` e observar RED do adaptador ausente.
3. Implementar subprocesso com argumentos separados, schema e final separados dos eventos; cumprir todos os métodos de `GenerativeModelPort`. Reutilizar montagem de prompts e validadores existentes, sem criar síntese paralela sem verificação.
4. Validar que `codex` e `chatgpt_oauth` preservam a semântica HTTP antiga; `codex_cli` é selecionado explicitamente. O teste verifica que credenciais não aparecem nos argumentos, prompt ou eventos públicos.
5. Commit sugerido: `feat: add explicit Codex CLI generative provider`.

### Tarefa 6 — Sessões, cancelamento e runner real (CS-02)

**Criar:** `src/prometeus/infrastructure/codex/session_store.py`, `deploy/docker/Dockerfile.codex`, `config/codex/runtime.example.toml`, `tests/integration/llm/test_codex_cli_sessions.py`, `tests/operational/test_codex_runner_lifecycle.py`. **Modificar:** `compose.yaml`, `application/runtime_preflight.py`, `application/integral_evidence_reader.py`, `entrypoints/rest/app.py`, `web/app.js` sob suas raízes atuais.

1. Testar sessão de outra análise recusada, retomada por ID, alteração de modelo/skills invalidando cache e resposta tardia após lease perdido descartada.
2. Observar RED nos dois arquivos novos; implementar ciclo de vida e armazenamento privado, sem herança da configuração pessoal do desktop.
3. Ensaiar morte/cancelamento do subprocesso e recursos filhos; fixar versão de CLI e oferecer configuração do provider na UI sem conexão fictícia.
4. Rodar testes novos; depois autenticar no runner e provar inferência real, disponibilidade do modelo e renovação. Não assumir que o token OAuth atual do app é utilizável pelo CLI.
5. Commit sugerido: `feat: isolate Codex sessions and runner lifecycle`. Registrar gate CS-02 somente após inferência real e testes operacionais.

### Tarefa 7 — Scrapling HTTP e browser (CS-03)

**Criar:** `src/prometeus/infrastructure/scrapling/client.py`, `src/prometeus/infrastructure/scrapling/normalizer.py`, `deploy/docker/Dockerfile.scrapling`, `tests/contract/market_sources/test_scrapling_acquisition.py`. **Modificar:** `pyproject.toml`, `uv.lock`, `compose.yaml` e router de CS-01.

1. Usar páginas locais controladas para HTTP, JS, aba de currículo, redirect, 404 e timeout; uma página de bloqueio não vira oferta.
2. Observar RED com `rtk proxy .venv/Scripts/python.exe -m pytest tests/contract/market_sources/test_scrapling_acquisition.py -q -o addopts=`.
3. Fixar dependências após validar documentação; implementar provider selecionável para `web_crawler` com proveniência real e política de recursos. HTTP pode escalar para browser com diagnóstico.
4. Reexecutar contratos e confirmar que Google Search, Trends e demais capabilities ainda usam Apify; custos locais são separados.
5. Commit sugerido: `feat: add Scrapling course-page acquisition provider`.

### Tarefa 8 — Acervo e sessão duráveis (CS-03)

**Criar:** `src/prometeus/infrastructure/evidence/artifact_store.py`, `src/prometeus/infrastructure/scrapling/session_store.py`, `tests/integration/market_sources/test_scrapling_retention.py`, `tests/operational/test_scrapling_session_recovery.py`. **Modificar:** `application/read_collected_datasets.py`, `application/evidence_reading_audit.py`, `application/evidence_reading_context.py` sob `src/prometeus/`.

1. Testar captura extensa, PDF/documento, conteúdo dinâmico, falha após prefixo, artefato original versus higienizado e cursores de leitura. Omissão impede alegação de integralidade.
2. Observar RED nos dois testes novos; implementar armazenamento atômico/hash, reabertura de sessão permitida e leitura por partes sem truncamento silencioso.
3. Conferir que perda de browser não significa perda do acervo; cookies ficam isolados e operações já terminadas não são recompradas.
4. Rodar testes novos e ensaio real nas mesmas URLs do crawler atual, registrando resultados e consumo. Não expor payload bruto na API.
5. Commit sugerido: `feat: preserve Scrapling artifacts and resumable acquisition`. Registrar gate CS-03 com corpus e limites.

### Tarefa 9 — Gateway MCP interno e skills (CS-04)

**Criar:** `src/prometeus/application/research_tool_gateway.py`, `src/prometeus/entrypoints/mcp/research_server.py`, `src/prometeus/infrastructure/codex/skill_bundle.py`, `config/codex/tools.example.toml`, `tests/contract/mcp/test_research_gateway.py`. **Modificar:** `application/skill_registry.py` e skills pertinentes.

1. Testar tenant/analysis impostos pelo servidor, ferramenta não permitida, lease expirado e chamada repetida. O MCP de integração externa existente não é uma credencial de administração interna.
2. Observar RED no teste novo; implementar ferramentas definidas nos contratos sobre os mesmos casos de uso de aquisição/ingestão.
3. Empacotar as skills existentes por etapa, com versão/hash; não copiar skills e MCPs pessoais. Testar transporte real das instruções e ferramentas permitidas.
4. Validar URLs/redirecionamentos, IDs opacos de artefatos e ausência de escrita em produção; scripts/páginas não alteram políticas.
5. Commit sugerido: `feat: expose scoped research tools to Codex runtime`.

### Tarefa 10 — Loop de pesquisa dentro dos checkpoints (CS-04)

**Modificar:** `src/prometeus/application/run_course_analysis.py`, `plan_course_research.py`, `research_sufficiency.py` e `collection_diagnostics.py` no mesmo diretório. **Criar:** `tests/integration/market_sources/test_agent_research_recovery.py`, `tests/evaluation/research/test_codex_research_policy.py`.

1. Testar trajetória em que Codex descobre uma URL pela Apify, solicita Scrapling, detecta aba adicional e devolve evidência ao acervo. Testar ausência de sinal, falha técnica, repetição e conteúdo malicioso.
2. Observar RED nos testes novos; integrar decisões delimitadas de aprofundamento sem delegar transições de estado ao modelo.
3. Preservar até três retentativas da tarefa, reconciliação incerta e deduplicação entre workflow e MCP. Toda consulta externa usada na conclusão ganha proveniência.
4. Executar os testes e uma trajetória real auditada. Medir ganho de evidência, não somente contagem de tools.
5. Commit sugerido: `feat: integrate tool-assisted research within canonical checkpoints`.

### Tarefa 11 — Dossiê canônico e CMS (CS-05)

**Modificar:** `src/prometeus/application/synthesize_dossier.py`, `dossier_verifier.py`, `dossier_cms_builder.py`, `src/prometeus/domain/dossiers.py`, `src/prometeus/entrypoints/rest/app.py`, `web/app.js` e prompts/skills afetados. **Criar:** `tests/contract/dossiers/test_codex_dossier_output.py`, `tests/integration/dossiers/test_codex_cms_roundtrip.py`, `tests/evaluation/dossier/test_codex_factual_controls.py`.

1. Testar saída do Codex com claims válidas/inventadas, fatos desfavoráveis e corpus maior que o contexto. O gate bloqueia texto sem suporte e leitura pendente.
2. Observar RED nos testes novos; integrar síntese/revisão à porta existente e builder determinístico. Escrita incremental somente se o contrato atual não atender.
3. Persistir, servir, recarregar e comparar as nove páginas; garantir que a hidratação conserva conteúdo canônico e revisões humanas.
4. Rodar testes novos e navegar no CMS com dossiê real, conferindo economia negativa, histórico sintético, fontes e distinção entre nota, confiança e cobertura.
5. Commit sugerido: `feat: generate verified CMS dossiers through Codex CLI`.

### Tarefa 12 — Homologação, ativação e reversão (CS-06)

**Criar:** `tests/evaluation/research/codex_scrapling_protocol.md`, `scripts/audit_codex_scrapling_runtime.py`, `tests/e2e/test_codex_scrapling_course_analysis.py`, `tests/operational/test_codex_scrapling_rollout.py`. **Atualizar:** documentação de configuração, deploy, testes, gates e relatório de homologação.

1. Congelar amostra e rubrica antes dos resultados; incluir abundância, nicho, sinal desfavorável e insuficiência/bloqueio. Separar replay analítico de coleta live.
2. Escrever/rodar testes de ativação só para novas análises e reversão; implementar controle explícito de defaults e telemetria. Nenhum fallback silencioso de runtime.
3. Executar suíte, lint e tipagem no Windows e Linux suportados. Testes live usam opt-in e credenciais seguras; não inferir resultado live de teste pulado.
4. Fazer análise real completa, conferir todos os cinco módulos externos nos casos aptos e demonstrar parada honesta nos demais. Preservar base ENS, dossiês e artefatos de tentativas.
5. Registrar resultados/limites, ensaiar rollback do padrão e decidir ativação segundo [CS-06](../implementation/codex-scrapling/phase-cs-06-homologation.md). Commit sugerido: `feat: enable validated Codex and Scrapling rollout` somente se gate cumprido; caso contrário publicar relatório sem mudar default.

## Checklist de encerramento da trilha

- [ ] CS-00 reproduziu/corrigiu a causa da reconciliação.
- [ ] CS-01 preservou snapshots e acervo legados.
- [ ] CS-02 provou execução CLI real, autenticação e cancelamento.
- [ ] CS-03 reteve e analisou dados adquiridos via Scrapling sem IDs fictícios.
- [ ] CS-04 provou pesquisa assistida sem compras duplicadas e sem reiniciar tentativas.
- [ ] CS-05 provou síntese/revisão e nove páginas após reload.
- [ ] CS-06 publicou amostra, resultados, consumo e rollback, sem alegar calibração comercial não realizada.

Todos os itens estão pendentes no momento da documentação. Relatórios devem ser criados após execução, seguindo o template existente, e distinguir **planejado**, **implementado**, **validado em teste** e **homologado em execução real**.
