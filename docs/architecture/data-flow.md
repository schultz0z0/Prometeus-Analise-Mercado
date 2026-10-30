# Fluxo de dados

## Sequência principal

O fluxo de referência é: briefing → dados internos e externos → coleta e preparação → julgamentos semânticos → motor analítico determinístico → dashboard e dossiê → decisão da instituição. O [ADR-0008](adr/0008-ai-runtime-and-chatgpt-oauth.md) define quem executa as tarefas de IA:

- **JEV desativado (`traditional`):** a LLM tradicional faz entendimento, planejamento, julgamentos semânticos delimitados e redação.
- **JEV ativado (`hybrid`):** a LLM tradicional faz entendimento, planejamento e redação; o JEV executa os decision packs atômicos.
- **Seleção automática (`auto`):** a configuração de credencial JEV seleciona o modo; isso não equivale a uma verificação de disponibilidade do fornecedor. Falha durante uma execução híbrida não autoriza troca silenciosa de motor.

Nos dois modos, código valida os contratos e controla coleta, orçamento, deduplicação, fórmulas, scoring consolidado, permissões e estados. A recomendação calculada apoia a decisão humana; a LLM redatora não a altera. Projeções financeiras, quando implementadas, exigem premissas explícitas e cálculo em código; o score de mercado atual não é uma projeção de retorno.

```mermaid
sequenceDiagram
    participant C as Chatbot
    participant A as API/MCP
    participant Q as Queue
    participant W as Worker
    participant D as Data Sources
    participant J as Motor de julgamento ativo
    participant S as Score Engine
    participant L as Generative LLM

    C->>A: create_analysis(proposal, idempotency_key)
    A->>Q: enqueue(analysis_id)
    A-->>C: 202 + analysis_id
    Q->>W: execute workflow
    W->>D: collect internal and external evidence
    Note over W,J: traditional = LLM; hybrid = JEV
    W->>J: atomic typed decisions
    J-->>W: choices/scores/probabilities
    W->>S: validated features + versioned profile
    S-->>W: score + coverage + confidence
    W->>L: approved dossier payload
    L-->>W: narrative sections
    W->>W: factual validation
    W->>W: persist verified dossier and dashboard data
    W-->>C: signed webhook
    C->>A: get_analysis(analysis_id)
    A-->>C: structured dossier
```

O diagrama representa responsabilidades. A implementação atual antecipa prontidão e relevância de palavras-chave à coleta e ainda não aplica todos os packs de pertinência, comentários e contradição previstos. A [auditoria de 2026-10-28](../implementation/reports/market-flow-audit-2026-10-28.md) distingue o fluxo de referência do comportamento observado e propõe um ciclo de coleta adicional limitado por suficiência e orçamento.

## Imutabilidade

Entradas, evidence items, decision results, scoring profile e dossier recebem versões. Correções produzem nova análise ou revisão vinculada; não alteram silenciosamente o passado.

## Idempotência

- Criação: chave fornecida pelo chatbot.
- Coleta: chave por instituição, fonte, consulta e janela.
- Webhook: `event_id` único.
- Reprocessamento: cada step possui chave e estado próprios.

## Dados não confiáveis

HTML, comentários, descrições, documentos e resultados de scraping são isolados como conteúdo. Nunca são concatenados a instruções de sistema sem delimitação, sanitização e política de tamanho.
