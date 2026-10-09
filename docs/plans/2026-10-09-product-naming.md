# Prometeus Naming Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Tornar Prometeus o nome canônico reconhecido pela documentação, configuração e agentes de desenvolvimento, atribuído à Agência Prometeus.

**Architecture:** A identidade fica centralizada em `docs/product/brand-and-naming.md` e referenciada pelos documentos de entrada. O namespace técnico Python permanece estável até a Fase 01, enquanto nomes públicos, configuração e telemetria usam `prometeus`.

**Tech Stack:** Markdown, YAML e variáveis de ambiente.

---

### Task 1: Registrar a identidade canônica

**Files:**
- Create: `docs/product/brand-and-naming.md`
- Modify: `README.md`
- Modify: `docs/product/PRD.md`

**Steps:**

1. Registrar nome, descritor, grafia e regras white-label.
2. Atualizar os documentos de entrada.
3. Validar links com `python scripts/validate_docs.py`.

### Task 2: Informar agentes e configuração

**Files:**
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `.env.example`
- Modify: `config/tenants/ens.example.yaml`

**Steps:**

1. Instruir agentes sobre a identidade do produto.
2. Atualizar nome do serviço e telemetria.
3. Preservar o namespace Python provisório.

### Task 3: Verificar e publicar

**Files:**
- Modify: `docs/README.md`

**Steps:**

1. Executar o validador documental.
2. Inspecionar o diff e procurar grafia legada inadequada.
3. Criar commit e push somente após verificação fresca.
