# Melhorias de pesquisa, dossiê executivo e seleção OAuth

**Produto:** Prometeus — Inteligência para Produtos Educacionais  
**Mantenedora:** Agência Prometeus  
**Data:** 2026-10-28  
**Branch:** `codex/market-evidence-dossier`  
**Escopo:** implementação aprovada a partir da [auditoria](market-flow-audit-2026-10-28.md), com correção adicional da seleção de modelos ChatGPT OAuth solicitada durante a execução.

## Resultado entregue

O fluxo conserva dois modos: LLM tradicional para todas as tarefas de IA no modo tradicional; JEV para julgamentos atômicos e LLM tradicional para entendimento, planejamento e redação no modo híbrido. Código continua responsável por coleta, orçamento, fórmulas, score consolidado e estados. Não foi implementada uma projeção financeira de lançamento; o índice continua experimental e não representa retorno esperado ou chance de sucesso.

### Coleta e evidências

- Corrigida a recursão que tratava qualidade de um objeto filho como penalidade. HTML comum é limpo sem falsa penalização de injeção; scripts/iframes têm o conteúdo removido e entidades são decodificadas antes de detectar instruções maliciosas.
- Dependências são validadas antes de executar Actors. Descoberta usa apenas origens do plano/chamada corretos; URLs fornecidas também exigem proveniência. Crawler considera tanto seeds quanto páginas efetivamente visitadas para evitar recrawl.
- SERPs são decompostas em resultados individuais com consulta, ranking e chamada de origem. Identidades repetidas não aumentam contagem ou enviesam a mediana, conservando referências das capturas.
- YouTube exige vídeo e comentário identificáveis. Comentários de uma coleta com vários vídeos precisam de vínculo inequívoco; um canal com texto não conta como comentário. Diretórios, erros e metadados sociais são separados em auditoria limitada.
- Builders normalizam Brasil/Brazil, preservam hashtags de nicho e exigem intenção educacional nas buscas de anúncios. Não houve troca de Actor/build pinado. A documentação atual do Instagram confirma busca por hashtag; não foi aplicada a suposição de que toda busca por hashtag retorna apenas diretório.
- `raw_items_count` representa o lote recebido. Total informado pelo fornecedor, URLs resolvidas e rejeições limitadas ficam nos parâmetros de auditoria da run. Custos são persistidos com o resultado observado.

### Inteligência de pesquisa e indicadores

- O catálogo semântico fornece finalidade, estratégia de query, evidência esperada e limitações somente para fontes configuradas.
- O pack experimental `market-relevance-v1`, pela porta do modo ativo, avalia pertinência por item antes das features. Anúncios B2C, vagas fora do recorte e conteúdos inconclusivos não sustentam as contagens. Contexto setorial pode ser usado como contexto na redação sem pontuar demanda/concorrência.
- Localização de vagas precisa ser observada; ausência de localização não autoriza atribuição ao Brasil.
- Ausência de coleta não gera feature de contagem zero. Uma consulta válida vazia conserva ID de run como proveniência; falha ou rejeição não equivale a zero observado. A política de bloqueio de canais obrigatórios permanece explícita.
- Trends é extraído da série válida, desconsiderando pontos sem dado ou parciais; crescimento compara metades de igual tamanho quando há amostra mínima operacional e base positiva. Não se converte índice relativo em volume absoluto.
- Preços são comparados somente com periodicidade declarada. O formulário de mensalidade envia `monthly`; clientes externos sem unidade ficam `unknown`. Taxa de matrícula e mensalidade não são confundidas: múltiplos preços em texto livre são ambíguos e exigem extração estruturada.
- Lacunas podem gerar uma rodada adicional com plano persistido, consultas novas e orçamento cumulativo. Dependentes de uma busca removida por repetição são descartados; não bloqueiam a análise original nem geram gasto.
- Fórmulas, pesos e tetos de confiança foram preservados. Não foi feita recalibração estatística com o caso auditado.

### Dossiê e interface

- Contrato de apresentação v2 tipa pontos fortes/riscos, critérios, ações, comparação de ofertas e relação ementa/necessidade; os blocos referenciam claims existentes.
- Critérios ficam pendentes e ações propostas. A redatora não concede validação institucional.
- Números e URLs são checados independentemente do tipo de claim e em todo texto visível. A escala `/100` só é autorizada no contexto do índice, não como contagem de vagas. Arredondamentos de apresentação e crescimento negativo são tratados explicitamente.
- Removidos os caminhos que acrescentavam evidências arbitrárias ou reclassificavam uma claim inválida como qualitativa para passar. Queries do plano não são fatos de mercado e `institutional_history` só é referência válida quando há um fato histórico correspondente.
- O workflow executa `evidence-support-v1` sobre claims e blocos para avaliar sustentação semântica, respeitando baixa confiança e grau de certeza. Esse gate é experimental e não garante correção dos modelos.
- Os fatos preservam métricas normalizadas, periodicidade, região, trechos maiores e limitações. Evidências rejeitadas ficam disponíveis na auditoria, sem virar fatos aprovados; fontes de contexto são rotuladas como contexto.
- Dashboard apresenta recomendação, três indicadores, seis pilares, leituras por área, comparação de ofertas, relação curricular, validações e próximos passos. Falta de dados é explicada sem barra de desempenho zero; cobertura é descrita como ponderada.
- Metadados técnicos ficam no inspetor. Vínculos percorrem seção → claim → evidência; o inspetor filtra fontes, fecha com Escape, restaura foco e impede foco em conteúdo fechado. URLs não HTTP(S) não se tornam links.
- Foram corrigidos transbordamento da página no celular e duplicação longa de afirmações nas leituras, agora expansíveis.

### Modelos ChatGPT OAuth

- `GET /v1/auth/chatgpt/models` consulta o catálogo real usando a sessão existente, renovando-a quando necessário; não executa inferência.
- A tela exibe seletor com carregamento, atualização e falha legível. Modelo de API e modelo OAuth permanecem separados.
- Ao salvar, o modelo precisa existir no catálogo da conta. `selected_model` e `GEN_LLM_MODEL` passam a representar a mesma seleção, consumida pelo factory na próxima análise.
- Em falha de gravação, rollback só restaura a seleção da operação quando conta e seleção ainda correspondem; tokens renovados, nova conta e seleção mais recente são preservados.
- Modelos e esforços são filtrados por campos públicos; tokens não são devolvidos. Capacidades específicas de raciocínio só são restringidas quando fornecidas pelo catálogo.

## Verificações

A execução usou TDD: regressões foram observadas falhando antes das correções e depois passaram. Cobriu sanitização recursiva, dependências, metadados sociais, vídeo correto, custo/retomada, fontes habilitadas, cobertura vazia, geografia, preços, série temporal, claims/JSON, persistência, seleção OAuth e renderização JavaScript.

Comandos principais:

```powershell
rtk proxy .venv/Scripts/python.exe -m pytest -o addopts='' -q
rtk proxy .venv/Scripts/python.exe -m mypy src
rtk proxy .venv/Scripts/python.exe -m ruff check src
rtk git diff --check
```

Resultados consolidados: **329 testes passaram e um foi ignorado**; `mypy src` passou em 64 arquivos; lint passou em `src` e nos testes/migração alterados; validação documental passou em 123 arquivos Markdown. O lint global dos testes também encontrou formatação de imports preexistente em três arquivos fora do escopo, preservada sem alteração. O teste opt-in `test_apify_live_schemas.py` é explicitamente ignorado sem autorização/configuração de execução ao vivo. Os testes não executaram Actors pagos nem inferência em contas reais.

Revisão independente: coleta/sanitização aprovada após correções de recrawl e proveniência de comentários. A revisão do núcleo identificou e confirmou correção de cinco defeitos adicionais (duplicação de entidades, preço ambíguo, escala do score, limitações técnicas e dependências órfãs). A mesma revisão confirmou o rollback OAuth sem perda de tokens, com 51 testes focados aprovados, lint e checagem de diff. Não havia achado acionável restante nesse escopo.

## QA no navegador e operação local

Ambiente: `http://localhost:8000`, Chromium via Playwright já fornecido pelo runtime local, viewports de 1440×1000 e 390×844. O plugin Browser não estava disponível; nenhuma dependência de navegador foi instalada no projeto.

| Conferência | Resultado observado |
|---|---|
| Identidade da página | Título Prometeus e curso/área esperados |
| Conteúdo principal | Dossiê e configurações renderizados, sem página vazia ou overlay de erro |
| Console | Sem erros de aplicação nos fluxos conferidos |
| Evidências | Abrem filtradas; Escape fecha e retorna foco ao botão de origem |
| Responsividade | Sem rolagem horizontal da página a 390px após correção do cabeçalho |
| OAuth real, somente leitura | Catálogo retornou 8 modelos da conta; seletor habilitado |
| Interação de modelo | Opção muda na interface; troca OAuth/API alterna os campos corretos |
| Persistência de seleção | Verificada em testes temporários com mocks; não foi salva mudança real de modelo na conta |
| Apresentação v2 com fixture de QA | Duas tabelas renderizadas, afirmações expansíveis, sem transbordamento da página no celular e controles ocultos na impressão |

Screenshots e scripts temporários de QA ficam fora do repositório, no diretório de visualizações da conversa e no diretório temporário local. A captura com dados reais confere compatibilidade do dossiê anterior; as estruturas novas são verificadas com fixtures e round-trip de persistência, sem inventar conteúdo na base de produção.

Foi aplicada a migração `0009_dossier_presentation`, que adiciona `dossiers.presentation` com padrão `{}`. A base manteve oito dossiês. As imagens de API e worker foram reconstruídas e os serviços locais recriados para incluir a migração. Durante a primeira reinicialização, o worker ainda estava sem o arquivo da migração; o arquivo foi incluído, e a reconstrução dos dois serviços elimina essa divergência em recriações posteriores.

## Limites e próxima homologação

- O resultado da análise auditada não foi recalculado nem sobrescrito. Melhorias de coleta e redação são usadas em novas análises.
- Não houve nova coleta paga ou inferência real; comportamento dos builds pinados e qualidade de uma pesquisa real após as correções ainda precisam ser observados.
- Os packs de pertinência e suporte são experimentais, exigindo conjunto rotulado e calibração antes de afirmar precisão conhecida.
- Dados ausentes ou preços sem unidade podem reduzir cobertura; isso é preferível a fabricar precisão.
- Aprovação de lançamento e validação dos critérios permanecem com a instituição.
- A homologação do dossiê por usuários finais e a medição de utilidade da nova pesquisa continuam como atividade de piloto, sem promessa de elevar a nota de viabilidade.
