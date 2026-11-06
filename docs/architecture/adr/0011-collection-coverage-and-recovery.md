# ADR-0011 — Coleta por escopo, cobertura verificável e recuperação limitada

**Status:** aprovado pelo responsável do produto em 04/11/2026; implementado e aplicado em 05–06/11/2026. Homologação técnica real concluída com dossiê verificado e dez instituições pesquisadas; limitações comerciais e de SLA permanecem, conforme relatório de homologação.

## Decisão

Novas análises usam `collection-v2`, com monitoramento de custos e sem teto monetário da aplicação. Não reservam US$ 0,50 por chamada nem herdam o teto padrão de US$ 5; omitem `maxTotalChargeUsd`. Escopo, concorrência, tempo, cancelamento, identidade e permissões permanecem controlados em código. Restrições da conta e do Actor continuam possíveis e devem ser expostas como restrições externas.

Essa política substitui as reservas financeiras da ADR-0010 somente para novos snapshots. Planos anteriores mantêm sua política; custos observados são provisórios até reconciliação e nunca devem ser apresentados como fatura final.

Uma tarefa lógica admite tentativa inicial e até três retentativas diagnosticadas e persistidas. Identidade da tarefa e contador sobrevivem a reparo e retomada. Falha permanente pode encerrar antes do limite. POST com resultado incerto exige reconciliação e não autoriza nova compra cega. Leitura repetida da mesma run não é nova execução paga.

Cobertura é comprovada por consultas e evidências vinculadas a cada instituição, incluindo os planos complementares. Planejamento não equivale a execução; buscas por vários domínios não comprovam cobertura individual. O objeto final do dossiê, incluindo apresentação, passa por verificação antes de publicação; benchmark parcial fica explícito.

MCP Apify é apoio opcional de descoberta e documentação. A API permanece executora; Actors descobertos não recebem autorização automática.

## Referências

- [Plano aprovado](../../plans/2026-11-04-collection-coverage-and-apify-recovery.md)
- [ADR-0010](0010-remote-budget-commitments.md)
- [Apify: iniciar Actor](https://docs.apify.com/api/v2/actors-runs-post)
- [Apify: retentativas](https://docs.apify.com/api/client/python/docs/concepts/retries)
- [Apify MCP](https://docs.apify.com/mcp)
