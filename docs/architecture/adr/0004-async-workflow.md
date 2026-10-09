# ADR-0004 — Processamento assíncrono

**Status:** aceito  
**Data:** 2026-10-09

## Decisão

Criação de análise retorna `analysis_id`. O processamento ocorre em worker e a conclusão é entregue por webhook ou polling.

## Motivos

Coleta externa e Actors podem levar minutos, falhar ou exigir retentativa. Uma conexão MCP/HTTP longa não é confiável.

## Consequências

Precisamos de máquina de estados, idempotência, progresso, cancelamento, filas de erro e reconciliação.
