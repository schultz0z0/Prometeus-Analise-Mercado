# CS-04 — Pesquisa assistida por Codex, MCP e skills

**Status:** planejada. **Dependências:** CS-02 + CS-03. **Responsável:** IA/coleta/backend. [Índice](README.md).

## Objetivo

Permitir que Codex solicite coletas, leia corpus higienizado, interaja com páginas e proponha aprofundamento a partir de lacunas, dentro do checkpoint e das políticas do Prometeus. O workflow continua responsável pelo avanço entre etapas.

## Arquivos previstos

- Criar `src/prometeus/application/research_tool_gateway.py`, `entrypoints/mcp/research_server.py`, `infrastructure/codex/skill_bundle.py` e `config/codex/tools.example.toml`.
- Alterar `application/run_course_analysis.py`, `application/plan_course_research.py`, `application/research_sufficiency.py`, `application/skill_registry.py`, `application/collection_diagnostics.py` e skills existentes afetadas.
- Criar `tests/contract/mcp/test_research_gateway.py`, `tests/integration/market_sources/test_agent_research_recovery.py` e `tests/evaluation/research/test_codex_research_policy.py`.

## Tarefas e provas

1. Definir schemas de ferramentas conforme [contratos](../../integrations/codex-scrapling-contracts.md); servidor deriva escopo da credencial/lease, sem aceitar tenant arbitrário do modelo.
2. Expor coleta, inspeção, leitura e interação através do mesmo gateway usado pelo workflow. Testar reenvio de chamada, duas vias de aquisição e operação incerta: não duplicam compra.
3. Adaptar as dez skills atuais ao runner, com seleção por etapa e hashes. Acrescentar procedimentos de browser e saída do CMS apenas onde pertinentes. Testar instruções realmente recebidas; não instalar skills genéricas como substituto das rubricas.
4. Testar pesquisa que muda de estratégia após falha, dados já disponíveis localmente e ausência observada. Browser/MCP externo não autoriza novos Actors ou reinício de tentativas.
5. Tratar web search como fonte de descoberta/contexto: conteúdo usado como evidência deve entrar no acervo. Citação de busca não comprova leitura de página ou série numérica. Texto web malicioso não pode alterar tools, skills, configuração ou publicação.
6. Validar progresso por evidências novas/qualificadas, cobertura e diagnóstico, não apenas número de chamadas. Documentar encerramento por ausência de consulta inédita, configuração externa ou dados primários ausentes, mantendo lacunas explícitas. Não converter falha em zero.

```powershell
rtk proxy .venv/Scripts/python.exe -m pytest tests/contract/mcp/test_research_gateway.py tests/integration/market_sources/test_agent_research_recovery.py tests/evaluation/research/test_codex_research_policy.py -q -o addopts=
```

## Gate CS-04

Caso integrado real com descoberta Apify, navegação Scrapling, retorno ao acervo e aprofundamento pelo Codex. Recuperação e cancelamento auditáveis, tentativas preservadas, todas as aquisições pertinentes lidas e sem acesso cruzado. Ter ferramentas não comprova que o agente decidiu usá-las corretamente: avaliar trajetória e fatos usados.

Relatório esperado: `docs/implementation/reports/cs-04-assisted-research.md`. O MCP oficial Apify continua opcional; toda execução paga deve entrar na trilha canônica mesmo que ferramentas externas de descoberta estejam habilitadas.
