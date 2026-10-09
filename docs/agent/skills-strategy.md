# Estratégia de skills

Skills são pacotes versionados de procedimento e conhecimento usados pela LLM, não código executável e não fonte automática de verdade.

## Skills planejadas

- `edtech-curriculum-auditor-brazil`
- `edtech-pricing-and-offer-brazil`
- `edtech-sales-copy-generator`
- `insurance-education-domain`
- `evidence-critical-reviewer`

## Regras

- Toda regra regulatória inclui fonte, jurisdição, data e revisão humana.
- Faixas de preço e benchmarks têm validade temporal.
- Skills não podem sobrescrever contratos, score ou políticas de segurança.
- Uma skill nova precisa de casos de teste e proprietário.
- O snapshot da skill usada é registrado na análise.

## Ativação

O JEV classifica modalidade e domínio; código mapeia essa classificação para uma allowlist de skills. O modelo não pode escolher um arquivo arbitrário.
