# Auditoria profunda da etapa 13 e homologação real

## Objetivo autorizado

Investigar os bloqueios recorrentes de dossiê, corrigir o sistema e conduzir homologação automatizada E2E pela interface com LLM e fontes reais. Preservar análises anteriores e não editar evidências, scores ou referências para fazer a saída passar.

## Diagnóstico

O contrato relacional do dossiê era descrito apenas no prompt. O modelo podia retornar referências vazias, claims sem seção e outra estrutura inválida. Erros de parsing anteriores ao verificador não consumiam a única revisão de forma auditável.

Os fatos citáveis eram assimétricos. Score e suas definições eram entregues ao redator como valores e instruções, mas a fonte enviada ao julgador não incluía integralmente a natureza experimental e o significado dos índices. O IPD estava nos pilares, enquanto a fonte histórica ainda exportava nomes de features antigos. A revisão precisava deduzir referências adequadas e podia piorar uma estrutura antes válida.

O diagnóstico semântico parava no primeiro problema e não identificava claim/bloco estável, referências, resultado e confiança. Testes anteriores usavam principalmente fakes coerentes com o próprio verificador; não comprovavam o comportamento da LLM real sobre o contrato completo.

## Implementação

1. Uma fonte canônica citável para scoring, valores e definições, compartilhada por geração, verificação numérica e semântica e incluída no hash.
2. Fonte histórica exporta explicitamente o IPD calculado, confiança e escala quando o pilar está presente, além de natureza sintética e comparáveis.
3. JSON Schema estrito no transporte oficial de Chat Completions/Responses: referências existentes e não vazias, três seções e limites de blocos; validação factual posterior permanece obrigatória.
4. Diagnóstico por alvo estável, referências, resultado, confiança e revisão pendente. Reunir problemas dos alvos, até quarenta, para orientar uma única revisão.
5. Erro de geração por contrato entra nessa mesma revisão limitada; preservar rascunho e diagnóstico, sem fabricar referências nem reclassificar números inválidos.

## Verificação

- Regressões de paridade factual, IPD, schema e payload Responses, geração inválida inicial/revisada, indisponibilidade, referências órfãs e preservação de fatos.
- Auditoria com LLM real sobre fatos da análise que falhou, somente leitura e sem publicação; armazenar fatos, rascunho, verificação e resultado em `var/diagnostics`.
- E2E novo pela interface: upload DOCX original, Extensão, EAD síncrono, um mês, 12 parcelas de R$ 100; acompanhamento até quinze checkpoints, abertura do dossiê, inspeção de referências, reload e screenshot.
- Relatar separadamente coleta parcial, execução concluída, recomendação e homologação. Evidência insuficiente é um resultado legítimo; não significa falha do software.

## Preservação

As análises f92b1f4a, 1b903741 e ba806630 permanecem como evidência da falha. A auditoria isolada não publica dossiê nem altera seus registros. A execução E2E cria uma nova análise pelo formulário público e usa orçamento/configuração existentes. Nenhum gate é desativado.
