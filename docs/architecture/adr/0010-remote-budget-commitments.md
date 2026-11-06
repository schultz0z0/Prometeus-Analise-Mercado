# ADR-0010 — Compromissos de orçamento remoto independentes da cobrança observada

**Status:** decidido em 04/11/2026 durante homologação real autorizada. Complementa ADR-0009.

## Evidência

A Apify retornou `SUCCEEDED` com cobrança de US$ 0,00005; consultas posteriores à mesma run retornaram US$ 0,00455. Até contadores `chargedEventCounts == accountedChargedEventCounts` podem anteceder o registro de outro evento. Snapshots estáveis ou uma espera local não comprovam encerramento da cobrança.

## Decisão

- Antes do POST de cada Actor, persistir seu limite máximo autorizado, com proveniência, na run local. O código valida números finitos e positivos e o saldo disponível.
- O teto agregado usa a soma dos limites comprometidos em todas as pesquisas da mesma análise, incluindo reparo. Custo observado não libera automaticamente saldo.
- Usar `parameters.max_total_charge_usd` da chamada, com autorização mínima padrão de US$ 0,50 quando não houver valor operacional maior, sempre validado em código e subordinado ao saldo. Esse valor é política conservadora do deployment, não estimativa de preço do Actor. Mínimo maior exigido pelo provedor pode gerar rejeição sem compra; não aumentar orçamento silenciosamente.
- Não reservar todo o saldo para a primeira consulta por padrão. Se não houver saldo para a autorização, registrar `budget_skipped`, sem inferir ausência de mercado.
- Somente uma rejeição inequívoca anterior à execução ou reconciliação operacional explícita permite liberar compromisso. Incerteza de transporte, término ou cobrança preserva a reserva, marca `IN_DOUBT` e impede novas compras.
- Runs legadas sem registro de autorização exigem reconciliação antes de continuar compras. Não inventar autorizações retroativas nem modificar análises históricas para parecerem aderentes à política nova.
- Exibir custo observado, origem/data da observação e compromisso autorizado como informações distintas. Conferir a fatura final do provedor na reconciliação operacional.

## Consequências

A pesquisa pode consumir o orçamento de autorizações antes de consumir a mesma quantia em cobrança observada. Nesse caso, a cobertura permanece incompleta e o operador decide sobre nova análise/orçamento; o programa não reutiliza saldo provisório. A garantia é sobre o máximo autorizado pela aplicação e depende de o fornecedor respeitar o `maxTotalChargeUsd` aceito. Excesso observado do provedor deve bloquear continuidade e requerer investigação.
