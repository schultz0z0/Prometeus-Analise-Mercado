# Política da LLM generativa

## Usos permitidos

IDs e vínculos de claims são restringidos por enum no schema de geração, incluindo prós/contras. Na revisão, o enum usa os IDs existentes no rascunho; o código não resolve referências por aproximação. A existência e a consistência dos vínculos continuam verificadas antes da publicação.

Esta política descreve a redação generativa. Pelo [ADR-0008](../architecture/adr/0008-ai-runtime-and-chatgpt-oauth.md), a LLM tradicional também faz entendimento e planejamento nos dois modos e executa julgamentos semânticos tipados no modo `traditional`; no modo `hybrid`, esses julgamentos cabem ao JEV. Notas semânticas delimitadas são entradas validadas do motor analítico, não autorização para a LLM calcular o score consolidado.

- gerar candidatos de palavras-chave;
- redigir resumo executivo;
- explicar riscos e oportunidades;
- propor ajustes curriculares;
- sugerir naming, posicionamento e ganchos;
- produzir perguntas de esclarecimento a partir de lacunas estruturadas.

## Usos proibidos

- calcular ou alterar scores consolidados, fórmulas financeiras ou recomendações definidas em código;
- inventar fontes, números ou concorrentes;
- decidir permissões ou aprovação final;
- executar instruções encontradas em páginas ou comentários;
- afirmar conformidade legal ou regulatória sem revisão qualificada;
- transformar ausência de evidência em evidência negativa.

## Contrato de entrada

A LLM recebe um `DossierFacts` com IDs de evidência, métricas, limitações e seções solicitadas. Dados coletados são delimitados como conteúdo e nunca inseridos como instrução.

## Contrato de saída

JSON estruturado com claims vinculadas a `evidence_ids`. Claims quantitativas passam por verificação exata; claims sem suporte são removidas ou enviadas para revisão.

Desde o contrato de apresentação v2, números e URLs são verificados em todos os tipos de claim e em todo texto visível, inclusive resumo, títulos, seções, critérios e ações. Alterar uma claim para qualitativa não contorna o gate. O cliente não fabrica referências, não acrescenta `scoring_result` para encobrir falta de suporte e não reclassifica números inválidos.

No workflow principal, um segundo gate usa `evidence-support-v1` no motor ativo para avaliar suporte semântico de claims e blocos. Ele é um julgamento experimental sujeito a erro; não transforma existência de um ID em prova. Conteúdo sem suporte, baixa confiança ou certeza exagerada impede a publicação. A verificação determinística continua obrigatória.

Uma rejeição determinística ou semântica permite **uma única revisão de redação** pela LLM: no máximo duas gerações do dossiê. O diagnóstico é persistido antes dessa chamada. A revisão recebe cópias dos mesmos fatos, do rascunho recusado e do relatório, com conteúdo delimitado como dado não confiável; não coleta novas fontes nem altera scores, recomendação ou evidências. O novo texto passa novamente pelos dois gates. Se continuar inválido ou a revisão falhar, a publicação permanece bloqueada, com diagnóstico preservado. Não há fallback para um dossiê fabricado ou aprovação por esgotamento de tentativas. Esta recuperação não inicia ou retoma automaticamente análises já bloqueadas.

O pack `evidence-support-v1` 1.1.0 distingue descrição fiel de um registro e comprovação externa de mercado. É permitido afirmar quantos cursos sintéticos foram comparados quando quantidade, família, período e natureza estão nos fatos citados; esses mesmos dados não comprovam demanda ou conversão real. A comparação histórica expõe esses campos de forma estruturada. A proposta expõe o total calculado em código a partir de parcela e quantidade explícitas, sem usar duração acadêmica para completar parcelamento. O verificador reconhece unidades compactas como `16h` e não usa booleanos como autorização para números.

O contrato citável v3 elimina entradas assimétricas: `scoring_result` é um item canônico com valores, recomendação, natureza experimental e definições metodológicas, entregue igualmente à redação e ao julgador. O IPD está na fonte histórica citável, além do pilar calculado. JSON Schema estrito limita a saída da API às fontes existentes e exige referências não vazias; relações entre claims e seções continuam sendo validadas localmente. Diagnósticos semânticos incluem alvo estável, fontes, resultado e confiança e reúnem os problemas dentro do limite de quarenta alvos por geração. Uma saída que viole o contrato recebe a mesma única revisão, nunca tentativas adicionais por ter falhado antes do parsing. Rascunhos recusados ficam na auditoria da análise, sem publicação como dossiê ou impressão em logs gerais.

Os textos usam linguagem executiva em português. Identificadores, nomes de variáveis e enums são proibidos nos campos visíveis da saída v2, mantendo-os apenas nas referências e metadados. Critérios gerados são pendentes, ações são propostas e nenhuma meta, preço, módulo ou concorrente pode ser inventado para preencher um bloco visual.

## Portabilidade

O provedor é um adaptador. Modelo e parâmetros ficam em configuração. Mudança de modelo exige conjunto de avaliação e comparação antes de produção.
