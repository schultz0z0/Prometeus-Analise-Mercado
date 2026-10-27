# Configuração

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

## Modo de decisão

- `AI_MODE=traditional`: LLM tradicional assume os julgamentos semânticos delimitados;
- `AI_MODE=hybrid`: exige `TYPESAFE_API_KEY` e usa JEV nos decision packs;
- `AI_MODE=auto`: usa JEV quando configurado, caso contrário usa a LLM tradicional.

Em todos os modos, cálculos e mudanças de estado são validados em código.

## Apify

`APIFY_TOKEN` e todos os Actors requeridos devem estar configurados com referência `owner/name@build-number`. `latest` é rejeitado. `APIFY_REQUIRED_SOURCES` define as fontes obrigatórias e `APIFY_MAX_TOTAL_CHARGE_USD_PER_ANALYSIS` limita o custo. O preflight bloqueia antes da coleta se faltar token, Actor ou LLM real.
