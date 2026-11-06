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

## Conteúdo e comparabilidade de ofertas

O projetor `typed-projection-v3` leva corpo da página e descrição/snippet ao julgamento como dados não confiáveis, com pointers de origem. `page_text`, `description` e `syllabus` são distintos: texto de notícia não vira ementa. O orçamento de contexto limita também esses campos e registra omissões. Mudança do projetor invalida qualificações baseadas em conteúdo incompleto.

A qualificação v4 separa sinal publicitário de oferta individual confirmada. Anúncio pertinente pode contar como publicidade sem comprovar curso concorrente. Notícia, homepage institucional, conteúdo próprio e Radar Setorial não se tornam ofertas externas confirmadas.

Para Meta Ads, `ad-observation-v2` e `ad-projection-v2` preservam `ad_archive_id`, texto/título/link aninhados em `snapshot` e criativos individuais de carrossel, com pointers. Conteúdo longo é reduzido com diagnóstico e preservação de trecho útil; não se elimina o único card apenas por ser longo. A subversão invalida somente julgamentos de `PAID_COMPETITION`, preservando o cache de outros tipos de evidência.

Relação direta ou adjacente exige identidade da oferta, pertinência temática e categoria educacional observada. Mesma categoria pode ser direta; categoria diferente e tema compatível pode ser adjacente. A categoria da instituição e a carga horária isolada não decidem essa relação. Oferta real com categoria ausente permanece no benchmark com relação `unclassified`, sem inventar categoria ou preço.

Recuperação e fatos do dossiê usam a mesma admissão de oferta qualificada. Contexto não impede buscas complementares por ser marcado acidentalmente como adjacente. Ao fundir registros da mesma formação/URL, preservam-se evidências e atributos observados mais completos da página validada.

## Claims

Cada claim contém tipo, texto, evidências, nível de suporte e escopo. O validador compara números do texto com fatos estruturados.

## Linguagem

- “observamos” para dados diretos;
- “sugere” para proxies;
- “hipótese” para geração estratégica;
- nunca “comprova demanda” apenas por anúncios, busca ou comentários.
