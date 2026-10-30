# Fase 03 — Integração JEV e decision packs

## Objetivo

Integrar o JEV como dependência do modo híbrido e provar a qualidade de cada julgamento delimitado. Conforme o [ADR-0008](../architecture/adr/0008-ai-runtime-and-chatgpt-oauth.md), o modo tradicional executa os mesmos contratos semânticos pela LLM tradicional. Implementa prontidão e julgamentos semânticos do [workflow](../agent/workflow.md), além de dar suporte aos decision packs de palavras-chave, histórico e verificação. Fórmulas e recomendação consolidada permanecem em código nos dois modos.

## Gate de release relacionado

[Gate C — AI ready](../roadmap/release-gates.md#gate-c--ai-ready) (JEV e decision packs).

## Dependências

Exige spikes concluídos da [Fase 00](phase-00-validation.md) e infraestrutura base da [Fase 01](phase-01-foundation.md).

## Arquivos principais previstos

- `src/prometeus/domain/ports/decision_model.py`
- `src/prometeus/infrastructure/jev/client.py`
- `src/prometeus/application/decision_service.py`
- `config/decision-packs/*.yaml`
- `tests/evaluation/jev/`
- `scripts/evaluate_jev.py`

## Tarefas

1. Criar porta Choice/Score/Noul sem tipos específicos do SDK.
2. Criar cliente fake para testes unitários.
3. Implementar adapter TypeSafe com timeout, retry e telemetria.
4. Criar packs de prontidão, taxonomia, keywords e comparáveis.
5. Criar packs de comentários, ementa, evidência e contradição.
6. Montar golden dataset sanitizado e rótulos duplos.
7. Avaliar métricas e confidence por pack.
8. Definir limiares de revisão separados.
9. Fixar modelo aprovado para staging/produção.
10. Implementar circuito `BLOCKED` para indisponibilidade.

## Verificação

```bash
pytest tests/unit/decisions -q
pytest tests/contract/jev -q
python scripts/evaluate_jev.py --dataset tests/evaluation/jev --report artifacts/jev-report.json
```

## Gate

Nenhum pack entra no workflow sem relatório, owner, versão, limiar e desempenho mínimo acordado.
