# CS-00 — Baseline e reconciliação da coleta

**Status:** implementação parcial, gate pendente. **Dependência:** versão vigente. **Responsável:** backend/coleta. [Índice da trilha](README.md).

Em 12/11, retenção/diagnóstico foram corrigidos com regressões RED/GREEN, e runs existentes foram relidas sem compra. A causa exata do mismatch original não foi reproduzida ao vivo; a resposta antiga não foi conservada. Não avançar como se o gate estivesse concluído. Ver [relatório](../reports/cs-00-baseline-and-reconciliation.md).

A correção também foi aplicada ao runtime local com renovação controlada e retomada da mesma análise na etapa 9: checkpoint de coleta, 49 runs e 252 partes validadas preservados. Resta somente a comprovação da causa original para satisfazer integralmente o gate definido; não há autorização implícita para substituir esse critério por sucesso de teste simulado.

## Objetivo e escopo

Reproduzir a divergência de leitura das buscas Google observada em 11/11 e comprovar a recuperação das mesmas runs. A hipótese de consistência eventual é apenas uma hipótese; comparar parâmetros enviados, headers de paginação, contagens, corpo real, estado terminal e horários antes de escolher a correção.

Capturar baseline privado das análises atuais, versões, dossiês e histórico ENS. Não refazer Actors pagos para obter uma reprodução quando o dataset já existe. Não alterar análise ativa, reiniciar sua compra ou apagar mensagens de erro para aparentar sucesso.

## Arquivos e trabalho

- Investigar `src/prometeus/infrastructure/apify/client.py`, `application/recover_market_collection.py` e `application/collect_market_evidence.py`.
- Adicionar regressão em `tests/contract/market_sources/test_apify_dataset_reconciliation.py` e integração em `tests/integration/market_sources/test_existing_run_reconciliation.py` (arquivos planejados).
- Reutilizar os testes existentes de retenção e recuperação e atualizar o contrato em `docs/data/complete-collection-retention.md` somente se o comportamento mudar.

## Sequência TDD

1. Salvar resposta e metadados higienizados suficientes para reprodução; comparar chamada do sistema com GET direto.
2. Criar fixture fiel ao caso real e teste que falhe pela causa observada, sem remover as checagens de integridade.
3. Corrigir a camada responsável; verificar leitura completa, retomada da mesma run e retenção de prefixos.
4. Exercitar página realmente incompleta, contagem mutável, dataset vazio e falha de rede; esses casos devem continuar explícitos.
5. Reconciliar uma run existente no runtime de teste e comparar hashes antes/depois. Publicar relatório sem segredos.

Verificação planejada após criar os testes:

```powershell
rtk proxy .venv/Scripts/python.exe -m pytest tests/contract/market_sources/test_apify_dataset_reconciliation.py tests/integration/market_sources/test_existing_run_reconciliation.py -q -o addopts=
```

## Gate CS-00

- Causa identificada com evidência reproduzível, não inferida apenas pelo status verde do Actor.
- Dataset disponível recuperado com contagens conciliadas; nenhuma compra duplicada.
- Registros parciais e custos anteriores preservados, com pendências reais visíveis.
- Baseline dos cursos/funis sintéticos e dos dossiês anteriores preservado por hash.

Falha neste gate bloqueia declarar a substituição homologada; não impede documentação ou spikes isolados sem produção. Entrega esperada: `docs/implementation/reports/cs-00-baseline-and-reconciliation.md`, somente após execução real dos procedimentos.
