# Calibração e backtest

## Resultado-alvo

Antes do backtest, a ENS deve escolher uma definição operacional de sucesso, por exemplo:

- matrículas dentro de uma janela;
- receita líquida;
- margem de contribuição;
- atingimento da meta de turma;
- combinação versionada desses resultados.

## Protocolo

1. Selecionar coortes históricas e congelar critérios.
2. Separar treino/calibração e teste temporal.
3. Remover das entradas qualquer informação posterior ao lançamento.
4. Executar coleta reproduzível conforme disponibilidade histórica.
5. Avaliar ranking, calibração, estabilidade e erros por modalidade.
6. Comparar com baseline simples e decisão humana histórica.
7. Documentar ajustes antes de olhar novamente o conjunto de teste.
8. Rodar shadow mode em propostas novas.

## Métricas candidatas

- Spearman para ranking;
- AUC/precision/recall se houver rótulo binário válido;
- lift no quartil superior;
- erro absoluto para resultados contínuos;
- Brier score e reliability diagram para decisões probabilísticas;
- taxa de revisão e erro por decision pack.

## Critério de avanço

O produto não usará linguagem de recomendação definitiva enquanto não superar baseline acordado, demonstrar estabilidade e concluir shadow mode.
