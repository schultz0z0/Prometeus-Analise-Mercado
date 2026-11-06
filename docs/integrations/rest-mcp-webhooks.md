# REST, MCP e webhooks

## Contrato operacional vigente — 04/11/2026

REST `/v1/` é autenticado; criação e reanálise exigem `Idempotency-Key`, com snapshot e outbox. Decisão usa `POST /v1/analyses/{id}/decisions`; exportação estruturada usa `GET /v1/analyses/{id}/dossier`. A documentação HTTP gerada pela API descreve os endpoints efetivos.

MCP stdio é executado com `python -m prometeus.entrypoints.mcp`. As cinco ferramentas são `create_course_analysis`, `check_analysis_progress`, `retrieve_course_dossier`, `submit_decision` e `record_course_outcome`; criação exige `idempotency_key` e compartilha a transação canônica. O processo local confiável é restrito à instituição configurada. Não há listener remoto MCP entregue.

Eventos atualmente conectados à outbox são `analysis.completed`, `analysis.blocked` e `analysis.failed`; recomendação de revisão humana segue no payload da conclusão. Destino HTTPS e segredo são explícitos, despacho é posterior ao commit, retries são exponenciais e entregas terminais não se repetem. Headers: `X-Prometeus-Signature`, `X-Prometeus-Timestamp` e `X-Prometeus-Event-ID`. Corpo contém `event_id`, `event_type`, `analysis_id`, `tenant_id`, `timestamp` e `payload`. Consulte [operação](../operations/audit-remediation.md) e [ADR-0009](../architecture/adr/0009-access-and-workflow-recovery.md).

O catálogo abaixo é o planejamento histórico, e não uma declaração de endpoints/eventos implementados adicionais.

## REST planejado

- `POST /v1/analyses`
- `GET /v1/analyses/{analysis_id}`
- `GET /v1/analyses/{analysis_id}/status`
- `GET /v1/analyses/{analysis_id}/evidence`
- `POST /v1/analyses/{analysis_id}/input`
- `POST /v1/analyses/{analysis_id}/cancel`
- `POST /v1/analyses/{analysis_id}/human-decision`
- `POST /v1/analyses/{analysis_id}/outcomes`
- `GET /v1/analyses/{analysis_id}/export` (RF-012, dossiê estruturado)
- `GET /health/live`
- `GET /health/ready`

Criação exige `Idempotency-Key`. Respostas de erro usam Problem Details e `correlation_id`.

## MCP planejado

Ferramentas de alto nível:

- `create_course_analysis`
- `get_course_analysis_status`
- `get_course_analysis`
- `submit_missing_information`
- `record_course_decision`
- `list_analysis_evidence`

O MCP não expõe diretamente ferramentas internas de scraping ou credenciais. Transporte remoto deverá seguir a especificação vigente, autenticação e allowlist de cliente.

Referência: [Model Context Protocol Specification](https://modelcontextprotocol.io/specification). A versão 2025-06-18 citada anteriormente já foi sucedida por revisões posteriores; a revisão alvo, o transporte e o SDK devem ser validados e registrados em ADR na Fase 07.

## Webhooks

Eventos:

- `analysis.progressed`
- `analysis.waiting_for_input`
- `analysis.blocked`
- `analysis.requires_review`
- `analysis.completed`
- `analysis.failed`
- `analysis.cancelled`

`analysis.requires_review` é emitido junto com `analysis.completed` quando `recommendation = REQUIRES_HUMAN_REVIEW`. Os eventos de conclusão incluem `status` e `recommendation` ([ADR-0005](../architecture/adr/0005-status-vs-recommendation.md)).

Payload contém `event_id`, `event_type`, `occurred_at`, `analysis_id`, `institution_id` e link de consulta. É assinado com HMAC, possui timestamp antirreplay, retries exponenciais e dead-letter queue.

## Autenticação

Fase inicial: API keys rotacionáveis por serviço e escopos mínimos. Evolução possível para OAuth2 client credentials quando o ecossistema do chatbot exigir.
