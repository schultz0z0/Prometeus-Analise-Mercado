# ADR-0007 — Integração via MCP de Alto Nível e Webhooks Assinados

**Status:** aceito  
**Data:** 2026-10-22

## Contexto

O Prometeus atua como backend de inteligência de mercado educacional para chatbots, agentes autônomos e sistemas legados (LMS/CRM). Chamadas diretas do chatbot para coleta de mercado ou scoring gerariam acoplamento excessivo, risco de vazamento de ferramentas internas de baixo nível e timeout de conexão HTTP em análises profundas que duram vários segundos ou minutos.

## Decisão

1. **Protocolo MCP (Model Context Protocol)**:
   - Adotar o padrão aberto MCP (especificação 2024-11-05 / vigente) para interoperabilidade nativa com Claude Desktop, LibreChat, OpenAI-compatible chatbot agents e assistentes corporativos.
   - O servidor MCP expõe **apenas ferramentas de alto nível orientadas ao usuário final** (`create_course_analysis`, `check_analysis_progress`, `retrieve_course_dossier`, `submit_decision`, `record_course_outcome`), ocultando conectores externos (Apify, Ads, JEV direto).

2. **Comunicação Assíncrona e Notificação via Webhook**:
   - Requisições de análise retornam `202 Accepted` imediatamente com `analysis_id` e status `QUEUED`.
   - O término da análise (`COMPLETED`), falha (`FAILED`) ou exigência de revisão (`BLOCKED` / `REQUIRES_HUMAN_REVIEW`) dispara um Webhook assinado.
   - Cada entrega de Webhook deve incluir:
     - Header `X-Prometeus-Signature: t={timestamp},v1={hmac_sha256}` para autenticidade.
     - Header `X-Prometeus-Timestamp` para mitigação de ataques de repetição (*replay attacks* com janela máx de 300s).
     - Header `X-Prometeus-Event-ID` para idempotência no receptor.
   - Retries com backoff exponencial e encaminhamento para *dead-letter* após 5 tentativas mal-sucedidas.

3. **REST API v1 Padronizada**:
   - Todos os endpoints HTTP seguem a especificação RFC 7807 (Problem Details) para erros.
   - Chave de idempotência via header `Idempotency-Key` é obrigatória na criação e em ações mutantes.

## Consequências

- Chatbots e agentes não bloqueiam a interface do usuário aguardando a finalização da análise.
- O chatbot pode ser notificado de forma proativa via Webhook ou fazer polling leve das etapas de progresso.
- Garante total segurança e proteção contra adulteração de payloads externos.
