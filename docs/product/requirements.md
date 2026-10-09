# Requisitos

## Funcionais

| ID | Requisito | Prioridade |
|---|---|---|
| RF-001 | Criar análise a partir de proposta canônica | Obrigatório |
| RF-002 | Validar prontidão estrutural e semântica | Obrigatório |
| RF-003 | Consultar histórico por adaptador institucional | Obrigatório |
| RF-004 | Coletar fontes externas habilitadas | Obrigatório |
| RF-005 | Executar decision packs JEV versionados | Obrigatório |
| RF-006 | Calcular score, confiança e cobertura em código | Obrigatório |
| RF-007 | Produzir dossiê com evidências | Obrigatório |
| RF-008 | Expor REST, MCP e webhook | Obrigatório |
| RF-009 | Registrar feedback e decisão humana | Obrigatório |
| RF-010 | Reexecutar análise sem sobrescrever a anterior | Obrigatório |
| RF-011 | Configurar instituição sem fork de código | Obrigatório |
| RF-012 | Exportar dossiê estruturado | Importante |
| RF-013 | Associar resultados reais e rodar backtests | Obrigatório antes da produção plena |

## Não funcionais

| ID | Requisito |
|---|---|
| RNF-001 | Deployment isolado por instituição |
| RNF-002 | Operação por Docker Compose em VPS |
| RNF-003 | Jobs reiniciáveis e idempotentes |
| RNF-004 | Autenticação máquina-a-máquina e autorização por escopo |
| RNF-005 | Logs estruturados e sem dados pessoais desnecessários |
| RNF-006 | Snapshots imutáveis de fórmulas e decisões |
| RNF-007 | Timeouts, retries, circuit breakers e rate limits |
| RNF-008 | Backup criptografado e restore testado |
| RNF-009 | Contratos versionados e compatibilidade controlada |
| RNF-010 | Métricas de custo, latência, erro, confiança e cobertura |

## Critério de interpretação

Termos como “demanda comprovada”, “zero risco” e “garantia de sucesso” são proibidos. O produto comunica evidência observada, proxy utilizado, confiança e limitações.
