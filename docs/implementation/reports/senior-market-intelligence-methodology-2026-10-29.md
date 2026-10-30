# Auditoria metodológica — inteligência de mercado sênior ENS

Data de consulta: 29/10/2026. Escopo: somente leitura de código, configuração, skills, documentação, exportação dos 144 registros e fontes oficiais públicas. Nenhuma inferência paga, Actor, mudança de estado ou cálculo publicado. As propostas abaixo são critérios a validar com especialistas ENS; não constituem método comercial já calibrado.

## Conclusão

Há uma base razoável de governança (fontes, contratos, calculadora, regras explícitas de comparabilidade, distinção entre observação e hipótese), mas a aplicação ainda mede predominantemente um conjunto experimental de proxies. Não entrega, por contrato, um estudo econômico-financeiro completo ou uma SWOT rastreável. Instruções de mercado existentes são melhores que os resultados do teste; acrescentar prompts e múltiplos agentes sem corrigir a passagem de dados e avaliar as decisões tende a multiplicar as mesmas perdas.

O recorrente `INSUFFICIENT_EVIDENCE` tem ao menos três causas distintas: evidência realmente fraca, dados úteis perdidos antes do julgamento/redação, e desenho de confidence/gates com requisitos que as fontes atuais frequentemente não preenchem. Não atribuir esses três fenômenos a uma inteligência única da LLM, à Apify ou ao mercado. Tampouco otimizar o sistema para produzir mais aprovações.

## Achados de metodologia, com evidências

### M1 — P1 — A recuperação dos dados não basta para passar pelo gate de confiança atual

O perfil `config/scoring/portfolio-v2.yaml:15` exige confidence ≥0,75 e torna `internal_history` e `search_and_media` obrigatórios. A calculadora reduz a confidence pela parcela de componentes observados (`src/prometeus/domain/scoring/calculator.py:43`). Isso mistura completude de features e confiança num escalar sem calibração empírica.

Nos dados atuais:

| Pilar | Feature disponível no teste | Confidence produzida |
|---|---|---:|
| Histórico | IPD sintético e grade | 0,90 |
| Concorrência paga | Só contagem de anúncios | 0,44 = 0,88 × 0,50 |
| Busca, se recuperada | Interesse relativo + crescimento, sem volume mensal | no máximo 0,506 = 0,92 × (0,30+0,25) |
| Empregabilidade | Contagem, sem salário | 0,51 = 0,85 × 0,60 |
| Aderência | Nota sem feature separada de dores cobertas | 0,675 = 0,90 × 0,75 |
| Preço | Só origem interna | 0,50; ambas as origens dão 0,80 |

Cálculo contrafactual de leitura, mantendo as outras features e o perfil do teste: a confidence atual 0,6198 com coverage 0,8 implica contribuição ponderada 0,49584. Adicionar somente Trends com confidence máxima 0,506 elevaria coverage para 1,0 e confidence para aproximadamente 0,5970; continuaria abaixo de 0,75. Trata-se de ilustração dos gates, não recalculação válida ou mudança da análise. Mesmo ambas as origens de preço, sem volume, índice de concorrência, salário e cobertura separada de dores, dão teto aproximado 0,627 para o conjunto dessas premissas. Não é prova de impossibilidade global: outras features/fontes podem mudar o teto.

Referências: `calculator.py:71–118`, `121–168`, `313`; `src/prometeus/application/scoring_service.py:95–158`; `run_course_analysis.py:648–662`; `docs/Estudo_Prometeus_144_registros_73501c53_2026-10-29/dossie_publicado.json`.

Correção de desenho: matriz de alcançabilidade de cada gate por categoria e fontes contratadas, teste de contrafactuais e calibração com decisões humanas e desfechos. Separar completude, qualidade, força/inferência, procedência e incerteza do modelo. Não reduzir arbitrariamente o limiar nem preencher campos faltantes só para obter aprovação.

### M2 — P1 — Score de preço não é viabilidade econômica

`calculator.py:171–200` converte a razão entre preço proposto e referência em uma curva de competitividade. Isso não calcula custos, margem, caixa ou quórum econômico. Receita histórica existe no adaptador, mas não aparece como projeção econômica validada para a nova oferta. Busca no código/configuração por SWOT, CAC, fluxo de caixa, break-even e custos de docência não localizou um contrato/motor correspondente no workflow. A existência de notas financeiras em dados sintéticos ou feedback de receita não implementa esse motor.

É correto o prompt dizer que preço próximo da média não prova margem (`config/prompts/dossier-v1.yaml:39–41`). O problema é a expectativa do produto de viabilidade econômico-financeira sem os dados e contratos que a sustentem. Nomear o resultado atual como índice relativo experimental de atratividade, mantendo uma avaliação econômica separada até sua implementação/calibração.

### M3 — P1 — Concorrência paga recebe sinal positivo mecanicamente

`calculator.py:71–89` faz mais anúncios e maior índice de concorrência elevarem a nota. A própria variável mistura possível validação de atenção/oferta com pressão competitiva e custo de aquisição. É uma hipótese causal não validada. Maior investimento concorrente pode significar oportunidade ou CAC elevado; ausência numa consulta limitada não é ausência de mercado. O resultado atual usou `ad_count=0` de uma consulta vazia, não um censo completo de anunciantes.

Separar intensidade de oferta, diversidade de players, diferenciação, pressão de aquisição e evidência de intenção de alunos. Não simplesmente inverter o sinal da fórmula: fazer sensibilidade e backtest, preservando o perfil antigo.

### M4 — P1 — Referências de demanda continuam muito distantes de matrícula

O processo distingue corretamente vagas de matrículas nos textos das skills, mas os indicadores externos de busca, anúncios, vagas e comentários não observam propensão real a pagar pela formação específica. Uma vaga relevante sustenta necessidades profissionais/ementa; prêmio de seguro ou força de trabalho setorial sustenta contexto econômico; nenhum deles é uma matrícula potencial individual.

O sistema precisa de uma escada explícita de evidências: contexto setorial → necessidade profissional → intenção educacional → qualificação comercial → comportamento/pagamento, com restrições sobre o que cada nível pode concluir. B2B (compra de turmas pelas empresas) e B2C (aluno individual) exigem funis diferentes. A base sintética testa contratos, não essa escada.

### M5 — P2 — Comparabilidade curricular/preço ainda usa heurísticas muito rasas

`internal_history.py:191–204` seleciona os três cursos por sobreposição lexical/Jaccard em título, tags e grade. Não usa, nessa seleção v2, um julgamento atômico por competências verificadas. Termos genéricos podem escolher cursos distantes; sinônimos podem ser perdidos. `pricing_reference.py:91–116` aceita proximidade de tema se houver qualquer token compartilhado, mesmo sem matriz curricular. `_category` em `pricing_reference.py:78–88` cobre MBA, Pós, Extensão, Graduação; categorias solicitadas como Imersão e Certificação Avançada não aparecem como grupos distintos nessa função.

Manter pré-filtros determinísticos por instituição/família; recuperar candidatos por léxico/embeddings como mecanismo de recall; depois classificar tema, competência, público, nível, carga e modalidade em dimensões separadas e justificáveis. Selecionar no máximo três para IPD, sem obrigação de preencher três. Categoria comercial exata continua separada da família estatística. Construir pares gold de mesma categoria/tema e de falsos cognatos.

### M6 — P2 — IPD relativo depende do contexto comercial das ofertas históricas

A fórmula IPD acordada 20% leads/30% inscrições/50% matrículas deve ser preservada como regra ENS. Percentis sobre a mesma família e janela são adequados ao contrato, mas não neutralizam exposição de mídia, verba, duração da captação, canal, esforço comercial, tamanho da base, mudanças de preço e capacidade. Maior volume histórico pode decorrer de maior investimento; IPD não é demanda latente nem previsão de matrículas. O confidence de 0,90 da massa sintética é completude estrutural, não prova real de qualidade comercial.

Acrescentar metadados de oferta, condição de aquisição, real/sintético, cancelamentos e motivos; apresentar volume e taxas lado a lado. Fazer backtest temporal sem vazamento de resultados posteriores ao lançamento. Respeitar a fórmula; revisar interpretação e limites com o autor da apresentação ENS.

### M7 — P2 — Redação e revisão factual não equivalem à revisão de mercado sênior

O contrato do dossiê contém resumo, três seções por público, claims, prós/contras, comparáveis, aderência e ações. Não localizei um objeto SWOT/econômico nem um parecer de adequação de pesquisa, matriz de hipóteses e contrapontos por decisão. Um texto pode ter cada frase sustentada e ainda não responder as perguntas que o comitê precisa decidir. O verificador atual é essencial, mas avalia principalmente suporte/estrutura/números.

Introduzir avaliação anterior à redação: pergunta de decisão, resposta possível, evidência que apoia, evidência que contraria, lacuna residual, impacto da lacuna, próximo teste de maior valor. Depois, um revisor sênior avalia materialidade, representatividade, alternativas e coerência entre achados e recomendação. Redator não corrige dado ausente com texto plausível; revisor não aprova uma análise só porque tem fontes.

### M8 — P2 — Cobertura de pilares é diferente de cobertura de pesquisa

Cinco pilares presentes não mostram se há diversidade de instituições, anúncios independentes, temas curriculares, cargos e regiões. Uma única captura pode tornar o pilar presente; 144 registros podem representar duplicação de entidades e consultas. Reportar entidades únicas, recorte, tamanho de amostra e fração de dados úteis por finalidade, sem inventar denominador de mercado.

## Fontes → perguntas → indicadores → limites

| Fonte/entrada | Pergunta útil | Indicadores plausíveis | Limite metodológico |
|---|---|---|---|
| CRM ENS real por oferta/coorte | Quem compra cursos próximos, em quais condições? | Leads qualificados, inscritos, matriculados, conversão, receita líquida, CAC, cancelamento, prazo de captação | Synthetic só testa; taxas com amostras pequenas e verba distinta precisam de ressalva |
| Catálogo oficial ENS e ementas | Onde a nova oferta se encaixa? Canibaliza/complementa portfólio? | Categoria, público, temas, resultados de aprendizagem, carga, modalidade, coorte | Página pública não revela desempenho nem capacidade; catálogo atual não prova oferta histórica |
| Páginas originais dos concorrentes | Quais ofertas diretas, adjacentes e substitutas existem? | Instituição/curso únicos, categoria, carga, modalidade, currículo, preço total/condição/data | Identidade/currículo podem ser úteis mesmo sem preço; notícia antiga não é condição comercial atual |
| Google Ads/Keyword Planner | Existe busca com intenção educacional no recorte? | Faixas/estimativas de volume, termos específicos, sazonalidade, competição de anúncio, lances | Aproximados; variantes próximas se sobrepõem; não somar sem dedup; forecasts não são alunos ou conversões ENS comprovadas |
| Google Trends | O interesse relativo mudou? Há sazonalidade? | Série comparável por consulta/janela/região, densidade e pontos sem dados | Escala 0–100 é relativa/amostrada, não volume absoluto; não comparar médias de consultas independentes como mercado absoluto |
| Vagas oficiais/LinkedIn/Indeed | Quais atividades e competências aparecem? | Vagas únicas, recência, empregadores, senioridade, skills, salários publicados/cobertura | Amostra limitada, reposts/ghost jobs, cargos adjacentes; não prova intenção de cursar ou empregabilidade do egresso |
| RAIS/Novo Caged/PDET | Há estoque/fluxo formal no setor/ocupação/região? | Estoque anual, admissões/desligamentos/saldo, ocupação/CNAE, remuneração quando disponível | Saldo não é vagas abertas; formal não é total; mudança classificatória/data precisam harmonização |
| SUSEP SES/relatórios | O segmento segurador e suas operações estão mudando? | Produção/segmentos/linhas e trajetória setorial verificável | Não multiplicar crescimento de prêmios em demanda por matrícula; delimitar mercado supervisionado |
| CNseg conjuntura | Quais fatores setoriais/econômicos merecem hipótese de formação? | Tendências setoriais, riscos, cenários identificados | Fonte setorial tem natureza institucional; projeção deve ser atribuída, não adotada como certeza |
| IBGE PNAD/SIDRA | Público, renda e força de trabalho são compatíveis com o recorte? | Escolaridade, ocupação/renda/distribuição regional, tamanho de grupos | Amostral, recortes pequenos frágeis, informalidade; não é lista de leads |
| INEP Censo Superior | Qual contexto de oferta e fluxo de graduação? | Cursos/IES/matrículas/ingressantes/concluintes por recorte disponível | O Censo Superior cobre graduação e sequenciais, não um censo detalhado de todo MBA/extensão; não usar diretamente como procura desses programas |
| Entrevistas/pesquisa primária ENS | Há problema urgente e formação preferida? Quem paga? | Tarefas, dificuldades, alternativas atuais, disponibilidade, orçamento declarado | Intenção declarada sofre viés; amostra não probabilística não permite extrapolação automática |
| Piloto comercial/landing page/empresa parceira | Há conversão real suficiente ao preço/condição? | Contatos elegíveis, comparecimento, inscrição, reserva/pagamento, custo e desistência | Exige autorização e mensuração; resultado condicionado à mensagem/canal/coorte; não executado nesta auditoria |

As páginas oficiais foram consultadas, mas não foi validado acesso automático a todas essas fontes, APIs ou credenciais. Começar por arquivos oficiais/API documentada e importações controladas; depois integrar o que tiver valor comprovado. Não criar dependência de scraper para dado público já estruturado.

## Arquitetura recomendada de funções

Implementar primeiro papéis e contratos, não uma tropa de agentes autônomos. O orquestrador em código permanece dono de orçamento, fontes permitidas, estado, seleção de dados, fórmulas e publicação. Chamadas por especialidade podem ser paralelas quando independentes, sem compartilhar conversa bruta ou perder proveniência.

| Papel | Responsabilidade e saída | Acesso permitido |
|---|---|---|
| Líder de pesquisa educacional | ResearchBrief com decisão, público/comprador, categoria, alternativas, perguntas, hipóteses, critérios de evidência por dimensão, fonte e recorte | Lê briefing/knowledge ENS; propõe plano, não executa livremente |
| Operador de fontes | ToolCallPlan e diagnóstico: pergunta→fonte→input validado→expectativa→run→resultado útil/falha | Apenas ferramentas autorizadas pelo código, budgets e registry |
| Curador/QA de dados | EvidenceRecord canônico com campos tipados e evidência por finalidade, perdas, duplicatas, validade e revisões pendentes | Não emite aprovação; preserva bruto/higienizado e snapshots |
| Analistas especializados | Interno/IPD; concorrência/preço; necessidades/empregabilidade; demanda educacional; cenário setorial e SWOT | Só evidências verificadas da tarefa; saídas estruturadas com citações e limites |
| Analista econômico assistido | Lista premissas e interpreta cenários calculados | Não faz fórmula em LLM/JEV; motor Decimal/determinístico valida inputs e resultados |
| Revisor sênior cético | Evidência favorável/contrária, qualidade de pergunta/resposta, dependências, alternativas, conclusão admissível e plano de validação | Não altera dados/score; pode pedir uma recuperação delimitada ou revisão humana |
| Redator executivo | Transforma parecer e fatos em narrativa e tabelas legíveis para comitê, acadêmico e comercial | Sem acesso a executar tools ou criar métricas |
| Verificador factual | Estrutura, números, fontes, citações, semântica e contradições | Não confundir frase correta com pesquisa suficiente; gate código decide publicação |

Esses são oito contratos lógicos, não necessariamente oito workers/modelos/agentes permanentes. Para reduzir custos, agrupar inicialmente especialistas em três passes de análise com contratos independentes; separar mais somente se a avaliação mostrar ganho. Revisão do mesmo modelo com o mesmo contexto tem erros correlacionados: prompt diferente não prova independência.

O fluxo híbrido troca o executor de julgamentos atômicos delimitados (relevância por finalidade, comparação de competência, suporte de claim), não entrega orquestração, finanças ou redação ao JEV. LLM tradicional continua entendimento/plano/síntese. Os mesmos datasets de avaliação e contratos devem medir ambos; concordância JEV–LLM não substitui referência humana.

## Contratos de análise para nível sênior

### Concorrência e oferta

`OfferIdentity`: instituição, curso, categoria declarada, público, modalidade, carga, calendário, credencial, versão de ementa, URL e trecho. `OfferRelation`: direto/adjacente/substituto, dimensões de compatibilidade e justificativas, não booleano único. `PriceObservation`: moeda, valor total, parcelamento, taxas, desconto/elegibilidade, validade/data, atribuição à oferta e fonte. O preço pode estar pendente enquanto identidade/currículo são válidos. Preservar a média combinada ENS acordada, exibir amostras por origem e sensibilidade a outliers sem trocar a regra silenciosamente.

### Demanda de alunos

`LearnerDemandCase`: problema/formação/comprador e beneficiário; evidências reais do funil; procura educacional explícita; alternativas e barreiras; disposição a pagar declarada versus comportamento; alcance/canais e tempo. Separar mercado potencial, elegível, alcançável e capacidade. Não calcular SOM por simples percentual de trabalhadores ou de prêmios de seguros. Cenários de matrículas são hipóteses de funil, não forecasts validados sem backtest.

### SWOT rastreável e TOWS

Cada item deve ter dimensão interna/externa, evidência/trecho, natureza observado/inferido/hipótese, recorte/data e implicação para decisão. Forças/fraquezas da instituição requerem fatos ENS; reputação, diferencial docente ou infraestrutura não podem ser inventados. Uma grade declarada não prova qualidade de ensino. Oportunidades/ameaças precisam de fonte e condição; relacionar estratégias SO/ST/WO/WT a ações/testes, não a frases genéricas. Lacuna de dado vira pendência de validação, não fraqueza do curso ou ausência do mercado.

### Economia financeira determinística

Coletar e validar: preço total/parcelas, desconto/bolsa, recebimento esperado/inadimplência/estornos, impostos/taxas de processamento, custo docente e coordenação, produção/licenças/material, suporte variável, mídia e esforço comercial, capacidade e custos por degraus, cronograma acadêmico versus financeiro. Classificar cada premissa como observada, informada ENS ou hipótese aprovada.

Acrescentar proveniência por campo: documento original e página/trecho; valor declarado pelo usuário; parâmetro de teste preenchido pelo agente; catálogo oficial; mercado observado; premissa de cenário. No E2E desta extensão, R$100 × 12 e um mês foram parâmetros de teste, não condição comercial oficial validada ENS. Não confundir esse preenchimento, os R$976 × 20 declarados pelo usuário para outro MBA e preços de páginas históricas. A base interna também é sintética: o nome oficial de um curso não torna seus funis/preços simulados reais.

Modelo contábil consistente:

```text
recebimento_líquido_unitário = preço efetivamente realizável − deduções variáveis de receita
margem_antes_aquisição = recebimento_líquido_unitário − custo_variável_entrega_unitário
resultado_turma(N) = N × margem_antes_aquisição − custos_fixos_turma − aquisição_total(N)
```

Se aquisição for linear por matrícula, `aquisição_total(N)=N×CAC`, então `N_equilíbrio=ceil(custos_fixos/(margem_antes_aquisição−CAC))`, somente quando o denominador é positivo. Se a mídia for um orçamento fixo, tratá-la como custo fixo de cenário; não subtrair o orçamento inteiro e um CAC derivado dele novamente. Comparar equilíbrio com capacidade; margem não positiva ou equilíbrio acima da capacidade são resultados relevantes, não erro matemático.

Fluxo mensal separa recebimentos, pagamentos, prazo de parcelas e duração acadêmica. NPV/payback só com cronograma, política e taxa informados; cenários conservador/base/otimista devem ter premissas e sensibilidade, sem atribuir probabilidades inventadas. Nada disso substitui a validação de mercado. Falta de custo deve resultar em economia não calculável, não retorno fabricado.

## Avaliação e gates propostos

Os números abaixo são propostas iniciais para acordo ENS e revisão após baseline, não níveis já atingidos:

1. **Dataset de referência:** rotular os 144 por finalidade e erro de transformação; ampliar com outras categorias ENS, casos fáceis/difíceis, cursos viáveis/inviáveis e fontes vazias/ruins. Dois revisores de domínio independentes, adjudicação e registro de desacordo. Separar conjunto de desenvolvimento, regressão e teste temporal não visto.
2. **Integridade inegociável:** 100% dos campos críticos de série, moeda/valor/unidade, categoria, descrição e URL preservados ou perda explicitamente registrada; zero alteração indevida de timestamps/IDs; nenhum dado crítico cortado silenciosamente. Medir por campos esperados, não por total de bytes.
3. **Extração/comparabilidade:** precisão e recall por campo/categoria, alvo inicial ≥95% em campos críticos e erro monetário zero para exemplos aceitos; casos ambíguos contam como abstenção correta, não acerto inventado. Validar tamanho por categoria e intervalos de incerteza.
4. **Qualificação:** medir precisão e recall por finalidade, macro-F1 e matriz de confusão; inspecionar especialmente falsos descartes. Alvo inicial ≥90% de recall de evidência útil sem promover conteúdo incompatível. Não usar aumento do número aceito como objetivo isolado.
5. **Planejamento:** especialistas avaliam se cada pergunta possui fonte capaz/recorte/intenção e critério de parada; medir diversidade de entidades, rendimento qualificado por consulta/custo, recuperação de lacunas, erros e amostragem. Alvo inicial: nenhuma chamada incapaz de responder a sua pergunta por contrato.
6. **Scoring:** fórmulas/denominadores/unit economics corretos em 100% dos casos gold; estados ausente/zero/inconclusivo distintos; teste de alcance dos gates em todos os perfis antes de publicação; sensibilidade e contraexemplos de direções dos sinais. Validade comercial exige histórico real e comparação com baseline humano/simples.
7. **Parecer sênior:** rubrica 1–5 por resposta à decisão, triangulação, uso de contraprovas, separação de proxies, clareza de incerteza, utilidade de ações, economia e consistência com critérios ENS. Alvo inicial: nenhuma omissão material sem pendência explícita e ≥4/5 em dimensões essenciais segundo painel ENS; não usar só LLM-judge.
8. **Redação/revisão:** 100% de claims materiais e números rastreáveis; controles negativos contendo contradições, preço errado, synthetic como real e cronologia inválida devem ser recusados. Testar falso positivo do revisor e falso negativo do redator separadamente. Um relatório elegante e citável pode continuar analiticamente raso.
9. **LLM tradicional antes do híbrido:** repetir replay das mesmas entradas, congelando modelo/prompt/skills/código e comparando precisão/recall, abstenção, custo, latência e consistência. Só depois rodar JEV em shadow em julgamentos delimitados. Modos mantêm fórmulas e estado iguais.
10. **E2E real:** combinar testes offline/replay com homologação real de novas propostas e fontes; medir orçamento, conclusão técnica e qualidade por dimensão separadamente. Incluir resultados de insuficiência legítima e de alta/baixa atratividade para detectar viés de abstenção/aprovação. Nenhuma meta de taxa de aprovação.

## Sequência de fases sugerida

| Fase | Entrega | Dependência e critério para seguir |
|---|---|---|
| 0 — Verdade de referência | Perguntas ENS, rubrica gold por finalidade, mapa de campos e baseline dos 144; matriz capability→feature→gate | Revisão ENS de amostra e critérios; falhas e limites separados |
| 1 — Fidelidade dos dados | Corrigir perdas, tipos, amostragem, dedup/entidades e projeções por fonte | Gate de integridade e replay, sem custo Apify novo; mesmos dados não desaparecem entre etapas |
| 2 — Pesquisa e curadoria | Planejamento orientado a perguntas/intenção; fonte oficial/curso direto; recuperação por lacuna; classificação multifinalidade | Qualificação e ofertas com precisão/recall gold; dados úteis/custo melhor que baseline |
| 3 — Parecer de mercado | Contratos de concorrência, currículo, aluno/comprador, contexto e SWOT; reviewer sênior | Painel ENS aprova utilidade e materialidade, não só texto/source count |
| 4 — Decisão e economia | Revisão de confidence/gates/perfil por capacidade; motor financeiro e cenários com inputs ENS | Testes exatos e premissas completas; versão nova, sem recalcular retrospectivamente análise antiga |
| 5 — Entrega e calibração | Dossiê ligado ao ledger, rubric reviewer, experimentos primários autorizáveis, backtest temporal/shadow | LLM tradicional passa baseline multidimensional; identificar o que ainda é hipótese |
| 6 — JEV híbrido | Adapters para decisões atômicas com mesmo contexto/corpus/teste | Shadow + não inferioridade acordada por tarefa; sem trocar workflow/score/redação por JEV |

## Reutilização: skills, ferramentas e MCP

- **Apify oficial:** `apify-ultimate-scraper` e `apify-integration-development` são candidatos para reaproveitar boas práticas de discovery, schemas e execução. O pacote oficial e seus contratos devem ser fixados por versão/commit e adaptados ao registry e orçamento do Prometeus. Fonte: [Apify Agent Skills](https://docs.apify.com/agents/skills), [repositório oficial](https://github.com/apify/agent-skills).
- **MCP Apify:** descoberta, execução e acesso a storage; hosted expõe schemas inferidos. Opcional para desenvolvimento/inspeção; não corrige sozinho projeções de dado, método de pesquisa ou interpretação. Manter allowlist e validação mesmo se houver MCP. [Documentação oficial](https://docs.apify.com/mcp).
- **Skill comunitária competitiva:** `apify-easy-competitive-intelligence` tem módulos SWOT/concorrência/preço e verificação. Não instalar como está: o texto consultado assume EUA, suprime stderr e chega a equiparar zero jobs a ausência de contratação. Isso conflita com recorte ENS e distinção entre falha/ausência/amostra. Aproveitar estrutura de módulos após revisão, licença e commit. [Fonte do autor/registry](https://github.com/apify/awesome-skills/blob/main/skills/apify-easy-competitive-intelligence/SKILL.md).
- **Skill comunitária de vagas:** `apify-jobs-data` propõe dedup entre boards, campo de cobertura salarial e limitações de ghost-job heurístico. Bons candidatos a fixtures e desenho de contrato; não aceitar heurística como comprovação. Validar Actors, geografia e custo antes de qualquer uso. [Fonte](https://github.com/apify/awesome-skills/blob/main/skills/apify-jobs-data/SKILL.md).
- **Orquestração de papéis:** o SDK Agents oficial descreve manager/tools e handoffs; pode orientar o desenho, sem migração obrigatória do loop atual. [Documentação](https://openai.github.io/openai-agents-python/agents/). A biblioteca não fornece expertise ENS nem avaliação comercial pronta.
- **Know-how de domínio:** contratar/validar com especialista ENS em portfólio, captação, coordenação e finanças para produzir rubricas e gold. Um `SKILL.md` genérico de marketing ou finanças não substitui isso. Skills instaladas no Codex não passam automaticamente a ser usadas no runtime: precisam ser incorporadas ao registry, com versão/hash e evidência de carga na chamada.

## Fontes públicas oficiais consultadas e limites de uso

- [ENS — notícia oficial sobre o MBA Gestão Avançada de Seguros](https://acontece.ens.edu.br/mba-gestao-avancada-de-seguros-abre-inscricoes-para-nova-turma/): confirma contexto de formação executiva/setor e currículo daquele anúncio. A própria página mistura marcação temporal e condições históricas; não adotá-la como preço/calendário atual sem página da oferta. A homepage ENS abriu sem corpo legível na ferramenta de leitura e a página CIMMO expôs principalmente rodapé; ausência de texto não significa ausência de cursos. O catálogo requer renderização/leitura de origem validada.
- [SUSEP — estatísticas do mercado](https://www.gov.br/susep/pt-br/fale-conosco/consultar-estatisticas-do-mercado): portas oficiais SES/AUTOSEG/IVR/boletins. Usar como contexto setorial e delimitado, não procura por curso.
- [CNseg — portal oficial](https://cnseg.org.br/): publica conjuntura e estatísticas. Fonte setorial primária para suas próprias séries/projeções, sem pressupor que projete educação ENS.
- [MTE/PDET](https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho), [serviço oficial RAIS/Caged](https://www.gov.br/pt-br/servicos/solicitar-consulta-as-estatisticas-da-rais-e-do-caged?id=7839&origem=servico): registros formais e microdados TXT disponíveis; acesso online pode ter requisitos. Não são contagem de vagas anunciadas.
- [INEP — Censo Superior](https://www.gov.br/inep/pt-br/areas-de-atuacao/pesquisas-estatisticas-e-indicadores/censo-da-educacao-superior/), [sinopses](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/sinopses-estatisticas/educacao-superior): estatísticas de graduação/sequenciais e contexto de oferta; a cobertura não inclui um censo completo de MBAs/extensão.
- [IBGE — PNAD Contínua](https://www.ibge.gov.br/estatisticas/sociais/populacao/9171-pesquisa-nacional-por-amostra-de-domicilios-continua): fonte amostral para força de trabalho/renda/escolaridade; respeitar recorte e periodicidade.
- [Google Trends — metodologia](https://support.google.com/trends/answer/4365533?hl=pt-BR): amostragem/normalização relativa e baixa frequência. Não interpretar 0–100 como volume de pessoas ou matrículas.
- [Google Ads — histórico/previsões de Keyword Planner](https://support.google.com/google-ads/answer/3022575?hl=pt-BR): volumes aproximados com recorte e forecasts condicionados. Acesso pode exigir configuração de conta; não foi validada API ou credencial da ENS.
- [Sebrae — guia financeiro](https://sebrae.com.br/Sebrae/Portal%20Sebrae/Semana%20MEI%202019/conteudos%20MEI/ebook%20MEI2.pdf): suporte conceitual para margem/contribuição/equilíbrio. A modelagem específica de curso, custos e classificação contábil requer validação ENS.

Nenhum pacote externo foi instalado, nenhum experimento comercial foi disparado e nenhuma fonte adicional foi integrada nesta auditoria.
