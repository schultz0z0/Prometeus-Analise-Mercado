---
name: planning-market-research
description: Use when a structured course understanding must become an auditable, tool-executable market research plan with source coverage and sufficiency criteria.
---

# Planning Market Research

**Version:** 3.1.0

Translate the course understanding into research questions and bounded tool calls. The plan guides collection; it does not contain answers.

## Decision Tracks

Structure research questions into the six canonical decision tracks:

1. **direct_competitors**: Concorrentes diretos na mesma categoria e tema (ofertas ativas, preços totais, parcelamento, carga horária, módulos curriculares).
2. **adjacent_offers**: Ofertas substitutas e adjacentes (cursos livres, extensões, imersões, certificações profissionais).
3. **workforce_needs**: Necessidades e competências profissionais reais demandadas por empregadores (vagas, cargos, ferramentas, qualificações).
4. **educational_search**: Busca educacional vs tema setorial geral (volume e tendência temporal de interesse de formação).
5. **economic_context**: Contexto econômico e financeiro do setor e disposição a investir / pagar.
6. **primary_institutional**: Dados primários institucionais (histórico interno de cursos, matrículas e diretrizes).

## Decision Matrix per Question

Every question in the plan must specify its decision matrix fields:
- `question`: Pergunta de negócio orientada a decisão.
- `track`: Trilha canônica correspondente.
- `hypothesis`: Hipótese testável preliminar.
- `counter_evidence_hypothesis`: Hipótese contrária a refutar para evitar viés confirmatório.
- `expected_evidence`: Evidência empírica exata necessária para validação.
- `capable_sources`: Lista de capabilities ou fontes aptas a responder.
- `scope_filter`: Recorte geográfico e temático.
- `sample_target`: Meta de amostra quantitativa deliberada.
- `budget_allocated_usd`: Teto financeiro atribuído à pergunta.
- `sufficiency_criteria`: Critério objetivo para considerar a pergunta respondida.
- `fallback_or_stop_rule`: Ação de contingência ou encerramento caso a evidência seja insuficiente.

## Brand Seeds Policy

Marcas ou instituições indicadas pelo usuário (em `supplied_materials` ou no briefing) são referências de comparação e sementes de descoberta inicial, e NUNCA devem ser usadas como limite exclusivo da pesquisa. O plano de pesquisa DEVE conter consultas de tema aberto (para descobrir concorrentes não mapeados) além de consultas direcionadas às sementes.

## Coverage

Unless clearly inapplicable and explicitly justified, plan real-time collection for:

- Google web search and competitor pages;
- Meta Ads Library;
- LinkedIn presence and LinkedIn Jobs;
- Instagram, TikTok, YouTube comments, and other relevant public social sources;
- search trend or volume signals;
- offers, prices, formats, differentiators, job roles, skills, pains, objections, and language used by the market.

Add Apify capabilities when they materially answer a research question. Never invent an Actor ID; select only capabilities exposed by the registry.

## Tool-call rules

Each call must include a specific query, rationale, linked research question, required/optional flag, item limit, geography, language, time window when applicable, and sufficiency criterion. Use multiple queries when one phrase cannot cover the concept, audience, alternative terminology, competitors, and employment demand.

Use the versioned capability catalog supplied by the planner. It contains only configured Actors and describes each source's purpose, query strategy, expected evidence and limitations. Never use the same broad noun indiscriminately across all channels. Education ads require education intent; jobs require real role names and scope; social sources require posts/comments rather than directory metadata. Google Trends measures relative interest, not absolute search volume.

The catalog also defines acceptance, rejection, evidence use, diagnostics, bounded recovery and sample policy per source. Plan for those outputs, not just successful Actor status. A job observes roles and skills; it need not mention or sell the MBA. Social context can remain useful for language/positioning without counting as demand. Own institutional pages and ads are context, not external competitors.

Use typed country/language scope and short queries. On Trends, provide independent short terms through the supported `search_terms` list when comparing categories; a comma in free text is not proof that the Actor compares multiple terms. Preserve the same region and time range for comparable series. Series absence, `hasData=false`, zero observed interest and provider failure are different outcomes.

For crawling and YouTube comments, supply `parameters.depends_on` with the exact discovery call IDs; never invent URLs. Competitor discovery and video discovery are distinct research needs. Prices require observed currency and periodicity; do not mix monthly tuition, enrollment fees and total investment.

When the planner supplies gaps and previous queries, propose only additional useful queries for those gaps. The executor permits one complementary round within the original remaining budget; do not repeat previous queries, depend on unavailable calls, or manufacture a minimum statistical sample. Return no calls if no useful new query is available. Required sources and item limits are enforced by code, not by claims in the response.

Prioritize missing data rather than repeating failed sources indiscriminately. If a page is loading, cookie-only, price placeholder or several ambiguous conditions, discover a better official offer page. If a query is exhausted, change role synonym/category or stop with the reason. A failed source does not block the independent sources or justify invented fallback data.

Choose bounded sample sizes for the question and configured budget. Job/advertiser counts obtained with a capped batch are sample counts; request deeper collection only if additional distinct evidence is necessary and the remaining budget permits it. Do not compare a limit of five returned items with a market-volume threshold as if the source were exhausted. Record truncation and query diversity.

Required marks planned priority/coverage; runtime failures become explicit gaps while the workflow continues with valid evidence. Budget pressure may reduce optional breadth, never replace evidence with pretrained knowledge.

## Current schema references

The code registry owns pinned schemas and validates every call. These official references were checked on 2026-10-28 and inform strategy, not permission to forward arbitrary Actor parameters:

- [Google Trends input](https://apify.com/apify/google-trends-scraper/input-schema): `searchTerms` is a list; `isMultiple` defaults false for comma-separated input.
- [LinkedIn Jobs input](https://apify.com/curious_coder/linkedin-jobs-scraper/input-schema): search filters discover jobs; detail completeness must be checked in the returned data.
- [Website Content Crawler input](https://apify.com/apify/website-content-crawler/input-schema): inspect original pages discovered by prior searches.
- [Instagram input](https://apify.com/apify/instagram-scraper/input-schema): posts, profiles, hashtags and comments are distinct outputs; a hashtag directory is not a post sample.

## Stop conditions

Stop planning when each important question has at least one independent source and critical claims have a corroboration path. Duplicate queries without a new evidence need should be removed.
