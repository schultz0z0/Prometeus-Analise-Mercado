# Histórico sintético de homologação ENS

## Escopo e origem

Versão `ens-synthetic-ipd-v2`, ampliada em 2026-10-28 a pedido do usuário. Doze identidades acadêmicas (nome e categoria) foram conferidas em fontes oficiais da ENS. Os demais nomes e todas as grades de teste, públicos, preços, ofertas e indicadores são fictícios. Não representam resultados ou faturamento reais da ENS, nem evidência de mercado externo. As edições 2024–2025 são cenários de teste, não comprovação de que o curso oficial foi oferecido nesses anos.

O catálogo possui 33 cursos: dez na família Pós/MBA, dez de extensão, dez de qualificação técnica e um exemplo de cada categoria Graduação Tecnológica, Imersão Internacional e Certificação Avançada. Cada curso tem uma observação simulada encerrada de 2024 e outra de 2025 (66 registros). Os cinco IDs e números de funil anteriores são preservados; seus metadados e grades foram enriquecidos.

## Categorias e referências acadêmicas

Categoria e família são campos separados. MBA e Pós-Graduação compartilham a família de percentis `pos_mba`, mas preservam categoria específica para comparar preço. Graduação, Imersão, Certificação Avançada e Extensão não viram Pós/MBA por conterem a palavra gestão ou seguros.

| Exemplos conferidos | Categoria | Fonte oficial |
|---|---|---|
| Gestão Avançada de Seguros | MBA | [Notícia da oferta](https://acontece.ens.edu.br/mba-gestao-avancada-de-seguros-abre-inscricoes-para-nova-turma/) |
| Finanças e Seguros | MBA | [Programa](https://prdapi.ens.edu.br/media/course/visual-content/Programa_MBA_Financas_e_Segurosv4.2novo_1.pdf) |
| Gestão Estratégica de Seguros | Pós-Graduação | [Oferta](https://acontece.ens.edu.br/pos-graduacao-capacita-para-gestao-estrategica-em-seguros/) |
| Gestão de Resseguro | Extensão | [Página renderizada](https://ens.edu.br/pos/gestao-de-resseguro) |
| Gestão de Seguros | Graduação Tecnológica | [Programa](https://prdapi.ens.edu.br/media/course/visual-content/Programa_CST_Gestao_de_Seguros_2025.pdf) |
| Risk Management and Innovation | Imersão Internacional | [Oferta](https://acontece.ens.edu.br/ens-anuncia-treinamento-inedito-em-connecticut-nova-iorque/) |
| Seguro de RC Produtos e Operações Completadas | Certificação Avançada | [Oferta](https://acontece.ens.edu.br/curso-inedito-capacitara-profissionais-em-rc-produtos-e-operacoes-completadas/) |

A rota `/pos/` não determina categoria: a descrição renderizada atual de Gestão de Resseguro identifica **Extensão**, apesar da rota. Notícias antigas usam outras classificações; foi priorizada a oferta atual. As demais referências estão em `catalog_references.py`, com `checked_at`, URL e lista exata de campos conferidos. Isso não assegura disponibilidade de turma atual.

## Casos cobertos

- Grades com pelo menos quatro módulos, família normalizada, categoria específica e público.
- Leads, inscrições e matrículas coerentes; exemplos fortes, intermediários, fracos, em queda e cancelados, inclusive zero matrícula.
- Tickets declarados em BRL pelo curso completo, sem inferir mensalidade pela duração acadêmica.
- Ofertas encerradas completas e cancelamentos com receita zero/estorno. Matrículas anteriores ao cancelamento não são receita realizada.
- Dez cursos por família como referência do percentil; seleção de até três próximos por tema e grade, preservando categoria específica na comparação de preços.

Os dados não foram escolhidos para aprovar o MBA em teste. Regras e pesos do `portfolio-v2` permanecem iguais. Uma análise ainda pode terminar com evidências insuficientes, baixa confiança ou revisão humana por suas demais fontes.

## Carga e preservação

A sincronização usa o seeder existente com `reset=false`: atualiza os registros da fixture por identificador externo e cria os adicionais, preservando IDs e cursos fora da fixture. A carga não recalcula análises concluídas nem altera evidências externas. Repeti-la não duplica os 33 cursos e 66 ofertas. O botão do portfólio também sincroniza sem reset.

Entradas de API expõem família, grade, metadados de oferta/preço, `is_synthetic`, `dataset_version` e `academic_reference`. `curriculum_origin`, `funnel_origin` e `price_origin` permanecem `synthetic`. O portfólio identifica a base como teste e liga os nomes/categorias verificados à fonte. Os testes isolados verificam integridade, categorias distintas, idempotência e IPD/preço, sem criar análises ou executar LLM/Apify.

## Verificação da carga local em 28/10/2026

Build e atualização de API/worker concluídos. Sincronização local pelo endpoint existente com `reset=false`: cinco cursos atualizados com IDs preservados, 28 criados e 56 novas observações. Total confirmado por banco/API: 33 cursos e 66 observações (58 concluídas, oito canceladas), todos os tickets com unidade total explícita. O estado anterior foi salvo no volume de backups PostgreSQL em `ens_history_before_enrichment_20261028_v2.dump`.

Preservados 12 registros de análise, nove dossiês e 229 evidências externas. O hash do dossiê manual continua `77ddb1276c47f8943709780eda420d1c`. Nenhuma análise nova foi iniciada ou recalculada.

Suíte: 394 testes passaram e um teste opt-in Apify online foi ignorado. Ruff, mypy (69 arquivos) e documentação passaram. No navegador isolado, o portfólio carregou 33 linhas e 12 links de referências acadêmicas, sem erros JavaScript; o viewport de 390 px não apresentou overflow da página. A análise real do MBA com a base ampliada permanece para homologação do usuário.
