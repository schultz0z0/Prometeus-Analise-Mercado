# IPD, scoring v2 e revisão das skills por fonte

Data: 2026-10-28. Prometeus — Inteligência para Produtos Educacionais.

## Escopo

Implementação autorizada após a [auditoria manual](manual-mba-scoring-audit-2026-10-28.md), conforme o [plano](../../plans/2026-10-28-ipd-evidence-scoring-v2.md). O dossiê manual não foi recalculado, suas evidências não foram reclassificadas e nenhuma análise paga foi iniciada. A homologação real do novo perfil cabe ao usuário.

## Por que a pesquisa estava incompleta

- A descrição textual de Brasil era usada como correspondência literal contra endereços de vagas, descartando fontes brasileiras pertinentes.
- IDs públicos de vagas viravam marcadores de telefone; a deduplicação tratava vagas diferentes como a mesma entidade.
- O adaptador tradicional não enviava rubricas/notas. Melhorar o arquivo não alterava efetivamente o julgamento.
- A pertinência confundia finalidade da fonte com comprovação de compra de curso. Vagas/competências, contexto setorial e sinais sociais precisam de usos diferentes.
- Uma consulta Trends unia assuntos em uma expressão; respostas vazias e timeout não sustentavam tendência. Isso não demonstra demanda zero.
- Preços estavam em páginas com várias condições/ofertas, sem vínculo seguro. A referência anterior não combinava preços internos e externos.
- O histórico misturava famílias e usava similaridade/conversão, não o IPD apresentado. O pedido de revisão curricular não chegava à recomendação global.

Nem toda exclusão era incorreta. Anúncio próprio, região incompatível, conteúdo genérico, cookies, placeholders e preço sem atribuição continuam fora do indicador correspondente. Contexto útil é preservado para a redação.

## Mudanças

`portfolio-v2` congela regras por análise e exibe score observado, cobertura, confiança, contribuição e quatro blocos. Mantém gates de insuficiência e revisão. O histórico usa a última janela encerrada/completa, referência por família, percentis de posto médio e até três cursos próximos por tema/grade. Menos de três cursos de referência impede IPD; grade ausente não é inventada.

A referência de preço é média por curso comparável, do mesmo tema/categoria, com total explícito interno ou externo. Origens e quantidades permanecem separadas. Taxa de matrícula, duração acadêmica, instituição própria e preço de outro curso não são total concorrente. Múltiplos totais sem vínculo inequívoco ficam ambíguos, mesmo com prazo coincidente. A implementação não resolve automaticamente toda página multi-oferta.

Geografia/idioma são normalizados preservando restrições explícitas. IDs técnicos públicos tipados sobrevivem à higienização, mantendo proteção de PII no texto livre. Qualificação/cache incluem finalidade, contexto institucional e versão/hash de rubrica/skill. Falha de fonte continua registrada individualmente, preservando o restante do fluxo.

## Skills, tools e system prompts

Foram aprimoradas cinco skills existentes. O catálogo v3 descreve onze capacidades com objetivo, consulta, dados esperados, aceitação, rejeição, diagnóstico, recuperação e amostragem. Comparáveis/preço reutilizam as skills allowlisted de revisão/oferta, sem duplicar uma skill por Actor.

Rubricas/notas agora chegam ao julgamento tradicional e ao JEV, mantendo os endpoints existentes. Instruções locais entram no system prompt das etapas correspondentes; conteúdo web permanece dado não confiável. Confiança e revisão explícita chegam ao gate determinístico. Não houve homologação JEV online.

## Limites dos dados e validação

A migração `0010_historical_ipd_metadata` não atribui fechamento nem periodicidade a registros legados desconhecidos. A base de teste não contém grades históricas e possui poucos cursos por família. Isso pode manter IPD ou preço interno indisponíveis até a instituição fornecer os metadados. Não foram acrescentados cursos/números artificiais para superar gates.

Regressões offline cobrem geografia, IDs, pertinência, rubricas, taxas/preços, revisão global, IPD, migração, snapshots e compatibilidade legada. A interface foi exercitada em `http://localhost:8000` com respostas interceptadas somente no navegador isolado, em 1440×1000 e 390×844: conteúdo, motivos expansíveis, inspeção de evidências e retorno ao portfólio; sem erros JavaScript ou overflow horizontal. Browser plugin indisponível; usado Playwright instalado. Fixtures não foram gravadas na base.

## Verificação e atualização local concluídas

- Suíte completa: `389 passed, 1 skipped` (18,17 s). O teste opt-in de schemas Apify online ficou desativado; não foram feitas chamadas pagas de homologação.
- Ruff passou; mypy passou nos 68 arquivos de código; validação documental passou e `git diff --check` passou.
- Build de API/worker concluído; containers recriados após confirmar ausência de tarefas ativas/reservadas/agendadas. A análise `QUEUED` de 23/10 já existente não foi retomada nem alterada.
- Migração PostgreSQL está em `0010_historical_ipd_metadata`; API readiness confirma banco/Redis e worker responde `pong`. O processo carrega `portfolio-v2` e as cinco skills versionadas.
- Contagens preservadas: 12 análises, nove dossiês e 229 evidências. Hash do dossiê manual antes/depois: `77ddb1276c47f8943709780eda420d1c`. O GET do dossiê conserva perfil `default-v1`, nota 27,47 e cobertura 55%.
- A interface v2 e a leitura legada foram verificadas no navegador isolado; não houve erro JavaScript. A referência de preço também explica suas exclusões sem excluir automaticamente a página dos outros usos.

Os dez registros históricos legados conservam `price_period=unknown` e `cohort_status=UNKNOWN`. Sua participação no IPD/preço requer metadados explícitos, sem atualização artificial nesta entrega. Nenhuma conclusão comercial sobre o MBA decorre dos testes offline. Homologação de nova análise real permanece pendente com o usuário.
