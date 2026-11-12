# CS-00 — Baseline e reconciliação: implementação parcial

**Data:** 12/11/2026. **Status:** retenção/diagnóstico corrigidos e recuperação verificada; **gate CS-00 pendente de causa comprovada da divergência original**. Não inicia CS-01, Codex CLI ou Scrapling.

## Conferência real

A análise `c393baed-a055-49ae-a200-e00bb94b4fb9` tinha 21 tarefas Google Search: 19 `SUCCEEDED`, duas `EMPTY`, 21 arquivos conciliados. Cada tarefa tinha uma tentativa paga e uma identidade remota. Dezenove registravam uma releitura, sem segunda tentativa paga. Esses estados já existiam no início da auditoria; não são resultado da correção desta entrega.

O método real `ApifyClient.resume` releu três runs existentes: Conhecer Seguros (`V2FwPQJbW3xkOLkXQ`), FGV (`aZ2AfS4rqkmzHozxl`) e Ibmec (`3FNqiKxxU87FQnQD0`). Todas retornaram um registro com header de total igual a um e conteúdo idêntico ao arquivo preservado. Um registro SERP pode conter vários resultados filhos. A amostra inclui duas runs com reconciliação anterior e uma sem ela.

Somente GETs de run/build/dataset foram usados. Items foram pedidos com `format=json`, `clean=false`, `limit=1000`, `offset=0`. Metadados e hashes foram capturados em artefatos privados. Nenhum Actor novo foi iniciado pelo procedimento de diagnóstico; o workflow do usuário continuou independente, sem cancelamento ou reinício nesta auditoria.

## Defeito reproduzido e correção

O cliente anterior levantava `ApifyReconciliationRequiredError` sem `dataset_result` quando a leitura de um Actor `SUCCEEDED` tinha contagem divergente ou falha HTTP. Objetos já baixados ficavam apenas em memória. A mensagem genérica também não conservava os números para identificar retrospectivamente a condição exata. A revisão independente encontrou o mesmo descarte de prefixo quando uma página posterior retornava JSON inválido/não-lista; esse caso também foi reproduzido e corrigido.

Agora os objetos JSON válidos recebidos ficam em checkpoint privado não verificado, inclusive a página que revelou mudança de contagem. Arquivos parciais não são promovidos a evidências pontuadas. Contagem inconsistente, total mutável e erro HTTP preservam diagnóstico com offset/limite pedidos, quantidade recebida, total anterior/atual e status disponíveis. O histórico `dataset_read_failures` fica na tarefa/tentativa, inclusive após recuperação bem-sucedida; não contém token, headers de autorização, URL assinada ou corpo bruto.

`dataset_read_pending` distingue extração pendente de falha de execução/cobrança sem arquivo. O contador continua limitado a três releituras persistidas da mesma run; divergência persistente fica `IN_DOUBT` e não autoriza nova compra. Nenhuma condição de contagem foi relaxada. Erro de schema preserva o prefixo válido e continua sendo erro de schema, exigindo revisão.

## Limite de causalidade

A divergência original não se repetiu nos GETs reais de 12/11. O sistema antigo não conservou corpo/números daquela falha. Consistência eventual do provedor é uma hipótese compatível com o sucesso da releitura, não uma causa comprovada. Não se atribui a falha a RAM, Actor ou LLM sem evidência. O [contrato Apify](https://docs.apify.com/api/v2/dataset-items-get) define os headers, mas não prova o que ocorreu naquela resposta.

Os testes simulados provam a perda de dados e sua correção no cliente; não reproduzem ao vivo o mismatch original. Para fechar o gate, capturar recorrência com o novo diagnóstico e comparar request, headers, corpo preservado, término remoto e horários. Se não houver recorrência na janela definida, registrar ausência de reprodução e revisar o critério de aceite com essa limitação, sem declarar causa descoberta. Não comprar novos Actors apenas para fabricar recorrência.

## Validação

Novos arquivos: `tests/contract/market_sources/test_apify_dataset_reconciliation.py` (sete casos) e `tests/integration/market_sources/test_existing_run_reconciliation.py` (dois casos). Foram observados RED/GREEN para retenção, diagnóstico e persistência. As integrações comprovam recuperação eventual, limite de três releituras, uma tentativa paga, custo sem duplicação e nenhuma admissão de arquivo parcial.

```powershell
rtk proxy .venv/Scripts/python.exe -m pytest tests/contract/market_sources/test_apify_dataset_reconciliation.py tests/integration/market_sources/test_existing_run_reconciliation.py tests/integration/market_sources/test_complete_collection_retention.py tests/integration/market_sources/test_apify_recovery_policy.py -q -o addopts=
```

Resultado focal: **30 aprovados**. Suíte final: **952 aprovados, 5 pulados** no Windows e no Linux, com um aviso de depreciação de configuração do Alembic em cada ambiente. Ruff aprovado e mypy aprovado em 102 arquivos. A revisão independente encontrou o caso de JSON inválido; após RED/GREEN, confirmou a correção e não encontrou bloqueio restante para integrar o patch parcial. Testes reais pulados por opt-in não contam como executados; os GETs acima são procedimento separado.

## Preservação e aplicação

Baselines antes/depois confirmaram hashes idênticos dos 33 cursos e 66 funis sintéticos ENS e dos 13 dossiês existentes. Artefatos ficam em `var/diagnostics/cs00-*20261112*`, ignorados pelo Git. Não há migração, troca de provider ou edição de dossiês.

Na primeira entrega, o código foi exercitado por processos separados e testes, sem restart do worker ativo. Após nova autorização para concluir CS-00, foi realizada a renovação controlada descrita abaixo. A correção não recria diagnósticos antigos nem apaga avisos históricos.

### Atualização operacional — 12/11/2026

Antes da renovação, verificou-se que a etapa 8 estava `COMPLETED`, a etapa 9 estava lendo o corpus e nenhuma das 49 tarefas de coleta estava `RUNNING`. Foi salvo um manifesto com hash do checkpoint da etapa 8, identidades/hashes dos arquivos de todas as runs e hashes dos resultados das 252 partes já validadas.

API e worker foram reiniciados com janela de parada de 20 segundos. O mesmo job da análise foi reagendado pelos casos de uso canônicos `schedule_analysis_job_retry` e `publish_analysis_job`, conservando os checkpoints e a análise `RUNNING`. Não foi criada outra análise nem alterado o estado para concluído/cancelado. Uma inferência ainda em voo pode ser repetida; resultados validados não foram descartados.

Após a retomada, a conferência demonstrou checkpoint da etapa 8 idêntico, 49 identidades de runs e hashes dos arquivos preservados, e todas as 252 partes anteriormente validadas mantidas. A leitura progrediu de 25 para 27 estados de leitura registrados; o novo processo de worker ficou saudável e recebeu o mesmo job. A coleta concluída não foi refeita nessa retomada. O baseline pós-ativação voltou a confirmar os 33 cursos, 66 funis sintéticos e 13 dossiês preservados por hash.

Evidências privadas adicionais: `var/diagnostics/cs00-upgrade/before.json` e `var/diagnostics/cs00-activated-20261112.json`. Essa aplicação encerra a pendência de versão carregada no worker; não produz a resposta histórica ausente necessária para provar a causa do mismatch original.

## Gate

| Critério | Estado |
|---|---|
| Baseline, preservação e recuperação da mesma run | Verificado |
| Retenção de parcial, limite e ausência de recompra | Corrigido e testado |
| Causa exata do mismatch original reproduzida | Pendente |
| Ativação controlada no runtime local | Verificado após renovação e retomada do mesmo job |

Próximo marco permanece CS-00. Esta entrega não deve ser usada para declarar CS-01 ou substituição de runtime concluídos.
