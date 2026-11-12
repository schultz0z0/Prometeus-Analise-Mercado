# CS-01 — Contratos neutros, persistência e roteamento

**Status:** planejada. **Dependência:** CS-00. **Responsável:** domínio/backend. [Índice](README.md).

## Objetivo

Separar tarefa lógica, tentativa, provider, operação remota/local e artefato conforme os [contratos](../../integrations/codex-scrapling-contracts.md). Manter `web_crawler` como capability e preservar todas as outras fontes Apify.

## Arquivos previstos

- Criar `src/prometeus/domain/collection_results.py`, `domain/ports/research_tools.py`, `infrastructure/research/router.py` e `infrastructure/research/apify_adapter.py`.
- Alterar `application/collect_market_evidence.py`, `application/recover_market_collection.py`, `application/runtime_preflight.py`, `workers/tasks.py`, `entrypoints/rest/app.py` e `entrypoints/cli/main.py`.
- Revisar `infrastructure/db/models.py`, `domain/configuration.py` e `application/create_analysis.py` para campos/snapshots de provider e artefatos. Usar a próxima migração disponível no momento da execução, sem presumir o número ou criar duas heads.
- Adicionar `tests/unit/application/test_research_router.py`, `tests/integration/market_sources/test_provider_neutral_recovery.py` e `tests/operational/test_research_provider_migration.py`.

## Tarefas e provas

1. Escrever testes de contrato para execução local sem IDs remotos e execução Apify com identidade real; rejeitar provider/artefato de outra análise e custo inválido.
2. Adicionar o adaptador Apify atrás da nova porta; remover dependência de `isinstance(ApifyClient)` da política de recuperação sem perder `on_run_started`, busca de run incerta ou custo.
3. Criar migração aditiva e leitor compatível: arquivos antigos continuam `dataset_archive` v1; não copiar grandes payloads em migração global nem recalcular hashes.
4. Provar que workflow e ferramenta interna reutilizam a mesma tarefa, que a troca de provider conserva o contador e que retomada não duplica compra.
5. Atualizar preflight e os três pontos de construção de executor (worker, REST e CLI). Configuração e capacidade são congeladas por análise.

```powershell
rtk proxy .venv/Scripts/python.exe -m pytest tests/unit/application/test_research_router.py tests/integration/market_sources/test_provider_neutral_recovery.py tests/operational/test_research_provider_migration.py -q -o addopts=
```

## Gate CS-01

Dois executores simulados exercitam a mesma porta; Apify mantém regressões existentes. Persistência admite identificadores locais sem falsificar dataset/Actor. Backfill é mínimo e reversão preserva leitura dos novos artefatos. Upgrade testado em cópia do PostgreSQL, com backup e uma head de migração. Nenhum provider novo é ativado em análises em curso.

Entregar relatório de compatibilidade em `docs/implementation/reports/cs-01-provider-contracts.md`. Essa fase cria infraestrutura; não demonstra o funcionamento real de Scrapling ou Codex.
