# Fase 06 — Dossiê e síntese generativa

## Objetivo

Produzir narrativa útil sem permitir que o modelo altere fatos ou invente sustentação.

## Arquivos principais previstos

- `src/.../domain/dossiers.py`
- `src/.../domain/ports/generative_model.py`
- `src/.../infrastructure/llm/`
- `src/.../application/synthesize_dossier.py`
- `config/prompts/dossier-v1.yaml`
- `tests/evaluation/dossier/`

## Tarefas

1. Definir `DossierFacts` e schema de saída.
2. Criar adapter fake e fixtures de fatos.
3. Criar prompts com separação entre instrução e conteúdo.
4. Implementar provider escolhido e timeout.
5. Exigir `evidence_ids` por claim relevante.
6. Implementar verificação numérica e de referências.
7. Testar prompt injection, conflito e dados ausentes.
8. Criar seções para diretoria, acadêmico e marketing.
9. Revisar amostras com usuários da ENS.
10. Versionar prompt, modelo e skills no snapshot.

## Verificação

```bash
pytest tests/unit/dossiers -q
pytest tests/evaluation/dossier -q
```

## Gate

Zero claim quantitativa sem origem em fixtures de avaliação e taxa de revisão qualitativa aprovada pelos responsáveis.
