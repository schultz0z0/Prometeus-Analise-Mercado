# CS-05 — Síntese Codex e cadastro no CMS

**Status:** planejada. **Dependência:** CS-04. **Responsável:** IA/dossiê/frontend. [Índice](README.md).

## Objetivo

Fazer Codex redigir e revisar o dossiê canônico, com fatos, referências e resultados dos seis módulos; produzir as nove páginas existentes sem perder conteúdo na hidratação. KPIs e simulações continuam calculados e validados em código.

## Arquivos previstos

- Alterar `infrastructure/llm/codex_cli.py`, `application/synthesize_dossier.py`, `application/dossier_verifier.py`, `application/dossier_cms_builder.py`, `domain/dossiers.py`, `entrypoints/rest/app.py` e `web/app.js` quando o contrato exigir.
- Revisar prompts e skills existentes de síntese/revisão, preservando a identidade Prometeus.
- Criar `tests/contract/dossiers/test_codex_dossier_output.py`, `tests/integration/dossiers/test_codex_cms_roundtrip.py` e `tests/evaluation/dossier/test_codex_factual_controls.py`.

## Tarefas e provas

1. Capturar os schemas/claims aceitos pelo pipeline atual; testar rascunho válido e referência inventada. Codex retorna `DossierOutput`, não scores escolhidos por texto.
2. Exercitar síntese e revisão com fatos desfavoráveis, contraprovas, custos negativos de resultado econômico, dados ausentes e histórico sintético identificado. Confiança não equivale a probabilidade de venda.
3. Validar corpus maior que o contexto de uma chamada. Qualquer consolidação hierárquica mantém referências e manifesto de cobertura; resumo de sessão não comprova análise de todos os itens.
4. Persistir o dossiê, servir pela API, recarregar e comparar semântica dos blocos/claims. Testar campos que hoje seriam reconstruídos por `_hydrate_dossier_presentation`; a fonte canônica deve sobreviver ao reload.
5. Percorrer as nove páginas: visão geral, métricas-chave, concorrência fixa, radar setorial, economia/cenários, SWOT/TOWS, pilares, revisões e fontes/evidências. Conferir listas grandes, rastreabilidade e ausência de fórmulas inventadas.
6. Manter revisões humanas e controle de versão. A ferramenta opcional `submit_dossier_draft` somente entra se escrita incremental for necessária; não criar um segundo canal de publicação ou edição visual do próprio CMS.

```powershell
rtk proxy .venv/Scripts/python.exe -m pytest tests/contract/dossiers/test_codex_dossier_output.py tests/integration/dossiers/test_codex_cms_roundtrip.py tests/evaluation/dossier/test_codex_factual_controls.py -q -o addopts=
```

## Gate CS-05

Rascunho e revisão produzidos pelo CLI real, gates factuais aprovados, nove páginas coerentes após reload e fontes inspecionáveis. Nenhuma aprovação departamental atribuída ao agente. Dossiês antigos e revisões preservados; casos sem evidência continuam explícitos e não ganham score fabricado para completar cards.

Relatório esperado: `docs/implementation/reports/cs-05-codex-cms.md`. Essa fase valida a entrega editorial e técnica; não substitui homologação de mercado e rollout da fase seguinte.
