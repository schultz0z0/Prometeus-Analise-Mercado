# CS-06 — Homologação, ativação e reversão

**Status:** planejada. **Dependência:** CS-05. **Responsáveis:** engenharia, produto e avaliador de domínio. [Índice](README.md).

## Objetivo

Comparar o fluxo atual com Codex CLI + Apify + Scrapling, ativar somente após evidência e comprovar reversão sem perda. O objetivo é avaliar viabilidade favorável ou desfavorável com o mesmo rigor.

## Corpus e medidas

Antes de executar, congelar propostas e critérios em `tests/evaluation/research/codex_scrapling_protocol.md` (arquivo planejado). Incluir pelo menos proposta com fontes abundantes, proposta de nicho, caso com sinais desfavoráveis e caso com dados insuficientes/bloqueios; o curso de Direito dos Seguros pode integrar a amostra, sem usar sua vitrine sintética como prova de mercado. Revisão de domínio deve avaliar evidências, não preferência por aprovação.

Comparação tem duas partes: mesmo corpus preservado para interpretação e novas coletas reais na mesma janela para aquisição. Registrar por provider e módulo: produzidos/extraídos/preservados/lidos/admitidos, URLs únicas, instituições consultadas, referências válidas, contradições, campos ausentes, falhas/reconciliações, tarefas duplicadas, custo observado, consumo de runner/browser e duração. Não fixar promessa de economia ou superioridade antes da medição.

## Arquivos e ensaios previstos

- Criar `scripts/audit_codex_scrapling_runtime.py` com modo replay sem rede paga por padrão e opt-in explícito para live.
- Criar `tests/e2e/test_codex_scrapling_course_analysis.py`, `tests/operational/test_codex_scrapling_rollout.py` e o protocolo de avaliação acima.
- Atualizar CI segura, `docs/roadmap/release-gates.md`, runbook e relatório final após evidências reais.

```powershell
rtk proxy .venv/Scripts/python.exe -m pytest tests/e2e/test_codex_scrapling_course_analysis.py tests/operational/test_codex_scrapling_rollout.py -q -o addopts=
rtk proxy .venv/Scripts/python.exe -m ruff check src tests
rtk proxy .venv/Scripts/python.exe -m mypy src
rtk proxy .venv/Scripts/python.exe -m pytest -q -o addopts=
```

## Gate CS-06

- Cinco módulos externos com base verificável nos casos aptos; casos impossíveis permanecem insuficientes e impedem declarar cobertura universal. Histórico ENS sintético é preservado e pode ficar sem base.
- Zero referências inventadas e zero compras duplicadas nos ensaios; critérios de equivalência e qualidade avaliados sem alterar rubrica depois de conhecer o resultado.
- Todos os dados adquiridos pertinentes conciliados e lidos; omissões impedem declaração de integralidade.
- Restart, quota/autenticação indisponível, cancelamento, perda de lease, backup/restore e reversão testados no runtime Linux e ambiente local suportado.
- Ativação explícita por configuração para novas análises. Nenhuma troca automática no meio de uma execução nem fallback oculto de modelo.

Se a nova arquitetura não demonstrar equivalência factual e operacional, manter o padrão anterior e registrar resultados. A aceitação desta trilha não aprova automaticamente Gate D de calibração comercial ou rollout institucional amplo.

Relatório esperado: `docs/implementation/reports/cs-06-live-homologation-and-rollout.md`, com IDs reais, commits, versões, limitações, decisão e instrução de reversão. Segredos, dumps e corpus privado continuam fora do Git.
