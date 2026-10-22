# ADR-0006 — Namespace Python `prometeus`

**Status:** aceito  
**Data:** 2026-10-22

## Contexto

O namespace `course_market_intelligence` foi definido como provisório até a Fase 01. Antes do primeiro código, o pacote continha apenas diretórios vazios, o que torna a renomeação praticamente gratuita.

## Decisão

O pacote Python passa a ser `prometeus`, localizado em `src/prometeus/`. Serviços, imagens, telemetria, banco local e volumes também usam o slug `prometeus`.

## Consequências

- Imports seguem a forma `from prometeus.domain...`.
- Documentos históricos em `docs/plans/` podem citar o nome anterior; eles não são fonte de estrutura vigente.
- Nomes de exibição white-label continuam configuráveis por instituição e não alteram o namespace.
