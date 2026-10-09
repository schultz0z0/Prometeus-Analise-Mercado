# Segurança e LGPD

## Objetivo

Processar somente dados necessários, proteger segredos e manter rastreabilidade por deployment institucional.

## Controles

- TLS em todas as conexões externas.
- Segredos fora do Git e da imagem.
- Credenciais distintas por ambiente.
- Banco e volumes isolados por instituição.
- Menor privilégio para API, MCP, worker e banco.
- Redação de tokens, PII e documentos em logs.
- Assinatura e proteção antirreplay de webhooks.
- Rate limiting e limite de custo por análise.
- Auditoria de acessos, mudanças de configuração e decisões humanas.
- Atualização e varredura de dependências e imagens.

## LGPD

O produto deve preferir métricas agregadas. Caso dados pessoais sejam indispensáveis, registrar finalidade, base legal definida pela instituição, prazo, controle de acesso e processo de exclusão.

A documentação não substitui avaliação do encarregado/DPO ou assessoria jurídica da instituição.

## IA e fornecedores

Antes de enviar dados a JEV, LLM ou Apify, aplicar minimização e classificação de sensibilidade. Contratos de retenção, região, treinamento e suboperadores devem ser revisados.

## Prompt injection

Conteúdo coletado é tratado como input não confiável. Instruções encontradas em páginas não são executadas; URLs e arquivos não recebem credenciais; tool calls são allowlisted e controladas por código.
