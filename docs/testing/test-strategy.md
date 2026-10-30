# Estratégia de testes

## Pirâmide

- Unitários: domínio, fórmulas, transições e normalizadores.
- Contratuais: ENS, JEV, LLM, Apify, Google e webhook.
- Integração: PostgreSQL, Redis e adapters sandbox/mocks.
- Avaliação de IA: decision packs e geração factual ([avaliação de inteligência de mercado](market-intelligence-evaluation.md)).
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

## Homologação real de dossiês

`scripts/audit_dossier_runtime.py --live --analysis-id ID --output /app/var/diagnostics/NOME` executa até duas gerações e os dois gates sobre os fatos de uma análise existente, sem publicar nem refazer Actors. Usa as credenciais configuradas e exige autorização operacional; os artefatos privados locais incluem fatos, rascunhos, verificações e resultado.

`tests/evaluation/dossier/test_live_support_contract.py` exige `PROMETEUS_RUN_LIVE_DOSSIER_TESTS=1` e `PROMETEUS_LIVE_DOSSIER_FACTS` apontando para o artefato factual. Os controles verificam que descrições corretas de cálculo e histórico sintético são aceitas e que confiança como chance de sucesso e simulação como prova de demanda são recusadas. Não alteram registros de análise.

A homologação E2E completa deve incluir formulário real, upload original, LLM e Actors configurados, checkpoints persistidos até publicação, abertura do dossiê, consulta de evidências, reload e inspeção de erros de navegador. Coleta parcial e recomendação de evidência insuficiente são resultados possíveis e não equivalem a falha de software. Testes com fakes ou auditoria isolada da síntese não substituem esse percurso.
