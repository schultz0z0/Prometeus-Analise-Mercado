# Runbooks

## JEV indisponível

Abrir circuit breaker, parar conclusões novas, marcar jobs `BLOCKED`, preservar coleta já feita e alertar operador. Retomar após health check e sem trocar de modelo silenciosamente.

## Apify indisponível ou custo excedido

Abortar novas runs, consultar status das existentes, marcar fontes afetadas e concluir somente se política permitir análise parcial.

## CRM da instituição indisponível

Aplicar retries limitados. Não substituir histórico por zero. Marcar pilar como indisponível e notificar responsável técnico.

## LLM indisponível

Preservar score e facts. Manter síntese pendente e repetir de forma idempotente.

## Webhook falhando

Repetir com backoff, validar DNS/TLS/assinatura e enviar para dead-letter após limite. O chatbot ainda pode consultar por polling.

## Suspeita de vazamento

Revogar credenciais, bloquear egress quando necessário, preservar logs, acionar responsável de segurança/DPO e seguir plano institucional de incidente.

## Banco ou Redis

Parar aceite de jobs se readiness falhar. Nunca continuar uma execução sem persistência transacional ou lock confiável.
