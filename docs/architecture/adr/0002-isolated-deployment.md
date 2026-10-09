# ADR-0002 — Deployment isolado por instituição

**Status:** aceito  
**Data:** 2026-10-09

## Decisão

Cada instituição terá stack, banco, segredos e volumes próprios. White-label ocorrerá por configuração.

## Motivos

Reduz risco de vazamento, simplifica customizações de CRM e é operacionalmente viável no estágio atual.

## Consequências

Atualizações precisarão de automação de rollout. Multi-tenancy compartilhado não é requisito inicial.
