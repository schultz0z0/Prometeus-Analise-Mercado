# Workflow do agente

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

A execução canônica implementada possui os checkpoints `runtime_preflight`, `intake_normalization`, `readiness_assessment`, `course_understanding`, `keyword_entity_mapping`, `research_planning`, `institutional_history`, `external_tool_execution`, `evidence_sanitization`, `semantic_judgments`, `verified_feature_scoring`, `quality_gates`, `dossier_synthesis`, `factual_verification` e `publish_completion`. A tabela acima organiza responsabilidades conceituais; feedback humano é posterior à publicação. Os números exibidos no painel seguem esses checkpoints do código.

Desde 29/10/2026, `conducting-course-analysis` orienta todas as etapas semânticas. A operação Apify e os procedimentos seletivos por fonte complementam essa orientação conforme a [estratégia de skills](skills-strategy.md). Antes de recuperar pesquisa, a LLM recebe diagnóstico por consulta com status, registros normalizados, qualificados/contextuais, motivos e erro seguro. Sucesso técnico sem evidência qualificada é distinguido de coleta útil. O diagnóstico inicial fica no checkpoint 9; limites de rodada, orçamento e reuso continuam validados em código.

- Cada etapa recebe e devolve contratos versionados.
- O resultado é persistido antes de publicar o próximo evento.
- Etapas externas possuem timeout, retry com jitter e circuit breaker.
- Repetição usa idempotency key e não duplica custos quando cache válido existe.
- Dados brutos nunca são considerados verdade sem proveniência e validação.
- O workflow pode retomar do último checkpoint seguro.
- Falha, timeout ou conteúdo inutilizável de uma ferramenta externa não bloqueia a análise: o plano termina `PARTIAL`, continua com as outras ferramentas e usa somente evidências válidas. `required` indica prioridade/cobertura planejada, não veto de execução. Falta de evidências limita a recomendação, sem fabricar demanda ou conclusão.
- Timeout com aborto terminal confirmado pode preservar itens independentes já gravados no dataset. A consulta fica `PARTIAL` e não é tratada como sucesso integral; seus itens passam pelos mesmos gates e sua lacuna/custo permanecem na narrativa e no painel. Aborto ainda em andamento não autoriza recuperar o dataset.
- Retomada reutiliza resultados terminais, inclusive falhas e datasets vazios, evitando repetir custos de fonte indisponível. Novas tentativas exigem uma nova consulta autorizada dentro do orçamento cumulativo.
- O painel acompanha o estado do backend até um estado terminal, sem encerrar após cinco minutos. Falhas de conexão geram aviso e nova consulta automática; lacunas de ferramentas aparecem no painel e no dossiê.
- Antes de qualquer Actor pago, o preflight exige LLM real e todas as capabilities obrigatórias.
- URLs usadas por crawler e YouTube são resolvidas de evidências anteriores; a LLM não pode inventá-las.
- O dossiê só é entregue com scoring persistido, claims referenciadas e status `VERIFIED`.
- Antes das features, cada evidência passa pelo pack experimental `market-relevance-v1` no modo ativo. Sinais rejeitados e contexto setorial não entram nas contagens de demanda ou concorrência.
- Lacunas críticas podem gerar uma rodada complementar de consultas novas, com plano persistido e orçamento cumulativo. Zero observado, ausência de coleta e resultado inadequado são estados distintos.
- O dossiê v2 passa por verificações numéricas/referenciais de todos os blocos e por julgamento semântico delimitado; seus critérios e ações não concluem validações humanas.
- Quando o dossiê é rejeitado por esses gates, há no máximo uma revisão da redação com os mesmos fatos e diagnóstico persistido antes da chamada. Ambos os gates são executados novamente; somente uma revisão válida é publicada. Falha persistente preserva bloqueio e diagnóstico, sem repetir pesquisa ou alterar scoring.

A fase responsável por implementar cada etapa está em [Planos de implementação](../implementation/README.md#etapas-do-workflow-por-fase).

## Progresso

O percentual é aproximado e baseado em etapas concluídas, não em tempo estimado. O chatbot recebe status legível, última atualização e eventuais ações exigidas.

## Cancelamento

Cancelamento interrompe novas etapas e solicita aborto de Actors quando suportado. Evidências e custos já incorridos permanecem no audit log.
