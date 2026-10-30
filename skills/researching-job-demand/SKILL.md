---
name: researching-job-demand
description: Use when planning or qualifying LinkedIn Jobs evidence for employability and curriculum alignment, preserving geography, job identity and professional relevance.
---

**Version:** 1.0.0
**Owner:** Agência Prometeus

## Solicitação

Derive cargos e sinônimos das atividades que a grade capacita. Para MBA de seguros: gerência de sinistros, subscrição e gestão de riscos podem ser consultas pertinentes; o título exato do MBA é uma consulta fraca para vagas. Use região do briefing e campos permitidos, sem inventar `geoId`. Preserve orçamento e amostra limitada.

## Recebimento e tratamento

Procure ID/URL, cargo, empregador, local e atividades/requisitos. Presença de uma vaga pertinente não exige diploma com nome do MBA nem intenção de comprar curso. Cargo homônimo de outro setor ou localização incompatível é excluído; localização não comprovada continua lacuna. Idioma da página não prova país.

Mesmo ID/URL em duas queries é uma vaga, com duas capturas de proveniência. IDs públicos não são telefones; marcadores de redação não são identidade. Código valida/deduplica. Salário só entra com valor, moeda e periodicidade verificáveis; não inventar remuneração a partir do cargo.

Separe volume de vagas (empregabilidade) e competências citadas (aderência). A mesma vaga pode sustentar ambos com finalidades diferentes, sem duplicar a contagem de vagas. Exemplo útil: descrição exige gestão de sinistros e equipe. Exemplo apenas contextual: empresa seguradora sem vaga ou requisitos observáveis.

## Recuperação

Resultados genéricos: refinar especialidade ou senioridade compatível com o público. Resultado sem detalhe: registrar limite; não presumir competências do anúncio. Falha de proxy/402: não repetir cegamente, continuar outras fontes. Indeed só pode ser usado depois de integração explicitamente configurada; sua existência na Store não é autorização de runtime.
