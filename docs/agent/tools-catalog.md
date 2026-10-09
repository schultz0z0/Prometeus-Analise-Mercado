# Catálogo de ferramentas

As tools são capacidades do domínio, não chamadas diretas de fornecedor. Cada uma possui contrato canônico e um ou mais adaptadores.

| ID | Tool | Executor | Observação |
|---|---|---|---|
| TOOL-01 | `generate_keyword_candidates` | LLM | Gera candidatos; não decide relevância |
| TOOL-02 | `rank_keyword_relevance` | JEV | Escolhe/pontua candidatos delimitados |
| TOOL-03 | `fetch_internal_funnel_metrics` | Adaptador institucional | ENS é o primeiro adaptador real |
| TOOL-04 | `find_historical_comparables` | Código + JEV | Recuperação por features; JEV avalia relevância |
| TOOL-05 | `fetch_search_trends` | Provedor configurado | Google Trends oficial se houver acesso |
| TOOL-06 | `fetch_search_volume_and_cpc` | Google Ads/provedor | Requer credenciais e limites próprios |
| TOOL-07 | `fetch_paid_competition` | Apify/provedor | Meta comercial Brasil não é garantido pela API oficial |
| TOOL-08 | `fetch_competitor_offers` | Apify/web | Preço e condições com data da coleta |
| TOOL-09 | `fetch_job_market_demand` | Apify/provedor | Vagas são proxy, com deduplicação |
| TOOL-10 | `fetch_social_voice` | YouTube/Apify | Amostra e viés obrigatórios |
| TOOL-11 | `classify_social_signals` | JEV | Taxonomia versionada |
| TOOL-12 | `audit_syllabus` | JEV + regras | Não emite conformidade jurídica |
| TOOL-13 | `calculate_viability_score` | Código | Nunca executada por modelo |
| TOOL-14 | `synthesize_executive_dossier` | LLM | Usa somente fatos aprovados |
| TOOL-15 | `verify_dossier_claims` | Código + JEV delimitado | Bloqueia claims sem suporte |
| TOOL-16 | `record_human_decision` | Código | Exige autenticação e auditoria |

## Política de execução

- O orquestrador controla tools, orçamento e permissões.
- JEV pode classificar a necessidade ou relevância, mas não recebe autorização irrestrita para executar ferramentas.
- Tools externas recebem limites de itens, tempo e custo.
- Actor IDs são configuração pinada por deployment após avaliação.
- Saídas brutas são convertidas para contratos internos antes do uso.
