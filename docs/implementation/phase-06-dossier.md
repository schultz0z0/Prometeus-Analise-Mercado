# Fase 06 — Dossiê e síntese generativa

## Objetivo

Homologação real de 29/10/2026 concluída com recuperação: quinze checkpoints e dossiê verificado na interface, usando OAuth e Actors reais. A auditoria corrigiu simetria factual, contratos de referência, expansão de títulos sanitizados e persistência de falhas. Evidências, limitações e retomadas estão no [relatório da auditoria e E2E](reports/dossier-deep-audit-e2e-2026-10-29.md).

Produzir narrativa útil sem permitir que o modelo altere fatos ou invente sustentação. Implementa as etapas 12 (síntese) e 13 (verificação) do [workflow](../agent/workflow.md).

## Gate de release relacionado

[Gate C — AI ready](../roadmap/release-gates.md#gate-c--ai-ready) (factualidade e injection da LLM).

## Arquivos principais previstos

- `src/prometeus/domain/dossiers.py`
- `src/prometeus/domain/ports/generative_model.py` (criada na Fase 04; estender sem quebrar)
- `src/prometeus/infrastructure/llm/`
- `src/prometeus/application/synthesize_dossier.py`
- `config/prompts/dossier-v1.yaml`
- `tests/evaluation/dossier/`

## Tarefas

1. Definir `DossierFacts` e schema de saída.
2. Criar adapter fake e fixtures de fatos.
3. Criar prompts com separação entre instrução e conteúdo.
4. Estender o provider da Fase 04 para saída estruturada do dossiê, com timeout e teto de custo.
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

## Reabertura de 2026-10-28

Contrato de apresentação v2 com destaques tipados, comparação de ofertas, relação ementa/necessidade, critérios pendentes e ações propostas; todos ligados a claims. Verificação de números independe do rótulo qualitativo/quantitativo e alcança cada bloco visível. O workflow agrega julgamento semântico de suporte pelo motor ativo. A migração aditiva preserva dossiês anteriores e o dashboard mantém auditoria por evidência. Ver [relatório da reabertura](reports/market-dossier-improvements-2026-10-28.md). Redação de novas análises reais e homologação por decisores permanecem pendentes.

## Diagnóstico de rejeições em 2026-10-29

Uma rejeição determinística mantém problemas por claim/bloco no checkpoint de síntese, com motivo e trecho limitado. O painel expõe o diagnóstico sem publicar o dossiê recusado. A análise permanece bloqueada e os fatos não são alterados. Ver [investigação da homologação de extensão](reports/extension-factual-gate-2026-10-29.md).

Na recuperação posterior, uma rejeição determinística/semântica dispara até uma revisão da redação, com diagnóstico salvo antes da chamada e cópias dos fatos aprovados. Todos os gates são repetidos sobre a revisão. Recusa persistente mantém bloqueio; sucesso guarda contagem de gerações e diagnóstico anterior na auditoria. As consultas Apify e o score não são refeitos. O teste automatizado dessa recuperação não substitui nova homologação real.

A segunda homologação revelou problemas de contrato factual: unidade `16h`, total comercial ausente nos fatos citáveis e natureza sintética condicional no histórico. Foram corrigidos extração de unidades, total calculado a partir das parcelas e campos explícitos do histórico. A rubrica semântica diferencia descrição de simulação e comprovação de mercado; mantém a exigência de suporte para cada tipo de alegação. Ver [segunda homologação](reports/extension-second-homologation-2026-10-29.md).

## Auditoria estrutural após a terceira homologação

Contrato citável v3 compartilha a mesma fonte de scoring/definições entre redator, verificador numérico e semântico e inclui-a no hash. A fonte histórica exporta o IPD calculado e sua confiança, respeitando o pilar presente. Prompt 3.0.0 usa JSON Schema estrito no transporte real OpenAI/OAuth; o verificador continua conferindo números, fontes e relações entre claims/seções. Erros de contrato inicial entram na mesma única revisão e não publicam fallback. Diagnóstico semântico identifica alvos e agrega falhas, com limite de quarenta alvos e registro de fontes, escolha e confiança. Ver [plano da auditoria](../plans/2026-10-29-dossier-contract-audit.md).
