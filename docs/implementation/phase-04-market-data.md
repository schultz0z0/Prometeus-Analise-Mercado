# Fase 04 — Dados externos de mercado

## Objetivo

Coletar e normalizar evidências externas com custo, quota, proveniência e comportamento de falha conhecidos.

## Arquivos principais previstos

- `src/.../domain/ports/market_sources.py`
- `src/.../infrastructure/apify/`
- `src/.../infrastructure/google_ads/`
- `src/.../infrastructure/youtube/`
- `src/.../infrastructure/trends/`
- `tests/contract/market_sources/`

## Tarefas

1. Definir contratos de trends, search metrics, ads, offers, jobs e social voice.
2. Implementar orçamento por análise e cache key canônica.
3. Avaliar e pinar Actors por schema, custo, manutenção e termos.
4. Implementar adapter Apify e acompanhamento assíncrono de runs.
5. Implementar Google Ads Keyword Planning quando o acesso estiver aprovado.
6. Implementar YouTube com cálculo explícito de quota.
7. Implementar provider de Trends selecionado na Fase 00.
8. Normalizar, deduplicar e registrar proveniência.
9. Simular timeout, 429, schema drift, resultado vazio e custo excedido.
10. Validar amostras manualmente com analista de marketing.

## Verificação

```bash
pytest tests/contract/market_sources -q
pytest tests/integration/market_sources -q
```

## Gate

Cada fonte possui contrato, termos revisados, teto de custo, métricas de qualidade e fallback/status parcial definido.
