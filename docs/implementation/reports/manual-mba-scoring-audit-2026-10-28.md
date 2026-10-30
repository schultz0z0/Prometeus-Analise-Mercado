# Auditoria do dossiê manual e desenho do scoring

Data: 2026-10-28. Produto: Prometeus — Inteligência para Produtos Educacionais.

## Escopo e estado

Auditoria somente de leitura da homologação manual `6e885807-145d-4346-825b-c9743177122e`, concluída com dossiê `8230bd8e-9da6-4a19-8357-cd93bff055d6`, criado em 2026-10-28 às 13:32:09, horário de Brasília. Esta é a execução manual do usuário, distinta do ensaio assistido anterior. Nenhum resultado, evidência, configuração ou serviço foi modificado nesta auditoria. Nenhuma coleta paga ou inferência foi iniciada.

Fontes: endpoints locais de detalhe da análise e dossiê, tabelas históricas e resultado da decisão curricular, código atual, documentação de scoring, nove slides de `IPD_Tematico_ENS_Apresentacao_Executiva (1).pptx` fornecidos pelo usuário e instruções diretas complementares.

## Conclusão

A nota 27,47 não permite concluir baixa viabilidade comercial do MBA. Ela combina desempenho parcial com ausência de dados, e contém efeitos de defeitos confirmados de geografia, identidade das vagas, seleção histórica e tratamento da confiança curricular. A recomendação de evidência insuficiente é compreensível diante das lacunas efetivamente recebidas pelo scoring, mas o diagnóstico externo apresentado está prejudicado pelo sistema.

Coletar várias fontes não assegura suficiência por dimensão. Houve 22 chamadas: 19 `SUCCEEDED`, duas `FAILED` e uma `EMPTY`, com 83 registros persistidos. A qualificação aceitou 26 registros e rejeitou 57. Entre os aceitos, 22 são registros de ofertas, três sinais sociais e um anúncio. Esses registros não equivalem necessariamente a cursos, pessoas ou empresas distintos. O custo somado informado nas runs é US$ 0,189831, sem representar o custo completo da LLM.

## Reconciliação da nota

| Dimensão | Score | Peso | Contribuição |
|---|---:|---:|---:|
| Histórico institucional | 70,11 | 20% | 14,022 |
| Concorrência em mídia paga | 12,50 | 20% | 2,500 |
| Aderência curricular | 73,00 | 15% | 10,950 |
| Busca e tendência | ausente | 20% | sem contribuição |
| Empregabilidade | ausente | 15% | sem contribuição |
| Precificação | ausente | 10% | sem contribuição |

Soma: 27,472, apresentada como 27,47. Cobertura ponderada: 55%. O diagnóstico normalizado sobre os pilares presentes seria aproximadamente 49,95 (valor calculado a partir dos dados exibidos). Este último valor também não é uma nota corrigida de viabilidade: conserva os defeitos dos componentes e não supera os gates de suficiência.

O motor mantém pesos ausentes fora da soma e mostra a soma como nota em escala 0–100. Embora o texto avise que ausência não significa desempenho negativo, a apresentação da nota continua confundindo qualidade da oportunidade com completude da pesquisa. A revisão deve separar score observado, cobertura, confiança e possibilidade de emitir recomendação final.

## Achados confirmados

### Vagas coletadas e descartadas por comparação de texto geográfico

As quatro buscas de vagas concluíram e persistiram 20 registros. O entendimento retornou `Brasil como contexto do programa e do mercado estudado; participação online de qualquer localidade.`. O extrator reconhece Brasil somente quando o trecho anterior ao ponto e vírgula é exatamente Brasil/Brazil/BR. Nesta execução, tentou encontrar a frase descritiva inteira no endereço da vaga.

Cinco registros classificados `RELEVANT` foram rejeitados por localização, apesar de indicarem São Paulo/Brazil. Eles correspondem a quatro URLs de vagas distintas, removendo parâmetros de rastreamento. Uma simulação somente em memória com escopo `Brasil` aceita a localização de 19 dos 20 registros, sem mudar a classificação semântica. Isso não justifica aceitar todos: vários são contexto, cargos adjacentes ou têm suporte insuficiente.

Referências: `application/evidence_features.py`, inicialização do extrator e `accepts`; entendimento da etapa 4; qualificações persistidas.

### IDs de vagas confundidos com telefone

Nos cinco registros pertinentes acima, `sanitized_data.id` é `[PHONE_REDACTED]`. `_entity_key` prioriza esse campo para vagas e produz a mesma identidade para todos. A reprodução em memória, corrigindo somente a geografia, conta uma vaga onde existem quatro URLs distintas.

É necessário preservar identificadores técnicos públicos tipados, higienizar PII nos campos apropriados e nunca usar um marcador de redação como chave de entidade. Se o identificador não for confiável, usar URL canônica e ID público da vaga extraído de forma validada. Não remover a proteção de PII do texto livre.

### Tendências: falha real e consulta composta inadequada

A primeira run terminou, mas `interestOverTime_timelineData` e médias vieram vazios. Outra consulta excedeu 300 verificações e teve cancelamento remoto confirmado. Não há série válida que possa ser pontuada como tendência.

O builder envia `searchTerms: [call.query]`. A consulta era `MBA seguros, gestão de riscos`; o resultado registrou `searchTerm: MBA seguros gestão de riscos`. O schema oficial oferece `isMultiple`, padrão falso, para tratar vírgula como separador. Portanto, termos que pretendiam comparar assuntos viraram uma expressão composta. Isso prejudica a estratégia de busca, mas não prova que seja a única causa da falta de dados do provedor. Correção proposta: termos independentes em contrato explícito, período/geo tipados e tratamento distinto para série indisponível e interesse zero observado.

Fonte oficial conferida: https://apify.com/apify/google-trends-scraper/input-schema.

### Precificação: havia valores, mas não preços estruturados comparáveis

As nove páginas recebidas pelo crawler incluem placeholders da Uninter, várias condições na Facuminas, ofertas de marketplace e notícias de 2024 com valores distintos. `_price_brl` retorna valor somente quando encontra um único montante distinto; `observed_price_period` rejeita páginas que misturam mensalidade e total. Isso evita uma comparação inválida, mas o sistema não faz a etapa seguinte de estruturar cada condição comercial.

O cálculo atual usa mediana externa e não incorpora preços históricos internos. Também falta um contrato obrigatório de tema/família para cada oferta precificada. Uma notícia de extensão ou uma página com vários cursos não deve ser usada como preço de MBA só por ser relevante ao setor.

Proposta declarada nesta execução: R$ 970, 20 parcelas e 14 meses, total determinístico de R$ 19.400. Isso difere dos R$ 976 informados para o ensaio anterior. O registro manual deve ser preservado, sem substituição pelo valor de outra execução.

### Concorrência paga: anúncio da própria instituição

O único anúncio aceito é da Escola de Negócios e Seguros. O formulário colocou a própria ENS na lista de concorrentes, e o entendimento não recebeu contexto institucional suficiente para resolver a identidade. O anúncio precisa ser classificado como presença própria, e não como concorrente externo.

O score de 12,5 resulta de `1 / 8 × 100`. Ele mede uma contagem na amostra com referência fixa, não intensidade de toda a concorrência nem matrículas. O planejador orienta coletar de três a cinco itens por chamada. Notas por contagem precisam considerar truncamento, paginação, janela, deduplicação e diversidade de anunciantes; não podem tratar o teto de coleta como tamanho do mercado.

### Histórico: a implementação não calcula o IPD apresentado

O motor atual combina 50% de proximidade semântica, 30% de conversão lead/matrícula normalizada por 15% e 20% de matrículas médias normalizadas por 50. Nesta execução: proximidade 82, conversão 6,3544% e média arredondada de 41 matrículas, resultando em 70,11.

O fluxo usa os cinco cursos e os dez registros anuais do tenant, misturando MBA, pós, extensão e aperfeiçoamentos. Não seleciona até três comparáveis, não usa inscrições no score e não normaliza por família. A base canônica histórica possui nome, categoria, tags, público e carga horária, mas não grade curricular estruturada. Não é possível alegar comparação real de grades sem incorporar esse conteúdo.

### Aderência curricular: confiança baixa não respeitada no scoring

A decisão que retornou 73 possui confiança 0,57 e `requires_human_review=true`. O workflow consome `score_value` e não transmite essa restrição ao pilar. A confiança apresentada é 0,675, calculada por completude fixa dos componentes, e não a confiança dessa decisão.

Além disso, o julgamento recebe ofertas e anúncios aceitos, mesmo quando não há competências verificadas de vagas. O score não prova cobertura das necessidades de trabalho. A revisão deve requerer vínculos módulo–competência–evidência e preservar baixa confiança/revisão até a recomendação, sem converter um julgamento incerto em dimensão coberta automaticamente.

### Texto executivo e contexto declarativo

O dossiê enfatiza esclarecer a identidade da ENS e as condições de cobrança. A primeira dúvida tem origem na própria ENS listada como concorrente e na falta do contexto do tenant para o entendimento. A segunda persiste embora parcela, quantidade e duração sejam campos estruturados.

O serviço cria um fato de proposta com JSON cortado em 10.000 caracteres; uma ementa longa pode anteceder os campos comerciais. A revisão deve enviar metadados comerciais e institucionais explicitamente, junto da proposta, distinguindo condições declaradas de alegações externas. Isso evita transformar fatos fornecidos em perguntas repetitivas e libera a síntese para analisar o mercado.

## Modelo proposto conforme instruções do usuário

### Histórico institucional e IPD

1. Determinar família normalizada da formação, tema, público e módulos da proposta. A família Pós/MBA do PPT pode reunir subcategorias, preservadas no filtro comercial de preços.
2. Selecionar até três cursos internos pertinentes por tema e proximidade curricular, com justificativa e referências. Aceitar menos quando não houver três adequados. A similaridade seleciona/pesa comparáveis; não substitui o potencial de demanda.
3. Normalizar leads, inscrições e matrículas por percentil usando uma coorte de referência da mesma família, instituição e janela. Os três selecionados não são toda a distribuição de referência. Usar ofertas concluídas e comparáveis, identificando exposição, cancelamentos e dados incompletos.
4. Calcular em código `IPD = 0,20 × percentil_leads + 0,30 × percentil_inscrições + 0,50 × percentil_matrículas` por comparável. Agregar os comparáveis em regra versionada e mostrar a base de cada um.
5. Não preencher falta de grade ou coorte com valores inventados. Com somente um curso por categoria e poucos por família na massa atual, apresentar IPD de teste e insuficiência de referência para ranking robusto.

O PPT não fixa convenção de empate/percentil, janela, tratamento de repetição de ofertas nem ponderação dos comparáveis; esses pontos devem ser definidos e testados no novo perfil. O IPD não incorpora margem ou custo como se fossem demanda.

### Mercado externo

Separar demanda de busca/tendência, empregabilidade/competências e concorrência/oferta. Redes sociais fundamentam dores e posicionamento, sem equivaler a volume de compradores. Cada dimensão informa resultados brutos, válidos, únicos e aproveitados, recorte temporal, localização e perda por falha/filtro.

Exibir score externo agregado somente com cobertura identificada. Não somar repetidamente o mesmo sinal em vários componentes. A própria instituição permanece identificada e excluída do conjunto de concorrentes externos.

### Precificação combinada

Usar média de cursos internos similares e de ofertas concorrentes do mesmo tema e categoria, conforme instrução do usuário. Extrair por oferta: instituição, categoria, tema, modalidade, carga horária, moeda, parcelas, valor da parcela, total, taxas e condição promocional. Calcular total apenas quando os termos observados permitirem; não multiplicar pela duração acadêmica.

Deduplicar a oferta e a condição, separar origens e não contar a mesma oferta ENS como interna e concorrente. Comparar investimento total com investimento total. Referências ausentes são lacunas, não preço zero. Informar tamanho da amostra, intervalo/dispersão e frescor. Proximidade do preço não demonstra margem, qualidade ou viabilidade econômica.

Ponto aberto enviado ao usuário: média única por curso comparável versus peso de 50% para cada origem. São fórmulas distintas e não devem ser trocadas silenciosamente.

### Composição final

Recomendação inicial: preservar os pesos baseline como hipótese durante a correção, agrupando-os de forma explícita, antes de recalibrar. Histórico interno 20%; mercado externo 55% (mídia paga 20%, busca 20%, vagas 15%); aderência curricular 15%; precificação combinada 10%. Os dois últimos cruzam fontes e devem aparecer separados, evitando contá-los duas vezes dentro de um score externo e novamente no final.

Uma alternativa é atribuir novos pesos aos dois grandes blocos, mas isso exigiria definir como tratar aderência e preço misto e validar o perfil. Uma média simples entre IPD e mercado não resolve sozinha esse problema.

O painel deve mostrar: IPD/histórico dos comparáveis, avaliação externa, aderência/precificação, score consolidado, cobertura e confiança. Falta de coleta não deve ser apresentada como desempenho ruim. A recomendação final pode permanecer insuficiente mesmo com diagnóstico parcial alto. Pesos e gates novos devem ser versionados; análises antigas continuam imutáveis.

## Limites e próximos passos

Esta auditoria não aprova o lançamento nem fornece score corrigido do MBA. Requer correções de sistema, contratos de comparabilidade/identidade/geografia/preço, regras do novo perfil e posterior homologação manual. Não houve nova inferência sobre as evidências nem backtest. As reproduções de localização/deduplicação foram em memória, preservando a análise original.
