# Relatórios de conclusão das fases

Cada execução de fase deve produzir um relatório em:

```text
phase-00-completion.md
phase-01-completion.md
...
phase-09-completion.md
```

O relatório é evidência operacional, não material de marketing. Ele registra falhas, correções, comandos, resultados, decisões e pendências.

## Reexecuções

Quando uma fase for reaberta, preserve o conteúdo anterior e adicione uma nova seção de execução ou revalidação. Atualize o resumo no topo sem apagar o histórico que explica como o estado atual foi alcançado.

## Status

- `COMPLETE`: 10/10 com todas as evidências.
- `PARTIAL`: progresso com critérios abertos.
- `BLOCKED`: dependência impede avanço.
- `AWAITING_APPROVAL`: falta homologação humana/externa obrigatória.

Use [_phase-report-template.md](_phase-report-template.md) como base.
