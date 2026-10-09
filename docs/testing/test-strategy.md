# Estratégia de testes

## Pirâmide

- Unitários: domínio, fórmulas, transições e normalizadores.
- Contratuais: ENS, JEV, LLM, Apify, Google e webhook.
- Integração: PostgreSQL, Redis e adapters sandbox/mocks.
- Avaliação de IA: decision packs e geração factual.
- E2E: chatbot simulado até webhook e consulta final.
- Operacionais: backup, restore, migração e falhas de fornecedor.

## JEV

- golden dataset por decision pack;
- métricas por classe e confiança;
- regressão entre versões;
- casos ambíguos e adversariais;
- timeout, rate limit e indisponibilidade.

## LLM

- schema válido;
- números restritos ao facts payload;
- `evidence_ids` existentes;
- resistência a instruções em conteúdo coletado;
- consistência de idioma e tom;
- ausência de promessas proibidas.

## Scoring

- property-based tests para limites e monotonicidade;
- soma dos pesos;
- dados ausentes e cobertura;
- imutabilidade de versões;
- reprodução por snapshot.

## CI planejada

```text
ruff check .
ruff format --check .
mypy src
pytest -q
pytest tests/contract -q
```

Testes que exigem credenciais reais ficam em pipeline manual/seguro e nunca em pull requests de forks.
