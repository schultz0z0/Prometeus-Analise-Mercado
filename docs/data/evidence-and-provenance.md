# Evidências e proveniência

## Regra central

Nenhuma claim quantitativa ou recomendação crítica pode existir sem `evidence_ids` ou sem ser marcada explicitamente como hipótese.

## Metadados mínimos

- fornecedor e conector;
- consulta normalizada;
- URL/ID quando permitido;
- data e hora;
- período representado;
- região e idioma;
- quantidade bruta e válida;
- método de deduplicação;
- hash do conteúdo;
- termos/licença conhecidos;
- limitações e qualidade.

## Snapshots

O título resumido da evidência respeita 256 caracteres após a higienização: marcadores de ocultação podem expandir o texto. Esse limite não corta o conteúdo completo armazenado no payload original e higienizado. Erros de flush são revertidos antes do registro de falha do workflow para evitar progresso falsamente ativo.

Quando permitido, o sistema guarda o conteúdo mínimo necessário para reprodução. Caso os termos proíbam retenção, guarda referência, transformação, hash e resultado derivado permitido.

## Claims

Cada claim contém tipo, texto, evidências, nível de suporte e escopo. O validador compara números do texto com fatos estruturados.

## Linguagem

- “observamos” para dados diretos;
- “sugere” para proxies;
- “hipótese” para geração estratégica;
- nunca “comprova demanda” apenas por anúncios, busca ou comentários.
