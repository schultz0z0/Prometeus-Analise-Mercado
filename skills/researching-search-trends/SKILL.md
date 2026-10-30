---
name: researching-search-trends
description: Use when planning or qualifying Google Trends evidence for course viability, especially independent terms, missing series and relative-index interpretation.
---

**Version:** 1.0.0
**Owner:** Agência Prometeus

## Solicitação

Use termos curtos independentes em `search_terms`, região explícita e janela permitida pelo builder. Bom: `["gestão de seguros", "MBA seguros"]`; ruim: uma frase que concatena título, preço, modalidade e temas. Não ampliar uma restrição local para Brasil sem autorização. O catálogo contém a finalidade; o registry valida input e build.

## Recebimento e interpretação

Exija termo, período, região e pontos temporais observados. Metadados/consultas relacionadas não são série. Ignore pontos parciais e `hasData=false` para cálculo conforme normalizador; não converta indisponibilidade em zero. Um zero explicitamente medido é distinto de série ausente.

O índice é relativo, não buscas mensais, pessoas ou matrículas. Séries de consultas independentes não têm escala absoluta comparável. Crescimento é calculado em código, não estimado visualmente pelo modelo. Uma série setorial é proxy; explique distância da intenção de cursar o programa.

## Recuperação

Série vazia para título longo: pesquisar categoria/sinônimo, com mesma região e janela válida. Timeout/proxy: preservar falha e usar outras fontes disponíveis; uma notícia não substitui série numérica. Se a recuperação não fornecer pontos válidos, dimensão continua ausente com o motivo observado.
