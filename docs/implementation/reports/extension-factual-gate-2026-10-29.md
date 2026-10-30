# Homologação de extensão — investigação e correções de diagnóstico

Data: 29/10/2026. Análise: `f92b1f4a-f1b4-45c9-b424-c0fa791c632c`, instituição ENS, curso Extensão em Fraude e Litigância predatória no mercado de seguros.

## Estado observado

A execução de 14:44:35 a 15:16:35 UTC terminou `BLOCKED` no checkpoint 13, síntese/verificação do dossiê. Não está aguardando término de Actor. Preflight confirma modo tradicional e JEV desativado, perfil `portfolio-v2` e snapshots das dez skills. Foram persistidas 131 evidências e 20 consultas. As falhas de coleta não interromperam o cálculo.

O cálculo persistido, ainda não publicado, indica score observado 55,82, cobertura 80% e confiança 61,98%. A recomendação calculada é evidência insuficiente: confiança abaixo de 75% e dimensão obrigatória de busca ausente. Esses valores não constituem um dossiê validado nem recomendação de lançamento.

O log do verificador acusa `structural_error=True`, `hallucination=True`, `unsupported_claims=0`. O primeiro sinal também inclui textos de blocos que falham na verificação, não apenas estrutura JSON inválida. O serviço anterior rejeitava o rascunho antes da persistência e guardava somente a mensagem geral. Portanto, não há evidência suficiente para identificar a frase/número exatos, distinguir uma alegação inventada de eventual falso positivo do verificador, ou afirmar que uma mudança de prompt resolveria esta execução. Não foi gerado um substituto para encobrir essa lacuna.

## Apify: leitura de runs e datasets existentes

Somente GETs; nenhuma nova execução ou retomada de coleta.

- Instagram `jtO9FeRMQ4Wa3M52r` terminou `SUCCEEDED`. Dataset `ApdzmmyHs9ZGZ6XPL` contém `error=no_items`, descrição “Empty or private data for provided input”. O validador o classificava incorretamente como schema drift; isso também impedia guardar a proveniência do retorno no checkpoint local.
- Trends `56aBwrjONn8dAR4U6`: actor entrou em retries/timeouts de widgets e requisições de inicialização; aborto remoto feito pelo sistema após o limite local. Dataset `1UrCgoilaADk7fcXi` contém uma série de litigância predatória com 262 pontos, dos quais 35 têm `hasData=true`. É retorno parcial, não prova de cobertura completa nem aprovação automática de uma feature. O conector antigo descartava todo retorno ao lançar timeout.
- Trends `vMABkTJ0eIpSxCPgh`: mesmos problemas operacionais; retorno disponível para fraude securitária sem pontos temporais válidos na consulta inspecionada. Não sustenta demanda zero.
- Custos terminais das duas runs Trends: aproximadamente US$ 0,136104 e US$ 0,136267. O custo local agregado de US$ 0,215008 omitia esses timeouts; não foi reescrito retroativamente.
- Duas consultas Meta concluíram sem resultados, o que é diferente de erro técnico e não demonstra ausência de mercado.

Referências oficiais consultadas: [Instagram Scraper](https://apify.com/apify/instagram-scraper), [entrada Google Trends](https://apify.com/apify/google-trends-scraper/input-schema), [aborto de run](https://docs.apify.com/api/v2/actor-run-abort-post) e [itens do dataset](https://docs.apify.com/api/v2/dataset-items-get).

## Correções no sistema

Rejeições determinísticas agora preservam código, localização, motivo e trecho limitado no checkpoint, exibidos com escape no painel. Gates e publicação continuam exigindo o mesmo suporte factual. Dossiês recusados não são publicados; não há reclassificação artificial de claims nem inserção de referências para fazê-las passar.

Timeout pode recuperar itens já persistidos somente após aborto terminal confirmado, mantendo todas as validações anteriores e status local `PARTIAL`. A evidência recuperada ainda precisa passar por normalização, higienização, qualificação e extração de features. Custos/proveniência ficam registrados, inclusive sem itens, quando o provedor informa os valores terminais. Reuso de checkpoint não repete a chamada paga. Esta mudança não resolve a indisponibilidade do actor Trends nem garante uma série suficiente.

`no_items` do Instagram passa como diagnóstico conhecido e é rejeitado da base de posts, preservando consulta/run/dataset e sem converter dados vazios/privados em procura zero.

O erro de console `currentTarget.disabled` foi reproduzido: o evento perde `currentTarget` após `await`. O handler passa a guardar a referência do botão antes de aguardar e a restaurá-la em `finally`. Os erros `chrome-extension://` são de extensão e não demonstram causa do gate. O HTTP 400 da extração documental não pode ser diagnosticado somente pela print; falta o corpo da resposta e o arquivo/requisição daquela tentativa. Nenhuma correção especulativa de upload foi aplicada.

## Preservação e limites

Não foi alterada nem retomada a análise real. Hash da linha de análise antes da atualização: `ac1be0770dec708cec4b0da75d0fbd6b`; estado `BLOCKED`, zero dossiês, 131 evidências, 20 runs. Alterações aplicam-se a execuções futuras. O texto específico rejeitado nesta execução permanece desconhecido e o curso continua sem dossiê publicável.

Validações automatizadas e confirmação do ambiente são registradas após execução dos checks; não equivalem a homologação real de outra análise.

## Verificação e ambiente

- Suíte completa: 433 testes passaram, 1 teste opt-in de metadados reais não executado. As 14 novas regressões cobrem aborto/recuperação parcial, custo, schema/build, reuso, páginas realmente emitidas, Instagram, diagnóstico factual persistido e escape da interface, além do evento assíncrono.
- Ruff passou em `src` e nos testes alterados; mypy passou em 70 arquivos. A varredura Ruff de todo `tests` apontou apenas, após corrigir os imports novos, formatação de imports preexistente em `tests/e2e/test_foundation_flow.py`, mantida fora deste delta. Validação documental passou em 137 arquivos; whitespace passou.
- Revisão independente identificou dois P2 e aprovou suas correções: impedir recrawl de URLs já emitidas em retorno parcial sem marcar seeds não capturadas como visitadas; manter custo/proveniência conhecidos mesmo com build/schema incompatível, continuando a rejeitar as evidências.
- Build de API/worker concluído; containers recriados e saudáveis, backend HTTP 200 e versão web `20261029a` confirmada. Worker pronto às 15:39:14 UTC. Nenhuma análise estava em execução antes da atualização.
- Após atualização, análise original segue com o mesmo hash `ac1be0770dec708cec4b0da75d0fbd6b`, mesma atualização às 15:16:35 UTC, `BLOCKED`, zero dossiês, 131 evidências e 20 runs. Não houve nova coleta, inferência ou alteração direta de resultado.
- Criada uma conferência automática de leitura em 15 minutos, sem repetir aviso se o estado não mudar. O acompanhamento se pausa ao confirmar o estado terminal; não retoma nem refaz a análise.

## Recuperação da redação após a investigação

A versão anterior a esta recuperação bloqueava imediatamente na primeira rejeição do texto. Foi acrescentada uma revisão delimitada na própria síntese, com no máximo duas gerações: rascunho inicial e uma revisão. O mesmo verificador determinístico e o mesmo gate semântico avaliam novamente o texto revisado. A revisão recebe cópias dos fatos aprovados, do rascunho e do relatório; não executa Actors, não pesquisa fontes novas, não modifica a recomendação nem o score e não inicia análises por conta própria.

O diagnóstico inicial é salvo antes de pedir a revisão. Sucesso guarda contagem de gerações e recusas anteriores em `presentation.verification`. Recusa persistente, falha na geração revisada ou indisponibilidade do verificador mantém o bloqueio com diagnóstico. Indisponibilidade não dispara revisão, pois mudar a redação não conserta o acesso ao provedor. A auditoria preserva também uma rejeição inicial quando o verificador cai depois da revisão. Falhas de infraestrutura ou parsing da geração inicial continuam sujeitas aos tratamentos de erro do runtime; não há garantia de execução sem falha externa.

Testes novos cobrem revisão válida, ainda inválida, indisponível, tentativa de mutar fatos pelo adaptador, revalidação semântica, transporte do prompt com skills e preservação do diagnóstico se o verificador ficar indisponível antes ou depois de uma revisão. Esses testes reproduzem a classe de bloqueio e validam a recuperação; não recuperam a frase perdida da homologação original nem comprovam que aquela redação específica teria sido corrigida pela LLM real. Nenhuma nova chamada paga foi feita para esta validação.

Verificação desta recuperação: **441 testes passaram e 1 teste opt-in foi ignorado**, em 26,41 segundos; Ruff passou no código e nos testes alterados, mypy passou em 70 arquivos e validação documental passou em 137 documentos. Revisão independente reproduziu uma perda de diagnóstico por indisponibilidade semântica após a revisão; o caso foi corrigido, coberto por regressão e aprovado na segunda revisão. Checksum/contagens da análise original permaneciam intactos antes da atualização, sem análises em execução. Nova homologação real continua necessária para verificar a geração específica do provedor.

Atualização concluída: imagens API/worker reconstruídas e containers recriados. API HTTP 200, web `20261029b`, worker saudável com resposta `pong`; modo `traditional`, cliente `ChatGPTPlanGenerativeClient` com `revise_dossier` confirmado sem inferência externa. Os 18 testes de dossiê e contrato de geração também passaram dentro do container. Análise original mantém hash `ac1be0770dec708cec4b0da75d0fbd6b`, estado bloqueado, 131 evidências, 20 runs e zero dossiês após a atualização.
