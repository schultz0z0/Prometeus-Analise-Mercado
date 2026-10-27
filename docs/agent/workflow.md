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

- Cada etapa recebe e devolve contratos versionados.
- O resultado é persistido antes de publicar o próximo evento.
- Etapas externas possuem timeout, retry com jitter e circuit breaker.
- Repetição usa idempotency key e não duplica custos quando cache válido existe.
- Dados brutos nunca são considerados verdade sem proveniência e validação.
- O workflow pode retomar do último checkpoint seguro.
- Antes de qualquer Actor pago, o preflight exige LLM real e todas as capabilities obrigatórias.
- URLs usadas por crawler e YouTube são resolvidas de evidências anteriores; a LLM não pode inventá-las.
- O dossiê só é entregue com scoring persistido, claims referenciadas e status `VERIFIED`.

A fase responsável por implementar cada etapa está em [Planos de implementação](../implementation/README.md#etapas-do-workflow-por-fase).

## Progresso

O percentual é aproximado e baseado em etapas concluídas, não em tempo estimado. O chatbot recebe status legível, última atualização e eventuais ações exigidas.

## Cancelamento

Cancelamento interrompe novas etapas e solicita aborto de Actors quando suportado. Evidências e custos já incorridos permanecem no audit log.
