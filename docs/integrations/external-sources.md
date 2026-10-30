# Fontes externas

**Validado em:** 2026-10-27. Revalidar em cada upgrade relevante.

## JEV / TypeSafe AI

Fonte oficial confirma Choice, Score e Noul, decisões paralelas, probabilidades e confidence. Perguntas complexas devem ser decompostas e combinadas em código.

- [Introdução oficial](https://docs.typesafe.ai/introduction)
- [Anúncio oficial](https://typesafe.ai/blog/introducing-system-one-models-and-jev)

Status: opcional no modo híbrido. O modo tradicional usa a LLM para os mesmos julgamentos delimitados, preservando fórmulas e estados em código.

## OpenAI / plano ChatGPT

O fluxo oficial para aplicações locais/open source permite registro dinâmico sem client secret, uso do escopo `chatgpt.tokens.use.direct`, descoberta de modelos da conta e inferência na Responses API com a cota do plano ChatGPT elegível.

- [Registro e login](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
- [Modelos e inferência](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [Token e renovação](https://developers.openai.com/siwc/token-sharing-open-source/token-reference)
- [Erros e recuperação](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery)

Decisão: usar somente `https://api.openai.com/v1/models` e `POST /v1/responses` nesse modo. Tokens antigos sem escopo direto e endpoints internos do ChatGPT são rejeitados.

## Apify

O MCP e a API oficial permitem descobrir e executar Actors, acompanhar runs e ler datasets. Em produção, Actor, versão, schema, custo máximo e limites devem ser pinados.

- [Apify MCP](https://docs.apify.com/mcp)
- [Execução de Actors](https://docs.apify.com/actors/running)

Status: backbone preferencial de scraping. Actors da Store não são automaticamente confiáveis; avaliar proprietário, qualidade, permissões, preço, manutenção, termos e resultado.

Falhas de execução, timeout, quota de proxy e dados rejeitados de um Actor são lacunas da coleta, sem interromper as outras fontes. Runs, erros e custos permanecem auditáveis; a recomendação considera a cobertura efetiva. A restrição de proxy externo da conta não equivale a bloqueio de uso interno pelos Actors. O token da API não substitui a senha do proxy, e o cliente Prometeus não configura conexão direta ao proxy.

Desde 29/10/2026, após timeout e aborto **terminal `ABORTED` confirmado**, o conector pode ler o dataset já persistido. Os itens passam pelos mesmos controles de build, schema, higienização, qualificação e features. A consulta local fica `PARTIAL`, conserva erro/custo/proveniência e a lacuna continua explícita; retomadas reutilizam o checkpoint. `ABORTING` não autoriza essa recuperação, pois o cancelamento ainda está em curso. Sem itens utilizáveis, permanece falha, conservando custo observado quando informado na resposta terminal. Nada é reprocessado retroativamente. Um item diagnóstico `no_items` do Instagram é preservado na auditoria, sem se tornar evidência social ou observação de procura zero.

Se `buildNumber` vier nulo na resposta terminal, o conector consulta novamente a mesma run. Persistindo a ausência, usa `buildId` para consultar o build real e conferir IDs de build/Actor antes da comparação com a versão pinada. Não substitui metadado ausente pela versão configurada; ausência não é relatada como se fosse uma versão divergente. GETs de run/build não iniciam coleta.

- [Apify Proxy: conexão externa e por Actors](https://docs.apify.com/proxy) — conferido em 2026-10-28.
- [Abortar run de Actor](https://docs.apify.com/api/v2/actor-run-abort-post) — em timeout de acompanhamento, o cliente solicita aborto e informa se houve confirmação; Run ID permanece disponível para reconciliação.
- [Indeed Scraper](https://apify.com/misceres/indeed-scraper/input-schema) — alternativa confirmada na Store; ainda não integrada nem ativada como substituição automática.

## Meta Ad Library

A documentação oficial permite anúncios políticos/sociais globalmente e anúncios de qualquer tipo apenas entregues no Reino Unido/União Europeia. Isso não sustenta a premissa de API oficial para anúncios comerciais de educação no Brasil.

- [Meta Ad Library API](https://www.facebook.com/ads/library/api/)

Decisão: para anúncios comerciais brasileiros, usar Actor Apify avaliado ou outro provedor autorizado. Marcar como dependência externa de risco alto e obter revisão de termos/jurídica.

## Google Trends

A API oficial existe em alpha com acesso limitado e janela móvel documentada. Não presumir disponibilidade.

- [Google Trends API alpha](https://developers.google.com/search/apis/trends)

Decisão: porta `SearchTrendsProvider`, com oficial quando aprovado e alternativa configurada quando não.

## Google Ads Keyword Planning

O `KeywordPlanIdeaService` oferece volume histórico, competição e lances. Exige conta, OAuth, developer token e possui limites mais restritos.

- [Keyword planning](https://developers.google.com/google-ads/api/docs/keyword-planning/overview)

## YouTube Data API

Possui quota e políticas próprias; a quota padrão documentada é 10.000 unidades/dia, sujeita a mudança. Cache e orçamento de quota são obrigatórios.

- [Visão geral](https://developers.google.com/youtube/v3/getting-started)
- [Custos de quota](https://developers.google.com/youtube/v3/determine_quota_cost)

## Vagas, Instagram, TikTok e páginas concorrentes

São capabilities reais do registry Apify: `google_search`, `web_crawler`, `meta_ads_library`, `linkedin`, `linkedin_jobs`, `instagram`, `tiktok`, `youtube_comments`, além de `reddit`, `google_trends` e `google_analytics` opcionais. O deployment fornece Actor e build pinados; ausência de capability obrigatória bloqueia a análise. O uso continua sujeito à revisão de termos, permissões e políticas de cada fonte.

## Critérios comuns

- legalidade e termos;
- cobertura geográfica;
- frescor e estabilidade;
- schema e completude;
- custo e rate limits;
- retenção permitida;
- viés e representatividade;
- fallback e comportamento de falha.
