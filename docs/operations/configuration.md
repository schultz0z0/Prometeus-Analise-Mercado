# Configuração

## Evolução planejada — 12/11/2026

O [runbook Codex CLI + Scrapling](codex-scrapling-rollout.md) especifica configurações **futuras**, provisionamento, credenciais, migração e reversão. `codex_cli`, seleção de provider de crawler e demais nomes ali propostos ainda não devem ser tratados como opções funcionais. Os providers/configurações existentes continuam vigentes até implementação e gates CS. O alias `codex` atual não deve ganhar significado novo silenciosamente.

## Controle de acesso e recuperação — 04/11/2026

Consulte o [guia das correções](audit-remediation.md) para `SERVICE_API_KEYS`, bootstrap em `AUTH_ADMIN_KEY_PATH`, sessão do navegador, `WEBHOOK_SECRET`, `WEBHOOK_TARGET_URL`, `API_BIND_HOST` e scheduler. O acesso ao Prometeus é independente do ChatGPT OAuth de inferência. A migração atual é `0013_workflow_reliability`; não há reset da base sintética ENS. A exigência de modelo JEV pinado só se aplica quando o motor JEV estiver selecionado.

O healthcheck do worker consulta somente o próprio nó Celery, usando seu hostname, com espera de resposta de dois segundos e limite externo de vinte segundos para acomodar a inicialização do comando Python no Docker Desktop. Uma resposta ausente continua resultando em falha; não existe fallback de sucesso. O período inicial de quarenta segundos acomoda o início dos processos.

## Homologação local com LLM tradicional

Para a homologação iniciada em 2026-10-28, o `.env` local está em `AI_MODE=traditional`. Esse modo mantém todos os julgamentos na LLM mesmo se houver chave JEV configurada. O campo `is_jev_configured` informa presença de credencial; `jev_enabled` e `ai_mode` informam ativação efetiva. Alterar para `auto` ou `hybrid` deve ser uma escolha explícita quando o teste de JEV for iniciado.

## Scoring de novas análises

O padrão de `SCORING_PROFILE_PATH` e dos serviços Compose é `config/scoring/portfolio-v2.yaml`. A configuração é congelada na criação da análise; trocar o padrão não recalcula análises concluídas. O perfil anterior continua disponível para reproduzir snapshots. A migração `0010_historical_ipd_metadata` deve estar aplicada antes de usar o novo histórico; API aplica as migrações quando `AUTO_MIGRATE=true`.

## Camadas

1. Valores seguros no código.
2. Arquivo institucional versionado, sem segredos.
3. Variáveis de ambiente.
4. Segredos montados pelo deployment.

## Validação de startup

O serviço deve falhar antes de aceitar tráfego quando:

- configuração institucional estiver inválida;
- perfil de score não fechar 100%;
- segredo obrigatório estiver ausente;
- ambiente de produção usar `jev-latest`;
- endpoints inseguros forem configurados;
- schema ou versão não forem suportados.

## White-label

`config/tenants/<institution>.yaml` define identidade, locale, modalidades, features, fontes, callbacks, referências para perfis e o bloco opcional `ecosystem`. Não contém tokens.

### Ecossistema institucional e Radar Setorial Permanente

O bloco `ecosystem` em `config/tenants/<institution>.yaml` separa explicitamente dois papéis de mercado e é congelado no snapshot de cada análise (`proposal_data["_institution_context"]`):

- `competitors`: instituições educacionais concorrentes (ex.: Conhecer Seguros, FGV, Ibmec, FIPECAFI, FIA, Insper, Estácio, ESA OAB-SP, FIAP e Alura na ENS), usadas para varredura comparativa de oferta, modalidade, carga horária, ementa e preço;
- `sector_radar`: empresas empregadoras e formadoras de demanda do setor (ex.: as 10 seguradoras do Radar Setorial Permanente da ENS — Porto Seguro, Bradesco Seguros, Tokio Marine, Allianz, HDI, MAPFRE, Brasilseg/BB, Zurich, Itaú Seguros e Yelum), monitoradas para tendências de produto, sinistros e dores de corretores, **jamais** contabilizadas como concorrência educacional direta nem incluídas em `reference_mean_price_brl`;
- `radar_ttl_hours` (padrão `168`) e `allow_extra_intake_competitors` (padrão `true`): controlam a validade do snapshot persistido na tabela `sector_radar_snapshots` (migração `0012_sector_radar_snapshots`) e a oferta de campo opcional extra no formulário de intake. Perfis sociais não confirmados permanecem `null` e perfis corporativos globais recebem `linkedin_scope: global`.

A operação pode consultar o catálogo público via `GET /v1/tenants/{tenant_id}/ecosystem` e atualizar o snapshot sob demanda via `POST /v1/tenants/{tenant_id}/sector-radar/refresh` ou `prometeus radar-refresh --tenant ens`. Tenants sem a chave `ecosystem` (ex.: `infnet.example.yaml`) preservam comportamento padrão retrocompatível.

## `.env.example`

O arquivo raiz é um inventário, não deve ser copiado cegamente para produção. Cada deployment precisa de revisão de obrigatoriedade, rotação e armazenamento seguro.

## LLM tradicional

Há dois adaptadores reais:

- `GEN_LLM_PROVIDER=openai`: exige `OPENAI_API_KEY` e usa o contrato tradicional configurado;
- `GEN_LLM_PROVIDER=chatgpt_oauth`: exige conexão pela tela **Continuar com ChatGPT** e usa a cota do plano ChatGPT elegível.

No modo OAuth, não se cola token manualmente. O backend usa callback loopback exato em `http://127.0.0.1:1455/auth/callback`, salva o conjunto rotativo em `CHATGPT_CREDENTIALS_PATH` (padrão `var/chatgpt/credentials.json`) e só exibe “conectado” depois de descobrir modelos e concluir uma inferência real. O diretório `var/` é ignorado pelo Git e montado tanto na API quanto no worker no Compose.

Uma credencial antiga, token de sessão ou autorização sem `chatgpt.tokens.use.direct` não habilita o runtime. O preflight bloqueia a análise antes de iniciar Actors pagos.

### Seleção do modelo ChatGPT

Na tela **Configurações & conectores**, selecione **Plano ChatGPT (OAuth)** e escolha **Modelo da conta ChatGPT**. A lista vem de `GET /v1/auth/chatgpt/models`, que consulta o catálogo real e renova a sessão quando necessário. **Atualizar modelos** refaz essa consulta; não dispara inferência. Sem catálogo válido, a tela conserva a seleção atual e informa a falha sem inventar alternativas.

Ao salvar, o backend valida o modelo contra o catálogo da conta e persiste a seleção tanto nas credenciais compartilhadas quanto em `GEN_LLM_MODEL`. O worker usa o `selected_model` dessas credenciais na próxima construção do cliente; trocar modelo OAuth não exige nova autorização. Preferências de modelo da API ficam separadas na interface. Tokens nunca são devolvidos pelo endpoint de modelos.

O nível de raciocínio aceita o padrão do modelo ou os valores públicos implementados. Restrições específicas só são aplicadas quando o catálogo fornece `supported_reasoning_efforts`; não se presume que todos os modelos suportem todos os níveis. Alterações de outras variáveis de ambiente, incluindo nível de raciocínio, provedor e credenciais de API, exigem recriar o worker para processos que já as herdaram no ambiente.

## Modo de decisão

- `AI_MODE=traditional`: LLM tradicional assume os julgamentos semânticos delimitados;
- `AI_MODE=hybrid`: exige `TYPESAFE_API_KEY` e usa JEV nos decision packs;
- `AI_MODE=auto`: usa JEV quando configurado, caso contrário usa a LLM tradicional.

Em todos os modos, cálculos e mudanças de estado são validados em código.

## Apify

`APIFY_TOKEN` e todos os Actors requeridos devem estar configurados com referência `owner/name@build-number`. `latest` é rejeitado. `APIFY_REQUIRED_SOURCES` define as fontes obrigatórias. Novos planos usam `collection-v2`, `spending_mode=monitor_only`, sem teto monetário local nem reserva por chamada; `maxTotalChargeUsd` é omitido. O parâmetro legado `APIFY_MAX_TOTAL_CHARGE_USD_PER_ANALYSIS` não autoriza novos planos e aparece separado nas configurações. O preflight bloqueia antes da coleta se faltar token, Actor ou LLM real.

O catálogo do planejador inclui somente Actors configurados. Quando Trends estiver configurado, o plano inicial inclui sua série mesmo se não for um canal obrigatório. Escopo finito, limites de páginas/itens/tempo e três retentativas controlam a execução. Pesquisa competitiva começa por cada instituição, podendo ampliar até três variantes semânticas; outras lacunas têm uma rodada complementar. Custos provisórios não constituem garantia de gasto máximo. Restrições da conta e defaults remotos permanecem possíveis. Falha terminal ou fonte vazia permite continuar com lacunas explícitas; execução indeterminada impede nova compra da mesma tarefa e exige reconciliação.

`APIFY_DISCOVERY_MCP_ENABLED=true` habilita o apoio opcional por MCP remoto. Requer o extra `apify-mcp` instalado (incluído na imagem Docker); a API de diagnóstico administrativa aceita somente descoberta de Actors e consulta de documentação/schema. Não inicia Actors nem promove automaticamente alternativas ao catálogo. MCP indisponível não impede as coletas pela API.

Na atualização de 2026-10-28, executar `alembic upgrade head` antes de iniciar o código novo; a migração `0009_dossier_presentation` acrescenta uma coluna JSON com valor padrão vazio e preserva os dossiês existentes. Reconstruir as imagens de API e worker inclui a migração nos dois serviços. O piloto local foi atualizado e os resultados antigos não foram recalculados.
