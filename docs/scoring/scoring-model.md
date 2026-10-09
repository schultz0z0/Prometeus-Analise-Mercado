# Modelo de scoring

## Objetivo

Ordenar e explicar o potencial relativo de propostas, sem representar garantia de venda ou retorno financeiro.

## Fórmula baseline v1

Para seis pilares válidos:

```text
V = 0.20H + 0.20C + 0.20B + 0.15E + 0.15A + 0.10P
```

Onde cada sub-score está em `[0, 100]`:

- `H`: histórico interno;
- `C`: concorrência paga;
- `B`: busca e viabilidade de mídia;
- `E`: empregabilidade;
- `A`: aderência da ementa;
- `P`: precificação.

## Dados ausentes

O sistema não redistribui pesos silenciosamente. Calcula:

```text
coverage = soma dos pesos dos pilares válidos
partial_score = soma(weight_i * score_i) / coverage
```

`partial_score` é apenas diagnóstico. Uma recomendação final requer cobertura mínima configurada, inicialmente 0,80, e presença dos pilares obrigatórios definidos no perfil.

## Limiares baseline

| Resultado | Condição inicial |
|---|---|
| `APPROVED` | V >= 75, cobertura >= 0,80 e confiança aprovada |
| `APPROVED_WITH_ADJUSTMENTS` | 60 <= V < 75 e gates aprovados |
| `HIGH_RISK` | V < 60 e evidência suficiente |
| `INSUFFICIENT_EVIDENCE` | cobertura/confiança abaixo do mínimo |
| `REQUIRES_HUMAN_REVIEW` | proximidade do limite ou sinais conflitantes |

Todos os números são hipóteses até backtest.

## Sub-scores

Cada sub-score terá especificação própria com features, transformação, limites, dados mínimos e testes. Nenhuma feature pode aparecer em dois pilares sem justificativa para evitar dupla contagem.

## Versionamento

O `scoring_profile_id` identifica pesos, fórmulas, normalizações, obrigatoriedade de pilares e limiares. Análises antigas nunca são recalculadas sem criar uma nova versão.
