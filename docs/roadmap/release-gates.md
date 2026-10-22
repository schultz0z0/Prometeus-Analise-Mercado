# Gates de release

## Gate A — Foundation ready
*Status: Aprovado (Fase 01)*
- Configuração validada.
- Migrations e rollback testados.
- Jobs idempotentes e retomáveis.
- Logs sem segredos.

## Gate B — Data ready
*Status: Aprovado (Fase 02)*
- Contratos ENS aprovados.
- Reconciliação com amostra oficial.
- Dicionário e qualidade documentados.

## Gate C — AI ready
*Status: Aprovado (Fases 03 e 06)*
- Decision packs avaliados.
- Modelo JEV pinado (`jev-v1.2.0`).
- Limiares definidos por dados.
- LLM passa testes de factualidade e injection (TOOL-15 verifier).

## Gate D — Score ready
*Status: Aprovado (Fase 05)*
- Resultado-alvo definido.
- Backtest temporal concluído.
- Baseline superado conforme critério acordado (Brier score e acurácia).
- Shadow mode sem impacto operacional.

## Gate E — Integration ready
*Status: Aprovado (Fase 07)*
- Contratos REST e MCP versionados (OpenAPI v3 e JSON-RPC 2.0).
- Webhook idempotente e assinado com HMAC-SHA256 e tolerância a drift temporal (300s).
- E2E com chatbot em staging 100% verificado.

## Gate F — Production ready
*Status: Aprovado (Fase 08)*
- Threat model revisado:
  - Isolamento estrito de rede interna (`prometeus_internal` com `internal: true`).
  - Containers Docker multi-stage com usuário sem privilégios (`prometeus`, UID 10001).
  - Cabeçalhos de segurança HTTP ativos (HSTS, CSP, X-Frame-Options: DENY, nosniff).
- Backup e restore determinísticos testados e auditados:
  - Manifestos de integridade assinados por SHA-256 e restauração atômica transacional (`tests/operational/test_backup_restore.py`).
  - RPO < 24h e RTO < 30min comprovados.
- Resiliência e mitigação de risco validadas:
  - Kill Switch operacional ativo com resposta graciosa HTTP 503 para novas análises e manutenção de leituras.
  - Shadow Mode ativado sem efeitos colaterais de rede (`SHADOW_DELIVERED`).
  - Simulação de indisponibilidades externas (circuit breaker JEV, quota Apify, CRM ENS e fila dead-letter de webhooks).
- Alertas e runbooks operacionais ensaiados (`docs/operations/runbooks.md`).
- Aprovação conjunta: Produto, Engenharia e Diretoria ENS.
