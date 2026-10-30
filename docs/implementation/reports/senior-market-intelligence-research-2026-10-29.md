# Auditoria da pesquisa e operação Apify — ENS

Data: 29/10/2026. Escopo: leitura de código, documentação e os 144 registros da análise `73501c53-cc58-47f9-8927-d9e299b4f4b5`. Não houve Actor, inferência paga, instalação, modificação de dados ou código de produção. Documentação oficial consultada nesta data descreve o produto atual; mudanças devem ser conferidas contra o schema do build pinado antes de implementação.

## Diagnóstico

Não é correto atribuir o fracasso analítico apenas ao provedor ou ao modelo. Há três camadas distintas: a pesquisa realmente traz ruído; o adaptador muda ou ignora parte da intenção planejada; a leitura/amostragem e o processamento perdem dados úteis. A robustez operacional recente (15 checkpoints, publicação, falha parcial) não valida precisão, cobertura do universo ou profundidade da inteligência.

### Baseline mensurável desta execução

| Fonte | Capturas persistidas | Indicadores | Contexto | Excluídas | Observação de coleta |
|---|---:|---:|---:|---:|---|
| Google Search | 46 | 0 | 24 | 22 | 40 URLs canônicas distintas, preservando `v` de vídeos e retirando tracking |
| Crawler | 14 | 0 | 8 | 6 | 14 URLs distintas; inclui um 404 de profundidade 1 e páginas de outros temas |
| LinkedIn empresas | 10 | 0 | 10 | 0 | Query específica reduzida a `seguros` pelo adaptador |
| LinkedIn vagas | 30 | 16 | 12 | 2 | 30 URLs de vagas distintas; 4/15 qualificadas na primeira busca, 12/15 na segunda |
| Meta Ads | 11 | 0 | 10 | 1 | Apenas 6 `ad_archive_id` distintos; 5 anúncios ENS aparecem nas duas consultas |
| TikTok | 15 | 0 | 0 | 15 | 10 textos `es`, 4 `pt`, 1 `en`; 4 anteriores a 29/10/2025 apesar do plano “últimos 12 meses” |
| YouTube comentários | 15 | 1 | 9 | 5 | Todos os 15 são do mesmo vídeo, embora o plano tenha resolvido dez URLs |
| Google Trends | 3 | 0 | 0 | 3 | Duas capturas de litigância predatória, uma fraude em seguros; recuperação repetiu série já existente |
| Instagram | 0 | 0 | 0 | 0 | Item diagnóstico `no_items`, preservado fora das evidências |
| Total | 144 | 17 | 73 | 54 | Rendimento de qualificação 11,8%; isso NÃO é uma medida de precisão |

Consultas: 19, sendo 15 `SUCCEEDED`, 3 `EMPTY` e 1 `PARTIAL`. Custo Apify persistido: US$ 0,311142; cerca de US$ 0,0183 por item qualificado. Não é custo completo da análise: não inclui uma medida monetária de inferências OAuth e não comprova reconciliação de toda run remota interrompida antes de commit. O plano inicial tinha teto de US$ 5,00. A última recuperação Trends, US$ 0,111064, consumiu 35,7% do custo persistido sem produzir item qualificado. A parada foi `round_limit_reached`, não esgotamento do teto financeiro.

## Achados priorizados

### P1 — Limite por vídeo interpretado como limite total; leitura enviesada do dataset

`src/prometeus/infrastructure/apify/registry.py:201–212` envia todas as URLs do YouTube e `maxComments=call.max_items`. A documentação oficial define `maxComments` por vídeo. `src/prometeus/infrastructure/apify/client.py:269–275` lê somente os primeiros `call.max_items` itens do dataset, sem paginação ou seleção estratificada.

Evidência: dez URLs resolvidas em `parametros_planejados_persistidos.json`, call-12; dataset com total registrado 44, quinze comentários persistidos, todos `videoId=P0Mh4rnZcYU`. Assim, maior cobertura de URLs no plano não se converteu em cobertura de fontes no que a IA analisou. Pode haver custo de itens não consumidos. Não é correto inferir que quarenta e quatro comentários representem quarenta e quatro pessoas ou que quinze constituam amostra independente do setor.

Correção proposta: unidade de orçamento/amostra explícita (`per_query`, `per_video`, `total_retained`), cota por vídeo/canal, seleção prévia de vídeos pertinentes, paginação limitada e estratificada, registro `provider_items / fetched_items / retained_items / source_entities`. Gate: em fixture de três vídeos elegíveis com comentários, nenhum vídeo consome a cota de outro silenciosamente; perda por cap é indicada no resultado.

Fonte oficial: [YouTube Comments Scraper — input](https://apify.com/streamers/youtube-comments-scraper/input-schema). O schema também oferece `oldestCommentDate`; ativá-lo altera a ordenação para mais recentes. Nenhum preço publicado foi usado para estimar custo futuro.

### P1 — Plano declara idioma/período/região que alguns transportes não aplicam

`plan_course_research.py:334–344` adiciona `country`, `location`, `geo`, `language` a todas as chamadas. A maior parte dos adapters não traduz todos esses campos: Jobs (`registry.py:139–154`) não envia `datePosted`; Meta (`91–106`) não envia `minDate/maxDate`; Instagram (`157–185`) não aplica idioma/região/data; TikTok (`188–198`) envia apenas query/seção/cap; YouTube (`201–213`) usa top comments e ignora o período planejado.

Isso não quer dizer que todas as APIs suportem filtros equivalentes, nem que todos os itens fora do período tenham sido usados no score. Significa que o plano e o histórico de parâmetros podem dar falsa impressão de recorte efetivo. No TikTok é observável: query portuguesa, 11/15 textos em outros idiomas e 4/15 anteriores à janela declarada. Foram rejeitados, corretamente evitando contaminar indicadores, mas a busca não foi reformulada.

Correção: cada capability declara filtros `supported / translated / postfiltered / unsupported`; normalizador produz `effective_actor_input` e `effective_scope`, o pipeline valida data/idioma observados e preserva desconhecido. Jamais tratar idioma da query ou IP do proxy como localização do conteúdo. Recorte exigido e não implementável vira limitação explícita, não filtro fictício. Gates: 100% dos parâmetros requeridos têm destino ou motivo de não aplicação; fixtures fora da janela não entram no indicador de janela.

Fontes: [LinkedIn Jobs input](https://apify.com/curious_coder/linkedin-jobs-scraper/input-schema) possui `datePosted` com janelas finitas; [Meta Ads input](https://apify.com/igolaizola/facebook-ad-library-scraper/input-schema) possui `minDate/maxDate`; [TikTok input](https://apify.com/clockworks/tiktok-scraper/input-schema) precisa ser avaliado por versão e não deve receber campos inventados.

### P1 — Escolha de URLs equivale a “primeiros N”, sem avaliação prévia por finalidade

`collect_market_evidence.py:224–317` junta URLs de evidências em ordem de coleta, elimina visitadas e corta em `max_items`. Há controles úteis de segurança, descoberta e dependência; não há reranking temático, tipo de documento, diversidade institucional ou finalidade de evidência antes de gastar páginas.

Na call-3, a cota de sete inclui ENS, Instagram, cursos adjacentes e de outra categoria. Na call-16, a query `FGV PUC curso litigância predatória extensão investimento` gerou páginas de extensão em direitos humanos e de curricularização da extensão, sem relação com o curso. Um catálogo de cursos consumiu página sem que se chegasse a um curso específico relevante. Isso reduz a chance de obter oferta concorrente e preço verificável. Nenhuma dessas observações autoriza promover cursos adjacentes a benchmark de preço sem checagem.

Correção: descoberta separada de aquisição. Um ranker/classificador por URL usa título/snippet para `exact_course / adjacent_course / event / catalog / article / own_institution / irrelevant / file`, com nível, tema e instituição. Crawler recebe uma lista escolhida por pergunta; reservas de cota e extração direcionada de catálogos são ações distintas. Medir precisão@K de seleção de URLs em corpus adjudicado e diversidade de instituições; não impor números universais sem calibração.

### P1 — Crawler não garante uma resposta para cada URL priorizada; PDF não foi rastreado até evidência

`registry.py:82–88` limita `maxCrawlPages`, mas não define `maxCrawlDepth`, nem configura aquisição de arquivos ou reconciliação por URL. Na call-16, sete URLs iniciais incluem o PDF `corporatesolutions.swissre.com/.../treinamento_antifraude.2021-09-01-22-07-28.pdf`; não há registro correspondente entre as catorze evidências crawler. Em seu lugar há `6d9191c1-4fbc-49d6-acc3-80581ed03e3f`, URL malformada `https://securitariosp.org.br/curso/www.securitariosp.org.br`, profundidade 1, texto “Página não encontrada”.

A documentação atual diz que `maxCrawlDepth=0` restringe à lista inicial e que o cap de páginas inclui páginas sem conteúdo. Arquivos requerem configuração própria (`saveContentTypes`/storage). Não está demonstrado pelo snapshot se o PDF foi ignorado por content-type, falha ou limite; o problema comprovado é ausência de diagnóstico por URL planejada. O PDF de 2021 também exige rótulo de recência, não deve ser presumido oferta ativa.

Correção: fila por ativo com status (`fetched`, `unsupported_type`, `blocked`, `not_found`, `budget_skipped`, `extraction_failed`), `maxCrawlDepth=0` na confirmação de páginas e exploração separada para catálogos. Pipeline de PDF baixa/valida MIME, extrai texto/páginas e conserva origem, somente dentro do orçamento e allowlist. Gate: 100% das URLs escolhidas têm outcome explícito; 404 não conta como oferta válida.

Fonte: [Website Content Crawler input](https://apify.com/apify/website-content-crawler/input-schema). A mesma documentação alerta que seu resumo opcional por IA inicia Actors extras pagos; não ativar esse recurso como solução automática.

### P1 — Recuperação age na fonte quando a falha está no aproveitamento

O Trends inicial foi `SUCCEEDED`, dois registros. A qualificação recebeu JSON cortado antes da série e descartou dados; `research_gaps()` em `application/research_sufficiency.py:6–32` só vê ausência de features. O follow-up repete os dois termos, BR e cinco anos, adiciona sinistro de seguro, depois aborta com um registro de série já vista. O dedupe de consultas em `plan_course_research.py:308–313` usa apenas capability + texto da query: mudar a descrição da query evita esse dedupe mesmo que `search_terms/geo/time_range` coincidam.

Correção: diagnóstico causal por camada, fingerprint de input efetivo normalizado, comparação de conteúdo já adquirido e decisão `repair_parser / repair_normalization / rescore / fetch_more / ask_human / stop`. Não permitir nova cobrança para resolver campo já persistido sem uma justificativa de valor incremental. Medir `novel_useful_entities / incremental_cost` e ganho de cobertura útil, não número de Actors bem-sucedidos.

### P2 — LinkedIn empresas perde intencionalmente os termos específicos

`registry.py:120–133` reduz toda query contendo `segur` a `searchQuery='seguros'`. O plano pedia investigação de fraudes em seguros; as dez empresas viraram contexto setorial. O resultado pode servir a mapeamento de ecossistema, mas a alteração não é exposta como recuo de precisão. Preservar a query original quando suportada; broadening deve ser uma ação explícita baseada em diagnóstico, com sua finalidade contextual.

### P2 — Deduplicação de captura não corresponde a entidade

`collect_market_evidence.py:603–619` deduplica content hash; metadados de descoberta e retornos distintos preservam a mesma entidade em consultas diferentes. Dados: Google 46 capturas para quarenta URLs canônicas; Meta onze capturas para seis `ad_archive_id`, com os cinco anúncios ENS repetidos. Não houve duplicação observada de URL das trinta vagas. Esses anúncios não contam no score porque eram próprios; não há evidência de que esse caso tenha inflado a nota. Há, sim, inflação de contagem de capturas, contexto e possível gasto de qualificação.

Correção: separar `Capture` (por run/versão) de `Entity` (ad ID, job ID, course URL + intake/version, video/comment ID), com links para todas as origens e regra de validade temporal. Deduplicação preserva histórico e não apaga contradições. Medir `capture_duplicate_rate` por fonte, e contagens de entidades para inferência.

### P2 — Planejamento ainda é orientado por lista de ferramentas, não valor das perguntas

`plan_course_research.py:190–210` exige todas as fontes obrigatórias e sugere lotes; os “critérios de suficiência” são texto, não um contrato avaliado de qualidade. O orçamento recebido por cada Actor é todo o saldo do plano (`collect_market_evidence.py:717–738`); `allocated_budget` inicia vazio. O planner tem boa decomposição de perguntas, mas lhe faltam allocation por pergunta, stop por redundância e evidência contrária, critérios de pesquisa primária vs proxies e modalidades/categorias separadas. O conjunto atual força Instagram/TikTok mesmo quando uma consulta fracassa ou o público é profissional B2B de nicho.

Correção: responsável de pesquisa seleciona capacidades por pergunta e valor esperado; “obrigatório” passa a requisito de decisão/evidência, não uso universal de canais. Regras de orçamento continuam em código. A qualidade não deve ser otimizada para aumentar a nota ou eliminar o estado insuficiente.

## O que funciona e deve permanecer

- Actor/build pinados e allowlist; `registry.py:314–348`.
- Dependências reais de busca para crawler/YouTube; URLs não são inventadas pela LLM.
- Separação operacional de `FAILED`, `EMPTY`, `PARTIAL` e preservação de `no_items` fora da base factual.
- Recuperação de dataset apenas após aborto terminal confirmado; `client.py:242–249`.
- Adaptação de SERP para resultados individuais com rank/query/run; `collect_market_evidence.py:526–541`.
- Teto de cobrança e reutilização de checkpoints terminais; `collect_market_evidence.py:691–771`.
- Controle numérico/estado em código e histórico sintético identificado.

## Plano de melhoria desta frente

1. **Contrato de transporte auditável.** Criar manifesto versionado por capability com unidades de cap, filtros suportados, schema pinado de input/output, input efetivo sem segredos, recorte aplicado, hashes, por-URL outcomes e custos. Testes offline de mappers antes de paid canary.
2. **Reparar aquisição e amostragem.** YouTube quotas por vídeo, paginação; crawler target-only/PDF e inventário de URLs; filtros temporais/idioma e checagem pós-retorno. Não reconsultar antes de corrigir o processamento existente.
3. **Entidades e qualidade.** Captura separada de entidade; parser por fonte; completude para cada finalidade; não rejeitar conteúdo curricular porque falta preço, nem usar empresa como oferta.
4. **Planejador orientado por decisão.** Matriz pergunta → evidência desejada → fonte primária → sinal proxy → fallback → limite/custo → stop. Busca ampla temática e busca por marcas em trilhas separadas; queries negativas e diversificação sem ocultar adjacência.
5. **Diagnóstico de recuperação.** Analisar erro de camada antes de repetir chamada; detectar mesma assinatura semântica; usar aprendizado da rodada anterior em dados estruturados, sem obedecer instruções da web.
6. **Benchmark e gates.** Corpus humano adjudicado por fonte e curso; avaliar pertinência por finalidade, recuperação de fontes conhecidas, preço/categoria corretamente atribuídos, diversidade, frescor e custo. Só depois canary pago pequeno, com versão atual vs candidata no mesmo briefing e orçamento. Avaliar modo tradicional primeiro e contrato idêntico no híbrido; JEV não corrige mapper/corpus.

Metas candidatas de engenharia: zero truncamento silencioso de campo canônico obrigatório; 100% dos filtros obrigatórios aplicados ou declarados como indisponíveis; 100% das URLs prioritárias com outcome; 100% dos números de entidades rastreáveis. Alvos de precisão/recall dependem de anotação e intervalo de confiança e não devem ser escolhidos como marketing de “100%”.

## Ferramentas e skills: adquirir com propósito

- **Não há necessidade comprovada de trocar REST por MCP para corrigir os defeitos.** O [MCP oficial Apify](https://docs.apify.com/mcp) oferece descoberta, Actors e storages; o hosted expõe inferência de schemas de saída. Útil como ferramenta de manutenção/sandbox, mantendo execução de produção restrita/pinada. Não elimina normalização, calibração ou amostragem.
- **Reaproveitar skills oficiais Apify.** [Apify Agent Skills](https://docs.apify.com/agents/skills) lista `apify-ultimate-scraper` para roteamento/extração e `apify-integration-development` para integração; `apify-actor-development` faz sentido apenas se for construir Actor próprio. São procedimentos de plataforma, não metodologia de mercado ENS. Rever, versionar e adaptar; não instalar automaticamente nem disponibilizar “todos os Actors” no runtime.
- **Indeed como triangulação, não substituição automática.** [Indeed Scraper input](https://apify.com/misceres/indeed-scraper/input-schema) confirma busca/local/descrição e limites por busca. Exige contrato, avaliação de resultados brasileiros e dedupe interportais. Cobertura adicional e custo não foram testados nesta auditoria.
- **Dados de busca absoluta.** [Google Ads Keyword Planning](https://developers.google.com/google-ads/api/docs/keyword-planning/overview) fornece ideias, volume histórico e lances, com cache e quotas mais restritas. Considerar adaptador autorizado específico; Google Analytics não é substituto de volume total do mercado.
- **Aquisição institucional/profissional primária.** Catálogo ENS atual deve orientar taxonomia própria; fontes de mercado/empregabilidade e entrevistas devem ser selecionadas por pergunta. Fontes oficiais e sinais de alunos potenciais são prioritários sobre adicionar outra rede social genérica.

## Limites da auditoria

Uma análise não permite estimar desempenho geral do agente. O corpus é amostra por conveniência e não possui ground truth humano completo. As taxas reportadas são contagens reproduzíveis de pipeline e não precisão/recall do classificador, nem prova de viabilidade. O input efetivo foi inferido dos mappers e parâmetros persistidos; não há log integral autenticado do POST histórico em todos os casos. As fontes oficiais de Actor são atuais; o build pinado deve ser revalidado antes de qualquer alteração.
