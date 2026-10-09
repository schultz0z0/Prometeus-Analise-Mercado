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
