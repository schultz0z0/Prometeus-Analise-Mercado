# Observabilidade

## Logs

JSON estruturado com `correlation_id`, `analysis_id`, `step`, `institution_id`, duração e resultado. Proibido registrar tokens, payloads sensíveis ou conteúdo integral de documentos por padrão.

## Métricas

- jobs por status e etapa;
- duração e retries por conector;
- custo por análise, fonte e modelo;
- quota e cache hit rate;
- coverage/confidence por modalidade;
- taxa de baixa confiança JEV;
- rejeição de claims da LLM;
- webhook success e dead letters;
- conexões, filas e recursos de infraestrutura.

## Traces

Trace distribuído entre entrypoint, job e conectores, sem conteúdo sensível. IDs de runs externos são atributos protegidos.

## Alertas iniciais

- fila sem consumo;
- taxa de falha acima do baseline;
- banco/Redis indisponível;
- custo anormal;
- quota próxima do limite;
- webhook acumulado;
- backup não executado.
