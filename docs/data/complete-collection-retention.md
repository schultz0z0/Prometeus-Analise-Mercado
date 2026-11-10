# Retenção integral da coleta Apify

Desde 10/11/2026, o escopo solicitado no input do Actor controla a pesquisa; o cliente não recorta novamente a saída já produzida por `call.max_items`. Todos os objetos do dataset são lidos em páginas de até 1.000 registros, com `clean=false`, incluindo campos ocultos, filhos, metadados do provedor e diagnósticos. A normalização não aplica top-N ou cotas por vídeo. Deduplicação continua separada da retenção dos originais.

## Verificação da leitura

O cliente distingue `total_items_source=provider_pagination` (total explicitamente observado no cabeçalho) de `terminal_exhaustion` (paginação esgotada sem total fornecido). Executores que não verificam essa condição usam `unverified`. Uma página curta antes do total declarado, total alterado entre páginas, erro HTTP ou contagem divergente exige reconciliação da mesma run, sem iniciar nova compra. Uma resposta vazia com total positivo nunca comprova dataset vazio. Cancelamento continua sendo verificado em cada leitura.

O archive só marca `retrieval_complete=true` quando a contagem recuperada coincide com o total e a origem da contagem foi verificada. Uma execução ainda ativa pode ter sua leitura momentânea completa e, separadamente, `incomplete_reason`: isso não significa que o Actor terminou a pesquisa. Resultados parciais não são promovidos a sucesso integral.

## Archive privado e versão analisável

`ToolRunModel.parameters.dataset_archive` usa o contrato `schema_version=1`: `provider_run_id`, `dataset_id`, `retrieval_complete`, `dataset_total_items`, `total_items_source`, `items_read`, `source_sha256` e `items`. Cada item contém:

- `index`: índice zero-based no dataset original;
- `source_sha256`: SHA-256 do objeto original, serializado em JSON UTF-8 com chaves ordenadas;
- `raw_payload`: objeto original completo, restrito ao armazenamento privado;
- `sanitized_data`: objeto completo após o mesmo sanitizador das evidências, sem limite de caracteres;
- `sanitization_changed`: indica se a higienização alterou o objeto.

O hash do corpus usa a mesma serialização da lista original inteira. `prior_dataset_archives` conserva arquivos de runs anteriores quando uma chamada passa a outra run; uma releitura da mesma run substitui o snapshot atual. Rejeições preservam motivo e JSON higienizado integral. Filhos SERP preservam `_source_record.index` e `_source_record.pointer` para localizar o pai original; campos adicionais do pai permanecem no archive.

O archive não deve ser serializado inteiro em endpoints de progresso. Os consumidores públicos recebem manifesto e dados higienizados mediante autorização; `raw_payload` nunca é material da LLM nem resposta pública. A leitura analítica deve usar `sanitized_data` e referenciar run, índice e hash, mantendo o conteúdo como entrada não confiável.

Alteração de schema continua sendo uma falha explícita de admissão. Quando o dataset contém objetos JSON com campos desconhecidos, a leitura integral é conservada no checkpoint privado, marcada `schema_drift_requires_review`; nenhum desses objetos se torna evidência pontuada automaticamente. Falhas de transporte, JSON inválido ou itens não-objeto exigem reconciliação/revisão e não alegam retenção integral. Runs antigas não são retroativamente completadas por esta alteração.

Runs `FAILED` e `TIMED-OUT` com dataset também têm seus objetos extraídos e arquivados, mantendo a falha original e `failed_actor_dataset_retained`. Se a extração falhar, o erro original do Actor continua visível; registros já recuperados ficam em archive incompleto e `dataset_read_pending=true`, `dataset_read_recovery=resume_existing_provider_run` e `failed_actor_dataset_pending` identificam a recuperação pela mesma run. O diagnóstico não é promovido a evidência pontuada.

## Validação

Os testes de contrato cobrem datasets maiores que o escopo, campos ocultos, paginação sem total, total mutável, página desaparecida, consistência eventual após término e schema desconhecido em múltiplas páginas. Testes de integração cobrem todos os filhos SERP, todos os comentários por vídeo, duplicados, diagnósticos longos, separação original/higienizado, hashes, dataset parcial e checkpoint de schema drift. Os testes usam HTTP simulado e SQLite; não iniciam Actors pagos.
