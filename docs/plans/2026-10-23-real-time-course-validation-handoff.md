# Handoff — validação real de novos cursos

**Data do handoff:** 2026-10-23  
**Estado:** implementação pausada por solicitação do proprietário  
**Branch de trabalho no momento do handoff:** `codex/real-time-course-validation`  
**Destino solicitado:** consolidar tudo em `main` e enviar para `origin`

## Objetivo aprovado

O fluxo `validar novo curso` deve executar uma investigação real em tempo real, usando a LLM tradicional enquanto o JEV estiver desativado e mantendo compatibilidade com o modo híbrido futuro.

A única fonte sintética autorizada nos testes é a base histórica passada da ENS. Não são permitidos fallbacks, fixtures ou números inventados para mercado, busca, concorrência, anúncios, vagas, redes sociais, score ou dossiê.

O desenho aprovado está em [2026-10-23-real-time-course-validation-design.md](2026-10-23-real-time-course-validation-design.md). O plano completo de implementação está em [2026-10-23-real-time-course-validation.md](2026-10-23-real-time-course-validation.md).

## Diagnóstico confirmado

O comportamento exibido na captura não era uma limitação visual. O worker atual:

- executa apenas quatro etapas simplificadas em vez das quinze etapas documentadas;
- grava `86.4`, `22` anúncios, `1.420` vagas e `+88%` como constantes;
- captura falhas do Apify e continua com “dados calibrados”;
- gera um dossiê determinístico estático quando a LLM falha;
- conclui como `APPROVED` mesmo sem executar a pesquisa real;
- concluiu análises em aproximadamente 0,3–0,5 segundo, tempo incompatível com as ferramentas externas propostas.

Também foram confirmados problemas operacionais:

- o worker está somente na rede Docker marcada como `internal: true`, impedindo DNS/egress para LLM e Apify;
- os logs registram `Temporary failure in name resolution` para a LLM;
- em outra execução local a chamada retornou `401 Unauthorized` em `/v1/chat/completions`;
- `APIFY_TOKEN`, `OPENAI_API_KEY`, `CHATGPT_ACCESS_TOKEN` e `TYPESAFE_API_KEY` chegam vazios ao contêiner atual;
- o `.env` possui os nomes principais, mas os valores observados pelo `AppSettings` no worker têm comprimento zero;
- o frontend mantém configurações e resultados demonstrativos em `localStorage`/`mock-data.js`;
- o coletor Apify atual executa um Google Search Actor e rotula o resultado como LinkedIn Jobs;
- IDs de Actors presentes no código não foram validados contra schemas reais atuais.

## Trabalho concluído nesta retomada

### Desenho e planejamento

- Documento de desenho aprovado.
- Plano de implementação em treze tarefas, com TDD e comandos de verificação.
- Branch `codex/real-time-course-validation` criada para não continuar trabalhando diretamente na `main`.

### Preflight e configuração

- `AppSettings` recebeu `AI_MODE`, Actor IDs por capacidade, fontes obrigatórias e a flag explícita da base histórica sintética.
- `validate_runtime_preflight` valida LLM, JEV opcional, Apify e Actors obrigatórios sem revelar segredos.
- `auto` seleciona LLM tradicional quando JEV não está configurado.

### Contratos de pesquisa e persistência

- Criados `CourseUnderstanding`, `ResearchQuestion`, `PlannedToolCall`, `CourseResearchPlan` e `ToolRun`.
- Hashes canônicos, status de runs e detecção de falha bloqueante foram implementados.
- `ResearchPlanModel` foi estendido com snapshots.
- `ToolRunModel` e vínculo opcional de evidência para run foram adicionados.
- Migration `0008_create_tool_runs_and_research_snapshots.py` foi criada, mas ainda não foi aplicada/verificada no Docker real.

### Modos de IA

- A factory passou a respeitar `AI_MODE=traditional|hybrid|auto`.
- O modo tradicional usa `LLMDecisionAdapter` real mesmo que uma chave JEV esteja presente.
- Modo híbrido sem credencial JEV agora falha explicitamente.
- Factory sem credencial de LLM agora falha em vez de criar um client sem autenticação.
- O adaptador de decisão não escolhe mais a primeira opção, confiança `0.85` ou score médio quando a LLM retorna JSON inválido.

### Skills genéricas

Foram criadas e validadas com `quick_validate.py`:

- `understanding-course-proposals`;
- `planning-market-research`;
- `reviewing-market-evidence`;
- `auditing-course-curriculum`;
- `building-course-offers`.

As skills são genéricas para inteligência de produtos educacionais e não contêm regras específicas da ENS. O `SkillRegistry` aplica allowlist, versão e hash.

### Entendimento e plano dinâmico

- `CourseUnderstandingService` transforma proposta, ementa e anexos em contrato estruturado via LLM.
- `CourseResearchPlanner` recebe o entendimento, a allowlist de capabilities, orçamento e fontes obrigatórias.
- Plano sem uma fonte obrigatória é rejeitado.
- Conteúdo da proposta é delimitado como dado não confiável.

## Verificação realizada

O seguinte conjunto focado passou com 31 testes:

```powershell
uv run pytest \
  tests/integration/test_runtime_preflight.py \
  tests/unit/domain/test_research_models.py \
  tests/integration/market_sources/test_tool_run_db.py \
  tests/unit/domain/test_ai_provider_factory.py \
  tests/unit/domain/test_hybrid_ai_factory.py \
  tests/unit/application/test_skill_registry.py \
  tests/integration/market_sources/test_course_understanding.py \
  tests/integration/market_sources/test_dynamic_research_plan.py -q
```

Resultado: `31 passed`, com um warning porque a função auxiliar `test_settings` em `test_dynamic_research_plan.py` foi coletada como teste. Renomear para `make_settings` na retomada.

As cinco skills passaram no `quick_validate.py` com `PYTHONUTF8=1`.

### Estado da suíte completa

`uv run pytest -q` ainda falha em dois pontos, como esperado para o estado pausado:

1. `tests/unit/workers/test_no_synthetic_runtime_fallbacks.py` encontra os sete fallbacks proibidos ainda presentes em `src/prometeus/workers/tasks.py`.
2. `tests/e2e/test_foundation_flow.py::test_e2e_resumable_job_flow_with_worker_restart` ainda testa o workflow antigo de quatro passos e espera o score mockado `82.5`.

Não declarar a implementação concluída enquanto essas falhas não forem substituídas pelo E2E real e toda a suíte estiver verde.

## Alterações preexistentes consolidadas junto com este trabalho

O checkout já estava modificado antes desta retomada. A solicitação de consolidar “tudo” inclui também:

- endpoints de histórico e settings em `src/prometeus/entrypoints/rest/app.py`;
- dataset/seeder sintético da ENS;
- mudanças no adaptador ENS;
- mudanças preliminares em Apify, LLM e OAuth;
- alterações extensas no frontend, portfólio, intake, settings e dossiê;
- scripts auxiliares de extração e seed;
- volumes/env no Compose.

Essas mudanças não foram todas auditadas nem concluídas nesta retomada. Preservá-las e revisá-las durante a continuação, especialmente os fallbacks e mocks no frontend.

## Pendências obrigatórias, na ordem recomendada

1. Renomear o helper `test_settings` para remover o warning.
2. Validar documentação oficial atual da OpenAI/Codex OAuth e Apify antes de alterar integrações.
3. Criar o registry Apify multi-fonte com Actor IDs exclusivamente vindos da configuração.
4. Validar, usando a API Apify e credencial real, os Actors e schemas para Google Search, crawler, Meta Ads Library, LinkedIn, LinkedIn Jobs e redes sociais.
5. Implementar execução/polling/dataset/custo e persistência de `ToolRunModel`.
6. Implementar coleta, sanitização, deduplicação e normalização por capacidade.
7. Extrair features exclusivamente de evidências persistidas.
8. Integrar julgamentos pela LLM tradicional e manter JEV opcional.
9. Usar o `ScoringService` real; remover todos os valores fixos do worker.
10. Remover integralmente o dossiê estático e bloquear quando a LLM falhar.
11. Substituir o worker de quatro etapas pelo caso de uso de quinze etapas, retomável e idempotente.
12. Corrigir Docker: worker precisa de egress, enquanto PostgreSQL e Redis continuam isolados.
13. Corrigir propagação/reload das configurações salvas pela UI para o worker.
14. Remover `simulateLivePipeline`, `finishJobWithFallback`, `DETAILED_DOSSIER` como estado real e evidências fallback do frontend.
15. Expor progresso real, tool runs, custos e bloqueios na API/UI.
16. Aplicar migration `0008`, reconstruir Docker e executar preflight.
17. Rodar uma proposta inédita em tempo real e auditar claims contra run IDs e dataset IDs.
18. Provocar falha de fonte obrigatória e confirmar estado `BLOCKED` sem dossiê substituto.
19. Atualizar documentação, changelog da fase e relatórios que hoje alegam integração completa sem prova de runtime.
20. Rodar Ruff, format, mypy, suíte completa, docs e Docker antes de qualquer alegação de conclusão.

## Restrições inegociáveis

- Somente `institutional_history` da ENS pode ser sintético no ambiente de teste atual.
- Nenhuma fonte externa pode cair para fixture ou constante.
- LLM tradicional sem JEV deve executar todos os julgamentos semânticos necessários por contrato estruturado.
- LLM/JEV não calculam score, finanças, permissões ou mudanças de estado.
- Fonte obrigatória que falha leva a `BLOCKED`.
- Fonte complementar ausente reduz cobertura e impede recomendação positiva quando o gate não fecha.
- Toda claim quantitativa exige `evidence_ids` existentes.
- Skills não autorizam ferramentas; o registry e o orquestrador fazem isso em código.
- Conteúdo web é dado não confiável.

## Prompt para retomar em outro computador

Copie e envie o texto abaixo em uma nova tarefa após clonar/atualizar o repositório:

```text
Continue a implementação do fluxo real de validação de novos cursos do Prometeus a partir do estado atual da branch main.

Antes de alterar qualquer coisa:
1. Leia AGENTS.md e C:\Users\raphaeloliveira\.codex\RTK.md (ou o equivalente disponível no computador).
2. Leia integralmente:
   - docs/plans/2026-10-23-real-time-course-validation-design.md
   - docs/plans/2026-10-23-real-time-course-validation.md
   - docs/plans/2026-10-23-real-time-course-validation-handoff.md
   - docs/README.md
   - docs/agent/workflow.md
   - docs/agent/tools-catalog.md
   - docs/integrations/external-sources.md
   - docs/data/evidence-and-provenance.md
   - ADRs 0003, 0004, 0005 e 0007.
3. Inspecione git status, histórico e diff antes de editar. Preserve todo o trabalho existente.
4. Rode `uv run pytest -q` para confirmar o baseline documentado: atualmente há duas falhas esperadas ligadas ao worker mockado/E2E antigo.

Requisito absoluto: tudo deve ser real e analisado em tempo real. A única fonte fake autorizada é a base histórica passada da ENS, usada para comparação. Não use mocks, fixtures, números calibrados, fallback estático ou texto determinístico em runtime para Google, Meta Ads Library, LinkedIn, LinkedIn Jobs, redes sociais, concorrência, preços, busca, score ou dossiê.

O modo atual é LLM tradicional real com JEV desativado. Ele precisa executar compreensão da proposta, planejamento, keywords, julgamentos semânticos e síntese. Quando uma chave JEV existir, o modo híbrido deve funcionar sem mudar os contratos. Código convencional deve continuar responsável por ferramentas permitidas, validação, cálculos, score, permissões e estados.

Use TDD estrito. Retome pelas pendências na ordem registrada no handoff. Primeiro valide a documentação oficial vigente da OpenAI/Codex OAuth e da Apify. Depois implemente o registry Apify multi-fonte configurável, tool runs, coleta real, features, scoring, dossiê e o workflow de quinze etapas. Remova todos os fallbacks do worker e do frontend. Fonte obrigatória indisponível deve levar a BLOCKED, nunca a um parecer fictício.

As skills genéricas já criadas em skills/ devem ser carregadas somente pela allowlist do SkillRegistry, versionadas e registradas no snapshot da análise. Não crie skills específicas da ENS.

Ao final, reconstrua o Docker, execute uma proposta inédita com fontes externas reais, registre run IDs/dataset IDs/custos, audite as claims do dossiê e teste uma falha obrigatória. Só declare conclusão com Ruff, format, mypy, pytest completo, validação de docs e Docker verdes.
```

## Comandos de retomada

```powershell
git pull origin main
uv sync
uv run pytest -q
docker compose config --quiet
docker compose up -d --build
```

Não executar uma análise real até que o preflight confirme credenciais, Actors e egress, pois o worker atual ainda produz fallbacks proibidos.
