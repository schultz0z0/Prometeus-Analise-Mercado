# Contratos de decisão JEV

## Princípio

Perguntas devem ser atômicas. Quando uma decisão combina fatores independentes, cada fator vira uma pergunta separada e a composição ocorre em código.

## Decision packs planejados

| Pack | Tipo | Finalidade |
|---|---|---|
| `proposal_readiness_v1` | Noul/Choice | Detectar ambiguidade e lacunas semânticas |
| `course_taxonomy_v1` | Choice | Modalidade, área e perfil |
| `keyword_relevance_v1` | Score | Relevância de candidato para a proposta |
| `historical_match_v1` | Score | Força de comparabilidade entre cursos |
| `social_comment_v1` | Choice | Tipo, dor e intenção do comentário |
| `syllabus_coverage_v1` | Noul/Score | Cobertura de competências/demandas específicas |
| `evidence_relevance_v1` | Score | Relevância de evidência para uma claim |
| `contradiction_check_v1` | Noul | Presença de contradição delimitada |

## Metadados obrigatórios

- `decision_pack_id` e versão;
- modelo JEV fixado;
- hash do estado normalizado;
- pergunta, opções ou rubrica;
- resultado e distribuição;
- confidence quando fornecida;
- timestamp, duração e custo;
- decisão de aceitar, revisar ou rejeitar.

## Limiar

O limiar de revisão começa como hipótese em 0,75 e deve ser calibrado por pack. Confidence não é sinônimo de correção. Casos abaixo do limiar ou próximos a fronteiras seguem para revisão.

## Avaliação

Cada pack terá fixtures rotuladas, métricas por classe, matriz de confusão quando aplicável e teste de regressão contra versão anterior.

## Restrições

- Não pedir texto, resumo ou cadeia de raciocínio.
- Não solicitar cálculo aritmético composto.
- Não misturar autorização com julgamento semântico.
- Não enviar PII desnecessária.
- Não usar `jev-latest` em produção sem avaliação; fixar versão aprovada.

Referência oficial: [TypeSafe AI — Introduction](https://docs.typesafe.ai/introduction).
