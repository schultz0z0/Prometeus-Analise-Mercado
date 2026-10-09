# Fluxo de dados

## Sequência principal

```mermaid
sequenceDiagram
    participant C as Chatbot
    participant A as API/MCP
    participant Q as Queue
    participant W as Worker
    participant D as Data Sources
    participant J as JEV
    participant S as Score Engine
    participant L as Generative LLM

    C->>A: create_analysis(proposal, idempotency_key)
    A->>Q: enqueue(analysis_id)
    A-->>C: 202 + analysis_id
    Q->>W: execute workflow
    W->>D: collect internal and external evidence
    W->>J: atomic typed decisions
    J-->>W: choices/scores/probabilities
    W->>S: validated features + versioned profile
    S-->>W: score + coverage + confidence
    W->>L: approved dossier payload
    L-->>W: narrative sections
    W->>W: factual validation
    W-->>C: signed webhook
    C->>A: get_analysis(analysis_id)
    A-->>C: structured dossier
```

## Imutabilidade

Entradas, evidence items, decision results, scoring profile e dossier recebem versões. Correções produzem nova análise ou revisão vinculada; não alteram silenciosamente o passado.

## Idempotência

- Criação: chave fornecida pelo chatbot.
- Coleta: chave por instituição, fonte, consulta e janela.
- Webhook: `event_id` único.
- Reprocessamento: cada step possui chave e estado próprios.

## Dados não confiáveis

HTML, comentários, descrições, documentos e resultados de scraping são isolados como conteúdo. Nunca são concatenados a instruções de sistema sem delimitação, sanitização e política de tamanho.
