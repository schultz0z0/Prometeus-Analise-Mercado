# Phase Execution Prompt Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Criar um prompt reutilizável que implemente, homologue e registre exatamente uma fase do roadmap por execução.

**Architecture:** O usuário altera somente o número da fase. O agente resolve o plano correspondente, executa dentro do escopo, valida contra critérios e gates e grava um relatório permanente em `docs/implementation/reports/`. A fase só recebe `COMPLETE` quando atinge 10/10 com evidências frescas.

**Tech Stack:** Markdown, documentação do repositório, comandos de teste definidos por fase e Git quando já disponível.

---

### Task 1: Criar template do relatório

**Files:**
- Create: `docs/implementation/reports/README.md`
- Create: `docs/implementation/reports/_phase-report-template.md`

**Steps:**

1. Definir campos obrigatórios de escopo, evidência, correções, riscos e gate.
2. Definir política de preservar execuções anteriores.
3. Validar links locais com `python scripts/validate_docs.py`.

### Task 2: Criar prompt de execução

**Files:**
- Create: `docs/prompt-fase-template.md`

**Steps:**

1. Permitir alteração de somente `FASE_ALVO`.
2. Incluir preflight, scope lock, TDD, homologação, fix loop e relatório.
3. Incluir rubrica objetiva de 10 pontos e estados `COMPLETE`, `PARTIAL`, `BLOCKED` e `AWAITING_APPROVAL`.
4. Proibir avanço automático, push, produção e conclusão sem evidência.

### Task 3: Integrar ao índice e verificar

**Files:**
- Modify: `docs/README.md`
- Modify: `docs/implementation/README.md`

**Steps:**

1. Adicionar links para prompt e relatórios.
2. Executar `python scripts/validate_docs.py`.
3. Confirmar que não há links quebrados e que as dez fases continuam presentes.

## Nota de versionamento

O diretório ainda não era um repositório Git durante a criação deste plano. Nenhum commit ou push foi realizado.
