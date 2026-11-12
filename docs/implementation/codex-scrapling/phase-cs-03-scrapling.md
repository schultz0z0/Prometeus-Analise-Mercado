# CS-03 — Aquisição HTTP/browser com Scrapling

**Status:** planejada. **Dependência:** CS-01. **Responsável:** coleta/deployment. [Índice](README.md).

## Objetivo

Implementar o provider Scrapling para `web_crawler`. Começar por aquisição determinística de URLs descobertas; ações conduzidas por Codex entram em CS-04. Reutilizar os contratos `OfferObservation` e `PageAcquisition`, com origem real `scrapling` e sem prefixo Apify enganoso.

## Arquivos previstos

- Criar `src/prometeus/infrastructure/scrapling/client.py`, `infrastructure/scrapling/normalizer.py`, `infrastructure/scrapling/session_store.py`, `infrastructure/evidence/artifact_store.py` e `deploy/docker/Dockerfile.scrapling`.
- Alterar `application/read_collected_datasets.py`, `application/evidence_reading_audit.py`, `application/evidence_reading_context.py`, `application/qualify_market_evidence.py`, o roteador de CS-01, `compose.yaml` e `pyproject.toml`/`uv.lock`.
- Criar `tests/contract/market_sources/test_scrapling_acquisition.py`, `tests/integration/market_sources/test_scrapling_retention.py` e `tests/operational/test_scrapling_session_recovery.py`.

## Tarefas e provas

1. Fixar biblioteca e browser compatíveis após verificar a documentação vigente. Testar uma página local estática e uma dinâmica controladas antes de concorrentes reais.
2. Demonstrar HTTP, fallback justificado para browser, redirecionamentos, timeout, bloqueio, 404 e encerramento de sessão. Uma página de erro não se torna oferta nem demanda zero.
3. Arquivar conteúdo original disponível e versão higienizada antes de projetar contexto. Documento PDF e resposta de rede pertinente usam download/artefato próprios; screenshot ou Markdown não equivalem à captura integral.
4. Testar várias URLs, páginas, documentos e registros longos; conferir hashes, total adquirido, omissões e leitura completa em partes. Uma limitação de captura impede marcação de integralidade do escopo afetado.
5. Persistir o necessário para reabrir uma sessão compatível após queda; não declarar persistência de tabs em memória. Isolar cookies, arquivos e credenciais por análise/instituição.
6. Testar URLs privadas, redirects e subrequisições proibidos, limites de recursos e limpeza de browser. Medir RAM/CPU/proxy sem inventar custo de Apify.

```powershell
rtk proxy .venv/Scripts/python.exe -m pytest tests/contract/market_sources/test_scrapling_acquisition.py tests/integration/market_sources/test_scrapling_retention.py tests/operational/test_scrapling_session_recovery.py -q -o addopts=
```

## Gate CS-03

Conteúdo utilizável de páginas reais dos concorrentes configurados, com corpus e critérios registrados antes do ensaio. Todos os desfechos preservados, contagens conciliadas e leitura dos artefatos higienizados comprovada. Nenhum segredo em saída pública e nenhum ID remoto fictício. Comparação com o crawler atual usa mesmas URLs e janela; não pressupõe superioridade.

Relatório esperado: `docs/implementation/reports/cs-03-scrapling-acquisition.md`. [MCP oficial e limites](https://scrapling.readthedocs.io/en/latest/ai/mcp-server.html).
