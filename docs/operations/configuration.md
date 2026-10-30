# Configuração

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

`config/tenants/<institution>.yaml` define identidade, locale, modalidades, features, fontes, callbacks e referências para perfis. Não contém tokens.

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

`APIFY_TOKEN` e todos os Actors requeridos devem estar configurados com referência `owner/name@build-number`. `latest` é rejeitado. `APIFY_REQUIRED_SOURCES` define as fontes obrigatórias e `APIFY_MAX_TOTAL_CHARGE_USD_PER_ANALYSIS` limita o custo. O preflight bloqueia antes da coleta se faltar token, Actor ou LLM real.

O catálogo do planejador inclui somente Actors configurados. Quando Trends estiver configurado, o plano inicial inclui sua série mesmo se não for um canal obrigatório. Não há aumento automático do teto: uma rodada complementar, no máximo, usa o orçamento original restante. A análise pode continuar com lacunas explícitas se fontes opcionais falharem; fontes obrigatórias vazias ou indisponíveis mantêm a política de bloqueio.

Na atualização de 2026-10-28, executar `alembic upgrade head` antes de iniciar o código novo; a migração `0009_dossier_presentation` acrescenta uma coluna JSON com valor padrão vazio e preserva os dossiês existentes. Reconstruir as imagens de API e worker inclui a migração nos dois serviços. O piloto local foi atualizado e os resultados antigos não foram recalculados.
