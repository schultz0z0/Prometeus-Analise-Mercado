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

## Fontes por pilar

**Status: HIPÓTESE** — mapeamento inicial para evitar dupla contagem; revisar na Fase 05.

| Pilar | Chave no perfil | Tools/fontes principais | Observação |
|---|---|---|---|
| H | `internal_history` | TOOL-03, TOOL-04 | Comparar com coortes comparáveis da instituição |
| C | `paid_competition` | TOOL-07 | Anúncios são proxy de investimento, não de vendas |
| B | `search_and_media` | TOOL-05, TOOL-06 | Tendência, volume e CPC |
| E | `employability` | TOOL-09 | Vagas deduplicadas e por região |
| A | `syllabus_fit` | TOOL-10, TOOL-11, TOOL-12 | Dores sociais e competências de vagas versus cobertura da ementa |
| P | `pricing` | TOOL-08 | Preço pretendido versus faixa observada |

Social listening entra no pilar A como demanda qualitativa a ser coberta pela ementa. Ele não conta como volume de demanda em B. Competências de vagas podem alimentar A somente como cobertura, enquanto E usa volume e qualidade das vagas.

## Dados ausentes

O sistema não redistribui pesos silenciosamente. Calcula:

```text
coverage = soma dos pesos dos pilares válidos
partial_score = soma(weight_i * score_i) / coverage
```

`partial_score` é apenas diagnóstico. Uma recomendação final requer cobertura mínima configurada, inicialmente 0,80, e presença dos pilares obrigatórios definidos no perfil.

## Limiares baseline

A tabela define a `recommendation` de uma análise `COMPLETED` ([ADR-0005](../architecture/adr/0005-status-vs-recommendation.md)). A avaliação segue a ordem abaixo; a primeira condição verdadeira vence.

| Ordem | Recomendação | Condição inicial |
|---:|---|---|
| 1 | `INSUFFICIENT_EVIDENCE` | cobertura/confiança abaixo do mínimo ou pilar obrigatório ausente |
| 2 | `REQUIRES_HUMAN_REVIEW` | distância entre V e qualquer limiar menor que `boundary_review_margin` ou sinais conflitantes |
| 3 | `APPROVED` | V >= 75 e gates aprovados |
| 4 | `APPROVED_WITH_ADJUSTMENTS` | 60 <= V < 75 e gates aprovados |
| 5 | `HIGH_RISK` | V < 60 e gates aprovados |

Todos os números, incluindo `boundary_review_margin`, são hipóteses até backtest. Enquanto o Gate D não for aprovado, o dossiê marca `score.experimental = true`.

## Sub-scores

Cada sub-score terá especificação própria com features, transformação, limites, dados mínimos e testes. Nenhuma feature pode aparecer em dois pilares sem justificativa para evitar dupla contagem.

## Versionamento

O `scoring_profile_id` identifica pesos, fórmulas, normalizações, obrigatoriedade de pilares e limiares. Análises antigas nunca são recalculadas sem criar uma nova versão.

## Perfil portfolio-v2 — 2026-10-28

Novas análises usam `config/scoring/portfolio-v2.yaml`, congelado no snapshot da análise. `default-v1` permanece disponível para reproduzir análises anteriores. Os pesos e limiares continuam hipóteses, sem backtest comercial.

O histórico usa a família da formação (Pós/MBA, graduação, extensão etc.), a última janela encerrada e completa e até três cursos próximos por tema e grade. Se a grade não existe, a seleção registra a limitação e não alega comparação curricular. A distribuição de referência inclui todos os cursos elegíveis da mesma família/janela; os três comparáveis não são toda a distribuição.

```text
percentil = 100 × (quantidade abaixo + (quantidade empatada − 1)/2) / (n − 1)
IPD_curso = 0,20 × percentil_leads + 0,30 × percentil_inscrições + 0,50 × percentil_matrículas
H = média dos IPDs dos comparáveis selecionados
```

Menos de três cursos de referência, funil inconsistente ou ausência de ofertas completas e encerradas impede o IPD. Confiança é limitada pelo tamanho da referência e presença de grades. Registros legados sem status de fechamento ou unidade de preço permanecem desconhecidos; a migração não inventa esses metadados.

A referência de preço é a média aritmética de um preço total verificável por curso comparável, interno ou externo, de mesmo tema e categoria. O relatório separa médias e quantidades por origem. Não há ponderação automática de 50% por origem. Preços próprios não contam como concorrentes, taxas não são preço do curso e duração acadêmica não determina parcelas. Múltiplos totais sem atribuição inequívoca ficam ambíguos mesmo se um prazo coincide; a página permanece disponível para os outros usos.

O score principal é o `partial_score` observado, normalizado pela cobertura, identificado como provisório quando os gates falham. A contribuição ponderada permanece na auditoria. Cobertura, confiança e recomendação continuam independentes: nota parcial alta não autoriza lançamento. Blocos exibidos: interno 20%, mercado externo 55%, aderência 15% e preço misto 10%. Um sinal não é somado novamente nos blocos finais.

Confiança e pedido explícito de revisão da decisão curricular chegam ao scoring. Uma decisão que exige revisão não passa a ser um pilar coberto automaticamente.
