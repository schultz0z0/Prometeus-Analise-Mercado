# Estratégia de skills

Skills são pacotes versionados de procedimento e conhecimento usados pela LLM, não código executável e não fonte automática de verdade.

## Skills implementadas

O registry allowlisted ativa dez skills locais versionadas. As cinco skills de entendimento, planejamento, revisão, currículo e oferta permanecem. A skill `conducting-course-analysis` fornece o fluxo completo a todas as etapas semânticas. `operating-apify-research` acrescenta operação geral no planejamento e revisão. `researching-search-trends`, `researching-job-demand` e `extracting-course-offers` fornecem procedimentos dedicados às fontes complexas. As demais fontes usam seus contratos específicos no catálogo, sem duplicação de skill por Actor.

## Regras

- Toda regra regulatória inclui fonte, jurisdição, data e revisão humana.
- Faixas de preço e benchmarks têm validade temporal.
- Skills não podem sobrescrever contratos, score ou políticas de segurança.
- Uma skill nova precisa de casos de teste e proprietário.
- O snapshot da skill usada é registrado na análise.

## Ativação

O código mapeia cada etapa para uma allowlist de skills. O modelo não pode escolher um arquivo arbitrário. Versão e hash entram na auditoria; alterações na rubrica ou skill invalidam o cache de qualificação.

`instructions_for(stage, capabilities)` compõe o system prompt com identificação da etapa e versões. Planejamento recebe detalhes apenas das capabilities configuradas. Qualificação recebe o contrato local da fonte e, quando aplicável, seu procedimento dedicado. URLs, textos web e nomes de skill vindos da coleta não podem carregar arquivos arbitrários. O preflight guarda snapshots das dez skills; o plano registra as usadas e a qualificação registra as pertinentes ao item.

| Etapa semântica | Orientação carregada |
|---|---|
| Entendimento | Fluxo completo + proposta |
| Keywords | Fluxo completo + planejamento, sem procedimentos de redação |
| Planejamento/recuperação | Fluxo + planejamento + Apify + procedimentos das fontes configuradas |
| Qualificação | Fluxo + revisão + Apify + contrato da fonte + procedimento pertinente |
| Aderência | Fluxo + auditoria curricular |
| Comparáveis/preço | Fluxo + revisão/oferta; cálculo continua em código |
| Síntese | Fluxo + revisão + construção de oferta |
| Outros julgamentos delimitados | Fluxo + rubrica do pack; estados/fórmulas em código |

A LLM não conduz uma sessão autônoma entre etapas: cada chamada recebe orientação e dados da etapa, enquanto o workflow passa os resultados e valida o contrato. Receber a skill não comprova obediência perfeita. Testes de captura verificam transporte/seleção e regressões de fluxo verificam efeitos observáveis; a homologação real continua necessária.

As instruções locais de revisão e aderência são inseridas no system prompt da LLM tradicional; a síntese recebe as skills de revisão e oferta. Rubricas e notas dos decision packs são transmitidas aos dois adaptadores de julgamento. Conteúdo coletado continua dado não confiável e não pode se promover a instrução de sistema. O JEV recebe decisões delimitadas; fórmulas, autorização e transições continuam em código.

## Revisão de 2026-10-28

Foram reforçados finalidade por fonte, exemplos positivos/negativos, amostragem, distinção entre contexto e cálculo, tratamento de fontes próprias e recuperação por lacuna. A fragilidade não exigia instalar skills genéricas: parte das rubricas não chegava ao modelo e os contratos por fonte eram insuficientes. Testes verificam o transporte dessas instruções, não apenas sua existência em Markdown.
