# Homologação real do MBA Gestão Avançada de Seguros

**Data:** 2026-10-28. **Estado:** ensaio assistido encerrado; homologação autônoma pendente, a cargo do usuário.

## Cenário autorizado

Submissão pela interface local do Prometeus, usando somente o PDF fornecido pela instituição: `Programa MBA Gestão Avançada de Seguros - v9.2.CIMMO.pdf`. Valor declarado pelo usuário: 20 parcelas de R$ 976. Duração acadêmica do programa: 14 meses. O total de R$ 19.520 foi calculado em código e confirmado no checkpoint de entendimento.

Análise: `c291b37c-4186-4b34-b8f1-de7aa805a504`. Chromium isolado com Playwright, aplicação e worker reais em Docker, LLM da conta configurada e Actors Apify reais. Não foram homologados outros formatos nesta execução.

## Verificações observadas

- Extração das 16 páginas: 39.403 caracteres, incluindo o começo e o fim do documento. O texto da interface é idêntico à extração local completa: SHA-256 `73dd5186dd7a7880f91b52103a6035dac6958833213fc51a61994123dcb82db2`.
- Formulário com preço, parcelas, duração e público preenchidos; nome do arquivo e conteúdo persistidos na proposta.
- Corrigida a substituição do formulário por notificações de sincronização em segundo plano. Repetição controlada preservou o nome, o arquivo e seus 39.403 caracteres.
- Acompanhamento continuou após cinco minutos e mostrou falhas individuais com processamento em andamento.
- Falha transitória da consulta de progresso gerou aviso e recuperação automática, sem marcar a análise como interrompida.
- O idioma descritivo retornado pela LLM causou HTTP 400 no Google. O builder foi corrigido para normalizar português em `pt-BR` e recusar códigos desconhecidos antes de iniciar uma execução paga. Duas consultas complementares concluíram após a correção.
- Fontes concluídas da primeira rodada foram preservadas. Retomada após o checkpoint de coleta reutilizou seus resultados.
- Corrigido o recorte `Brasil; participação online de qualquer localidade`, que indevidamente rejeitava vagas com localização brasileira. A qualificação foi versionada e reaplicada.
- Uma consulta de tendências excedeu o limite local. O fluxo seguiu; o agente encerrou a run remota e reconciliou seu identificador/custo. O cliente agora solicita aborto automaticamente ao esgotar o polling, com testes para sucesso e falha desse cancelamento.

Este ensaio teve retomadas manuais do worker, cancelamento direto na Apify e reconciliação de metadados pelo agente. Portanto, não comprova execução autônoma de ponta a ponta. Após a orientação do usuário, essas intervenções cessaram e nenhuma nova análise foi iniciada.

## Verificação automatizada

341 testes passaram, um teste de schema ao vivo permaneceu opt-in. `mypy src`, `ruff check src` e checagem do diff passaram. Regressões incluem coleta parcial, retomada, acompanhamento prolongado e recuperação de conexão, PDF real versus PDF inválido/sem texto, preço parcelado versus total declarado e ausência de truncamento silencioso antes do entendimento.

## Resultado final

A análise permaneceu `BLOCKED` na etapa de síntese/verificação semântica: uma afirmação declarada observada recebeu suporte apenas sugestivo. Nenhum dossiê final foi publicado. O prompt passou a explicitar níveis de certeza, afirmações atômicas e separação entre fato e interpretação. O erro passa a identificar o trecho reprovado para diagnóstico. Essa última orientação ainda depende de uma nova execução real, que o usuário fará pela interface. O ambiente é atualizado sem iniciar ou retomar análises.
