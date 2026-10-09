# Casos de uso

## UC-01 — Avaliar nova proposta

O chatbot envia uma proposta estruturada. O serviço cria uma análise assíncrona, coleta evidências, calcula indicadores, produz o dossiê e notifica o chatbot.

## UC-02 — Solicitar dados faltantes

Quando a proposta não está pronta, o serviço devolve perguntas objetivas e mantém o job em `WAITING_FOR_INPUT`.

## UC-03 — Consultar progresso

O chatbot consulta estágio, percentual aproximado, fontes concluídas, bloqueios e previsão sem expor segredos ou logs internos.

## UC-04 — Inspecionar evidência

O usuário abre a origem de um número ou afirmação e visualiza fonte, trecho, data, método, qualidade e limitações.

## UC-05 — Registrar decisão humana

Diretoria ou responsável registra decisão, justificativa e ajustes aceitos. O registro não reescreve o score original.

## UC-06 — Reanalisar

Uma nova execução é criada com referência à anterior. Dados e versões antigas permanecem imutáveis.

## UC-07 — Associar resultado real

Após o período acordado, métricas reais são relacionadas à análise para backtest e recalibração.

## UC-08 — Operar uma falha

Administrador visualiza falha por etapa, repete somente etapas idempotentes e acompanha entrega de webhook.
