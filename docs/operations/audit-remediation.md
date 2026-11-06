# Operação após as correções da auditoria — 04/11/2026

## Escopo

As correções preservam as credenciais ChatGPT OAuth/Apify existentes, o histórico sintético ENS e análises publicadas. Não convertem fixtures em dados reais nem aprovam produção. A homologação manual com a ENS será realizada posteriormente.

## Acesso ao Prometeus

`SERVICE_API_KEYS` aceita uma lista JSON de objetos com `key` (mínimo 24 caracteres, usar segredo aleatório forte), `subject`, `tenant_id` e `role`. Papéis: `reader` consulta, `analyst` também cria análises e outcomes, `director` também registra decisões e `admin` também gerencia configuração. Cada identidade fica restrita à sua instituição. Não versionar chaves nem usar credenciais ChatGPT/Apify como chave da aplicação.

Quando a lista estiver vazia, o backend cria uma chave aleatória privada em `AUTH_ADMIN_KEY_PATH`, padrão `var/auth/admin.key`. O operador autorizado consulta esse arquivo localmente e informa a chave na tela **Entrar no Prometeus**. Ela nunca é retornada pela API. A sessão usa cookie HttpOnly com validade de oito horas; alterar as identidades/chaves revoga as sessões assinadas com a configuração anterior. **Sair** remove o cookie do navegador. Em HTTPS, o cookie é Secure. Mutações por cookie exigem mesma origem. Headers/proxy TLS devem preservar a origem externa e ser configurados apenas para proxies confiáveis.

REST exige `Authorization: Bearer <chave>` ou a sessão. Healthchecks e arquivos estáticos permanecem públicos; dados e administração em `/v1/` são protegidos. O callback OAuth `/auth/callback` continua público para concluir PKCE/state/nonce do fornecedor, mas início/desconexão/listagem de modelos exigem acesso administrativo. O login ChatGPT continua servindo exclusivamente à inferência.

O Compose liga 8000 e 1455 a `127.0.0.1` por padrão. `API_BIND_HOST` permite configurar o bind principal quando a infraestrutura tiver proxy/controle adequados; o callback loopback permanece local. Não publicar a porta direta para contornar o proxy.

## LLM tradicional e ENS

`AI_MODE=traditional` usa a LLM tradicional em todos os julgamentos, planejamento e redação, mesmo que exista configuração JEV. `auto` sem chave JEV também usa essa rota. O modelo selecionado no arquivo OAuth compartilhado é mantido. Não é necessário obter API JEV para esta fase. `hybrid` explícito sem credencial é erro, e não há fallback silencioso após falha de uma execução híbrida.

Sem credencial JEV, a fábrica de comparação shadow mantém apenas o primário tradicional real e desativa a comparação. Não usa respostas simuladas como contraparte. O worker atual usa a rota tradicional em `AI_MODE=shadow`; a homologação e integração da comparação real JEV continuam futuras.

`ALLOW_SYNTHETIC_INSTITUTIONAL_HISTORY=true` e a base sintética ENS permanecem permitidos para teste, com rótulos explícitos. Não executar seed/reset nem substituí-la durante a implantação dessas correções. A validação de modelo JEV em produção só se aplica quando JEV estiver efetivamente selecionado.

## Migração e processos

### Política vigente de coleta — ADR-0011

Para novos snapshots `collection-v2`, a [ADR-0011](../architecture/adr/0011-collection-coverage-and-recovery.md) substitui as reservas monetárias descritas abaixo. Não há teto local de US$ 5 nem limite financeiro por chamada; custos são observados e podem permanecer provisórios. Planos anteriores conservam os limites da ADR-0010 e não são recalculados silenciosamente.

Aplicar também `0014_collection_attempts`, com tabela de tentativas e proveniência por evidência. O backup JSON deriva da metadata e inclui a nova estrutura; backups anteriores à migração devem ser restaurados no esquema correspondente e depois migrados. `pg_dump` completo permanece disponível.

Recuperações aguardam pela outbox, preservando `RUNNING` na análise e `PENDING` no checkpoint. Uma tarefa admite tentativa inicial e até três retentativas; erros permanentes encerram antes. Novos planos e reinícios não zeram o contador. POST ambíguo exige reconciliação da run existente, sem compra repetida; após esgotar a reconciliação a tarefa fica explícita para intervenção. Fontes independentes mantêm seus resultados.

O benchmark usa todas as execuções iniciais e complementares, exibe múltiplas ofertas e distingue pesquisa não iniciada, falha, validação pendente e oferta confirmada. Um dossiê `VERIFIED` pode ter cobertura parcial, que deve aparecer no texto e na tabela.

### Política anterior, preservada nos planos legados

Antes de usar o novo worker, aplicar `alembic upgrade head` com backup completo e processos antigos parados, na janela de implantação. A migração `0013_workflow_reliability` acrescenta revisão otimista, chave de idempotência institucional, `analysis_jobs` e retentativa de webhooks. Registros históricos são preservados; chaves antigas de criação são recuperadas, reanálises antigas não herdam a reserva de criação. Duplicatas técnicas de event_id legadas são desambiguadas sem apagar registros.

O Compose inclui `scheduler` (Celery beat). Executar apenas um beat por deployment. A cada 15 segundos ele agenda reconciliação; o worker publica jobs vencidos e tenta webhook pendente. O scheduler tem healthcheck do próprio processo, e não da API. Falha de broker mantém a outbox pendente, sem depender da conexão HTTP original.

O consumidor possui lease de cinco minutos renovado a cada 30 segundos. Perda do lease interrompe o fluxo e solicita aborto do Actor em andamento quando possível. Cancelamento é confirmado no banco e impede novos checkpoints/julgamentos/coletas; uma chamada externa já realizada pode ter custo incorrido. Esses custos/resultados não são apagados.

Se uma execução externa foi interrompida sem resposta confirmada, sua consulta passa a `IN_DOUBT`, com custo desconhecido explicitado, e a análise bloqueia. Conferir a run/dataset no provedor e seus custos antes de retomar. Não apagar checkpoints ou repetir Actors para resolver esse estado. A reconciliação operacional deve preservar a proveniência e decidir se reutiliza resultado terminal verificado ou autoriza uma nova análise com orçamento próprio. Não existe retentativa automática de compra indeterminada.

Após a homologação real, aplica-se a [ADR-0010](../architecture/adr/0010-remote-budget-commitments.md): cada chamada reserva seu limite antes do POST. A soma dos limites comprometidos em todas as pesquisas da análise, inclusive reparo, respeita o orçamento original. Sucesso e custo observado baixo não liberam a reserva. O custo Apify pode aumentar depois de `SUCCEEDED` e mesmo depois de os contadores de cobrança parecerem alinhados; a interface o identifica como provisório. A autorização padrão por chamada é US$ 0,50, ou limite explícito maior validado em código e subordinado ao saldo. Consultas sem saldo ficam `budget_skipped`, sem inferir ausência de mercado. Runs legadas sem autorização verificável exigem reconciliação antes de novas compras. Falha de transporte após POST, leitura de dataset pago, aborto não confirmado ou cobrança indeterminada preservam a run e bloqueiam continuidade em `IN_DOUBT`; não se inventa custo zero.

Reanálise exige uma **nova** `Idempotency-Key` e cria snapshot próprio, vinculando `previous_analysis_id`. Repetir a chave dessa mesma reanálise recupera o resultado; a chave da criação anterior continua recuperando a análise original.

## MCP e webhook

MCP local: `python -m prometeus.entrypoints.mcp` ou `prometeus-mcp`, iniciado pelo cliente como subprocesso. Usa JSON-RPC em linhas UTF-8 no stdin/stdout e logs no stderr, conforme [transporte oficial](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports). O processo herda a identidade confiável `local-mcp`, restrita a `INSTITUTION_ID`. Não expor esse stdin/stdout por túnel não autenticado. A ferramenta de criação exige `idempotency_key`, grava snapshot e outbox e publica após commit. Não expõe ferramentas de scraping ou scoring de baixo nível.

Webhook requer `WEBHOOK_SECRET` e `WEBHOOK_TARGET_URL`, ou destino HTTPS no snapshot `tenant.webhooks.target_url`; `tenant.webhooks.events` limita os tipos. Sem destino/segredo, a análise funciona por polling e nenhuma assinatura usa segredo padrão. Eventos são persistidos na mesma transação da mudança de estado; o reconciliador tenta entrega com backoff exponencial, até cinco tentativas. `DELIVERED`, `SHADOW_DELIVERED` e `DEAD_LETTER` não são reenviados automaticamente. `SHADOW_MODE=true` registra entrega sem tráfego. Cada tentativa recebe timestamp/assinatura novos e preserva event_id para deduplicação pelo receptor.

## Dossiês e economia

Consulte [simulação econômica](../scoring/economic-simulation.md). O frontend só usa os blocos corrigidos com `presentation.contract_version=2`, preservando síntese/scoring/evidências históricos sem mostrar enriquecimentos antigos como fatos. Não há recálculo silencioso do histórico. Custos, capacidade, taxas e prazos ausentes geram pendência; cenários não estimam demanda ou matrículas.

## Backup e avaliação

O backup JSON formato 2 inclui todas as tabelas mapeadas, em ordem de FKs, e verifica cobertura/contagens/checksum antes de qualquer limpeza. Exportações incompletas formato 1 são recusadas como backup completo; preservá-las como artefatos históricos. No PostgreSQL a exportação exige sessão nova e snapshot Repeatable Read. O `pg_dump` operacional continua um mecanismo completo independente. SHA-256 detecta corrupção, não autentica sozinho um arquivo contra adulteração maliciosa; proteger o armazenamento e restringir acesso.

Os scripts offline de avaliação distinguem simulação de homologação. O runner de decisão não envia gabarito ao modelo e só usa fornecedor real com `--live` explícito. A avaliação real tradicional pode usar o OAuth existente; JEV será avaliado quando houver acesso. Backtest comercial exige resultado-alvo, dados oficiais e corte temporal; os gates vigentes estão em [gates de release](../roadmap/release-gates.md).
