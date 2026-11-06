# Homologação em execução real — 04/11/2026

**Produto:** Prometeus — Inteligência para Produtos Educacionais, Agência Prometeus.
**Autorização:** iniciar homologação e aplicar as correções ao ambiente de execução real.
**Destino observado:** Docker Desktop existente neste workspace, `APP_ENV=staging`, acesso local em `http://127.0.0.1:8000`. Não foi configurado um servidor público ou domínio de produção.

**Status:** homologação funcional local concluída com fornecedores reais; correções aplicadas ao ambiente em execução. Primeiro canário bloqueado por cota OAuth; reanálise concluiu os 15 checkpoints com dossiê `VERIFIED`, após atualização da conexão pelo usuário. Não aprova SLA ou produção ampla. Complementa o [relatório das correções](audit-remediation-2026-11-04.md).

## Atualização e preservação

Antes da atualização, não havia tarefas ativas ou reservadas no worker. Existiam 16 análises: dez concluídas, cinco bloqueadas e uma enfileirada desde 23/10, sem etapas executadas. O banco estava em `0010_historical_ipd_metadata`.

API e worker foram parados para backup consistente. O `pg_dump -Fc` pré-migração possui 2.681.542 bytes e SHA-256 `0316aaf3dd15eb7fb06040de24c82c78f4d740d4985567f0207967fdf3e82563`; está em `var/backups/homologation-2026-11-04/pre-migration.dump`, fora do Git. A listagem do `pg_restore` foi validada. Imagens anteriores receberam tags privadas de rollback e o código do commit anterior foi arquivado no mesmo diretório privado.

Esse dump foi restaurado em PostgreSQL 16 isolado. As migrações 0011–0013 foram aplicadas à cópia, preservando as contagens de todas as 15 tabelas de negócio existentes, inclusive 16 análises, dez dossiês, 784 evidências, 846 decisões e 147 runs. Hashes dos históricos também foram preservados. A seguir, as mesmas migrações foram aplicadas ao banco em uso, e API, worker e scheduler foram recriados.

Os 33 cursos e 66 registros históricos sintéticos ENS permanecem byte a byte equivalentes na projeção ordenada dos registros. O arquivo `.env` manteve seu hash, e a configuração continua tradicional com ChatGPT OAuth e modelo selecionado `gpt-6.1-terra`, sem JEV. A renovação normal dos tokens OAuth continua permitida pelo cliente; seus valores não são registrados neste relatório.

A outbox da submissão legada `6da2353c-fb77-4ff3-bd0d-08e5e8eab244` recebeu `next_attempt_at=2099-01-01` e motivo `LEGACY_PREDEPLOYMENT_PENDING_OPERATOR_REVIEW`. Seu estado de negócio permanece `QUEUED`; não foi executada nem apagada. Para retomá-la, revisar proposta e orçamento e liberar conscientemente a outbox. Isso evita que a reconciliação inicie trabalho histórico durante o ensaio.

## Verificações do ambiente

- Nova imagem Linux, com as dependências efetivamente instaladas e Node apenas na imagem de QA: 696 testes, zero falhas/erros, cinco live ignorados; 691 aprovados. A primeira tentativa herdou variáveis reais dos Actors e não tinha Node, interferindo nas fixtures; a repetição limpou somente o ambiente do processo de testes, sem alterar o `.env` real.
- Liveness e readiness HTTP 200; API, worker, scheduler, PostgreSQL e Redis saudáveis. Portas da aplicação restritas ao loopback.
- Login real com chave própria privada, sessão HttpOnly, leitura dos 33 cursos, rejeição de acesso anônimo, tenant divergente e escrita de outra origem; logout seguido de HTTP 401.
- MCP executado no contêiner real: negociação `2025-11-25`, duas respostas para initialize/tools-list e nenhuma resposta à notificação; cinco ferramentas disponíveis.
- Consulta live aos schemas dos dez conectores Apify configurados: aprovada. O teste foi corrigido após detectar que `default` avançou: agora resolve o build fixado no histórico do Actor e consulta seu schema por ID, sem atualizar automaticamente o pin. Referências: [listar builds](https://docs.apify.com/api/v2/actors-builds-get), [consultar build](https://docs.apify.com/api/v2/actor-build-get).
- Quatro controles reais de factualidade com o OAuth existente: todos aprovados. Reconheceu duas descrições fiéis de fatos calculados/sintéticos e recusou duas alegações indevidas de probabilidade de sucesso/demanda garantida. Usou fatos locais históricos conhecidos, sem inserir rótulo esperado no prompt ou alterar análises.
- Browser autenticado acompanha a análise por URL com ID persistido; screenshot local em `output/playwright/homologation-live-progress.png`. URLs dos módulos de autenticação, portfólio e dossiê foram versionadas para invalidar caches anteriores.
- Cancelamento real separado, análise `ef2398a8-4041-45b3-8b0c-cb2066e9fa2d`: `CANCELLED`, sem tool runs; não registra decisão comercial ou resultado de lançamento.
- Após as correções descobertas na homologação, suíte de **718 testes: 713 aprovados e cinco live ignorados**, tanto no Windows quanto em Linux. Os cinco opt-in foram executados separadamente: schema dos dez conectores Apify e quatro controles LLM passaram. Lint, formatação e mypy continuam aprovados. O teste isolado de concorrência PostgreSQL iniciou dois coletores para um orçamento de US$ 0,50: apenas uma chamada foi autorizada, com reserva visível em sessão independente antes do executor.
- Backup JSON formato 2 do ambiente atualizado, com 18 tabelas e 2.700 registros no snapshot intermediário, gerado e validado por esquema, contagens e checksum. Arquivo privado `var/backups/homologation-2026-11-04/postdeployment.json`. O PostgreSQL temporário foi removido após os ensaios; volumes do ambiente principal permanecem preservados.

## Canário com fornecedores reais

Análise `0fe55f2d-6b58-4177-9185-25255c860526`, curso de extensão **Governança de Inteligência Artificial e Proteção de Dados no Mercado Segurador**, 24 horas. Proposta marcada `validation_run=homologacao-real-2026-11-04`. Premissas financeiras são dados controlados de homologação, não orçamento aprovado da ENS. Nenhuma aprovação humana ou matrícula comercial foi criada.

A mesma submissão foi repetida com `Idempotency-Key=homologacao-20261104-real-01` e retornou o mesmo ID. Orçamento Apify configurado: US$ 5 para a análise. A primeira versão descontava custos provisórios do saldo; a homologação demonstrou que isso não garantia um teto agregado. A versão reaplicada usa compromissos persistidos conforme ADR-0010. Inferência usa o plano ChatGPT; custos em dinheiro não fornecidos por esse provedor não são estimados como se fossem custo observado.

O primeiro canário realizou 29 consultas entre plano inicial e reparo: 23 `SUCCEEDED`, cinco `EMPTY` e uma falha Google Trends. Qualificou 120 registros com o modelo real, mas bloqueou no checkpoint 9 em 04/11/2026 às 17:57:26 UTC por `subscription_sharing_usage_limit_exceeded`. Não produziu dossiê nem recomendação. Duração aproximada até o bloqueio: 32 minutos e 48 segundos. Os dados/checkpoints permaneceram preservados.

Na Google Trends, HTTP 502 durante início/acompanhamento deixou uma run remota ativa. Sua entrada foi comparada ao plano original, a identidade/build foram conferidos e a run foi abortada para parar o gasto. Reconciliação operacional posterior de todas as 29 runs, por GET autenticado e conferência de build, atualizou o custo observado total de US$ 0,228922 para **US$ 0,503981**, preservando o valor anterior e o motivo nos metadados. A análise continuou bloqueada e nenhuma autorização histórica foi fabricada. O ensaio independente de busca `gl428fH54tIi8yGAE`, com limite de US$ 0,50, também confirmou que um custo observado de US$ 0,00005 pode subir depois para US$ 0,00455.

As correções agora preservam identidade/custo nos erros de POST, polling, dataset e build; aborto sem término confirmado e cobrança indeterminada bloqueiam novas compras em `IN_DOUBT`. Uma run que falhou continua contabilizando custo confirmado. O refresh de cobrança não pode alterar silenciosamente estado/identidade; build anteriormente validado só é preservado quando o mesmo build ID/Actor permanecem verificáveis. Mesmo contadores aparentemente alinhados não liberam reserva: custo observado continua provisório e separado dos limites comprometidos.

Após o usuário informar atualização da LLM, uma chamada curta respondeu com sucesso (`OK.`), sem erro de cota, mantendo o provedor tradicional `chatgpt_oauth` e modelo selecionado `gpt-6.1-terra`. A reanálise **`dffd0359-4a40-4cc4-be00-fc5bb74bf687`**, vinculada ao canário anterior, foi criada em 19:30 UTC com nova idempotência e snapshot, na versão com autorizações por run.

Ela concluiu os **15 checkpoints**, com análise `COMPLETED`, outbox `FINISHED` e dossiê `VERIFIED`, em **926,69 segundos (15 min 26,69 s)**. Resultado calculado: **`INSUFFICIENT_EVIDENCE`**, índice observado experimental **30**, cobertura **15%**, confiança analítica **51%**. A publicação declara insuficiência para recomendar lançamento, pede validação do público/aderência curricular/benchmark e não transforma vagas em matrículas ou histórico sintético em procura real. As três frentes automáticas registraram `PASS`; isso não é aprovação humana ou comercial do curso.

Foram planejadas 22 consultas iniciais e seis de reparo. **Dez chamadas foram executadas**, mantendo o total comprometido em **US$ 5,00** entre os dois planos. Dezoito checkpoints sem compra conservaram os motivos de falta de saldo ou URL utilizável. Oito chamadas retornaram conteúdo, duas ficaram vazias e foram preservados **69 registros**. A recuperação não abriu orçamento novo nem repetiu compras para simular completude. O custo Apify observado inicial da reanálise foi US$ 0,085456; a conferência posterior das dez runs terminais retornou **US$ 0,170773**, ainda registrado como observação do provedor, com timestamp e valor anterior preservados. O limite comprometido não foi automaticamente liberado.

O primeiro rascunho desta reanálise precisou de revisão automática por um falso positivo numérico na expressão “índice de 30 em 100”. O segundo rascunho passou nos gates existentes e foi publicado sem essa formulação. A causa foi corrigida para execuções futuras: a fonte canônica declara a escala em metadata estruturada (`citable_contract_version=4`) e o verificador reconhece construções restritas de denominador do índice. Regressões mantêm rejeição de 100% inventado, numerador diferente e uso de 100 em volume de empresas/matrículas. A frase real foi revalidada em leitura com os fatos da análise no contêiner, sem reescrever o dossiê publicado.

A apresentação econômica foi comparada ao motor Decimal: **13 premissas explícitas**, cenários de 15/19/30 alunos dentro da capacidade, resultado base hipotético de R$ 11.970,94 e fluxo mensal conciliado ao centavo. A interface rotula simulação e não prevê matrículas. Conferência visual cobriu a visão geral, fontes, economia e revisões. A seção de revisões agora diferencia verificações automáticas da homologação humana e não inventa contagens, afirmações de viabilidade ou ausência universal de alucinações quando faltam dados.

Os artefatos locais `output/homologation-2026-11-04/` registram baseline, backup, restauração, testes, smoke HTTP, proposta, canários, reconciliação e progresso. Credenciais e dumps ficam exclusivamente nos caminhos privados de runtime.

## Limites da aprovação

Esta homologação confere o ambiente local existente e a execução técnica dos casos descritos. Mantém histórico ENS sintético explicitamente identificado. Não calibra o modelo com resultados oficiais, não aprova lançamento do curso, não comprova disponibilidade/p95 por período, não executa teste de carga e não conecta CRM. Webhook continua sem destino/segredo configurados, usando polling; não houve entrega externa fictícia. JEV permanece ausente e fora do caminho de execução.

O tempo do canário já excedeu a meta de workflow p95 inferior a 180 segundos do guia de piloto. Uma amostra não estima p95, mas não sustenta afirmar que esse objetivo foi atingido. A latência precisa de medição e otimização antes de aprovar esse SLA ou rollout amplo.

O histórico institucional continua sintético por instrução expressa. Neste caso, não houve comparável interno com proximidade verificável suficiente, e o próprio scoring não contou esse pilar como presente. A baixa cobertura decorre do suporte efetivo e dos limites de coleta; o sistema não foi forçado a emitir aprovação. A retomada do canário antigo ou o aumento de orçamento exigem nova decisão operacional, sem editar resultados para melhorar artificialmente o parecer.
# Nota posterior — 05/11/2026

A execução de 04/11 validou o fluxo técnico, mas deixou incompleta a pesquisa competitiva: as reservas financeiras interromperam buscas dirigidas e a apresentação confundiu planejamento com execução. Isso não comprova ausência de concorrentes nem homologa o benchmark. A correção e sua nova homologação estão no [relatório de cobertura e recuperação](collection-recovery-homologation-2026-11-05.md); os resultados históricos abaixo foram preservados.
