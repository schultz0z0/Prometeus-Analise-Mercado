# Skills de workflow completo e operação Apify

Data: 2026-10-29. Escopo autorizado: orientação da LLM em todo o ciclo de pesquisa/análise, mantendo modo tradicional, scoring e contratos determinísticos.

## Implementação

Cinco skills novas completam as cinco existentes: `conducting-course-analysis`, `operating-apify-research`, `researching-search-trends`, `researching-job-demand` e `extracting-course-offers`. A orientação transversal cobre proposta/categoria, perguntas, histórico/IPD, coleta, tratamento, julgamento, recuperação, aderência, preço, scores/gates e dossiê/verificação. Procedimentos locais explicam exemplos úteis/inadequados e interpretação, sem copiar schemas do fornecedor.

O registry compõe o system prompt por etapa e fonte allowlisted. Planejamento recebe as fontes configuradas; cada julgamento de pertinência recebe seu contrato local e somente o procedimento dedicado aplicável. Contexto coletado continua dado não confiável. Os packs mantêm contratos e rubricas; fórmulas de IPD, referência média de preço, pesos e gates não mudaram.

Foi corrigido um defeito encontrado na inspeção: instruções de revisão/oferta estavam anexadas a keywords e não ao método de síntese. Keywords recebem agora fluxo/planejamento; a síntese recebe fluxo/revisão/oferta no system prompt efetivo. Decisões curriculares e outros julgamentos também recebem orientação transversal.

A recuperação recebe diagnóstico por consulta: falha, vazio, contexto, ausência de qualificação ou amostra útil, com contagens e motivos observados. Isso orienta mudança concreta de consulta/fonte sem repetir falhas ou transformar execução técnica em evidência. O checkpoint 9 guarda o diagnóstico inicial, mantendo uma rodada de recuperação e orçamento cumulativo existentes.

## Verificação e limites

Testes de captura confirmam as instruções enviadas ao modelo, seleção por fonte, isolamento de conteúdo externo e correção de etapa. Testes de diagnóstico distinguem sucesso sem conteúdo pertinente. A suíte de integração cobre continuidade/retomada e publicação com evidência parcial. Os cinco novos arquivos passaram no `quick_validate.py` em UTF-8.

Esses testes comprovam carregamento, transporte e contratos; não comprovam que toda decisão futura da LLM será correta. Não foi iniciada homologação paga, alteração de dossiê concluído ou coleta externa nesta entrega. A homologação de uma nova análise permanece com o usuário.

## Resultado local

- Suíte completa final: **419 passed, 1 skipped** (40,95 s). O teste opt-in de metadados Apify online não foi repetido; não houve alteração de schemas/Actors.
- Revisão independente aprovada após corrigir diagnóstico que confundia itens rejeitados na normalização com uma busca vazia. A recuperação conserva contagem e motivos auditados, sem promover payload bruto a instrução.
- Ruff passou, mypy passou em 70 arquivos e validação documental passou. Os cinco novos arquivos passaram no validador de skills em UTF-8. Checagem de whitespace passou.
- Build de API/worker concluído; serviços recriados após confirmar worker sem tarefas. Ambos carregam dez skills, os três procedimentos dedicados das fontes configuradas e continuam `traditional`, `jev_enabled=false`. API readiness e healthchecks dos serviços passaram.
- Banco preservado: 12 análises, nove dossiês, 229 evidências externas, 33 cursos e 66 ofertas históricas. Hash do dossiê manual permanece `77ddb1276c47f8943709780eda420d1c`. Não houve criação ou retomada manual de análise.
