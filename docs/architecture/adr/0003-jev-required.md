# ADR-0003 — JEV obrigatório e delimitado

**Status:** aceito  
**Data:** 2026-10-09

**Atualização em 2026-10-27:** o [ADR-0008](0008-ai-runtime-and-chatgpt-oauth.md) substitui parcialmente esta decisão: JEV é exigido no modo híbrido e dispensado no modo tradicional. A delimitação de julgamentos atômicos e a responsabilidade do código pelos cálculos continuam válidas. A decisão original abaixo é preservada como histórico.

## Decisão

Uma análise completa exige JEV. Indisponibilidade gera `BLOCKED`; nenhuma LLM substitui silenciosamente o modelo.

JEV é usado somente para perguntas atômicas Choice, Score ou Noul. Cálculos e composição permanecem em código; texto permanece na LLM generativa.

## Motivos

JEV é parte da tese arquitetural do produto. Delimitar sua função segue a documentação oficial e mantém auditabilidade.

## Consequências

O fornecedor é dependência crítica. Modelo, decision packs e limiares devem ser versionados e avaliados. Produção exige plano para indisponibilidade e revisão de condições de retenção de dados.
