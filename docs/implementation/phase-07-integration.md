# Fase 07 — REST, MCP, webhook e chatbot

## Objetivo

Entregar contratos estáveis para o chatbot sem expor ferramentas internas ou manter chamadas longas.

## Arquivos principais previstos

- `src/.../entrypoints/rest/`
- `src/.../entrypoints/mcp/`
- `src/.../infrastructure/webhooks/`
- `openapi.yaml`
- `tests/contract/api/`
- `tests/contract/mcp/`
- `tests/e2e/test_chatbot_flow.py`

## Tarefas

1. Implementar endpoints v1 e Problem Details.
2. Implementar autenticação, escopos e rate limit.
3. Implementar tools MCP de alto nível.
4. Mapear progresso e erros para respostas legíveis.
5. Implementar webhooks HMAC, timestamp e idempotência.
6. Implementar retries e dead-letter.
7. Publicar OpenAPI e schemas MCP versionados.
8. Criar cliente simulador do chatbot.
9. Executar fluxo E2E, cancelamento e missing input.
10. Validar compatibilidade com o chatbot real em staging.

## Verificação

```bash
pytest tests/contract/api tests/contract/mcp -q
pytest tests/e2e/test_chatbot_flow.py -q
```

## Gate

Chatbot cria, acompanha, complementa e recebe uma análise em staging, incluindo falhas e retries.
