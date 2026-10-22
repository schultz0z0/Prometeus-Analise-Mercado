# Fase 05 — Motor de scoring e calibração

## Objetivo

Implementar scores reproduzíveis, medir poder preditivo e impedir recomendações com evidência insuficiente. Implementa as etapas 10 (scoring) e 11 (quality gate) do [workflow](../agent/workflow.md) e preenche `recommendation` ([ADR-0005](../architecture/adr/0005-status-vs-recommendation.md)).

## Gate de release relacionado

[Gate D — Score ready](../roadmap/release-gates.md#gate-d--score-ready).

## Arquivos principais previstos

- `src/prometeus/domain/scoring/models.py`
- `src/prometeus/domain/scoring/calculator.py`
- `src/prometeus/domain/scoring/quality_gates.py`
- `config/scoring/*.yaml`
- `tests/unit/scoring/`
- `tests/evaluation/scoring/`
- `scripts/run_backtest.py`

## Tarefas

1. Definir feature contracts e unidades por pilar.
2. Escrever testes de pesos, limites, monotonicidade e missing data.
3. Implementar sub-scores sem dependência de framework.
4. Implementar coverage/confidence separadamente.
5. Implementar gates e a ordem de avaliação da `recommendation`, incluindo `boundary_review_margin`.
6. Congelar profile snapshot em cada análise.
7. Rodar baseline simples e backtest temporal.
8. Comparar pesos alternativos sem otimizar no conjunto final.
9. Documentar erros por modalidade e região.
10. Executar shadow mode e revisar overrides.

## Verificação

```bash
pytest tests/unit/scoring -q
python scripts/run_backtest.py --profile default-v1 --report artifacts/backtest-v1.json
```

## Gate

Resultado-alvo, baseline, métricas e limiares aprovados. Sem esse gate, o produto entrega apenas evidências e score experimental.
