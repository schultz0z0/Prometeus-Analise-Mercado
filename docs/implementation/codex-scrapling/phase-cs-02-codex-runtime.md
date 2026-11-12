# CS-02 — Runtime Codex CLI

**Status:** planejada. **Dependência:** CS-01. **Responsável:** IA/backend/deployment. [Índice](README.md).

## Objetivo

Adicionar `codex_cli` como provider real da `GenerativeModelPort`, cobrindo texto, keywords, saída estruturada, síntese e revisão. Preservar providers atuais e modo tradicional sem JEV. O spike inicial roda sem ferramentas de coleta; a autonomia entra em CS-04.

## Arquivos previstos

- Criar `src/prometeus/infrastructure/llm/codex_cli.py`, `infrastructure/codex/runner.py`, `infrastructure/codex/session_store.py` e `deploy/docker/Dockerfile.codex`.
- Alterar `infrastructure/factory.py`, `domain/configuration.py`, `application/runtime_preflight.py`, `application/integral_evidence_reader.py` quando necessário para identidade de cache, `entrypoints/rest/app.py`, `web/app.js` e `compose.yaml`.
- Criar `config/codex/runtime.example.toml` sem segredos, `tests/contract/llm/test_codex_cli_transport.py`, `tests/integration/llm/test_codex_cli_sessions.py` e `tests/operational/test_codex_runner_lifecycle.py`.

## Tarefas e provas

1. Testar transporte com subprocesso controlado: stdin, JSONL, final separado, JSON inválido, falha de processo e saída sem conclusão. O teste não depende de cota real.
2. Implementar invocação por argumentos explícitos e schema; validar o resultado novamente no backend. Registrar versão de CLI, modelo efetivo e hashes, sem tratar JSONL como transcript completo do pensamento do modelo.
3. Persistir vínculo de sessão por instituição/análise/etapa; testar retomada específica, cache incompatível e bloqueio de acesso cruzado. Julgamentos atômicos não herdam sessão de pesquisa por padrão.
4. Ensaiar cancelamento, queda de processo, perda de lease e encerramento de operações filhas em Linux e no ambiente local suportado. Resultado tardio não pode persistir depois de perda de posse.
5. Provisionar versão fixa e autenticação própria no container. Provar login/renovação e inferência com a conta elegível no runner antes de iniciar Actor pago. Credenciais OAuth do app atual não são convertidas automaticamente.
6. Acrescentar opção explícita na configuração e diagnóstico de quota/autenticação. Configuração nova não pode fingir conexão só porque o binário existe.

```powershell
rtk proxy .venv/Scripts/python.exe -m pytest tests/contract/llm/test_codex_cli_transport.py tests/integration/llm/test_codex_cli_sessions.py tests/operational/test_codex_runner_lifecycle.py -q -o addopts=
```

## Gate CS-02

Todos os métodos exercitados e uma inferência real concluída no runner isolado; modelo configurado disponível; schemas aceitos e preservação dos gates de domínio. Sessões e artefatos isolados, cancelamento/renovação comprovados. Nenhum benchmark factual ou de custo é declarado a partir do simples funcionamento do CLI.

Entregar `docs/implementation/reports/cs-02-codex-runtime.md` com versões e limitações. Referência oficial: [execução não interativa](https://learn.chatgpt.com/docs/non-interactive-mode); revalidar versão/flags no início da implementação.
