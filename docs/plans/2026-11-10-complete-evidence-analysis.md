# Análise integral das evidências e eficácia do dossiê — 10/11/2026

## Objetivo autorizado

Priorizar eficácia e qualidade analítica sobre latência. Todos os registros retornados pelos Actors devem ser recuperados e preservados; todo conteúdo higienizado deve chegar à análise responsável, sem perda silenciosa na paginação, normalização ou orçamento de contexto. A síntese pode reunir fatos extraídos e referenciados em vez de repetir o corpus inteiro numa única chamada. Cada fato precisa permitir voltar ao registro e campo originais.

O produto investiga viabilidade favorável ou desfavorável com os mesmos critérios. Falha operacional e ausência de observação não equivalem a demanda zero. O histórico sintético ENS e os dossiês publicados permanecem preservados.

## Diagnóstico inicial

- O cliente limita a leitura do dataset por `call.max_items`, mesmo quando o Actor produziu mais registros.
- A normalização aplica novos limites e seleciona campos/filhos; alguns dados permanecem apenas no fornecedor.
- O projetor tipado tem orçamento de 14.000 caracteres e pode omitir conteúdo, registrando parte dessas omissões. Essa informação não equivale a análise do trecho omitido.
- O julgamento curricular não recebe diretamente `modules` quando não existe `curriculum` textual.
- A execução anterior de Trends sofreu timeouts de widgets e pressão de memória; três retentativas receberam 512 MB. Troca de plano da conta não aumenta automaticamente memória por run.

## Execução

1. Testar `data_xplorer/google-trends-fast-scraper` com build e schema verificados, modo keyword, Brasil e termos da proposta; executar sequencialmente. Persistir datasets completos, diagnósticos e custo. Validar a transformação de `timeline_data` antes de promover o Actor ao catálogo.
2. Corrigir paginação e retenção da coleta com TDD: ler todo o dataset produzido, preservar registros originais e metadados de origem, contabilizar duplicatas/diagnósticos explicitamente e impedir sucesso falsamente integral. Os limites de pesquisa ficam no input do Actor; não descartam sua saída já produzida.
3. Criar leitura semântica integral em partes com TDD: partes determinísticas e hashes/pointers, análise de cada parte com checkpoint, validação das respostas e consolidação rastreável. O cache deve incluir corpus, particionamento, modelo e prompt. Falha no meio não confirma cobertura completa.
4. Integrar essa leitura à qualificação; manter decisões por uso e distinção entre fato, contexto, contraprova e diagnóstico. A ausência de uma finalidade não apaga o conteúdo analisado.
5. Conectar módulos estruturados integralmente ao julgamento curricular e às comparações internas. Não reduzir critérios de confiança para preencher um card.
6. Expor contagens conciliadas (produzidos, recuperados, preservados, analisados, usados por pilar), justificativas e lacunas na API/dossiê. Bloquear indicação de leitura integral se qualquer parte estiver pendente.
7. Executar regressões, suíte completa apropriada, lint/tipagem/documentação e canário real controlado. Somente então atualizar o runtime e registrar limites restantes de coleta, scoring e apresentação.

## Contrato de entrega

- Contagem recuperada reconciliada com o dataset remoto terminal; mudanças durante paginação exigem reconciliação.
- Nenhum campo de conteúdo omitido por orçamento pode ser declarado analisado.
- Conteúdo web continua sendo dado não confiável; higienização protege segredos/dados pessoais e não concede autorização a instruções externas.
- Partes analisadas têm resultado persistido; a retomada não repete partes compatíveis já concluídas.
- O HTML representa o mesmo artefato factual verificado e distingue nota, confiança, suficiência, lacuna operacional e decisão de lançamento.
- Concluir o workflow técnico não substitui suficiência dos cinco pilares externos. Recuperação procura evidência adicional e alternativas homologadas; indisponibilidade persistente mantém análise pendente, sem fabricar nota.

## Estado

Em implementação. Plano registra o escopo autorizado nesta conversa; não representa homologação concluída.

Em 11/11, a integração passou a incluir as correções encontradas na revisão do CMS e da retomada de datasets. O canário real de Trends concluiu quatro consultas e leitura validada de 452 fragmentos. Resultados, preservação e limites estão no [relatório de validação](../implementation/reports/integral-evidence-cms-validation-2026-11-11.md). Suficiência dos cinco pilares externos continua sendo um critério separado de aceitação.
