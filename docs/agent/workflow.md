# Workflow do agente

## Evolução planejada — Codex CLI + Scrapling

A [trilha CS-00–CS-06](../implementation/codex-scrapling/README.md), documentada em 12/11/2026, preserva os checkpoints canônicos e propõe Codex CLI nas etapas inteligentes, Apify nas fontes especializadas e Scrapling em aquisição web. A execução assistida por ferramentas permanece dentro da etapa e passa pelo gateway do Prometeus. A trilha está planejada; os providers e contratos atuais continuam vigentes até implementação, testes e ativação explícita para novas análises.

## Correções de confiabilidade — 04/11/2026

A criação e a reanálise persistem snapshot e job de outbox antes do commit; a publicação Celery é posterior. O scheduler reconcilia falhas de broker e leases vencidos. Consumidores usam lease exclusivo, heartbeat e revisão otimista para preservar cancelamento/estados terminais. Checkpoints e julgamentos consultam cancelamento/posse antes de novas chamadas. Consultas remotas interrompidas sem resultado confirmado ficam `IN_DOUBT` e bloqueiam nova compra até reconciliação, sem supor custo zero.

Keywords são julgadas/persistidas sem compartilhar `AsyncSession` em tarefas concorrentes e recebem vínculo de análise/instituição. Falha técnica não equivale a `IRRELEVANT`. Reanálise exige nova chave e snapshot próprio; não copia identificadores internos da proposta anterior.

Eventos de conclusão/bloqueio/falha alimentam outbox de webhook na transação da mudança, com despacho posterior. MCP stdio usa a criação canônica. Dados visuais não recebem conclusões ou valores genéricos após os gates; economia é simulação explícita pelo motor Decimal. Detalhes em [operação após correções](../operations/audit-remediation.md) e [simulação econômica](../scoring/economic-simulation.md).

## Estados macro

O ciclo de vida segue o [ADR-0005](../architecture/adr/0005-status-vs-recommendation.md):

```text
QUEUED -> RUNNING -> WAITING_FOR_INPUT -> RUNNING
                  -> BLOCKED           -> RUNNING | FAILED
                  -> COMPLETED  (recommendation preenchida)
                  -> FAILED | CANCELLED
```

A `recommendation` (`APPROVED`, `APPROVED_WITH_ADJUSTMENTS`, `HIGH_RISK`, `INSUFFICIENT_EVIDENCE`, `REQUIRES_HUMAN_REVIEW`) é definida em código na etapa 11 e só existe quando `status = COMPLETED`.

## Etapas

| Etapa | Entrada | Responsável | Saída | Falha típica |
|---|---|---|---|---|
| 01 Contexto | institution_id | Código | Config snapshot | Config inválida |
| 02 Intake | Proposta | Schema/código | Proposal canônica | Campo ausente |
| 03 Readiness | Proposal | Regras + modo de IA | Perguntas ou aprovação | LLM/JEV indisponível |
| 04 Keywords | Proposal | LLM + modo de IA + código | Keyword set | Termos irrelevantes |
| 05 Research plan | Proposta + contexto + skills | LLM + política | Plano ordenado de tools | Fonte obrigatória sem acesso |
| 06 Histórico | Keyword set | Adaptador institucional | Comparáveis ENS sintéticos identificados | Contrato divergente |
| 07 Mercado | Research plan | Actors Apify reais | Evidências e tool runs | Quota/timeout/schema drift |
| 08 Higienização | Evidências brutas | Código | Evidências válidas | Duplicação ou conteúdo inválido |
| 09 Julgamentos | Estado delimitado | JEV ou LLM tradicional | Decision results | Baixa confiança |
| 10 Scoring | Features | Código | 3 índices + sub-scores | Cobertura insuficiente |
| 11 Quality gate | Dossiê estruturado | Código | `recommendation` + aprovar/revisar/bloquear | Contradição |
| 12 Síntese | Fatos aprovados | LLM | Texto estruturado | Afirmação não suportada |
| 13 Verificação | Texto + fatos | Código + modo de IA delimitado | Dossiê validado | Número inventado |
| 14 Entrega | Dossiê | Persistência/webhook | Evento entregue | Destino indisponível |
| 15 Feedback | Decisão humana | API/MCP | Outcome record | Usuário sem permissão |

## Regras por etapa

Novos planos usam a [ADR-0011](../architecture/adr/0011-collection-coverage-and-recovery.md): monitoramento sem teto monetário local, até três retentativas diagnosticadas por tarefa e cobertura por concorrente. A espera fica em `next_attempt_at`; o job retorna à fila, mantendo análise `RUNNING` e checkpoint `PENDING`. Redelivery antecipada não adquire o job. Execução incerta recupera a mesma run; cancelamento solicita aborto e impede novas tentativas.

A execução canônica implementada possui os checkpoints `runtime_preflight`, `intake_normalization`, `readiness_assessment`, `course_understanding`, `keyword_entity_mapping`, `research_planning`, `institutional_history`, `external_tool_execution`, `evidence_sanitization`, `semantic_judgments`, `verified_feature_scoring`, `quality_gates`, `dossier_synthesis`, `factual_verification` e `publish_completion`. A tabela acima organiza responsabilidades conceituais; feedback humano é posterior à publicação. Os números exibidos no painel seguem esses checkpoints do código.

Desde 29/10/2026, `conducting-course-analysis` orienta todas as etapas semânticas. A operação Apify e os procedimentos seletivos por fonte complementam essa orientação conforme a [estratégia de skills](skills-strategy.md). Antes de recuperar pesquisa, a LLM recebe diagnóstico por consulta com status, registros normalizados, qualificados/contextuais, motivos e erro seguro. Sucesso técnico sem evidência qualificada é distinguido de coleta útil. O diagnóstico inicial fica no checkpoint 9; limites de rodada, orçamento e reuso continuam validados em código.

- Cada etapa recebe e devolve contratos versionados.
- O resultado é persistido antes de publicar o próximo evento.
- Etapas externas possuem timeout, recuperação limitada e agendamento de espera; falhas permanentes exigem configuração do operador.
- Repetição usa idempotency key e não duplica custos quando cache válido existe.
- Dados brutos nunca são considerados verdade sem proveniência e validação.
- O workflow pode retomar do último checkpoint seguro.
- Falha, timeout ou conteúdo inutilizável de uma ferramenta externa não bloqueia a análise: o plano termina `PARTIAL`, continua com as outras ferramentas e usa somente evidências válidas. `required` indica prioridade/cobertura planejada, não veto de execução. Falta de evidências limita a recomendação, sem fabricar demanda ou conclusão.
- Timeout com aborto terminal confirmado pode preservar itens independentes já gravados no dataset. A consulta fica `PARTIAL` e não é tratada como sucesso integral; seus itens passam pelos mesmos gates e sua lacuna/custo permanecem na narrativa e no painel. Aborto ainda em andamento não autoriza recuperar o dataset.
- Retomada reutiliza resultados terminais e datasets vazios. `collection-v2` preserva tentativas anteriores e permite somente a recuperação diagnosticada ainda disponível; novo plano não reinicia o contador. Planos legados mantêm suas reservas financeiras originais.
- O painel acompanha o estado do backend até um estado terminal, sem encerrar após cinco minutos. Falhas de conexão geram aviso e nova consulta automática; lacunas de ferramentas aparecem no painel e no dossiê.
- Antes de qualquer Actor pago, o preflight exige LLM real e todas as capabilities obrigatórias.
- URLs usadas por crawler e YouTube são resolvidas de evidências anteriores; a LLM não pode inventá-las.
- O dossiê só é entregue com scoring persistido, claims referenciadas e status `VERIFIED`.
- Antes das features, cada evidência passa pelo pack experimental `market-relevance-v1` no modo ativo. Sinais rejeitados e contexto setorial não entram nas contagens de demanda ou concorrência.
- Quando o tenant declara `ecosystem.competitors`, cada instituição recebe busca dirigida prioritária e validação dependente em domínios oficiais. Sem ofertas qualificadas, até três variantes semânticas ampliam o recorte; bloqueio técnico não vira nova variante para contornar o contador. Descoberta aberta e radar setorial continuam no plano.
- Consultas competitivas começam pelo foco do título do curso; o primeiro domínio temático de apoio não pode ocupar sozinho todos os termos. A segunda variante inclui mais termos do título e formatos educacionais; a terceira busca o tema amplo dos domínios de apoio para ofertas adjacentes. Planos já persistidos mantêm o texto executado.
- Atores de `sector_radar` (seguradoras/empregadores) são isolados deterministicamente em `qualify_market_evidence`, `pricing_reference` (`sector_ecosystem_not_course_offer`) e `DossierVerifier` (`sector_actor_as_direct_competitor`): alimentam exclusivamente sinais de demanda, tendências e currículo (`#sec-sector-radar`), enquanto apenas concorrentes acadêmicos alimentam `#sec-competitive-benchmark`, `direct_competition` e preço de referência. Perfis LinkedIn marcados como `global` recebem selo contextual explícito e são bloqueados contra alegações de audiência nacional brasileira (`global_social_metric_as_national`).
- Outras lacunas geram rodadas complementares persistidas enquanto houver consultas novas. Não há encerramento automático após a primeira rodada: cada nova rodada recebe as consultas de todos os planos anteriores e diagnósticos atualizados, com custo acumulado. IDs estáveis permitem retomar as mesmas tentativas; consultas equivalentes são removidas pelo planejador. Sem novas consultas válidas, cancelamento ou restrição financeira de snapshot legado, a busca para e mantém as lacunas explícitas; isso não comprova suficiência. Zero observado, ausência de coleta e resultado inadequado são estados distintos. O dossiê reúne todos os planos e runs; validação sem URL após busca executada é marcada `no_candidates_to_validate`, sem compra de crawler.
- O dossiê v2 passa por verificações numéricas/referenciais de todos os blocos e por julgamento semântico delimitado; seus critérios e ações não concluem validações humanas.
- Quando o dossiê é rejeitado por esses gates, há no máximo uma revisão da redação com os mesmos fatos e diagnóstico persistido antes da chamada. Ambos os gates são executados novamente; somente uma revisão válida é publicada. Falha persistente preserva bloqueio e diagnóstico, sem repetir pesquisa ou alterar scoring.

A fase responsável por implementar cada etapa está em [Planos de implementação](../implementation/README.md#etapas-do-workflow-por-fase).

## Progresso

O gate final verifica também os blocos visuais exatos antes de persistir, incluindo o envelope CMS de 9 subpáginas (`presentation.cms_pages`: `overview`, `key_metrics`, `fixed_competition`, `sector_radar`, `economics`, `swot_tows`, `viability_pillars`, `revisions`, `sources_evidences`) construído deterministicamente por `DossierCmsPageBuilder` e validado em `DossierVerifier.verify_presentation`. Contagens de instituições pesquisadas, ofertas e lacunas vêm da mesma projeção determinística; `VERIFIED` não significa benchmark completo nem aprovação comercial. Revisões humanas por área (`Marketing`, `Produto`, `Comercial`, `Financeiro`) são registradas após a publicação na tabela `dossier_area_reviews` e hidratadas na aba `Revisões`.

O percentual é aproximado e baseado em etapas concluídas, não em tempo estimado. O chatbot recebe status legível, última atualização e eventuais ações exigidas.

## Cancelamento

Cancelamento interrompe novas etapas e solicita aborto de Actors quando suportado. Evidências e custos já incorridos permanecem no audit log.
