# Verificação de LLM tradicional e ferramentas Apify

Data: 2026-10-28. Escopo: deployment local Prometeus, sem JEV na homologação.

## Roteamento e configuração

O ambiente local foi fixado explicitamente em `AI_MODE=traditional`, preservando credenciais. API e worker resolvem `LLMDecisionAdapter` com `ChatGPTPlanGenerativeClient`, modelo selecionado `gpt-6.1-terra`, `jev_enabled=false` e preflight pronto. A fábrica respeita esse modo mesmo com uma credencial JEV configurada.

Corrigida a apresentação de `/v1/settings`: a existência de chave JEV indica configuração, não ativação. `ai_mode`, `jev_enabled` e o rótulo `mode` agora refletem o preflight efetivo. Regressão reproduziu o rótulo híbrido incorreto e passou após a correção.

## Conferência real de metadados, sem executar Actors

O teste opt-in `tests/contract/market_sources/test_apify_live_schemas.py` consultou a API oficial Apify com GET e passou. A cobertura foi ampliada para todas as capacidades configuradas, incluindo opcionais. Foram comparados build, status, campos de schema e entradas geradas pelos builders: presença de campos, obrigatoriedade, tipos, enumerações e limites numéricos suportados pelo teste. Isso não é validação integral de toda possível entrada JSON Schema.

| Capacidade | Actor/build verificado |
|---|---|
| Busca Google | `apify/google-search-scraper@0.0.474` |
| Google Trends | `apify/google-trends-scraper@0.0.143` |
| Instagram | `apify/instagram-scraper@0.0.831` |
| Empresas LinkedIn | `harvestapi/linkedin-company-search@0.0.21` |
| Vagas LinkedIn | `curious_coder/linkedin-jobs-scraper@1.7.18` |
| Meta Ads | `igolaizola/facebook-ad-library-scraper@0.0.59` |
| Reddit | `trudax/reddit-scraper-lite@5.8.7` |
| TikTok | `clockworks/tiktok-scraper@0.0.625` |
| Páginas de ofertas | `apify/website-content-crawler@0.3.102` |
| Comentários YouTube | `streamers/youtube-comments-scraper@0.0.257` |

Não foram iniciados Actors, inferências de homologação, análises nem reclassificações externas nesta verificação. Google Analytics não está configurado e não integra o conjunto acima. Indeed permanece alternativa não integrada; não existe troca silenciosa de provedor.

## Cobertura local

Testes verificam modo tradicional com rubricas e skills, geração/validação do plano, builders por fonte, dependências de URLs, coleta/polling/dataset, sanitização, deduplicação, pertinência por finalidade, orçamento, timeout e continuidade com falha parcial ou total de fontes. O teste de workflow usa o adaptador tradicional real com respostas de modelo e ferramentas controladas; não equivale a uma nova execução comercial online.

O modo tradicional utiliza a LLM em entendimento, planejamento, julgamentos semânticos, síntese e verificação semântica. Código continua responsável por executar as ferramentas permitidas, calcular scores/valores e validar estados/permissões.

## Resultado final

- Suíte completa: **395 testes passaram**, com o teste online opt-in ignorado nessa execução. O teste online foi executado separadamente e passou para os dez Actors, sem iniciar nenhuma run.
- Ruff e mypy (69 arquivos) passaram; documentação e checagem de whitespace passaram.
- Build de API/worker concluído e serviços recriados sem tarefas ativas. `/v1/settings` retorna `ai_mode=traditional`, `jev_enabled=false`, provedor `chatgpt_oauth` e modelo `gpt-6.1-terra`. Readiness confirma banco e Redis.
- Inspeção dentro do worker confirma `LLMDecisionAdapter` com `ChatGPTPlanGenerativeClient`; nenhum cliente JEV é escolhido nesse modo.
- Permanecem 12 análises, nove dossiês, 229 evidências externas, 33 cursos e 66 ofertas históricas. Hash do dossiê manual preservado: `77ddb1276c47f8943709780eda420d1c`.

## Limite da conclusão

O roteamento exclusivo para LLM tradicional e os contratos verificados estão comprovados pelos testes e inspeção do deployment. Metadados válidos não garantem disponibilidade futura, quota/proxy, conteúdo útil ou julgamento perfeito da LLM. A homologação real de uma nova análise permanece com o usuário; falhas de ferramentas devem aparecer como lacunas individuais e a análise deve continuar com o material disponível.
