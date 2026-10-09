# REST, MCP e webhooks

## REST planejado

- `POST /v1/analyses`
- `GET /v1/analyses/{analysis_id}`
- `GET /v1/analyses/{analysis_id}/status`
- `GET /v1/analyses/{analysis_id}/evidence`
- `POST /v1/analyses/{analysis_id}/input`
- `POST /v1/analyses/{analysis_id}/cancel`
- `POST /v1/analyses/{analysis_id}/human-decision`
- `POST /v1/analyses/{analysis_id}/outcomes`
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

Referência: [Model Context Protocol Specification](https://modelcontextprotocol.io/specification/2025-06-18).

## Webhooks

Eventos:

- `analysis.progressed`
- `analysis.waiting_for_input`
- `analysis.requires_review`
- `analysis.completed`
- `analysis.failed`

Payload contém `event_id`, `event_type`, `occurred_at`, `analysis_id`, `institution_id` e link de consulta. É assinado com HMAC, possui timestamp antirreplay, retries exponenciais e dead-letter queue.

## Autenticação

Fase inicial: API keys rotacionáveis por serviço e escopos mínimos. Evolução possível para OAuth2 client credentials quando o ecossistema do chatbot exigir.
