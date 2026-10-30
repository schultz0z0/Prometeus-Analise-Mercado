# Catálogo de ferramentas

As tools são capacidades do domínio, não chamadas diretas de fornecedor. Cada uma possui contrato canônico e um ou mais adaptadores.

| ID | Tool | Executor | Observação |
|---|---|---|---|
| TOOL-01 | `generate_keyword_candidates` | LLM | Gera candidatos; não decide relevância |
| TOOL-02 | `rank_keyword_relevance` | JEV ou LLM tradicional | Escolhe/pontua candidatos delimitados |
| TOOL-03 | `fetch_internal_funnel_metrics` | Adaptador institucional | Histórico ENS é a única base sintética autorizada no teste |
| TOOL-04 | `find_historical_comparables` | Código + modo de IA | Recuperação por features; sem cálculo delegado ao modelo |
| TOOL-05 | `fetch_search_trends` | Actor Apify configurado | Evidência real, datada e com provenance |
| TOOL-06 | `fetch_search_volume_and_cpc` | Actor/provedor autorizado | Requer credenciais e limites próprios |
| TOOL-07 | `fetch_paid_competition` | Actor Apify | Meta Ads Library para anúncios comerciais brasileiros |
| TOOL-08 | `fetch_competitor_offers` | Google Search + crawler Apify | URLs vêm da busca persistida, nunca são inventadas |
| TOOL-09 | `fetch_job_market_demand` | LinkedIn + LinkedIn Jobs via Apify | Vagas são proxy, com deduplicação |
| TOOL-10 | `fetch_social_voice` | Instagram, TikTok, YouTube e Reddit via Apify | Amostra e viés obrigatórios |
| TOOL-11 | `classify_social_signals` | JEV ou LLM tradicional | Taxonomia versionada |
| TOOL-12 | `audit_syllabus` | Modo de IA + regras | Não emite conformidade jurídica |
| TOOL-13 | `calculate_viability_score` | Código | Nunca executada por modelo |
| TOOL-14 | `synthesize_executive_dossier` | LLM | Usa somente fatos aprovados |
| TOOL-15 | `verify_dossier_claims` | Código + modo de IA delimitado | Bloqueia claims sem suporte |
| TOOL-16 | `record_human_decision` | Código | Exige autenticação e auditoria |

## Política de execução

- O orquestrador controla tools, orçamento e permissões.
- JEV ou LLM tradicional pode classificar necessidade e relevância, mas nenhum modelo recebe autorização irrestrita para executar ferramentas.
- Tools externas recebem limites de itens, tempo e custo.
- Actor IDs são configuração pinada por deployment após avaliação.
- Saídas brutas são convertidas para contratos internos antes do uso.
- Cada execução externa cria `tool_run` com Actor/build, timestamps, custo, dataset e erro seguro.

## Contratos por fonte v3

`application/tool_capabilities.py` registra, para as onze capacidades configuradas, objetivo, estratégia de consulta, campos esperados, finalidade da evidência, critérios de aceitação/rejeição, diagnóstico, recuperação e limites de amostragem. Os schemas do fornecedor permanecem no registry Apify pinado; orientação semântica não modifica permissões ou schema de entrada.

Vagas alimentam empregabilidade e competências; empresas são contexto; posts/comentários sustentam dores e linguagem; anúncios externos indicam concorrência educacional; busca descobre páginas; crawler confirma ofertas; Trends oferece índice relativo com série válida. Nenhuma dessas contagens comprova matrículas. Um erro de ferramenta gera lacuna individual, preservando o restante do fluxo e os dados úteis.

Trends aceita termos independentes e geo/idioma canônicos, conforme o [schema oficial do Actor](https://apify.com/apify/google-trends-scraper/input-schema). Restrições explícitas de estado/cidade são preservadas. Falha ou série vazia não equivale a interesse zero. A recuperação continua limitada ao orçamento e à rodada autorizada; não há substituição silenciosa por um novo Actor sem validar contrato.
