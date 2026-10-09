# Modelo de ameaças

| Ameaça | Impacto | Controles planejados |
|---|---|---|
| Vazamento entre instituições | Crítico | Deployment e banco separados |
| Prompt injection em conteúdo web | Alto | Isolamento de conteúdo, allowlist e validação |
| SSRF por URL coletada | Alto | Egress control, validação de URL e bloqueio de redes privadas |
| Exfiltração de segredo em log | Alto | Redação, filtros e testes |
| Tool call não autorizada | Alto | Escopos, allowlist, orçamento e confirmação por política |
| Replay de webhook | Médio | HMAC, timestamp e event ID |
| Poisoning de evidências | Alto | Proveniência, múltiplas fontes e revisão |
| Score manipulado por configuração | Alto | Versionamento, aprovação e auditoria |
| Indisponibilidade de fornecedor | Médio/alto | Circuit breaker, estado parcial/bloqueado e runbook |
| Abuso de custo | Alto | Quotas por análise e teto em Actors/LLM |
| Dependência comprometida | Alto | Lockfiles, scanning e imagens mínimas |

## Fronteiras de confiança

Chatbot, serviço, CRM, provedores de IA, Apify, internet pública e operador da VPS são fronteiras distintas. Autenticação e validação ocorrem em cada transição.

## Revisão

Atualizar antes do piloto, após adicionar uma nova fonte e após qualquer incidente.
