# ADR-0012 — Codex CLI e coleta com múltiplos providers

**Data:** 12/11/2026. **Status:** direção arquitetural aceita para planejamento pelo responsável do produto; implementação e ativação pendentes dos gates CS-00–CS-06. Este ADR registra a arquitetura escolhida, não uma homologação.

## Contexto

A [avaliação de 11/11](../../plans/2026-11-11-codex-cli-scrapling-assessment.md) constatou que o provider `codex` existente chama `ChatGPTPlanGenerativeClient` por HTTP, e que a coleta/recuperação depende de `ApifyExecutionResult`, registry de Actors e testes de tipo `ApifyClient`. O produto precisa usar o harness Codex preservando regras, evidências e o CMS, e avaliar Scrapling para navegação web.

## Decisão

1. Manter o workflow canônico como dono dos 15 checkpoints. Adicionar `codex_cli` como provider explícito da porta generativa; não reinterpretar os aliases existentes `codex` ou `chatgpt_oauth`.
2. Manter `traditional` como modo sem JEV. Codex CLI executa os trabalhos semânticos desse modo; JEV continua opcional conforme ADR-0008. Fórmulas e recomendação continuam em código.
3. Separar a capability `web_crawler` de seu provider. Um roteador interno encaminha solicitações autorizadas ao executor Apify ou Scrapling. A versão inicial conserva Apify nas outras capabilities.
4. Criar contratos neutros para execução, recuperação e artefatos. IDs remotos são opcionais e reais; execução local não deve inventar Actor, dataset ou tarifa Apify. Snapshots legados conservam sua semântica.
5. Dar ao Codex ferramentas internas com escopo imposto pelo backend. As ferramentas utilizam os mesmos casos de uso de coleta e ingestão do workflow, evitando execução duplicada. Uma sessão por contexto autorizado é retomada por ID explícito.
6. Provisionar runner Codex e aquisição Scrapling em serviços isolados e versionados no ambiente do Prometeus. Não depender do CLI, MCPs, browser, credenciais ou skills pessoais do computador do desenvolvedor.
7. Registrar conteúdo e documentos adquiridos no acervo privado antes de reduzi-los para prompts. Apenas a versão higienizada chega ao agente; cobertura é comprovada por manifestos, não por resumos de sessão.
8. Produzir dossiê via contrato canônico e verificadores atuais. O backend monta/hidrata as nove páginas. Escrita incremental futura exige schema e persistência próprios; revisões humanas não são preenchidas pelo agente.
9. Congelar runtime, ferramentas, modelos e versões no snapshot da análise. Novos defaults afetam somente análises novas. Reversão altera o padrão futuro, sem misturar providers na execução existente ou apagar artefatos.

## Alternativas consideradas

| Alternativa | Avaliação |
|---|---|
| Trocar apenas o cliente HTTP por subprocesso CLI | Útil como spike, mas insuficiente para autonomia de pesquisa, ingestão e recuperação |
| CLI com shell irrestrito, token Apify e escrita direta no banco | Não atende isolamento, tentativas, evidências e validação das transições |
| Reescrever todo o workflow em uma sessão Codex | Aumenta custo de migração e perde contratos operacionais já existentes |
| CLI com gateway de ferramentas e backend canônico | Direção adotada; aproveita o harness preservando controles e permite comparação incremental |
| Executar Codex/Scrapling em Actor próprio ou incluir Firecrawl agora | Adiado; não é necessário para testar a hipótese central |

## Consequências e limites

Será necessário atualizar preflight, factory, coletores, recuperação, schema de persistência, cache, configuração do frontend e deployment. O runtime deve suportar streaming de eventos, cancelamento de subprocessos/operações filhas, renovação de credenciais e isolamento de arquivos por instituição/análise.

MCP é transporte de ferramentas; não substitui a API Apify ou o acervo. Skills são instruções versionadas; não concedem permissões nem comprovam qualidade. A interface MCP externa atual do Prometeus não deve ser reutilizada como credencial administrativa do agente interno.

Browser local pode aumentar RAM/CPU/proxy e manutenção; falhas de proteção, indisponibilidade e ausência de dados continuam possíveis. A troca de `web_crawler` não corrige a reconciliação das buscas Google. A [trilha de implementação](../../implementation/codex-scrapling/README.md) começa por esse diagnóstico.

## Relação com decisões existentes

Complementa ADR-0007 (MCP), ADR-0008 (modos de IA) e ADR-0011 (coleta). Preserva ADR-0005 (estado versus recomendação), isolamento institucional e a política sem teto monetário artificial para novas coletas. Mudança de provider não reinicia o contador de até três retentativas diagnosticadas por tarefa.

## Referências

- [Codex não interativo: eventos, schema e retomada](https://learn.chatgpt.com/docs/non-interactive-mode).
- [Scrapling: projeto](https://github.com/d4vinci/Scrapling).
- [Scrapling: MCP e browser](https://scrapling.readthedocs.io/en/latest/ai/mcp-server.html).
- [Contratos propostos](../../integrations/codex-scrapling-contracts.md).
