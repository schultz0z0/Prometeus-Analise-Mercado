# ADR-0003 — JEV obrigatório e delimitado

**Status:** aceito  
**Data:** 2026-10-09

## Decisão

Uma análise completa exige JEV. Indisponibilidade gera `BLOCKED`; nenhuma LLM substitui silenciosamente o modelo.

JEV é usado somente para perguntas atômicas Choice, Score ou Noul. Cálculos e composição permanecem em código; texto permanece na LLM generativa.

## Motivos

JEV é parte da tese arquitetural do produto. Delimitar sua função segue a documentação oficial e mantém auditabilidade.

## Consequências

O fornecedor é dependência crítica. Modelo, decision packs e limiares devem ser versionados e avaliados. Produção exige plano para indisponibilidade e revisão de condições de retenção de dados.
