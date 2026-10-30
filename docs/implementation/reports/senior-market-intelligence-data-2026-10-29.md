# Auditoria de dados, decisões e grounding — Prometeus ENS

Data: 29/10/2026. Escopo: leitura e reproduções offline; nenhum Actor, inferência paga, alteração de produto, score, evidência ou estado. Base: `docs/Estudo_Prometeus_144_registros_73501c53_2026-10-29/`. O artefato de sensibilidade está em `var/diagnostics/senior-audit-confidence-sensitivity.json`.

## Conclusão principal

Não é possível avaliar a inteligência do modelo ou a suficiência do mercado somente pelo dossiê atual. Há perdas determinísticas entre coleta, qualificação e redação; o verificador lê a mesma base empobrecida que o redator. Além disso, a confiança agregada é governada por constantes de completude dos componentes, e o gate de 75% não é alcançável no cenário de features efetivamente produzido pela coleta atual, mesmo fazendo todos os seis pilares ficarem presentes. Isso não torna correto baixar o gate: demonstra necessidade de alinhar a especificação das features, sua disponibilidade e a calibração dos gates.

## Medidas verificadas, denominadores e limites

| Medida | Resultado | Interpretação correta |
|---|---:|---|
| Registros persistidos | 144 | Capturas; não tamanho de mercado ou entidades únicas |
| RELEVANT / CONTEXT / IRRELEVANT / INCONCLUSIVE | 17 / 73 / 29 / 25 | Classes atuais, sem gold humano para medir acerto |
| `quality_score=1.0` | 144/144 | A implementação mede basicamente ausência de regex de injection, não completude/qualidade de mercado |
| Entrada reconstruída >14 mil caracteres | 20/144 | Reconstrução do código atual e payload salvo; não log integral dos prompts históricos |
| Confidence da qualificação | min .76, mediana .97, max 1 | Autoavaliação da decisão, não precisão estatística |
| Qualificações com confidence >=.95 / >=.99 | 87/144 / 44/144 | Não demonstra bom classificador sem rótulos independentes |
| Qualificações exigindo revisão humana | 0/144 | Inclusive 25 INCONCLUSIVE; alta confiança na classe não é alta qualidade da evidência |
| Descrição de vagas fora do resumo do redator | 28/30 | Inclui 16/16 vagas qualificadas; não significa que a descrição faltou também na qualificação |
| Texto original completo preservado | 144/144 | A reparação pode começar por replay sem pagar nova coleta |
| Decisões persistidas deste pacote | 186 | 144 pertinência +40 suporte +1 readiness +1 aderência; todas rotuladas `llm-traditional` |

Não existe aqui prova de precisão/recall do agente, avaliação de demanda real de alunos ou eficácia comercial. As medidas acima são de integridade operacional do caso e inspeção de código.

## Achados prioritários

### D01 — P1: a série Trends fica fora do texto submetido à qualificação

Código: `src/prometeus/application/qualify_market_evidence.py:148-151`, recorte de `json.dumps({title,url,data})[:14000]`. A ordem de propriedades é a retornada pelo JSONB persistido, não uma seleção de relevância de campos. Registros de 67–80 mil caracteres incluem listas geográficas extensas antes da série.

As três séries começam aproximadamente nos caracteres 24.540–36.696, depois do corte; 262 pontos cada. Em duas capturas de “litigância predatória”, 30 pontos positivos/hasData; em “fraude em seguros”, dois. IDs `88f8fe8d-f605-48c0-b4bc-9fa0fc06ab00`, `679c794b-638a-4158-a2cd-5381a740b68d`, `a3ded491-613a-4ffd-b434-5df9f0c08b00`.

Impacto: a LLM pode afirmar INCONCLUSIVE vendo cidades e metadados sem a série decisiva. Corrigir apenas prompt ou trocar modelo não recupera bytes não enviados. Contrato necessário: `SearchTrendObservation` com termo, geo, janela, unidade, pontos válidos/ausentes/parciais, densidade, amostra temporal representativa e métricas calculadas em código. A qualificação semântica avalia pertinência do termo; a validade numérica fica em código.

### D02 — P1: sanitização genérica altera identificadores técnicos e datas

Código: `sanitization.py:30-48,79-82,95-139`. A exceção tipada cobre alguns IDs, não `time`, `link`/URL ou vários metadados públicos. A recursão trata todas as strings como texto livre.

Observado: 786/786 timestamps das três séries substituídos por `[PHONE_REDACTED]`; links internos de payload em 30/30 vagas também redigidos. A `source_url` separada continua intacta, portanto não afirmar que todas as fontes ficaram inacessíveis. No dataset, também há `id` de três perfis LinkedIn e outros metadados alterados.

Reprodução offline: `EvidenceSanitizer().sanitize_payload({'time':'1793300000','url':'https://linkedin.com/jobs/view/4470152525'})` devolve ambos como telefone, com quality_score 1.0. Preservar timestamps/números/URLs/IDs em schema conhecido; aplicar PII a campos de contato e texto livre; validar pós-condições de integridade. Testar PII real e números técnicos simultaneamente.

### D03 — P1: descriptionText é perdido na redação e o revisor não vê o original

Código: `synthesize_dossier.py:195-226` seleciona `description,text,markdown,caption,comment,body`, mas não `descriptionText`/`descriptionHtml`. Exemplo `0c5a6c8a-7501-4dd8-9709-c263d040de1d` contém 4.002 caracteres de descrição; o fato disponibilizado ao redator tem apenas título, empresa e localização. Isso afeta 28 descrições de vagas, incluindo 16 aceitas.

O revisor usa `facts.citable_items()` para as fontes citadas (`synthesize_dossier.py:569-581`). Assim, redação e revisão podem concordar sobre uma limitação que foi criada pelo próprio projetor de dados. Hash estável comprova consistência, não completude.

Contrato: `JobObservation` com responsabilidades, requisitos, competências, senioridade, empregador, local, datas e salário quando observável. Cada campo com ponteiro ao payload original e trecho. Antes do escritor, comparar campos críticos extraídos vs disponibilizados; impedir a frase “descrição ausente” quando a fonte possui descrição não processada. Reviewer de integridade precisa comparar o pacote com fonte canônica, separado do suporte semântico das claims.

### D04 — P1: teto operacional da confiança incompatível com o gate atual

Perfil `config/scoring/portfolio-v2.yaml:6-22`: pesos .20/.20/.20/.15/.15/.10, mínimo .75 de confidence, busca obrigatória. Não há demonstração de calibração comercial desses limiares.

Fórmulas `domain/scoring/calculator.py:28-44,71-168,280-315` multiplicam constantes máximas pelos pesos de componentes disponíveis. No fluxo atual: H até .90 (`internal_history.py:294-307`); Meta só contagem .44; Trends sem volume absoluto até .506; vagas sem mediana salarial tipada .51; aderência sem percentual de dores cobertas .675; preço de origem única .50 ou duas origens .80 (`run_course_analysis.py:648-661`).

| Pilar | Feature efetiva | Confidence do cenário atual com o componente presente |
|---|---|---:|
| H | IPD, referência >=10, grade disponível | .90 |
| C | ad_count; sem competition_index | .44 |
| B | average_interest + growth; sem monthly_volume | .506 |
| E | open_jobs_count; sem salary_median_brl | .51 |
| A | syllabus_fit_score; sem market_pain_points_covered_pct | .675 |
| P | preço interno sintético; sem externo comparável | .50 |

**Reprodução offline**: carregar os inputs dos cinco pilares presentes no dossiê e acrescentar `search_and_media={'average_interest':10,'growth_trend_pct':0,'is_present':True}`. Esses valores são placeholders para exercitar alcançabilidade, não evidências de mercado. A confiança independe desses valores de nota, depende da presença de componentes. Cobertura 1.0; confiança .5970; recomendação do gate INSUFFICIENT_EVIDENCE. A confiança atual era .6198 com cobertura .8. Acrescentar um pilar menos confiável pode reduzir a média, comportamento matemático esperado porém pouco explicado ao usuário. Mesmo com preço interno+externo (.8), o teto desse conjunto fica .6270.

**Limite da conclusão**: não é impossível matematicamente alcançar .75 no motor em geral. Com todos os componentes opcionais fornecidos e H=.9/P=.8, a média teórica chega .8825. O bloqueio é operacional do conjunto de features/produtores atuais. No corpus, `monthly_search_volume`, `competition_index`, `cpc_brl`, `salary_median_brl` e `market_pain_points_covered_pct` estão ausentes em todos os144 registros. `evidence_features.py:385-406` apenas lê os quatro primeiros como campos numéricos prontos; não normaliza o `salary` string que existe em três vagas. O workflow produz `syllabus_fit_score`, `syllabus_confidence` e revisão, não `market_pain_points_covered_pct` (`run_course_analysis.py:747-768`). Não há integração de volume absoluto entre os Actors deste caso; Google Search e Trends não fornecem esse número como substituto.

Não baixar .75 para “passar”. Definir matriz feature→fonte→capacidade→availability→confiança→custo; distinguir completude, pertinência, precisão e confiança semântica; calibrar por dados rotulados e outcomes. Adicionar teste de alcançabilidade com fixtures reais de cada provedor e um controle positivo viável sem inventar features que nenhum produtor entrega.

### D05 — P1/P2: métricas Trends sem densidade, escala conjunta ou frescor

Código: `evidence_features.py:202-235,380-405`. O extrator descarta `hasData=false` corretamente, mas calcula média somente nos pontos observados, sem publicar denominador/censura e agrega médias de termos em consultas potencialmente independentes. No caso, “fraude em seguros” tem dois pontos positivos de 262 e a rotina calcula average_interest 92.0. Isso não significa interesse alto ao longo do período nem volume absoluto. A confidence do componente não incorpora os 2/262.

Proposta: preservar ausência ≠ zero, registrar denominadores e janela, não fundir índices de consultas independentes como uma mesma escala; escolher comparações simultâneas/termo âncora quando suportado e justificar agregação. Densidade e tempo mínimo de observação são parâmetros a calibrar, não filtros ad hoc para eliminar nichos. Acrescentar casos de hasData false, zeros observados, períodos irregulares e consulta parcial.

Falha latente reproduzida offline: `_trends_metrics({'interestOverTime_timelineData':[{'time':'1','value':[100],'hasData':[True],'isPartial':[True]}]})` aceita o ponto como average100, porque só testa `isPartial is True` escalar. Não observada como causa no dataset; é lacuna de normalização de variantes.

### D06 — P1: não há validação simétrica forte dos adaptadores tradicional e JEV

Tradicional: `infrastructure/llm/decision_adapter.py:68-74,104-128` aceita booleano como float e converte distribuição sem conferir chaves, intervalos, soma ou consistência com selected_choice. Repro offline com FakeGenerativeModel: selected_choice RELEVANT, confidence true, distribution `{'RELEVANT':-3,'INVENTED':99}` => resultado confidence1, sem revisão. Nenhuma inferência real usada. `generate_text`, não o transporte `generate_structured`, continua sendo usado nos julgamentos.

Híbrido: `infrastructure/jev/client.py:126-145` usa `selected or choice or pack.options[0]`. Repro com `httpx.MockTransport` devolvendo apenas `{'confidence':1}` em pack cujas opções começam RELEVANT => `RELEVANT,1.0,requires_human_review=False`. Não é comportamento observado do fornecedor; é um fallback inseguro comprovado do cliente. O caminho ainda não foi homologado neste caso. Score em `:177-185` também pode fabricar zero em resposta ausente, não valida todos os limites e ignora um pedido explícito de revisão se vier fora do contrato usado.

Correção planejada: schema comum estrito, booleanos rejeitados para números, finite+range, opções e distribuição completas, normalização declarada do fornecedor sem defaults semânticos. Ausência vira erro de contrato/NOUL com diagnóstico, nunca primeira opção. Capturar modelo real/versão e avaliação em corpus idêntico nos dois modos. Trocar para JEV não conserta as perdas de entrada.

### D07 — P2: qualidade_score não é qualidade de dados

Código `sanitization.py:89-99`: score=1 menos penalidade por regex de injection; emails/telefones/timestamps alterados, página vazia, 404 e texto ausente não reduzem qualidade. Todos144 têm1.0. Rebatizar como indicador restrito de segurança ou substituir na avaliação por dimensões explícitas: disponibilidade, integridade estrutural, completude de campos críticos, recência, pertinência por finalidade, independência, origem primária, consistência e observabilidade. Não usar um único escalar como autorização de scoring.

### D08 — P2: comparabilidade de preço por token genérico

Código `pricing_reference.py:91-116`: stopwords não retiram “extensao”; a condição é qualquer token em comum. Repro offline `_same_theme('Extensão em Culinária','Extensão em Fraude e Litigância predatória no mercado de seguros') == True`. A categoria ainda é checada e há qualificação prévia, mas esses controles não corrigem o validador de tema. O erro não produziu um preço externo errado neste dossiê porque nenhum externo passou.

`pricing_reference.py:119-122` também descarta toda query da URL: `.../curso?id=fraudes` e `.../curso?id=culinaria` viram a mesma identidade. Falha latente, não comprovada como perda neste caso. Definir CourseOffer com categoria, família, tema principal, competências, workload, modalidade e condições comerciais. Distinguir comparável direto, adjacente e contexto. ID de oferta não pode excluir parâmetros semânticos indiscriminadamente. Manter média por curso conforme critério ENS; mostrar dispersão, fontes e cobertura, sem inventar valor ausente.

### D09 — P2: seleção interna e confiança sobreestimam presença de grade

Código `internal_history.py:174-214,294-307`: similaridade lexical Jaccard, limiar apenas >0; stopwords também não removem “extensao”. Até três selecionados, como pedido, e referência/janela corretas, mas ausência de piso de comparabilidade. No caso, theme_fit .0575–.0581, curriculum_fit .0084–.0135 e selection_fit .0403–.0425. Mesmo assim confiança H=.90 porque há dez cursos de referência e campos de grade presentes. Presença de grade não equivale a proximidade de grade. Esse achado é sobre seleção/explicação, não sobre invalidação da fórmula IPD20/30/50 aprovada.

Planejar contratos de comparabilidade com justificativa por módulos/competências, evidência de similaridade, piso calibrado e opção de devolver menos de três comparáveis. Não preencher três por quota. O histórico sintético deve continuar identificado e não deve calibrar probabilidade comercial.

### D10 — P2: cache/auditoria não reconstituem o julgamento completo

`qualify_market_evidence.py:85-101` invalida por versão da qualificação, instituição, skills, pack e entendimento (bons controles), mas não pelo modelo real, hash do input normalizado ou versão do sanitizador/projetor. `DecisionService` persiste a resposta, não o contexto/hash completo (`decision_service.py:110-125`; `db/models.py:298-328`). `model_version` é literal `llm-traditional`, não `gpt-6.1-terra`/versão; `ConfigSnapshot` congela tenant+scoring, sem pack/prompt/model/input snapshot completo (`create_analysis.py:90-98`, `db/models.py:183-201`).

Consequência: não se consegue provar retroativamente exatamente o que o modelo viu; payloads atuais permitem reconstrução, não log original. Troca de modelo ou preparação pode reutilizar decisão antiga se não houver bump manual. Criar ExecutionEnvelope por tentativa com hash de input/projeção, versão de schema/modelo/pack/prompt/skills/código, fontes/trechos, custos e decisões; conteúdo seguro sob retenção institucional, não logs gerais. Separar replay offline do job de produção e preservar tentativas anteriores imutáveis.

### D11 — P2: geografia depende de regex parcial de UFs

`evidence_features.py:175-198` aceita Brasil textual ou lista de UFs que omite AL/MA/MT/MS/SC e precisa regex em local string; `research_scope.py:46-69` exige o país textual em algumas combinações estreitas. Consequência latente: localidade brasileira válida sem país pode ser excluída; não demonstrada como causa dos dois descartes geográficos deste corpus. Contrato de local estruturado com country_code/IBGE/UF, distinção remoto/localidade do empregador e ambiguidade observada; fixtures todas27UF, Pennsylvania/PA, geografia desconhecida e escopo nacional/estadual.

## Controles bons a preservar

- Payload original e higienizado, custo, run/dataset e qualificação preservados; exportação permitiu descobrir perdas sem nova compra de dados.
- Fórmulas e mudanças de estado em código; score observado, coverage e recomendação separados; histórico sintético explícito.
- Anúncios próprios excluídos do benchmark externo; contexto preservado no corpus factual e distinto de demanda.
- Dedup por entidade para ofertas/vagas/anúncios/comentários com aliases de proveniência; não presumir que144 são144entidades.
- Verificação determinística e semântica bloqueia claims sem suporte; recuperação limitada e rastros de falha existem.
- Nenhuma correção proposta deve simplesmente aceitar tudo, elevar confiança ou remover gates para evitar INSUFFICIENT_EVIDENCE.

## Plano de contratos e testes por prioridade

### P0/P1 — Integridade antes de qualquer novo E2E pago

1. Criar `domain/evidence_observations.py` e adaptadores por capability (`infrastructure/apify/normalizers/`), com campos tipados, unidades, datas, país, origem de cada campo e status observed/missing/ambiguous/censored.
2. Substituir corte de JSON bruto por projeção específica de tarefa em `qualify_market_evidence.py`; registrar orçamento de contexto e campos omitidos. Tests: toda série/descrição/preço crítico alcança a projeção; strings longas e JSON key reorder não alteram campos críticos; zero cortes silenciosos.
3. Sanitização tipada de campos em `sanitization.py`; tests de preservação exata de timestamps/IDs/URL/BRL e remoção de PII textual; 100% dos campos críticos preservados neste corpus, com todos os casos de PII dos testes existentes.
4. Atualizar `synthesize_dossier.py` para consumir observações e descrições canônicas; teste source→fact de16/16vagas aceitas, e relatório automático de perdas por campo.
5. Contrato comum estrito em `domain/ports/decision_model.py`, ambos clientes; criar `tests/contract/decisions/test_decision_response_integrity.py` com missing choice, unknown label, boolean, NaN/Inf, score fora de faixa, distribution negativa/incompleta/soma errada, pedido explícito de revisão e NOUL. Nenhum desses casos pode virar RELEVANT/OBSERVED/score por default.
6. Replay offline versionado dos144 a partir de raw_payload, gravando em sandbox/artefato separado, sem alterar o dossiê original. Primeiro validar integridade determinística, depois submeter ao gold humano e somente então executar modelos reais em lote opt-in.

### P2 — Qualificação para uso, scoring e redator

7. Matriz de utilidade por finalidade, não um accepted universal: descoberta, concorrência direta, adjacente, empregabilidade, competências, preço, contexto, demanda. Ofertas sem preço podem informar posicionamento; conteúdo próprio informa portfólio, não competição externa.
8. Matriz feature→fonte→availability→confidence e teste de alcançabilidade: `tests/integration/scoring/test_feature_reachability.py`. Nenhum controle positivo pode depender de campo criado apenas no fixture e impossível nos normalizadores reais. Completeness/gatequality parametrizados e calibrados, sem baixar o gate para acomodar o caso.
9. Mapa curricular `módulo→competência→necessidade→evidência/trecho`, com lacunas e adjacências. Substituir nota monolítica autodeclarada por decomposição auditável, composição em código e revisão de coordenação ENS.
10. Comparabilidade de cursos/preço explícita com testes negativos de culinária/extensão, temas adjacentes, MBA vs pós, parâmetros de URL, preço promocional/parcelado/à vista, múltiplas ofertas e datas.
11. Escritor recebe EvidenceBrief organizado por pergunta de negócio, campos críticos presentes, contraprovas e unknowns. Revisor de integridade compara EvidenceBrief→observações→raw; revisor factual compara claims→fontes; revisor de completude cobra resposta às perguntas sem inventar dados. Mais agentes não substituem esses contratos.

### P3 — Avaliação senior e modo híbrido

12. Gold inicial humano: rotular os144 por utilidade específica, campos a extrair, categoria/família, competências e alegações permitidas. Dois revisores (mercado educacional ENS + dado/metodologia), desacordo adjudicado. Separar treino/teste por entidade/domínio/curso, não por captura para evitar vazamento.
13. Ampliar com pelo menos três briefs distintos e corpus com positivos/negativos/adjacentes/ambíguos, cursos de famílias diferentes e dados adversariais. Quantidades são metas de desenvolvimento, não amostra estatisticamente representativa do mercado.
14. Métricas separadas: validade estrutural; fidelidade de campos; critical-field retention; pertinência precision/recall por finalidade; taxa de descarte útil; resolução de ambiguidade; dedup precision/recall; extração de preço/category/competência; calibração de confidence (Brier/ECE e reliability curve onde houver amostra); claim faithfulness; coverage de perguntas de negócio; rejeições indevidas do revisor; custo e latência por evidência útil.
15. Gates propostos a calibrar: 0 corrupções de campo crítico e 0 defaults semânticos em resposta inválida; 100% lineage para métricas críticas; >=.95 recall de evidência crítica e >=.90 precision por finalidade no gold inicial; métricas com denominadores/intervalos, não afirmar garantia universal. Não impor meta de taxa de APPROVED.
16. Tradicional primeiro: contratos/gold/replay aceitos, depois lote real opt-in com versão de modelo fixada. Híbrido depois: mesmo EvidenceBrief/pack/rubrica e schema, resultados lado a lado em holdout, diferença por classe/score/custo/latência e revisão de divergências. Nunca testar JEV em produção para “ver se melhora” sem corrigir as entradas comuns.

## Lacuna de testes atual

Há bons testes de contrato/resiliência e quatro controles LLM reais do suporte de dossiê. Contudo `tests/integration/market_sources/test_evidence_qualification.py` usa FakeDecisionClient com opções canned; a suíte de “Gate C” usa fatos sintéticos selecionados e não mede a qualidade de coleta/retention dos144. `tests/evaluation/scoring/backtest_dataset.json` preenche campos como volume/CPC/salário/pain coverage que a coleta atual não entrega. Logo, aprovação da suíte não valida inteligência de mercado ou alcançabilidade do gate com fontes reais. O novo teste precisa começar dos payloads de fornecedor e medir perdas até a decisão final.

## Próximas evidências necessárias, sem presumir resultado

Precisão/recall e qualidade senior ainda exigem rotulagem humana; não se pode concluir que todos54excluídos são úteis, nem que corrigir as falhas tornará o curso viável. A correção deve permitir uma conclusão informada e auditável, incluindo insuficiência legítima, sem confundir falha de coleta/processamento com ausência de demanda.

## Comandos offline mínimos já executados

Tema de preço — resultado `True` para temas distintos:

```powershell
rtk proxy .venv/Scripts/python.exe -c "from prometeus.application.pricing_reference import _same_theme; print(_same_theme('Extensão em Culinária','Extensão em Fraude e Litigância predatória no mercado de seguros'))"
```

JEV — MockTransport local, sem rede, resultado `RELEVANT 1.0 False` apesar de choice ausente:

```powershell
rtk proxy .venv/Scripts/python.exe -c "import asyncio,httpx;from prometeus.infrastructure.jev.client import TypeSafeJEVClient;from prometeus.domain.ports.decision_model import DecisionPack,DecisionType;pack=DecisionPack(pack_id='audit',decision_type=DecisionType.CHOICE,question='x',options=['RELEVANT','IRRELEVANT']);client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(200,json={'confidence':1})));m=TypeSafeJEVClient(api_key='offline',http_client=client);r=asyncio.run(m.execute_choice(pack,{}));print(r.selected_choice,r.confidence,r.requires_human_review);asyncio.run(client.aclose())"
```

Tradicional — FakeGenerativeModel local, resultado confidence1 e distribuição inválida mantida:

```powershell
rtk proxy .venv/Scripts/python.exe -c "import asyncio,json;from prometeus.domain.ports.decision_model import DecisionPack,DecisionType;from prometeus.infrastructure.llm.decision_adapter import LLMDecisionAdapter;from prometeus.infrastructure.llm.fake import FakeGenerativeModel;pack=DecisionPack(pack_id='audit',decision_type=DecisionType.CHOICE,question='x',options=['RELEVANT','IRRELEVANT']);llm=FakeGenerativeModel(canned_text=json.dumps({'selected_choice':'RELEVANT','confidence':True,'distribution':{'RELEVANT':-3,'INVENTED':99}}));r=asyncio.run(LLMDecisionAdapter(llm).execute_choice(pack,{}));print(r.confidence,r.distribution,r.requires_human_review)"
```

Os mocks acima testam validação local dos clientes, não comportamento observado dos fornecedores.
