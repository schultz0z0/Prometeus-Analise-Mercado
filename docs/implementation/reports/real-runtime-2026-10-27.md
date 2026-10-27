# Relatório — runtime factual e OAuth ChatGPT

**Data:** 2026-10-27  
**Estado:** implementação concluída; validação externa da nova autorização ChatGPT aguarda reconexão interativa do usuário.

## Entregue

- planejamento LLM contextual antes da coleta;
- execução real e auditável das capabilities Apify configuradas;
- URLs dependentes resolvidas a partir de resultados anteriores;
- features, scoring, quality gate, síntese e verificação sem defaults fabricados;
- tela de progresso baseada em etapas e tool runs persistidos;
- dossiê exibido somente quando verificado;
- preflight antes de custo externo;
- LLM por OpenAI API key ou plano ChatGPT OAuth;
- JEV opcional, com modo 100% tradicional funcional;
- credenciais OAuth rotativas compartilhadas entre API e worker em `var/`.

## Validação executada

- suíte Python completa: aprovada, com teste live Apify deliberadamente opt-in;
- Ruff e mypy: aprovados;
- contratos OAuth, refresh, descoberta de modelos, Responses streaming e endpoint sem simulação: aprovados;
- token OAuth legado encontrado no ambiente: rejeitado corretamente por não possuir `chatgpt.tokens.use.direct`; uma tentativa real de `GET /v1/models` retornou 403, portanto ele não é marcado como conexão válida.

## Pendente externo

1. clicar em **Continuar com ChatGPT** e conceder o escopo de uso direto;
2. confirmar que o callback lista os modelos reais e conclui a inferência de prova;
3. executar uma análise real, o que pode consumir cota ChatGPT e créditos Apify;
4. habilitar explicitamente o teste live de schemas Apify quando houver autorização para custo.

Nenhum desses itens possui fallback sintético. Enquanto a reconexão não ocorrer, o workflow deve ficar `BLOCKED` antes de iniciar coleta paga.

