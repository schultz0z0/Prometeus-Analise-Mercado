# Auditoria profunda da etapa 13 e homologação automatizada

Data: 29/10/2026. Produto: Prometeus — Inteligência para Produtos Educacionais.

## Falha investigada

Análise `ba806630-3d17-42c8-944b-acbd1e66ab69`, Extensão em Fraude e Litigância predatória no mercado de seguros. A tentativa inicial passou pelo verificador determinístico, mas o semântico recusou uma descrição do resultado e suas ressalvas. A revisão posterior introduziu referência vazia no resultado, claim sem seção e IPD de 72,22 citado numa fonte que não exportava essa métrica.

O gate bloqueou a publicação. As fontes Apify não foram a causa imediata dessa recusa, embora houvesse lacunas de coleta. O problema não foi resolvido por apenas adicionar uma revisão ou corrigir formatos numéricos: permaneciam assimetrias entre os fatos vistos pelo redator e pelo verificador e um contrato estrutural transmitido somente como texto no prompt.

## Causas e correções

| Causa verificada | Correção |
|---|---|
| O redator via regras de cobertura/confiança/experimento que a fonte citável de scoring não continha integralmente | Fonte canônica `scoring_result` com valores, recomendação e definições, usada igualmente por redação e verificadores e incluída no hash |
| Fonte histórica ainda buscava nomes antigos de features, sem o IPD atual | IPD, confiança e escala do pilar calculado entram explicitamente na fonte histórica quando presente |
| Provedor recebia apenas um pedido textual de JSON, podendo retornar suportes vazios | JSON Schema estrito nos transportes Chat Completions e Responses/OAuth, com enum de fontes existentes e listas não vazias |
| Diagnóstico semântico interrompia no primeiro erro, sem localização ou referências suficientes | Agregação por claim/bloco, com referência, escolha, confiança e revisão pendente; limite explícito de quarenta alvos |
| Parsing inválido escapava antes do ciclo de revisão | Erro de contrato inicial e sua resposta original entram na mesma única revisão; a segunda recusa continua bloqueando |
| Rascunho recusado não era preservado integralmente | Auditoria conserva rascunho e diagnóstico no registro da tentativa, com dados delimitados e sem publicação ou logs gerais de conteúdo |

Nenhuma referência é preenchida automaticamente, não se reclassificam números inválidos e não há aprovação por esgotamento das tentativas. Os pesos e fórmulas de scoring não foram alterados. O caráter sintético da comparação institucional permanece explícito.

Fonte oficial consultada para o transporte: [Structured model outputs — OpenAI](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses). O schema melhora a forma e as referências permitidas; não substitui verificação factual ou semântica.

## Auditoria isolada com LLM real

`scripts/audit_dossier_runtime.py --live` foi executado sobre os fatos persistidos da análise que falhou, sem editar ou publicar seus resultados e sem repetir Actors. Modelo configurado: `gpt-6.1-terra`, via ChatGPT OAuth, modo tradicional.

Resultado: doze claims, aprovadas no verificador determinístico e semântico na primeira geração. A redação manteve a recomendação de evidências insuficientes e explicou a natureza experimental, histórico sintético, cobertura e confiança. Artefatos locais ignorados pelo Git: `var/diagnostics/deep-audit-run-1/`, contendo fatos, rascunho, texto verificado e resultado. Essa auditoria isolada não é a homologação do fluxo inteiro nem altera a análise original.

## Controles reais positivos e negativos

Quatro chamadas opt-in no pack `evidence-support-v1` passaram: descrição do resultado calculado e descrição do histórico sintético classificadas `OBSERVED`; confiança como probabilidade de sucesso e histórico sintético como prova de demanda/matrícula classificados `UNSUPPORTED`. Confiança retornada 1,0 nos quatro casos. Esse valor descreve a decisão do modelo no teste, não sua precisão estatística nem garantia de comportamento futuro.

Comando de teste: `tests/evaluation/dossier/test_live_support_contract.py`, usando artefato factual local e `PROMETEUS_RUN_LIVE_DOSSIER_TESTS=1`. Não houve publicação nem alteração de evidências nesses controles.

## Homologação E2E pela interface — concluída com recuperação

Análise nova `73501c53-cc58-47f9-8927-d9e299b4f4b5`, criada pelo formulário público em 29/10/2026 às 16:52:48 (America/Sao_Paulo). Navegador controlado por Playwright CLI, sem interceptar respostas de backend.

Entradas: DOCX original do programa de extensão, categoria Extensão/Aperfeiçoamento, EAD síncrono, um mês de duração acadêmica, doze parcelas de R$ 100 e público profissional de seguros/Direito/investigação. Upload pelo seletor de arquivo da interface extraiu 10.281 caracteres e manteve `16h`. O formulário não foi preenchido com resultados ou evidências inventados.

No acompanhamento inicial, o preflight confirmou modo tradicional e a execução passou ao worker real. A coleta inicial terminou, incluindo Google Trends com sucesso, e avançou à higienização/qualificação. Instagram retornou sem conteúdo utilizável e não interrompeu o workflow. As duas interrupções e correções encontradas durante a homologação estão registradas abaixo; o percurso incluiu recuperação pelo entrypoint normal, não foi uma execução inteiramente sem falhas desde a primeira submissão.

Conclusão confirmada em **29/10/2026 às 17:43:02 (America/Sao_Paulo)**. Análise `COMPLETED`, checkpoints 1–15 `COMPLETED`, dossiê `ead0c124-c147-449b-bddb-6869e8872f89` com status `VERIFIED`, onze claims verificadas. A tentativa final passou sem nova revisão, com geração e verificação semântica reais via `gpt-6.1-terra`/OAuth em modo tradicional. O job final `cfae7500-6155-4639-a09a-7a4b5e9e7af5` reutilizou os checkpoints 1–12; não repetiu Actors.

Resultado: índice observado 51,11/100, cobertura 80%, confiança 61,98%, recomendação `INSUFFICIENT_EVIDENCE`. Dezenove consultas persistidas: quinze com sucesso, três vazias e uma parcial. Foram preservadas 144 evidências: dezessete qualificadas para indicadores, 73 como contexto e 54 excluídas. O relatório mostra a base sintética, a ausência de preço externo comparável e a insuficiência de interesse de busca. Essas limitações não foram removidas para aprovar o software.

`scripts/assert_real_analysis.py` passou em leitura: estado final, quinze checkpoints, referências não vazias, verificação determinística repetida, igualdade do hash factual e proveniência Apify. Hash `7761d831324c2e5130258bc80691f4e3b8c9367afff5677cc4a0a890710f7a6e`. Na interface real foram confirmados texto, categoria/modalidade, indicadores, abertura da base da síntese e fontes, persistência após reload e console sem erros/avisos. O dossiê ficou aberto no Chrome do usuário.

Artefatos locais: `var/diagnostics/e2e-course-73501c53/acceptance.json`, `published-dossier.json` e `blocked-reference-audit.json`; captura `output/playwright/dossier-e2e-completed.png`; traces do formulário original e do acompanhamento em `.playwright-cli/traces/`. Esses diretórios são ignorados pelo Git. As três análises bloqueadas anteriores continuam com seus estados e timestamps originais.

## Validação local

### Interrupção de persistência encontrada no E2E

Às 17:11:26, o crawler complementar retornou conteúdo cujo título, limitado antes da higienização, cresceu com os marcadores de ocultação de PII. A gravação excedeu `market_evidences.title VARCHAR(256)`. A sessão SQLAlchemy ficou pendente de rollback e o handler tentou salvar a falha nessa mesma transação, produzindo `PendingRollbackError`; a análise permaneceu incorretamente `RUNNING`. Não houve erro OAuth no ponto de interrupção.

Regressões reproduzem expansão de título e falha real de flush. A higienização limita somente o título final, preservando o payload completo; o workflow faz rollback antes de registrar checkpoint/análise falhos e não expõe parâmetros SQL no diagnóstico público. Dez testes dos módulos afetados passaram, assim como a suíte completa após essa correção.

O usuário autorizou reiniciar o processo após atualizar o OAuth. Uma chamada real pelo worker retornou `OK`. API/worker foram reconstruídos e o job foi reenfileirado pelo entrypoint Celery normal em 29/10/2026 às 17:24, tarefa `888cad9a-0919-4500-a641-8606b06a39ca`, preservando a análise e checkpoints concluídos. Não houve alteração direta de evidências, resultados ou estados no banco.

### Referências inválidas encontradas na etapa 13 real

A retomada chegou à síntese e foi corretamente bloqueada porque `highlights.cons` citava identificadores inexistentes (`CLM-10 won't` e `CLM-10-independent` nas duas tentativas). O schema já restringia evidências, mas deixava IDs de claims e seus vínculos como strings livres. A correção limita todos esses campos por enum, incluindo prós/contras; na revisão usa exclusivamente os IDs existentes no rascunho. Nenhum vínculo é corrigido por aproximação ou inventado pelo código. O prompt passou a 3.0.1. Regressões cobrem o schema e sua transmissão na revisão; revisão independente aprovou o delta. A recusa completa foi preservada antes da retomada final, que passou nos gates.

### Reabertura do acompanhamento na interface

O navegador automatizado original havia sido encerrado durante a interrupção. A interface não reconstruía o painel de uma análise ao reabrir a página. Foi acrescentado o link `/?analysis=<UUID>`: consulta somente leitura aos checkpoints, confere a instituição selecionada, recupera categoria/modalidade/preço do catálogo persistido e continua o polling normal. Novas submissões preservam esse ID na URL para sobreviver ao recarregamento. Um teste de contrato cobre reabertura, metadados, ausência de POST e recusa de outra instituição. O acompanhamento foi aberto no Chrome do usuário e confirmado visualmente, sem criar nova análise.

Suíte completa: 464 testes aprovados, cinco opt-in ignorados (um de metadados Apify e quatro controles LLM reais, estes executados separadamente). Mypy passou em 71 arquivos; Ruff passou no código e testes alterados. Revisão independente aprovou o novo contrato sem P1/P2 no delta. Os testes locais incluem fontes canônicas, hash, IPD, schema de referência, payload Responses, parsing inválido com revisão limitada, falhas de provedor e diagnóstico por alvo.

## Limites

Homologar uma execução real não garante ausência de falhas externas ou comportamento invariável da LLM. A entrega deve continuar recusando afirmações sem suporte e representar uma análise de evidência insuficiente como resultado válido, sem forçar lançamento. Falhas anteriores permanecem preservadas como evidência da investigação.
