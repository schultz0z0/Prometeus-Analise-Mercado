# Observabilidade

## Logs

JSON estruturado com `correlation_id`, `analysis_id`, `step`, `institution_id`, duração e resultado. Proibido registrar tokens, payloads sensíveis ou conteúdo integral de documentos por padrão.

Rejeições determinísticas do dossiê ficam em `analysis_steps.output_summary.verification`: gate, hash factual e problemas por claim/bloco, com código, motivo e trecho limitado a 300 caracteres. Esses trechos ficam no banco e na consulta da própria análise, sujeitos ao isolamento institucional; não são copiados para os logs gerais nem publicados como dossiê. Diagnósticos são recalculados em código. Não é possível recuperar retroativamente rascunhos que uma versão anterior descartou.

## Métricas

O contrato factual v3 conserva também o rascunho completo e os diagnósticos semânticos por alvo na auditoria da própria análise, sob isolamento institucional e política de retenção. Esses artefatos não são copiados para logs gerais nem publicados como dossiê. Falhas de persistência exigem rollback antes do registro do checkpoint/estado terminal; o diagnóstico público identifica a classe do erro sem parâmetros SQL ou conteúdo coletado.

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

O painel de checkpoints pode ser reaberto por `/?analysis=<UUID>` na interface local. O link consulta o backend e valida a instituição selecionada; não reenfileira jobs, não chama Actors nem altera o resultado. A URL de novas submissões conserva o ID para permitir recarregar a página durante o processamento.

Trace distribuído entre entrypoint, job e conectores, sem conteúdo sensível. IDs de runs externos são atributos protegidos.

## Alertas iniciais

- fila sem consumo;
- taxa de falha acima do baseline;
- banco/Redis indisponível;
- custo anormal;
- quota próxima do limite;
- webhook acumulado;
- backup não executado.
