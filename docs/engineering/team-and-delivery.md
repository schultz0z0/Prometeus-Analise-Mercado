# Capacidade do time e processo de entrega

## Capacidade conhecida

Dois desenvolvedores com apoio de Codex e Claude Code.

## Implicações

- Monólito modular e um único banco transacional.
- Automação forte de testes e documentação.
- Integrações adquiridas/gerenciadas quando confiáveis.
- Limite explícito de work in progress: uma fase principal por vez.
- Revisão humana obrigatória de código gerado por agentes.

## Divisão sugerida

- Desenvolvedor A: domínio, scoring, contratos e JEV.
- Desenvolvedor B: integrações, infraestrutura, MCP/API e operação.
- Responsabilidade compartilhada: testes, segurança, documentação e revisão.

## Fluxo

1. Selecionar tarefa de um plano aprovado.
2. Criar teste que representa o critério de aceite.
3. Implementar mudança mínima.
4. Executar verificações locais.
5. Atualizar documentação/ADR quando necessário.
6. Revisão pelo outro desenvolvedor.
7. Merge somente com evidência de testes.

## Uso de agentes de código

- Fornecer arquivos e critérios exatos.
- Não aceitar claims de conclusão sem executar comandos.
- Não permitir que agentes escolham silenciosamente novas dependências.
- Revisar segurança, migrações, concorrência e tratamento de dados manualmente.
- Manter commits pequenos para auditoria e reversão.
