# Fase 02 — Adaptador institucional ENS

## Objetivo

Normalizar as APIs de leads, inscritos e matriculados da ENS sem acoplar o domínio aos schemas externos.

## Arquivos principais previstos

- `src/.../domain/ports/institutional_data.py`
- `src/.../infrastructure/institutional/ens/client.py`
- `src/.../infrastructure/institutional/ens/mappers.py`
- `src/.../infrastructure/institutional/mock.py`
- `tests/contract/institutional/ens/`
- `tests/fixtures/institutional/`

## Tarefas

1. Escrever porta e modelos canônicos a partir do dicionário aprovado.
2. Criar fixtures sintéticas de sucesso, vazio, paginação e erro.
3. Implementar mock e testes contratuais compartilhados.
4. Implementar cliente ENS com autenticação, timeout e paginação.
5. Implementar mapeadores e validações de qualidade.
6. Adicionar retries somente para operações seguras.
7. Reconciliar amostra com relatório oficial da ENS.
8. Medir campos nulos, duplicatas e divergências.
9. Documentar campos ignorados e decisões de minimização.

## Verificação

```bash
pytest tests/contract/institutional -q
pytest tests/integration/institutional -q
```

## Gate

Métricas canônicas reconciliadas dentro da tolerância aprovada pela ENS e sem PII desnecessária.
