# Cobertura competitiva e recuperação Apify — 05/11/2026

## Estado

**Homologação técnica concluída em 06/11/2026:** a mesma análise concluiu os 15 checkpoints e publicou dossiê VERIFIED, com dez ofertas em sete das dez instituições pesquisadas. A conferência independente do payload final, hash dos fatos, fontes oficiais e preservação histórica passou. Recomendação: INSUFFICIENT_EVIDENCE. Ambiente Docker local com OAuth tradicional e Apify reais; não representa aprovação comercial ou rollout público.

Durante a retomada, uma checagem dos anúncios encontrou perda de conteúdo: o Actor documenta [texto e criativos em `snapshot`](https://apify.com/igolaizola/facebook-ad-library-scraper), mas o normalizador só reconhecia o formato plano. Foram corrigidos ID, corpo, título, link e carrosséis, com regressões e subversão exclusiva para o cache publicitário. A conferência sobre os dados reais verificou corpo preservado em 70/70 anúncios e carrossel em 10/10, respeitando o orçamento de contexto. Os Actors não foram repetidos por essa correção; os outros tipos mantêm seus julgamentos compatíveis.

O bloqueio inicial por cota e as ocorrências da retomada estão preservados nas seções históricas abaixo. O dossiê final está disponível no mesmo ID 9cb4f98e-60b5-46d9-998e-5ad81ebe7d86.

## Mudanças

- Novos planos não herdam teto monetário de US$ 5 nem reserva de US$ 0,50 por chamada. Monitoram custos e mantêm escopo finito, versões pinadas, cancelamento e permissões em código. Restrições externas continuam possíveis.
- Cada concorrente tem busca dirigida e validação por domínios oficiais. Até três variantes semânticas ampliam pesquisas concluídas sem oferta; uma rodada adicional cobre outras lacunas.
- A homologação também identificou que o primeiro domínio temático genérico eliminava do texto da consulta o foco declarado no título. Novas buscas priorizam o título; complementos preservam seus termos e depois ampliam o domínio para ofertas adjacentes. O plano inicial já executado continua preservado e as novas variantes registram a ampliação.
- Tentativa inicial e até três retentativas são persistidas. O contador sobrevive a retomada e reparo. Backoff é agendado na outbox, sem manter worker dormindo. POST ambíguo é reconciliado antes de qualquer nova compra; leituras compartilham o limite de recuperação, sem multiplicar retries internos.
- Retomada de run com aborto terminal confirmado recupera dados parciais já persistidos; URL ausente em retorno interrompido é falha de extração, sem confundi-la com HTTP 404.
- Em 06/11, o log real do Google Trends revelou falha de inicialização do navegador. As próximas retentativas reduzem a concorrência nativa para uma página, preservando termos/região. A opção `maxConcurrency=1` foi conferida no schema oficial do build pinado `0.0.143`, além da [documentação oficial do Actor](https://apify.com/apify/google-trends-scraper/input-schema).
- Bloqueio dentro de dataset `SUCCEEDED` também é diagnosticado. A recuperação tenta somente as páginas pendentes e conserva ofertas e custos anteriores. Erros permanentes, inclusive credencial inválida, encerram com ação de configuração. Cobertura continua parcial se alguma página permanece bloqueada.
- O dossiê reúne todos os planos e execuções, preserva múltiplas ofertas e verifica o payload visual final antes de persistir. Consulta planejada não conta como pesquisa executada.
- MCP Apify de apoio foi habilitado no backend, com SDK oficial e quatro ferramentas de consulta. A API permanece executora e nenhum Actor descoberto é promovido automaticamente.

## Validação de código

Em 06/11, a homologação encontrou mais duas causas analíticas: o projetor omitia corpo/descrição da página no julgamento, e o reparo aceitava notícia contextual como oferta enquanto o dossiê a excluía. Ambas foram reproduzidas por regressões. O projetor v3 preserva o conteúdo e a qualificação v4 aplica admissão compartilhada, distingue categoria observada e conserva relação desconhecida sem promovê-la a direta. Sinais publicitários permanecem separados. A execução foi interrompida sem Actors ativos e foi retomada sobre os mesmos dados; os 171 julgamentos anteriores ficam preservados no histórico, e os dados passam por nova qualificação sob o contrato corrigido.

- Windows: 819 testes passaram; cinco testes live ficaram fora da suíte padrão por exigirem opt-in.
- Linux isolado e sem rede: 819 testes passaram; os mesmos cinco testes live foram separados. O teste live de schemas Apify foi executado separadamente e passou.
- Ruff aprovado; mypy aprovado em 96 módulos; documentação canônica validada.
- Regressões incluem dez instituições dirigidas, várias ofertas por instituição, consulta FGV planejada/bloqueada, payload visual adulterado, HTTP 429, bloqueio em dataset, credencial inválida, quatro tentativas máximas, custo acumulado, cancelamento durante retomada e ausência de multiplicação de GETs.
- Revisão independente encontrou lacunas em diagnóstico de dataset, cobertura de páginas parcialmente bloqueadas e composição de retries. Foram corrigidas e cobertas por regressões antes da atualização do ambiente.
- Quatro controles reais com a LLM passaram separadamente: ela distinguiu resultados registrados de alegações sem suporte e não aceitou histórico sintético como garantia de demanda ou matrículas. Esses controles usam um artefato de fatos explícito e não registram aprovação comercial.

As suítes completas foram repetidas em 06/11/2026: 824 casos por ambiente, sem falhas, com cinco live separados. A deduplicação inclui parâmetros de rastreamento (`utm_*`, `srsltid`), preservando parâmetros que identificam cursos diferentes.

## Migração, concorrência e preservação

Backup completo anterior: `var/backups/collection-v2-2026-11-05/pre-migration.dump`, 3.442.141 bytes, SHA-256 `ee2b213ddd9c8ad63d6c67a611caebbf22279afb4bce6c8d09491d82633d5a2a`.

O backup foi restaurado em PostgreSQL isolado e a migração `0014_collection_attempts` aplicada. Dois coletores concorrentes produziram somente uma execução no executor offline; o outro preservou a tentativa em andamento. O backup JSON posterior incluiu a tabela de tentativas e restaurou 2.998 registros no clone.

Os 33 cursos e 66 registros históricos ENS mantiveram seus hashes antes e depois da migração/restauração. Os onze dossiês anteriores também mantiveram o hash agregado ao atualizar o ambiente real. Não houve seed/reset, alteração de premissas históricas ou registro de decisão humana/outcome.

A configuração anterior foi guardada em área privada ignorada pelo Git. A transição removeu o parâmetro monetário obsoleto e habilitou somente o MCP de consulta; as demais configurações, incluindo OAuth e token Apify, foram preservadas.

## Verificações no ambiente atualizado

A primeira rodada (`8c609307-e515-4a14-aafe-5cf38c3c21f8`) revelou HTTP 400 `max-total-charge-usd-below-minimum` nas buscas. O parâmetro de início `maxItems`, que controla cobrança e não garante tamanho de dataset, causava um limite calculado abaixo do mínimo do Actor. A política sem teto monetário agora omite tanto `maxTotalChargeUsd` quanto esse parâmetro de cobrança. Os limites continuam no input próprio do Actor, como `maxPagesPerQuery` e `maxCrawlPages`.

Uma execução real, persistida no clone PostgreSQL, confirmou a busca aceita após o ajuste, sem limite monetário enviado pela aplicação. A primeira rodada foi cancelada, com a última run remota confirmada `ABORTED`; não publicou dossiê e seus resultados/custos foram preservados. Rejeições HTTP agora conservam código e mensagem estruturados do fornecedor com token removido, evitando diagnóstico baseado somente em HTTP 400. A segunda rodada mantém vínculo com a anterior e nova chave de idempotência.

- API pronta, worker e scheduler saudáveis; migração atual `0014_collection_attempts`.
- Settings confirmam `apify_spending_mode=monitor_only` e `apify_max_charge=null`.
- LLM tradicional por ChatGPT OAuth, modelo `gpt-6.1-terra`, sem JEV.
- Consulta real de metadados pelo MCP do backend retornou `ok`, com saída não confiável identificada e sem iniciar Actor.
- Navegador real confirmou a remoção do campo de teto e a apresentação de custos/recuperações. Registros brutos e itens normalizados têm rótulos separados, evitando a razão ambígua “8/1”. Capturas em `settings.png` e `live.png`.
- Nova reanálise criou ID próprio e o teste de idempotência recuperou o mesmo ID na repetição.

## Evidências

Artefatos em `output/collection-v2-2026-11-05/`: `windows-suite.xml`, `linux-suite.xml`, `quality-checks.json`, `baseline.json`, `postgres-checks.json`, `configuration-transition.json`, `runtime-smoke.json`, `canary2-progress.json`, `canary2-timeline.jsonl`, `blocked-verification.json` e `blocked-quota.png`. A primeira rodada cancelada permanece em `canary*`; não confundir com a segunda, `canary2*`.

## Resultado intermediário registrado em 06/11, antes da renovação da cota

- Dez instituições configuradas e dez buscas individuais concluídas; nove crawlers dirigidos retornaram conteúdo e o da FIPECAFI terminou vazio. Pesquisa executada não significa oferta confirmada.
- 48 tarefas: 42 `SUCCEEDED`, três `EMPTY`, uma `PARTIAL` (Google Trends) e duas `FAILED` (Instagram Porto/Bradesco Seguros). Nenhuma run permaneceu ativa/incerta. Nenhuma tarefa foi descartada por teto monetário local.
- 57 tentativas persistidas na segunda rodada, máximo de quatro por tarefa. As falhas naturais exercitaram o limite de três retentativas; Ibmec/Trends foram reconciliados pela mesma run, sem compra duplicada. Custos anteriores foram conservados.
- 337 evidências normalizadas preservadas. A qualificação v4 foi concluída em 64 itens; 273 ainda precisam dessa revisão. Uma oferta adjacente apareceu nesse trecho inicial. Isso não é o benchmark final e não permite concluir que só existe um concorrente.
- Custo Apify observado da segunda rodada: US$ 1,002182, provisório. O limite externo que interrompeu a análise pertence ao ChatGPT OAuth, não a uma reserva financeira Apify.
- Análise `BLOCKED`, job `FINISHED`, checkpoint 9 com diagnóstico da cota e zero dossiês novos. API, worker e agendador voltaram saudáveis; a análise bloqueada não é reenviada automaticamente para consumir a cota indisponível.
- Backup PostgreSQL final em `var/backups/collection-v2-2026-11-05/postdeployment.dump`. Backup JSON formato 2 em `postdeployment.json`: 4.171 registros, incluindo 83 tentativas no banco completo (não apenas as 57 desta rodada), SHA-256 do payload `7c7e25d0e08daf11737c0510b57d8efb0caf80d8746423f7889bab94cd54081a`.
- O clone de restauração foi removido após salvar `restored-clone-final.dump`, incluindo seus testes pagos. Os 33 cursos, 66 funis e onze dossiês anteriores mantiveram os hashes; decisões humanas/outcomes permanecem em quatro cada.

A retomada desse bloqueio exige confirmar uma chamada LLM bem-sucedida e usar o mesmo ID pelo workflow canônico, com reenvio controlado do job. Não criar outra análise nem apagar checkpoints/evidências para esse fim. Os resultados terminais Apify são reutilizados e a qualificação usa o cache compatível com o contrato/modelo vigente. Naquele momento, o gate visual final e a inspeção do dossiê real ainda estavam pendentes.

## Ocorrências na retomada de 06/11

A renovação da cota permitiu concluir a qualificação das 522 evidências sob a versão 4. Os planos complementares executaram 16 tarefas da segunda variante competitiva, dez da terceira e dez de reparo geral. O benchmark calculado passou a reunir dez ofertas em sete instituições, com pesquisas concluídas nas dez configuradas. Três ofertas mantêm relação ainda não classificada; ausência de preço ou carga horária estruturados continua explícita.

Uma sobrecarga externa (`server_is_overloaded`) no checkpoint 9 foi seguida de nova prova real de disponibilidade e retomada controlada do mesmo ID. Mais tarde, o runtime Docker/WSL perdeu comunicação (`no route to host`), impedindo inclusive consultas de saúde. O reinício normal expirou; a recuperação do runtime preservou os volumes. Ao voltar, o scheduler publicou automaticamente o job com lease vencido e o worker retomou a análise. As contagens permaneceram em 522 evidências e 93 tentativas; não houve nova coleta Apify por essa interrupção.

A primeira redação revelou um falso positivo determinístico: o denominador da escala do índice, seguido de vírgula, era rejeitado. A regressão falhou antes da correção e passou depois; casos de score incorreto, percentual inventado e volume de mercado continuam rejeitados. Em seguida, uma chamada do verificador semântico falhou. A repetição isolada do mesmo julgamento retornou `SUGGESTIVE`, confiança 0,95 e sem revisão humana exigida. O gate permaneceu fechado até a retomada explícita; nenhum dossiê foi publicado por esgotamento de tentativas. O diagnóstico desse bloqueio e o da retomada estão preservados nos artefatos.

## Limites de interpretação

`COMPLETED` e `VERIFIED` não comprovam cobertura integral de mercado, calibração comercial ou aprovação humana. O histórico ENS continua sintético e identificado. Custos Apify observados são provisórios. A meta ampla de latência e os gates comerciais permanecem sujeitos à homologação própria.

As paradas de manutenção e a indisponibilidade da cota nesta rodada impedem usá-la como medição de SLA. A homologação técnica deste dossiê foi concluída; não há autorização de rollout público.


## Resultado final e aceite técnico — 06/11/2026

- Análise COMPLETED, job FINISHED, 15 checkpoints concluídos e dossiê VERIFIED; verificação independente do hash e payload visual aprovada.
- Quatro planos, 84 tarefas e 93 tentativas: 78 sucessos, três vazios, um parcial e duas falhas; máximo de quatro tentativas por tarefa, IDs remotos únicos e nenhuma run ativa/incerta.
- 522 evidências qualificadas v4; anúncios com projetor específico v2. Dez ofertas em sete instituições, três relações ainda não classificadas. Cobertura completa do recorte competitivo; Trends/Instagram e comparabilidade financeira mantêm lacunas explícitas.
- Custo Apify observado: US$ 1,271501, provisório. Recomendação de evidências insuficientes; índice experimental 42,86, cobertura analítica 35% e confiança 47%, sem interpretação como chance de sucesso.
- Base preservada: 33 cursos sintéticos, 66 registros de funil, onze dossiês anteriores com hashes inalterados; quatro decisões e quatro outcomes anteriores.
- Backup JSON formato 2: 5.603 registros, 119 tentativas no banco completo, SHA-256 do payload 8b7fb57ac4ef1626855c81c8443e33fd189aa1b3f0193e3724d0acb34e7fc8fd. Backup PostgreSQL postcompletion.dump: 5.664.936 bytes, SHA-256 bb774cc6b0ec1747bfcd437e062fc1cec267dd8e8c3c54e485c9bae8f7908da. Backups ficam em área privada ignorada pelo Git.
- Conferência da tela confirmou as mesmas contagens e ressalvas. A quota de localStorage encontrada nesta inspeção foi corrigida: dossiês não são persistidos no navegador, e o cache legado é removido; regressão com 6 MB e 15 testes focais aprovados. As suítes completas anteriores ao ajuste de cache tiveram 819 aprovados e cinco live separados em Windows e Linux.
- Artefatos finais: completed-verification.json, inal-facts.json, inal-dossier.json, inal-dossier.png, postcompletion-backup.json, diagnósticos e retomadas em output/collection-v2-2026-11-05/.

A homologação de desempenho/SLA e a calibração comercial continuam pendentes. Não se atribui certificação global 10/10 ao produto com base neste canário.
