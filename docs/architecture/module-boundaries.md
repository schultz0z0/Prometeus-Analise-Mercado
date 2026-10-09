# Fronteiras dos módulos

## `domain`

Entidades, value objects, políticas, estados, fórmulas e interfaces. Não importa frameworks.

Subdomínios previstos:

- proposals;
- analyses;
- evidence;
- institutional_history;
- market_signals;
- decisions;
- scoring;
- dossiers;
- feedback;
- tenancy_configuration.

## `application`

Casos de uso, orquestração, comandos, queries e transações. Coordena portas sem conhecer detalhes de rede.

## `infrastructure`

PostgreSQL, Redis, TypeSafe SDK, LLMs, Apify, Google, Meta, HTTP e armazenamento de evidências.

## `entrypoints`

REST, MCP, CLI e consumers de worker. Apenas valida entrada, autentica, chama casos de uso e converte respostas.

## Regras de dependência

```text
entrypoints -> application -> domain
infrastructure -> application/domain contracts
domain -> biblioteca padrão
```

É proibido:

- calcular score em controller ou prompt;
- acessar CRM diretamente pelo domínio;
- retornar payload bruto de fornecedor ao chatbot;
- importar configuração específica da ENS para o core;
- usar texto gerado para decidir autorização ou mudar estado.
