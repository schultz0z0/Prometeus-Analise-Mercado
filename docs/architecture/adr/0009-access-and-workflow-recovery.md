# ADR-0009 — Acesso institucional e recuperação transacional

**Status:** decidido em 04/11/2026, na correção autorizada da auditoria. Complementa ADR-0002, ADR-0004, ADR-0005, ADR-0007 e ADR-0008.

## Decisão

- Acesso ao Prometeus tem identidade própria por instituição/papel; o OAuth ChatGPT autentica o fornecedor de inferência e não o usuário da aplicação. API usa Bearer e navegador usa sessão assinada HttpOnly/SameSite=Strict com verificação de origem em mutações. Chaves de serviço e bootstrap local ficam fora do Git.
- Todos os identificadores institucionais de caminho, query e corpo são validados sem precedência que esconda divergência; recursos são autorizados por seu tenant persistido. Identidade de decisão humana vem da credencial, não do corpo.
- Criação e reanálise compartilham caso de uso, snapshot e idempotência única por instituição. A mesma transação persiste uma outbox. Publicação ocorre após commit e falhas são retomadas pelo reconciliador periódico.
- Consumidores possuem leases exclusivos, heartbeat e confirmação tardia. Perda do lease interrompe o trabalho antigo. Revisão otimista do agregado impede sobrescrita de estado por instâncias antigas.
- Estado remoto desconhecido não autoriza repetir gasto: uma coleta `RUNNING` sem resultado confirmado passa a `IN_DOUBT` e bloqueia novas compras até reconciliação operacional.
- Eventos de conclusão, bloqueio e falha têm outbox persistida e webhook assinado com segredo configurado, retries e dead-letter. MCP é entregue como processo local confiável via stdio, usando o mesmo fluxo canônico; não é um listener HTTP público.
- Apresentação não completa fatos com conteúdo genérico. Projeções financeiras usam somente premissas explícitas e motor Decimal, com rótulo de simulação. Blocos legados inseguros não são exibidos como informação verificada.

## Consequências

A implantação exige migração `0013_workflow_reliability` e scheduler Celery beat único. As portas são ligadas ao loopback por padrão. O operador precisa obter a chave local ou configurar identidades antes de usar a interface; a conexão ChatGPT OAuth existente é preservada. Homologação e calibração permanecem etapas separadas dos checks de código.
