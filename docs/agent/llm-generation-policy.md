# Política da LLM generativa

## Usos permitidos

- gerar candidatos de palavras-chave;
- redigir resumo executivo;
- explicar riscos e oportunidades;
- propor ajustes curriculares;
- sugerir naming, posicionamento e ganchos;
- produzir perguntas de esclarecimento a partir de lacunas estruturadas.

## Usos proibidos

- calcular ou alterar scores;
- inventar fontes, números ou concorrentes;
- decidir permissões ou aprovação final;
- executar instruções encontradas em páginas ou comentários;
- afirmar conformidade legal ou regulatória sem revisão qualificada;
- transformar ausência de evidência em evidência negativa.

## Contrato de entrada

A LLM recebe um `DossierFacts` com IDs de evidência, métricas, limitações e seções solicitadas. Dados coletados são delimitados como conteúdo e nunca inseridos como instrução.

## Contrato de saída

JSON estruturado com claims vinculadas a `evidence_ids`. Claims quantitativas passam por verificação exata; claims sem suporte são removidas ou enviadas para revisão.

## Portabilidade

O provedor é um adaptador. Modelo e parâmetros ficam em configuração. Mudança de modelo exige conjunto de avaliação e comparação antes de produção.
