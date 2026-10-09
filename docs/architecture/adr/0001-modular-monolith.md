# ADR-0001 — Monólito modular

**Status:** aceito  
**Data:** 2026-10-09

## Decisão

Construir um único código-base Python com módulos internos e entrypoints separados para API, MCP, CLI e worker.

## Motivos

Equipe de dois desenvolvedores, domínio ainda em calibração e necessidade de transações e evolução rápidas.

## Consequências

Fronteiras precisam ser protegidas por testes arquiteturais. Módulos poderão ser extraídos somente após evidência operacional.
