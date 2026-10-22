# Fase 07 — REST, MCP, webhook e chatbot

## Objetivo

Entregar contratos estáveis para o chatbot sem expor ferramentas internas ou manter chamadas longas. Implementa as etapas 14 (entrega) e 15 (feedback) do [workflow](../agent/workflow.md) e fecha o fluxo de ponta a ponta.

## Gate de release relacionado

[Gate E — Integration ready](../roadmap/release-gates.md#gate-e--integration-ready).

## Arquivos principais previstos

- `src/prometeus/entrypoints/rest/`
- `src/prometeus/entrypoints/mcp/`
- `src/prometeus/infrastructure/webhooks/`
- `openapi.yaml`
- `tests/contract/api/`
- `tests/contract/mcp/`
- `tests/e2e/test_chatbot_flow.py`

## Tarefas

1. Validar a revisão vigente da especificação MCP e do SDK Python oficial e registrar a escolha em ADR.
2. Implementar endpoints v1 e Problem Details.
3. Implementar autenticação, escopos e rate limit.
4. Implementar tools MCP de alto nível.
5. Mapear progresso e erros para respostas legíveis.
6. Implementar reanálise vinculada (`previous_analysis_id`, RF-010), decisão humana (RF-009), outcomes (RF-013) e export do dossiê (RF-012).
7. Implementar webhooks HMAC, timestamp e idempotência.
8. Implementar retries e dead-letter.
9. Publicar OpenAPI e schemas MCP versionados.
10. Criar cliente simulador do chatbot.
11. Executar fluxo E2E, cancelamento, missing input e `BLOCKED`.
12. Validar compatibilidade com o chatbot real em staging.

## Verificação

```bash
pytest tests/contract/api tests/contract/mcp -q
pytest tests/e2e/test_chatbot_flow.py -q
```

## Gate

Chatbot cria, acompanha, complementa e recebe uma análise em staging, incluindo falhas e retries.
