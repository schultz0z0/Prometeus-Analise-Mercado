# Fontes externas

**Validado em:** 2026-10-09. Revalidar antes de implementar e em cada upgrade relevante.

## JEV / TypeSafe AI

Fonte oficial confirma Choice, Score e Noul, decisões paralelas, probabilidades e confidence. Perguntas complexas devem ser decompostas e combinadas em código.

- [Introdução oficial](https://docs.typesafe.ai/introduction)
- [Anúncio oficial](https://typesafe.ai/blog/introducing-system-one-models-and-jev)

Status: dependência obrigatória e ainda jovem. Validar limites, região de processamento, retenção, contrato e versão disponível.

## Apify

O MCP e a API oficial permitem descobrir e executar Actors, acompanhar runs e ler datasets. Em produção, Actor, versão, schema, custo máximo e limites devem ser pinados.

- [Apify MCP](https://docs.apify.com/mcp)
- [Execução de Actors](https://docs.apify.com/actors/running)

Status: backbone preferencial de scraping. Actors da Store não são automaticamente confiáveis; avaliar proprietário, qualidade, permissões, preço, manutenção, termos e resultado.

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

Serão atendidos por provedores/Actors configuráveis. Nenhum Actor específico é considerado garantido antes da avaliação da Fase 04. LinkedIn não será raspado diretamente sem autorização e revisão de termos.

## Critérios comuns

- legalidade e termos;
- cobertura geográfica;
- frescor e estabilidade;
- schema e completude;
- custo e rate limits;
- retenção permitida;
- viés e representatividade;
- fallback e comportamento de falha.
