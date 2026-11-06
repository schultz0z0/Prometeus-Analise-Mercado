# Cobertura de concorrentes e recuperação Apify — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Corrigir a interrupção artificial da pesquisa, comprovar a cobertura dos concorrentes por execução real e recuperar falhas Apify com até três retentativas diagnosticadas, sem duplicar coletas incertas.

**Architecture:** O backend controla políticas, execução e estados; a LLM propõe consultas e ajustes delimitados. Uma tarefa lógica de coleta possui tentativas persistidas e uma projeção única de cobertura, consumida pelo painel, pelo redator e pelo verificador do dossiê. Custos observados são monitorados sem reserva monetária fixa por chamada nas novas análises.

**Tech Stack:** Python, Pydantic, FastAPI, SQLAlchemy, PostgreSQL, Celery/Redis, httpx, pytest e JavaScript. MCP Apify é uma opção complementar de descoberta, não requisito para corrigir a coleta.

**Status:** aprovado em 04/11/2026; implementação aplicada em 05–06/11/2026. A nova análise real confirmou a coleta das dez instituições; a retomada concluiu os 15 checkpoints e publicou dossiê verificado, com dez ofertas em sete instituições. Validações e resultado vigente estão no [relatório de implementação e homologação](../implementation/reports/collection-recovery-homologation-2026-11-05.md). Dossiês anteriores permanecem preservados.

---

## 1. Evidência e escopo

A análise `dffd0359-4a40-4cc4-be00-fc5bb74bf687` concluiu o workflow técnico, mas não entregou benchmark competitivo completo:

- Dez instituições configuradas; zero ofertas qualificadas na matriz final.
- Dez chamadas iniciadas com autorizações de US$ 0,50 esgotaram o teto agregado de US$ 5. As buscas específicas dos dez concorrentes ficaram nas posições 16 e 17, ambas `budget_skipped`; o crawler dependente ficou sem URLs.
- As primeiras buscas gerais mencionaram algumas instituições, mas não substituíram uma pesquisa comprovada para cada concorrente.
- A apresentação inferiu consulta a partir do texto do plano. A FGV recebeu `no_offer_observed` por uma consulta planejada que também não executou. Além disso, a apresentação recebe o plano inicial e não representa integralmente execução e reparo.
- O custo observado sofreu atualização posterior; isso confirma que cobrança provisória não serve como garantia de teto financeiro. Não há necessidade de usar esse custo como saldo autorizador quando a política não impõe teto monetário.
- Blocos visuais são construídos depois da verificação da redação. A correção deve verificar o objeto final que será publicado.
- O histórico ENS sintético pertence ao pilar interno e deve permanecer preservado e identificado. Não determina quais concorrentes externos são consultados.

Artefatos de referência: `output/homologation-2026-11-04/canary2-progress.json`, `canary2-dossier.json`, `canary2-budget.json` e `canary2-cost-reconciliation.json`.

## 2. Decisões propostas

### 2.1 Custos e escopo operacional

Adotar **monitoramento de custos sem bloqueio monetário da aplicação** para novas análises desta implantação:

- Remover o teto padrão de US$ 5 e a reserva padrão de US$ 0,50 por chamada; não substituir por outro valor fixo maior.
- Omitir `maxTotalChargeUsd` no início das novas runs sob essa política. Não usar zero, infinito ou um valor fictício para representar ausência de teto.
- Registrar explicitamente no snapshot `spending_mode=monitor_only` e ausência de limite monetário da aplicação. Essa política é configuração de operador, nunca decisão da LLM.
- Atualizar formulário/API de configurações e `.env.example`; impedir que o antigo valor padrão ainda presente no `.env` seja herdado silenciosamente por novas análises. Registrar a transição de configuração sem expor segredos.
- Manter escopo finito por consulta: URLs, páginas, itens, profundidade, tempo, concorrência e até três retentativas. Limites de input devem ser implementados por Actor; `maxItems` da API não limita todos os modelos de cobrança nem garante tamanho do dataset.
- Separar custo observado, data/origem da observação, cobrança ainda pendente e eventuais restrições informadas pelo provedor. Ausência de custo confirmado não significa custo zero.
- Ausência de fatura final não bloqueia por si só novas tarefas independentes. Incerteza sobre execução remota impede duplicar aquela tarefa; identidade/build não verificados impedem usar seus dados.
- Restrições da conta e configurações padrão do Actor continuam possíveis: registrá-las como restrições do provedor. Não prometer coleta sem qualquer limite remoto ou garantia de gasto máximo nesse modo.
- Não implementar agora um teto global opcional cuja garantia dependeria novamente de limites monetários por run. Uma política financeira diferente exigirá contrato próprio.

Essa mudança substitui, para novas execuções, a parte financeira da ADR-0010. Persistência anterior ao POST, reconciliação de execução incerta, custos auditáveis e prevenção de duplicidade continuam obrigatórios. Criar ADR-0011 antes de implementar; não reescrever a decisão histórica para esconder a origem do problema.

### 2.2 Cobertura obrigatória e pesquisa por instituição

- Criar tarefas com `competitor_id`, domínios validados, objetivo, prioridade e dependências explícitas. Não descobrir vínculo de execução procurando palavras no texto da query.
- Priorizar descoberta de ofertas dos concorrentes configurados e validação das páginas encontradas, mantendo descoberta aberta de novos concorrentes.
- Clusters de domínios podem acelerar a descoberta inicial, mas uma busca com vários `site:` não comprova cobertura de todos: uma instituição pode dominar o lote.
- Para cada instituição sem descoberta suficiente, executar busca dirigida ao seu domínio. Se a query for estreita, ampliar para sinônimos e ofertas adjacentes, preservando o tema e registrando a diferença. Definir as variantes no plano, com no máximo três variantes semânticas por instituição; não confundir variantes com retentativas técnicas.
- Abrir URLs oficiais descobertas, extrair curso, instituição, modalidade, carga horária, preço e data quando disponíveis. Campo indisponível permanece ausente; preço não é condição para registrar toda oferta válida.
- Preservar as várias ofertas qualificadas de cada instituição, com deduplicação por curso/URL. A linha resumida da instituição deve permitir consultar todas as ofertas; não reduzir o mercado a um único melhor item.
- Classificar oferta direta e adjacente pela aderência ao curso, com justificativa/evidência, sem decidir apenas pela categoria da instituição ou por um corte isolado de horas.
- Notícias e páginas institucionais podem ajudar a descobrir URLs, mas não viram ofertas confirmadas automaticamente.
- Ao finalizar, cada instituição precisa de resultado auditável: pesquisa executada, oferta confirmada, validação pendente ou falha com motivo. Impossibilidade externa continua possível e deve permanecer visível.

### 2.3 Até três retentativas com diagnóstico

Interpretação adotada: **uma tentativa inicial + até três retentativas por tarefa lógica**, no máximo quatro tentativas de execução. O limite persiste após reinício de worker, reparo de plano e troca de transporte. Uma falha não deve abrir indefinidamente novas tarefas equivalentes para reiniciar o contador.

Cada recuperação registra causa estruturada, ação escolhida, alteração de parâmetros, próxima execução e resultado. A LLM pode sugerir ajustes; código aplica apenas opções permitidas pelo contrato e pelo schema do Actor aprovado.

| Causa identificada | Recuperação permitida | Condição para encerrar |
|---|---|---|
| HTTP 429 | Espera exponencial com jitter, respeitando `Retry-After` quando presente; reduzir concorrência compartilhada | Sucesso ou esgotamento das três retentativas |
| Erro de rede/5xx em GET de run, log ou dataset | Repetir leitura da mesma run; não iniciar outro Actor | Recuperação ou limite de retentativas da operação |
| Timeout/5xx no POST de início, resposta inválida ou HTTP 408 ambíguo | Reconciliar run existente usando ID quando conhecido; sem ID, procurar correspondência inequívoca por Actor/build, janela e input persistido | Se não for possível comprovar o resultado, marcar execução incerta; não repetir POST às cegas |
| Run ainda ativa depois do timeout local | Continuar acompanhamento ou solicitar aborto e confirmar estado terminal antes de qualquer substituição | Resultado conhecido ou reconciliação pendente |
| Actor termina com falha transitória recuperável | Consultar logs seguros e aplicar ajuste permitido; nova run somente depois de conhecer o término da anterior | Sucesso ou quatro tentativas totais |
| HTTP 402 por memória/concorrência da conta | Esperar recursos e reduzir concorrência; ajustar memória somente se documentado e compatível com o Actor | Recurso indisponível persistentemente ou limite de retentativas |
| HTTP 400/input inválido | Corrigir campos permitidos conforme schema aprovado; preservar objetivo e validar antes de reenviar | Sem correção válida ou limite de retentativas |
| Bloqueio do site ou configuração de proxy indisponível | Diagnosticar log, reduzir lote, usar modo documentado/URL pública alternativa ou Actor substituto previamente aprovado | Sem alternativa permitida ou limite de retentativas |
| Token inválido, falta de permissão, crédito esgotado, Actor desativado ou build/schema incompatível | Revalidar configuração e registrar ação necessária; alternativa somente se já aprovada e pertinente | Sem mudança efetiva possível, encerrar antes de repetir o mesmo erro |
| Dataset vazio válido | Registrar consulta executada sem resultado; eventual variante semântica pertence à pesquisa, não a retry de falha | Escopo semântico cumprido; nunca inferir procura de mercado igual a zero |

“Até três” é máximo, não obrigação de repetir credencial inválida quatro vezes. A recuperação tenta resolver a causa; não há promessa de superar qualquer bloqueio do fornecedor. Não remover autenticação, acessar conteúdo privado ou ignorar políticas para completar a coleta.

Polling normal não consome uma nova tentativa de Actor. Falhas de leituras possuem contagem de recuperação explícita e limitada, sem multiplicação oculta de retries entre HTTP, SDK, Celery e reparo semântico. Manter `restartOnError=false` para não criar reinícios remotos fora da política local.

### 2.4 Dossiê e progresso com uma única fonte de verdade

Criar projeção canônica que reúne plano inicial, complementos, tarefas, tentativas, runs e evidências qualificadas. Redator, cards, tabela e verificadores usam o mesmo snapshot versionado.

Separar duas dimensões em cada instituição:

- **Execução:** não iniciada, em execução, em retentativa, concluída, parcial, bloqueada ou execução incerta.
- **Evidência:** oferta direta confirmada, oferta adjacente confirmada, candidato pendente de validação ou nenhuma oferta qualificada encontrada no recorte pesquisado.

Assim, falha da segunda tentativa não apaga uma oferta válida da primeira; e uma oferta encontrada não esconde outras páginas bloqueadas. Estado planejado não conta como consulta executada.

Exibir separadamente instituições configuradas, efetivamente pesquisadas, parcialmente pesquisadas/bloqueadas, instituições com ofertas e total de ofertas distintas. Incluir URLs, data, tentativas, motivo da lacuna e campos não disponíveis.

Não usar “não há concorrência” ou “espaço de mercado livre” a partir de buscas vazias. Cobertura é o cumprimento do recorte declarado, nunca garantia de exaustividade da internet.

### 2.5 Critério de entrega

- Cobertura competitiva incompleta não pode receber selo de benchmark completo, nem sustentar conclusão favorável sobre ausência de concorrentes.
- O workflow pode concluir um dossiê parcial com limitações explícitas e recomendação coerente; `COMPLETED`, `VERIFIED` e homologação comercial permanecem conceitos distintos, conforme ADR-0005.
- Verificar o payload final, incluindo blocos visuais, antes de persistir/publicar. Divergência entre execução, tabela e narrativa bloqueia a publicação até correção.
- Não alterar os dossiês antigos silenciosamente. Reanálise cria novo ID e vínculo; um aviso de versão antiga pode ser exibido sem modificar os fatos publicados.

### 2.6 Papel do MCP da Apify dentro do Prometeus

Comparação de abordagens:

1. **Conector API robusto + descoberta MCP opcional — recomendado.** Corrige o problema na origem e permite consultar documentação, schemas e alternativas sem delegar pagamentos e estados ao modelo.
2. **Somente conector API robusto.** Resolve os bloqueios locais e retries; descoberta de alternativas continua no catálogo mantido pela aplicação.
3. **Substituir a execução por MCP.** Acrescenta outra camada de transporte e não elimina limites da conta, falhas do Actor ou do site; exige os mesmos controles de execução e proveniência. Não é a correção recomendada para o incidente.

Se adotado depois das correções centrais, adicionar um cliente MCP no **backend do Prometeus**, independente do MCP de entrada já oferecido pelo produto. Usar endpoint remoto documentado e allowlist inicial somente de `search-actors`, `fetch-actor-details`, `search-apify-docs` e `fetch-apify-docs`; credenciais ficam no backend quando necessárias.

Descoberta de Actor não equivale a autorização para executar. Um candidato só entra no catálogo de recuperação após validar documentação oficial, build pinado, schema, normalizador, preço e contrato de evidência. Antes disso, pode ser apresentado como sugestão técnica, sem coleta paga automática.

Não oferecer `call-actor` irrestrito à LLM. Se execução MCP for integrada futuramente, deve passar pelo mesmo serviço de tarefas/tentativas; uma falha via API não autoriza nova compra via MCP. A indisponibilidade do MCP de descoberta não impede executar os Actors já homologados.

## 3. Sequência de implementação com TDD

Executar na branch de trabalho existente, preservando as alterações da auditoria. Não mover nem limpar a árvore suja para criar isolamento artificial. Não fazer commit abrangente das mudanças prévias; qualquer commit deve listar os arquivos próprios da etapa.

Em cada tarefa: escrever as regressões indicadas; executar e confirmar a falha pelo motivo esperado; implementar o mínimo; repetir a suíte dirigida; atualizar documentação pertinente. Não marcar tarefa como pronta somente por escrever testes.

### Tarefa 1 — Contratos de política e tentativas persistidas

**Criar:** `src/prometeus/domain/collection_execution.py`, `migrations/versions/0014_collection_attempts.py`, `tests/unit/domain/test_collection_execution.py` e `tests/operational/test_collection_attempts_migration.py`.

**Modificar:** `src/prometeus/domain/research.py`, `src/prometeus/domain/configuration.py`, `src/prometeus/infrastructure/db/models.py`, `src/prometeus/infrastructure/db/backup.py` e `scripts/backup_restore.py`.

1. Testar primeiro `monitor_only` sem teto, máximo de quatro tentativas e estado legado sem política fabricada.
2. Modelar `CollectionExecutionPolicy`, motivo/ação de recuperação e `ToolRunAttemptModel`. Manter o vínculo único de tarefa lógica existente; cada tentativa tem índice, input hash, Actor/build, provider run ID, diagnóstico, timestamps, custo e próxima data de retry.
3. Adicionar proveniência da tentativa às evidências, preservando `tool_run_id`; unicidade por tarefa/índice, transação e isolamento institucional impedem duas compras concorrentes.
4. Permitir ausência explícita de limite monetário em novos planos. Preservar valores/snapshots de planos legados e sua política em retomadas; não reinterpretar análises antigas com o novo padrão.
5. Incluir tabela/colunas novas no backup e no restore; testar upgrade e restauração em clone PostgreSQL, além de fixtures SQLite.

Executar: `rtk proxy .venv/Scripts/python.exe -m pytest tests/unit/domain/test_collection_execution.py tests/operational/test_collection_attempts_migration.py tests/operational/test_backup_restore.py -q`.

### Tarefa 2 — Remover a barreira monetária artificial nas novas análises

**Modificar:** `src/prometeus/application/collect_market_evidence.py`, `src/prometeus/application/plan_course_research.py`, `src/prometeus/application/run_course_analysis.py`, `src/prometeus/domain/ports/market_sources.py`, `src/prometeus/infrastructure/apify/client.py`, `src/prometeus/entrypoints/rest/app.py`, `web/js/views/settings-view.js` e `.env.example`. Confirmar o módulo real de settings da UI antes de editar.

**Testes:** `tests/integration/market_sources/test_budget_commitments.py`, `tests/contract/market_sources/test_apify_execution.py`, `tests/unit/domain/test_configuration.py` e `tests/integration/test_chatgpt_model_selection.py`.

1. Reproduzir mais de dez tarefas em `monitor_only`: todas continuam elegíveis sem `budget_skipped` por reserva de US$ 0,50.
2. Assegurar que o POST não envia `maxTotalChargeUsd`; não exigir número positivo quando a política autoriza ausência de teto.
3. Remover os cortes financeiros da criação de seeds e do reparo de pesquisa. Seus limites passam a ser escopo e recuperação, não `5 - spent`.
4. Manter custos com observação pendente sem bloquear tarefas independentes; manter prevenção de execução duplicada mesmo sem controle financeiro por chamada.
5. Atualizar settings/API e testar que a alteração de política não toca OAuth, token Apify ou histórico ENS. Valores antigos permanecem legíveis como legado.

Executar: `rtk proxy .venv/Scripts/python.exe -m pytest tests/integration/market_sources/test_budget_commitments.py tests/contract/market_sources/test_apify_execution.py tests/unit/domain/test_configuration.py -q`.

### Tarefa 3 — Recuperação Apify orientada pela causa

**Criar:** `src/prometeus/application/recover_market_collection.py` e `tests/integration/market_sources/test_apify_recovery_policy.py`.

**Modificar:** `src/prometeus/infrastructure/apify/client.py`, `src/prometeus/infrastructure/apify/registry.py`, `src/prometeus/application/collect_market_evidence.py`, `src/prometeus/application/research_sufficiency.py`, `src/prometeus/application/analysis_jobs.py` e `src/prometeus/workers/tasks.py`.

1. Simular com `httpx.MockTransport` 429 seguido de sucesso; quatro falhas seguidas; GET 502 recuperável; POST com resposta perdida e run remota existente; 402 por concorrência; 401 permanente; input corrigível; timeout com aborto confirmado e dataset parcial.
2. Persistir tentativa e input validado antes do POST; salvar ID remoto assim que recebido, sem esperar até o fim para criar o vínculo local.
3. Para início ambíguo, reconciliar primeiro. Não declarar idempotência remota sem suporte documentado; a referência consultada não estabelece chave de idempotência do POST de início.
4. Aplicar espera por `next_attempt_at`, com cancelamento/lease/heartbeat. Não ocupar worker dormindo por longos períodos. Retomada e redelivery não zeram o contador.
5. Validar cada ajuste pelo registry, preservar a instituição e o objetivo. Mudança de credencial, build ou Actor não é improvisada pela LLM.
6. Deduplicar evidências entre tentativas; custo agregado usa IDs remotos distintos, substituindo snapshots de custo da mesma run em vez de somá-los novamente. Recuperação de GET não conta nova execução paga.
7. Impedir tentativas concorrentes para a mesma tarefa e impedir um segundo plano de reparo de disfarçar a quinta tentativa. Circuit breaker temporário agenda recuperação; não descarta silenciosamente concorrentes.

Executar: `rtk proxy .venv/Scripts/python.exe -m pytest tests/integration/market_sources/test_apify_recovery_policy.py tests/contract/market_sources/test_partial_provider_results.py tests/integration/market_sources/test_resilience_and_failures.py tests/integration/test_workflow_reliability.py -q`.

### Tarefa 4 — Cobertura de todos os concorrentes e suas ofertas

**Criar:** `src/prometeus/application/competitor_coverage.py` e `tests/integration/market_sources/test_competitor_coverage.py`.

**Modificar:** `src/prometeus/application/plan_course_research.py`, `src/prometeus/application/collect_market_evidence.py`, `src/prometeus/application/research_sufficiency.py`, `src/prometeus/application/qualify_market_evidence.py` e `src/prometeus/application/pricing_reference.py`.

**Testes existentes:** `tests/unit/application/test_ecosystem_research_planning.py`, `tests/integration/market_sources/test_url_prioritization_and_outcomes.py` e `tests/unit/application/test_ecosystem_evidence_isolation.py`.

1. Reproduzir dez concorrentes com vários resultados de apenas uma instituição no cluster; exigir buscas dirigidas para as demais.
2. Ordenar dependências por finalidade/prioridade explícita; coleta essencial de concorrência não fica atrás de amostras sociais genéricas.
3. Testar múltiplas ofertas da mesma instituição, preço não publicado, páginas de notícia, oferta adjacente e homônimos de domínio. Comparabilidade financeira e classificação competitiva continuam independentes.
4. Calcular cobertura somente com execuções/resultados associados; planos inicial e complementar contribuem pela mesma regra.
5. Registrar lacunas e motivo após recuperação esgotada; ausência de página não vira ausência de oferta ou de concorrência.

Executar: `rtk proxy .venv/Scripts/python.exe -m pytest tests/integration/market_sources/test_competitor_coverage.py tests/unit/application/test_ecosystem_research_planning.py tests/integration/market_sources/test_url_prioritization_and_outcomes.py tests/unit/application/test_ecosystem_evidence_isolation.py -q`.

### Tarefa 5 — Dossiê, API e interface sem ambiguidade

**Modificar:** `src/prometeus/domain/dossiers.py`, `src/prometeus/application/synthesize_dossier.py`, `src/prometeus/application/ecosystem_presentation.py`, `src/prometeus/application/dossier_verifier.py`, `src/prometeus/entrypoints/rest/app.py`, `web/js/views/dossier-view.js` e `web/js/views/live-view.js`.

**Testes:** `tests/unit/dossiers/test_ecosystem_presentation_blocks.py`, `tests/unit/dossiers/test_verified_presentation.py`, `tests/contract/api/test_analysis_progress.py`, `tests/operational/test_dossier_view_rendering.py` e `tests/integration/dossiers/test_synthesize_dossier_integration.py`.

1. Regressão obrigatória: query FGV planejada + `budget_skipped` nunca gera instituição pesquisada nem “consulta sem oferta”.
2. Regressão: instituição descoberta apenas no plano complementar aparece com sua execução/evidência; item de notícia não vira curso.
3. Montar projeção e blocos visuais antes do último gate; incorporar versão e hash dos fatos. Verificar contagens, estados, referências e narrativa no payload exato a persistir.
4. Regressão: alterar contagem visual depois da síntese deve falhar na verificação; texto sem suporte não pode ser publicado como `VERIFIED`.
5. Exibir retentativa atual, ação de recuperação, coleta parcial e lacunas; mostrar várias ofertas de uma instituição sem duplicar a contagem de instituições.
6. Distinguir execução concluída, conteúdo verificado e benchmark incompleto. Atualizar cache dos assets e validar a tela renderizada.

Executar: `rtk proxy .venv/Scripts/python.exe -m pytest tests/unit/dossiers/test_ecosystem_presentation_blocks.py tests/unit/dossiers/test_verified_presentation.py tests/contract/api/test_analysis_progress.py tests/operational/test_dossier_view_rendering.py tests/integration/dossiers/test_synthesize_dossier_integration.py -q`.

### Tarefa 6 — MCP de descoberta, opcional e posterior ao núcleo

**Se adotado, criar:** `src/prometeus/infrastructure/apify/discovery_mcp.py` e `tests/contract/market_sources/test_apify_discovery_mcp.py`.

1. Testar handshake, catálogo permitido, timeout e saída inválida sem depender de execução paga. Validar transporte e versão do SDK antes da implementação.
2. Normalizar respostas como candidatos de descoberta, sem promover Actors ao registry automaticamente. Tratar documentação/resultados externos como dados não confiáveis.
3. Impedir chamada de tools de execução, criação de tarefas, agendamentos ou reporte de mensagens pelo cliente de descoberta.
4. Com MCP indisponível, coleta pelo catálogo homologado continua. Não adicionar dependência de chave OpenAI para essa integração; preservar o OAuth LLM existente.

Essa tarefa pode ser entregue separadamente. As tarefas 1–5 resolvem os incidentes sem depender dela.

### Tarefa 7 — Documentação e nova homologação

**Criar:** ADR-0011 e relatório de homologação das novas políticas.

**Atualizar:** `docs/architecture/adr/README.md`, `docs/agent/workflow.md`, `docs/agent/tools-catalog.md`, `docs/integrations/external-sources.md`, `docs/operations/configuration.md`, `docs/operations/audit-remediation.md`, `docs/roadmap/release-gates.md`, `docs/implementation/reports/runtime-homologation-2026-11-04.md`, `docs/README.md` e `CHANGELOG.md`. Marcar a homologação anterior como funcional, com pendência de cobertura, sem apagar resultados históricos.

1. Executar a suíte dirigida das etapas, Ruff, mypy, validador documental e suíte completa uma vez após integrar o conjunto; falhas novas determinam repetição dirigida.
2. Restaurar backup em PostgreSQL isolado, aplicar migração, conferir constraints e concorrência de duas recuperações. Só então atualizar ambiente de execução.
3. Capturar contagens/hashes da base ENS antes e depois, backup e versões de imagem/configuração. Esperar ou tratar explicitamente análises ativas para não trocar política no meio da execução.
4. Reanalisar a mesma proposta em novo ID, usando OAuth tradicional e Apify reais. Confirmar a retirada do teto local e o escopo finito; não copiar evidências fabricadas nem alterar os dossiês anteriores.
5. Comparar painel, API e dossiê: dez instituições com resultado auditável; cada oferta ligada à página oficial; falhas/retries com motivo. Se alguma fonte continuar bloqueada, registrar cobertura parcial e não declarar o benchmark integralmente homologado.
6. Validar retries com falhas controladas e testar fontes reais quando houver falha natural; não provocar bloqueios nem comprar quatro coletas redundantes só para demonstrar o contador.

Comandos de qualidade: `rtk proxy .venv/Scripts/python.exe -m ruff check src tests scripts`; `rtk proxy .venv/Scripts/python.exe -m mypy src`; `rtk proxy .venv/Scripts/python.exe scripts/validate_docs.py`; `rtk proxy .venv/Scripts/python.exe -m pytest -q`.

## 4. Critérios objetivos de aceite

- [x] Novas análises não usam teto monetário local de US$ 5 nem reserva/cap fixo por chamada; o POST omite `maxTotalChargeUsd` nessa política.
- [x] Mais de dez tarefas executáveis não são descartadas por reservas artificiais; limites de escopo e cancelamento continuam funcionando.
- [x] Cada concorrente configurado recebe pesquisa verificável ou uma lacuna operacional com motivo, tentativas e ação tomada; cluster não simula cobertura individual.
- [x] Múltiplas ofertas qualificadas são preservadas, com instituição e curso contados separadamente (contratos, regressões e benchmark real final verificados).
- [x] Até três retentativas são persistidas e diagnosticadas; reinício, reparo e troca de transporte não autorizam quinta tentativa equivalente.
- [x] POST ambíguo não gera nova compra sem reconciliação; GET recuperado não cria novo Actor; cancelamento impede retries posteriores.
- [x] Falha, pesquisa não executada, dataset vazio, item rejeitado e candidato ainda não confirmado têm representações distintas.
- [x] Painel, API, narrativa e tabela usam a mesma projeção; a verificação alcança o payload final completo.
- [x] Benchmark parcial fica explícito e não fundamenta alegação de ausência de concorrência.
- [x] Histórico ENS, OAuth e segredos permanecem preservados; backup/restore e isolamento institucional incluem as novas estruturas.
- [x] A nova homologação produz evidências reais e não transforma conclusão técnica do workflow em aprovação comercial.

Os gates automatizados e a inspeção do dossiê real passaram em 06/11/2026. Dez instituições pesquisadas, dez ofertas em sete instituições, com lacunas externas e natureza sintética explícitas. A conclusão técnica não aprova lançamento de curso nem rollout público; SLA e calibração comercial permanecem fora deste aceite.

## 5. Documentação oficial consultada em 04/11/2026

- [Run Actor](https://docs.apify.com/api/v2/actors-runs-post): opções de início, build, timeout, `maxItems`, `maxTotalChargeUsd` e `restartOnError`.
- [Retries — cliente Python](https://docs.apify.com/api/client/python/docs/concepts/retries): falhas transitórias, espera exponencial e distinção de recursos da conta em HTTP 402. O Prometeus usa httpx próprio: comportamento do SDK não está automaticamente implementado aqui.
- [Apify API](https://docs.apify.com/api/v2): rate limiting e tratamento de HTTP 429.
- [Lista de runs](https://docs.apify.com/api/v2/actor-runs-get): apoio à reconciliação, sem tratar correspondência ambígua como prova de identidade.
- [Apify MCP](https://docs.apify.com/mcp): ferramentas de descoberta, execução, logs e datasets; autenticação; conexão remota e limitações.
- [Agent quickstart](https://docs.apify.com/get-started/agent-onboarding): integração por MCP para agentes e API client para backends.

Revalidar schemas e opções de cada Actor pinado antes de habilitar ajustes ou substitutos. Uma capacidade geral documentada pela plataforma não comprova suporte em todo Actor.
