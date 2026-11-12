# Operação planejada: Codex CLI + Scrapling

**Data:** 12/11/2026. **Status:** runbook para implementação futura. Não executar como receita de instalação da versão atual. Ver [fases](../implementation/codex-scrapling/README.md) e [ADR](../architecture/adr/0012-codex-cli-and-provider-neutral-collection.md).

## Configurações propostas, ainda não suportadas

Os nomes abaixo são alvos para desenvolvimento, não variáveis já reconhecidas. A implementação deve acrescentar validação, UI e snapshot antes do uso. Não editar `.env` de produção com esses valores nesta fase documental.

| Configuração proposta | Semântica |
|---|---|
| `GEN_LLM_PROVIDER=codex_cli` | Novo runtime CLI; `codex`/`chatgpt_oauth` preservam comportamento atual |
| `WEB_CRAWLER_PROVIDER=apify|scrapling` | Provider de páginas de curso; outras capabilities continuam Apify |
| `CODEX_TOOL_MODE=disabled|research` | Transporte sem ferramentas para spike versus ferramentas internas autorizadas |
| `CODEX_RUNTIME_CONFIG_PATH` | Configuração versionada própria do serviço |
| `CODEX_AUTH_ROOT` | Volume privado de autenticação administrado no runner |
| `RESEARCH_ARTIFACT_ROOT` | Acervo privado segregado por instituição/análise |
| `SCRAPLING_SERVICE_URL` | Serviço interno autenticado, sem exposição pública por padrão |

Modelo, versão do CLI, browser, biblioteca e skills devem ser registrados no snapshot; valores concretos são escolhidos após verificar compatibilidade no início de CS-02/CS-03. Não usar `latest` como pin de homologação. O default anterior permanece até CS-06.

## Provisionamento

1. Construir serviços dedicados, sem montar código de produção como diretório gravável do agente. Workspace de execução contém apenas contexto autorizado e saídas da análise.
2. Provisionar autenticação CLI pelo mecanismo suportado para a conta e ambiente; testar expiração/renovação. Não copiar token do app HTTP como se fosse credencial CLI equivalente. Proteger a conta técnica, seu acesso e volume.
3. Configurar MCP/gateway interno com identidade e escopo por invocação. Token Apify fica no executor backend, salvo necessidade justificada de outra arquitetura; MCP externo não pode abrir uma segunda via paga sem auditoria.
4. Empacotar as skills do projeto e permitir somente ferramentas da etapa. Configuração pessoal do desktop não deve interferir no runner.
5. Provisionar Scrapling/browser com RAM/CPU e concorrência medidas. Paralelismo de browser não precisa acompanhar o paralelismo de Actors; iniciar ensaio controlado e ajustar por dados.
6. Provar healthchecks locais e preflight de autenticação/modelo/ferramentas. Healthcheck não dispara inferência paga ou Actor a cada intervalo; preflight funcional é distinto da verificação de processo.

## Migração aditiva

Fazer backup e capturar hashes de histórico/dossiês antes de migrations. Inspecionar heads existentes; usar próximo número disponível. Adicionar campos de provider/artefato/sessão e leitor compatível, preservando `dataset_archive` v1 e metadados de Actor. Não converter análises antigas nem preencher lacunas com dados sintéticos novos.

Ensaiar em cópia do PostgreSQL. Manter uma versão de aplicação compatível com o schema aditivo para rollback; não depender de downgrade destrutivo da base. Evitar migração que copie todo o acervo JSON em uma transação gigante.

## Ativação gradual

1. **Replay sem coleta:** comparar interpretação do CLI com o mesmo corpus, sem novos Actors.
2. **Canário com provider explícito:** criar nova análise com snapshot Codex/Scrapling. Preservar todas as anteriores.
3. **Homologação completa:** cumprir CS-06 e abrir o CMS após reload, com inspeção de evidências.
4. **Novo default:** alterar somente após aceite documentado dos gates; registrar commit, hora, instituição, versão e operador responsável. Reiniciar apenas serviços necessários e confirmar que jobs existentes mantêm seus snapshots.

Não afirmar economia com base em tarifa Apify isolada: registrar LLM, custo observado de Actors, proxy, duração e consumo de runner/browser quando disponíveis. Autenticação CLI não remove limites de conta.

## Falhas e reversão

| Situação | Ação esperada |
|---|---|
| Quota/autenticação CLI indisponível | Impedir novas compras para a análise afetada; registrar diagnóstico e estado retomável; não trocar modelo em silêncio |
| Runner cai ou perde lease | Cancelar processo/operações filhas, preservar artefatos e retomar somente com nova posse válida |
| Browser cai | Fechar recursos órfãos e reabrir sessão compatível; conservar tarefa/tentativas e acervo já adquirido |
| Apify tem run incerta | Inspecionar/reconciliar a mesma identidade, sem recompra cega |
| CMS rejeita conteúdo | Persistir rascunho e diagnóstico privado, revisar pelos gates existentes; nenhuma publicação forçada |
| Regressão após ativação | Reverter default para provider anterior compatível nas análises novas e suspender admissão afetada; manter evidências e schema aditivo |

Uma análise iniciada em Codex não pode ser continuada automaticamente pelo cliente HTTP anterior. Se precisar de mudança de runtime, criar reanálise explícita com snapshot e vínculo próprios. Reversão não apaga a análise problemática ou reescreve seus scores. Restore completo só ocorre quando necessário, com procedimento de backup/recuperação existente e ensaio prévio.

## Evidências de operação

Registrar status de invocações, ferramenta/tarefa/tentativa, razão de recuperação, páginas adquiridas, omissões, partes lidas, evidências admitidas e fontes usadas por módulo. Separar evento JSONL interno do progresso público: segredos e payloads originais não entram na UI. Referências e conteúdo higienizado continuam acessíveis mediante autorização.

Ao terminar cada marco, gerar relatório em `docs/implementation/reports/` e atualizar seu status real. Não publicar logs sensíveis, cookies, credenciais, dumps ou corpus privado no Git.
