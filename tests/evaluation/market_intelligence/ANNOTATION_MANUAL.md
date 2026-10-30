# Manual de Anotação e Adjudicação — Conjunto de Referência de Mercado ENS

> Versão: **1.0.0**  
> Aplicação: **Formação do Ground Truth Humano para Homologação de Modelos e Classificadores**  
> Documento de Referência: [Plano de Implementação Sênior](../../../docs/plans/2026-10-30-senior-market-intelligence.md) (Fase 0, Tarefa 0.2)

---

## 1. Princípio Fundamental de Independência

1. **A referência é estritamente humana:** Nenhum rótulo ou classificação prévia gerada por modelos de linguagem (LLM tradicional ou JEV) pode ser adotado como gabarito ("ground truth").
2. **Avaliação por finalidade:** Uma mesma evidência pode ter utilidades diferentes dependendo da pergunta analítica (ex.: uma vaga pode ser excelente para mapear competências da ementa, mas inútil para provar intenção de matrícula).
3. **Unidade base:** O conjunto de referência avalia entidades e instâncias empíricas, separando capturas duplicadas de entidades do mundo real.

---

## 2. Perfis dos Revisores e Papéis

Cada exemplo do conjunto de referência deve ser avaliado de forma cega e independente por dois revisores qualificados:

| Perfil | Identificador | Responsabilidade |
|---|---|---|
| **Especialista ENS de Mercado e Portfólio** | `reviewer_ens_market` | Avalia pertinência ao setor segurador/financeiro, comparabilidade de categoria acadêmica (MBA vs. Extensão), atratividade comercial e aderência às diretrizes da ENS. |
| **Revisor de Dados e Metodologia** | `reviewer_data_methodology` | Avalia integridade do dado, validade estatística do recorte geográfico/temporal, presença de campos críticos e prevenção de viés de amostragem. |

---

## 3. Escala de Utilidade por Finalidade

Para cada evidência e finalidade de uso avaliada, os revisores atribuem exatamente uma classificação:

| Rótulo | Definição | Critério de Aceitação |
|---|---|---|
| **`direct`** | Atende diretamente à pergunta analítica com evidência empírica robusta. | Oferta concorrente verificável do mesmo nível/tema com preço e carga, ou vaga de trabalho exata para o egresso. |
| **`adjacent`** | Sinal correlato útil, mas que pertence a categoria educacional, público ou nicho próximo e não idêntico. | Curso de pós-graduação lato sensu quando a pesquisa é MBA executivo; vaga corporativa de nível gerencial mais amplo. |
| **`context`** | Dado informativo sobre o panorama setorial ou da própria instituição promotora. Não constitui concorrente externo nem prova demanda por matrícula. | Notícia setorial sobre sinistralidade; post da própria ENS sobre evento; anúncio institucional. |
| **`irrelevant`** | Conteúdo totalmente fora do escopo educacional ou mercadológico pesquisado. | Falso cognato ("segurança pública", "extensão de cílios"), spam, entretenimento sem conexão profissional. |
| **`insufficient`** | O link ou snippet pertence ao domínio, mas não contém conteúdo suficiente para extração do fato (página 404, snippet quebrado, sem dados substantivos). | Não inventar dados ausentes; classificar como insuficiente para a finalidade. |

---

## 4. Tipos de Controle Obrigatórios

O conjunto de referência deve conter balanceamento deliberado de 5 tipos de instâncias:

1. **`positive` (Controle Positivo):** Exemplos claros e bem documentados onde a evidência é indubitavelmente `direct`.
2. **`negative` (Controle Negativo):** Ruído inequívoco que deve ser descartado pelo sistema (`irrelevant`).
3. **`adjacent` (Controle Adjacente):** Casos limítrofes projetados para testar o discernimento entre concorrência direta e produtos substitutos.
4. **`false_cognate` (Falsos Cognatos):** Palavras-chave homônimas ou polissêmicas comuns em seguros (ex.: "risco", "sinistro", "apólice", "extensão") aplicadas a outros mercados ou contextos.
5. **`legitimate_absence` (Ausência Legítima):** Recortes onde a ausência de sinal é um fato de mercado (ex.: inexistência de vagas com título hiper-específico), testando se o sistema reporta `observed_zero` em vez de inventar ou forçar achados.

---

## 5. Protocolo de Desacordo e Adjudicação

```
     [Anotação Revisor 1]          [Anotação Revisor 2]
    (reviewer_ens_market)      (reviewer_data_methodology)
               \                            /
                \                          /
                 ▼                        ▼
           ┌────────────────────────────────────┐
           │ Houve concordância em utilidade,   │
           │ propósito e escopo?                │
           └─────────────────┬──────────────────┘
                    SIM      │      NÃO
                     ┌───────┴───────┐
                     ▼               ▼
              Status: AGREED   Divergência Material
                                     │
                                     ▼
                            [Reunião Técnica de
                                Adjudicação]
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
            Fonte resolve a dúvida?         Fonte omissa / insolúvel
                     │                               │
                     ▼                               ▼
            Status: ADJUDICATED             Status: UNKNOWN_UNRESOLVED
            (registra justificativa)        (registra pendência factual)
```

1. **Concordância:** Se `utility` e `purpose` coincidirem, o status é registrado como `AGREED`.
2. **Adjudicação:** Havendo divergência de utilidade, um adjudicador sênior emite parecer técnico conciliador detalhado, com status `ADJUDICATED`.
3. **Incerteza Irredutível:** Quando nem o especialista de mercado nem o de metodologia conseguem fundamentar a classificação devido à insuficiência intrínseca da fonte primária, o caso é marcado como `UNKNOWN_UNRESOLVED`, impedindo que incertezas virem certezas artificiais.

