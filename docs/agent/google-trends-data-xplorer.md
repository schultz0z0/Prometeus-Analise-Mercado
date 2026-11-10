# Google Trends: contrato Data Xplorer

O adaptador reconhece `data_xplorer/google-trends-fast-scraper` pela identidade configurada no deployment. O build homologado em 10/11/2026 é `2.10.2`, obtido pela tag `stable` e fixado numericamente. A tag mutável `latest` apontava para `0.0.33`, um contrato antigo com falha de proxy. Não se deve substituir o pin pelo nome de uma tag.

## Entrada e planejamento

O contrato verificado usa `mode=keyword`, `keyword` único, `predefinedTimeframe`, `geo`, `fetchRegionalData=false` e proxy residencial Apify. O modo deve ser explícito: o padrão do build é `trending`, que responde outra pergunta. O intervalo padrão do adaptador é `today 12-m`; o período solicitado é preservado quando suportado pelo schema. Período desconhecido gera erro, sem ampliar silenciosamente a janela.

O planner expande todos os `search_terms` em chamadas individuais, sem o antigo teto de cinco termos. Cada chamada conserva perguntas, obrigatoriedade, parâmetros e dependências; as referências à chamada original passam a referenciar todos os filhos. IDs são determinísticos. O adaptador rejeita listas ainda não expandidas em vez de descartar termos. O Actor legado `apify/google-trends-scraper` continua com seu contrato próprio.

`expand_google_trends_calls(calls, registry)` também pode adaptar planos persistidos antes da execução. Não altera o Actor configurado nem autoriza novas capacidades. A política global de execução controla concorrência e retomada; o contrato single-keyword não autoriza paralelismo irrestrito.

## Saída e interpretação

O normalizador `trends-observation-v2` reconhece `keyword` e `searchTerm`, datas ISO em `timeline_data[termo]`, indicadores em `timeline_data.isPartial` e as variantes de séries legadas. Cada ponto é mantido, inclusive valor zero e ponto parcial final. `raw_payload` mantém integralmente os campos de origem, inclusive campos desconhecidos, dados regionais retornados e URL. O payload original não é substituído pela projeção tipada.

Features determinísticas usam esses mesmos pontos, excluindo períodos parciais e `hasData=false` do cálculo. Zero observado participa da média; ausência de série não vira zero. Crescimento exige janelas equivalentes e base positiva. Índice relativo de 0–100 não é volume absoluto de buscas, pessoas ou matrículas. Séries obtidas em chamadas independentes têm normalização própria e não permitem comparar popularidade absoluta entre palavras.

O teste offline contém a série real de 53 semanas retornada pelo build, com preservação da cauda e campos desconhecidos. Quatro canários já executados sequencialmente com 256 MB terminaram com sucesso; isso valida o contrato observado e não constitui garantia de disponibilidade. Novas execuções pagas exigem a política normal do ambiente. O teste de schema opt-in somente consulta metadados do build.

Fontes oficiais verificadas: [Actor](https://apify.com/data_xplorer/google-trends-fast-scraper) e [schema de entrada](https://apify.com/data_xplorer/google-trends-fast-scraper/input-schema).
