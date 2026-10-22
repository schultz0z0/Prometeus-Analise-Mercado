# ADR-0005 — Separar ciclo de vida da análise e recomendação

**Status:** aceito  
**Data:** 2026-10-22

## Contexto

A versão 5.0.0-draft do PRD listava em um único `status` estados de execução (`QUEUED`, `RUNNING`, `FAILED`...) e resultados de recomendação (`APPROVED`, `HIGH_RISK`...). Isso gera ambiguidades:

- uma análise `APPROVED` parece aprovada por humanos, contrariando o princípio de que o produto não decide sozinho;
- a máquina de estados da Fase 01 teria de conhecer regras de scoring da Fase 05;
- não há como expressar “execução concluída com evidência insuficiente” sem misturar dimensões.

## Decisão

Uma análise possui dois campos independentes.

### `status` — ciclo de vida da execução

| Estado | Terminal | Significado |
|---|---|---|
| `QUEUED` | não | Aceita e aguardando worker |
| `RUNNING` | não | Workflow em execução |
| `WAITING_FOR_INPUT` | não | Aguarda dados complementares do chatbot |
| `BLOCKED` | não | Dependência obrigatória indisponível (ex.: JEV); retomável |
| `COMPLETED` | sim | Dossiê produzido e persistido |
| `FAILED` | sim | Erro não recuperável após retries |
| `CANCELLED` | sim | Cancelada por solicitação ou expiração |

Transições permitidas:

```text
QUEUED            -> RUNNING | CANCELLED
RUNNING           -> WAITING_FOR_INPUT | BLOCKED | COMPLETED | FAILED | CANCELLED
WAITING_FOR_INPUT -> RUNNING | CANCELLED
BLOCKED           -> RUNNING | FAILED | CANCELLED
COMPLETED, FAILED, CANCELLED -> (nenhuma)
```

### `recommendation` — resultado do motor determinístico

Preenchido somente quando `status = COMPLETED`:

- `APPROVED`
- `APPROVED_WITH_ADJUSTMENTS`
- `HIGH_RISK`
- `INSUFFICIENT_EVIDENCE`
- `REQUIRES_HUMAN_REVIEW`

A recomendação é calculada em código pelo quality gate (etapa 11 do workflow) e pelas regras de [scoring](../../scoring/scoring-model.md). LLM e JEV não definem esse campo.

### Decisão humana

A decisão humana é registrada em `HumanDecision` e não altera `status`, `recommendation` nem o score original.

## Invariantes testáveis

1. `recommendation != null` se e somente se `status == COMPLETED`.
2. Estados terminais não aceitam transição.
3. Toda transição gera `AuditEvent` com estado anterior, novo estado, motivo e `correlation_id`.
4. Enquanto o Gate D não for aprovado, o dossiê marca `score.experimental = true`.

## Consequências

- A Fase 01 implementa somente `status`; `recommendation` entra como campo nulo e é preenchido a partir da Fase 05.
- Webhooks passam a refletir o ciclo de vida (`analysis.completed`, `analysis.blocked`...) e carregam `recommendation` quando houver.
- PRD, workflow, scoring, contratos e glossário foram atualizados para esta separação.
