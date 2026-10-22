# Fase 00 — Validação de premissas e contratos

## Objetivo

Eliminar incógnitas que podem invalidar a arquitetura antes de implementar integrações.

## Dependências e paralelismo

Pode ser executada em paralelo com a [Fase 01](phase-01-foundation.md); o cumprimento deste gate é pré-requisito bloqueante para iniciar as Fases 02, 03 e 04. Ver [Dependências e paralelismo](README.md#dependências-e-paralelismo).

## Entradas

PRD, responsáveis da ENS, documentação das três APIs, acesso de avaliação ao JEV e contas/provedores externos.

## Trabalho

1. Definir resultado-alvo de sucesso de curso e janela de observação.
2. Inventariar dados históricos e produzir dicionário sanitizado.
3. Receber OpenAPI/exemplos das APIs ENS e mapear autenticação, paginação e limites.
4. Selecionar 30–100 cursos candidatos ao backtest, conforme disponibilidade.
5. Criar matriz de fontes externas com acesso, cobertura BR, termos, custo e owner.
6. Executar spikes do JEV para todos os tipos de pergunta planejados.
7. Confirmar região, retenção, versionamento e limites do fornecedor.
8. Definir política LGPD, retenção e responsáveis.
9. Definir contrato MCP esperado pelo chatbot existente.
10. Registrar decisões pendentes em ADRs.

## Artefatos

- `docs/data/ens-data-dictionary.private.example.md` sem dados reais;
- `docs/evaluations/jev-spike-report.md`;
- `docs/evaluations/source-feasibility.md`;
- contrato OpenAPI sanitizado;
- dataset de avaliação versionado em armazenamento seguro.

## Testes/evidências

- chamadas manuais documentadas aos sandboxes;
- reconciliação de pelo menos cinco cursos;
- resultados JEV repetidos e comparados com rótulos humanos;
- prova de que nenhuma credencial entrou no Git.

## Gate

Não iniciar Fase 02–04 sem acesso confirmado ou substituto explicitamente aprovado para cada dependência crítica.
