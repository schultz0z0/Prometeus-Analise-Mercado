# Changelog

## Fase 6 — JEV Híbrido, após Baseline Tradicional (2026-10-30)

- Criada a modelagem de domínio para orquestração de Shadow Mode e avaliação de não inferioridade em `src/prometeus/domain/shadow_decisions.py` (`DivergenceCategory`, `ShadowComparisonRecord`, `TaskNonInferiorityCriteria`, `NonInferiorityEvaluation`), em estrito cumprimento ao ADR-0008.
- Implementado o serviço de execução shadow `ShadowDecisionService` em `src/prometeus/application/shadow_decision_service.py`, executando o modelo shadow em sandbox isolado com blast radius zero: falhas externas, timeouts ou indisponibilidades do JEV não afetam nem atrasam o resultado entregue pela rota de produção primária.
- Implementado o avaliador de não inferioridade `NonInferiorityEvaluator` em `src/prometeus/application/non_inferiority_service.py`, comparando os registros shadow acumulados contra limiares acordados de concordância, abstenção e latência por tarefa (`pack_id`).
- Atualizadas as camadas de configuração e preflight em `src/prometeus/domain/configuration.py`, `src/prometeus/application/runtime_preflight.py` e a fábrica de IA em `src/prometeus/infrastructure/factory.py`, adicionando suporte a `AI_MODE="shadow"` e a função construtora `get_shadow_decision_service`.
- Expandido o runner de avaliação contínua em `scripts/evaluate_market_intelligence.py` com a flag `--shadow`, exportando `var/diagnostics/evaluation-candidate/shadow_evaluation.json` e incluindo a Seção 6 ("Avaliação Shadow Mode e Não Inferioridade JEV") no relatório executivo Markdown.
- Homologação por tarefa com duplo desfecho: aprovação seletiva para a rota híbrida do pack `keywords-relevance-v1` (100% de concordância, abstenção zero, ganho de 33.5ms de latência) e retenção integral da rota tradicional para o pack `evidence-support-v1` (concordância de 90.0% abaixo do limiar de 95.0% exigido para suporte factual crítico).
- Criados testes unitários, contratuais e de integração (`tests/unit/decisions/test_shadow_decision_service.py`, `tests/evaluation/market_intelligence/test_jev_non_inferiority.py`, `tests/integration/decisions/test_jev_shadow_execution.py`), totalizando 575 testes passando em todas as suítes (0 falhas, 0 regressões).

- Criada a arquitetura de revisão tripartite em `src/prometeus/domain/dossiers.py` (`DataIntegrityReview`, `SeniorAnalyticalReview`, `FactualDraftingReview`, `ThreeFoldDossierReview`), desacoplando a auditoria da integridade dos dados (`source → observation → brief`), a avaliação da qualidade analítica sênior e a factualidade da redação com diagnósticos acionáveis atribuídos aos módulos de origem.
- Implementado o verificador tripartite em `src/prometeus/application/dossier_verifier.py`, codificando 10 regras analíticas sênior de validação em código (proibição de vagas como matrículas diretas, vedação de multiplicadores diretos sobre prêmios de seguro, separação de cursos livres de MBAs acadêmicos, independência institucional da ENS contra concorrência externa fantasma e bloqueio de inferências sobre URLs 404).
- Versionado o contrato de geração de dossiês em `src/prometeus/application/dossier_generation_contract.py` (suporte a schemas 2 e 3) e atualizada a persistência em `src/prometeus/application/synthesize_dossier.py` e endpoints REST em `src/prometeus/entrypoints/rest/app.py`.
- Criado o runner executável de avaliação contínua em `scripts/evaluate_market_intelligence.py` com modo offline determinístico estrito que proíbe rede e modelos pagos, alcançando 100% de preservação de campos críticos e 10/10 de bloqueio de afirmações adversariais no manifesto human gold standard.
- Criada a suíte de testes de casos adversariais em `tests/evaluation/market_intelligence/test_adversarial_review_cases.py` cobrindo *redator certo / revisor errado*, *redator errado / revisor certo* e *base incompleta / revisor factual satisfeito*.
- Implementada a suíte Canary E2E em `tests/e2e/test_three_fold_canary_evaluation.py` validando os 3 contextos canônicos: caso com boa evidência (MBA consolidado), caso adjacente/ambíguo (curso de fronteira) e caso de carência probatória legítima (`INSUFFICIENT_EVIDENCE`), assegurando o desacoplamento estrito entre cálculo técnico e nota analítica.
- Atualizada a interface visual em `web/js/views/dossier-view.js` com o componente `renderThreeFoldReview` exibindo o status de homologação e pareceres de cada uma das três frentes de revisão.

## Fase 4 — Critérios de Decisão, SWOT e Economia (2026-10-30)

- Criado o inventário canônico de features de viabilidade em `src/prometeus/domain/scoring/feature_inventory.py`, mapeando cada feature a sua capacidade, normalizador, dimensões estritas de qualidade (`completeness`, `relevance`, `recency`, `diversity`, `inferential_strength`), custo e efeitos específicos nos gates de release.
- Implementado teste de integração de alcançabilidade ponta a ponta (`tests/integration/scoring/test_feature_reachability.py`), validando a progressão de payloads de fornecedores reais até os gates de qualidade, a degradação apropriada de confiança com dados ruidosos e a inviolabilidade dos limiares de release do perfil `portfolio-v2` (confiança mínima de 75% e cobertura mínima de 80%).
- Criado o domínio financeiro em `src/prometeus/domain/economics.py` (`CourseEconomicsInput`, `ScenarioProjection`, `CashFlowMonth`, `CourseEconomicsEvaluation`) com precisão exata em `Decimal` e separação entre prazo acadêmico e financeiro.
- Implementado o serviço determinístico `CourseEconomicsService` em `src/prometeus/application/economics_service.py` calculando receita líquida por aluno (deduzindo descontos, inadimplência e impostos), margem de contribuição, ponto de equilíbrio (break-even em alunos), compatibilidade com a capacidade máxima da turma, projeção de 3 cenários (conservador, base, otimista) com premissas transparentes, cronograma de fluxo de caixa mensal e regra de não duplicação de CAC quando campanha fixa de marketing é informada, com retorno estrito de `status="not_calculable"` para dados ausentes.
- Criada a modelagem de parecer estratégico em `src/prometeus/domain/strategic_assessment.py` (`MarketFinding`, `SWOTItem`, `TOWSAction`, `StrategicAssessment`), vinculando achados a contraprovas e estratégias TOWS a ações e áreas responsáveis.
- Implementado o serviço `StrategicAssessmentService` em `src/prometeus/application/strategic_assessment_service.py` codificando as 5 regras analíticas estritas da ENS: proibição de lacuna de dados como fraqueza comercial; proibição de reputação institucional genérica como prova de qualidade docente de curso novo; proibição de vaga de emprego como demanda direta de matrícula; proibição de crescimento de prêmios de seguro (SUSEP) como potencial de matrícula; e proibição de oferta própria como ameaça concorrente externa.


- Criadas 6 trilhas canônicas de pesquisa (`direct_competitors`, `adjacent_offers`, `workforce_needs`, `educational_search`, `economic_context`, `primary_institutional`) em `src/prometeus/domain/research.py` (`ResearchTrack`).
- Estruturada matriz de decisão completa em `ResearchQuestion`: pergunta → hipótese/contraprova → evidência desejada → fonte capaz → recorte → amostra → orçamento → critério de suficiência → fallback/stop.
- Atualizado o planejador `CourseResearchPlanner` em `src/prometeus/application/plan_course_research.py` e as skills de planejamento (`planning-market-research`, `conducting-course-analysis`), tratando marcas indicadas pelo usuário em `supplied_materials` ou descrição como referências/sementes de descoberta inicial e nunca como limites exclusivos da busca.
- Substituído o campo binário destrutivo `accepted` por curadoria multidimensional por finalidade (`EvidencePurpose`, `EvidenceUseAssessment`, `MultiPurposeAssessment`) em `src/prometeus/domain/evidence_observations.py` e `src/prometeus/application/qualify_market_evidence.py`, permitindo que evidências sem preço (ex.: ofertas de cursos sob consulta) permaneçam úteis para concorrência direta e descoberta, e que itens inconclusivos registrem causa e próximo passo sem confiança inflada.
- Eliminados falsos matches temáticos gerados por formatos acadêmicos em `src/prometeus/application/internal_history.py`, incluindo stopwords de categoria de cursos (`extensao`, `especializacao`, `capacitacao`, `treinamento`, `imersao`, `certificacao`, etc.) para impedir que "Extensão em Culinária" coincida com "Extensão em Fraudes".
- Instituído piso determinístico de similaridade mínima (`fit >= 0.15`) no `InternalHistoryService`, garantindo retorno determinístico de 0, 1, 2 ou 3 comparáveis reais e calibrando a confiança do IPD pela similaridade média real dos cursos encontrados em vez de contagem arbitrária de campos.
- Preservados parâmetros semânticos de query na deduplicação de URLs em `src/prometeus/application/pricing_reference.py` (`_canonical`), descartando apenas parâmetros de rastreamento (`utm_*`, `fbclid`, `gclid`), e adicionado cálculo de dispersão e gap de preços entre interno e concorrentes externos.
- Criado o modelo `CurriculumMappingItem` em `src/prometeus/domain/research.py` mapeando módulo → resultado de aprendizagem → competência/necessidade → fonte/trecho → cobertura/gap → ação recomendada.
- Formalizado o modelo `LearnerDemandCase` em `src/prometeus/domain/research.py`, modelando comprador vs beneficiário, B2B vs B2C, elegibilidade, intenção, alternativas, barreiras e funil de conversão da primeira turma, com validador estrito proibindo o uso de dados macroeconômicos (SUSEP, CNseg, etc.) como multiplicadores diretos de matrícula.


- Reconciliados contratos de capability e input efetivo em `src/prometeus/application/tool_capabilities.py`, `src/prometeus/infrastructure/apify/registry.py` e `src/prometeus/application/collect_market_evidence.py`, com especificação de unidade de limite (`per_video`, `per_query`, `retained_total`), eliminação de broadening silencioso não solicitado e persistência de `effective_actor_input` e `effective_scope`.
- Cobertura integral das 27 UFs brasileiras e resolução de ambiguidades geográficas em `src/prometeus/application/research_scope.py` e `src/prometeus/application/evidence_features.py`, corrigindo omissão de estados (`AL`, `MA`, `MT`, `MS`, `SC`).
- Resolução da regressão de amostragem do YouTube: implementada amostragem estratificada por vídeo em `CollectMarketEvidenceService._normalized_items` e paginação no cliente Apify, garantindo distribuição justa de quotas quando múltiplos vídeos são consultados e registrando diagnósticos de truncamento em `audit["sampling"]`.
- Separação canônica entre Captura (observação pontual no tempo) e Entidade (ativo real de mercado) em `src/prometeus/domain/market_entities.py` (`MarketEntity`, `MarketCapture`, `EntityLineageTracker`), preservando versões e contradições sem inflar contagens de concorrentes.
- Rankeamento determinístico e priorização de URLs para crawling com diversidade de domínios (máximo 2 URLs por domínio), rejeição prévia de URLs malformadas, configuração de `maxCrawlDepth=0` para confirmação de páginas alvo e registro explícito de outcomes técnicos por URL (`fetched`, `not_found`, `blocked`, `unsupported_type`, `budget_skipped`, `extraction_failed`), assegurando que páginas 404 jamais virem ofertas válidas.
- Classificador causal de lacunas de pesquisa nas 7 causas canônicas em `src/prometeus/application/research_sufficiency.py` e enriquecimento de diagnósticos em `collection_diagnostics.py`, garantindo que dados persistidos nunca sejam recomprados para resolver perdas locais de normalização ou projeção.
- Deduplicação de consultas no planejador de pesquisa em `src/prometeus/application/plan_course_research.py` baseada em assinaturas normalizadas de input efetivo com eliminação de stopwords.

- Criadas observações canônicas por fonte em `src/prometeus/domain/evidence_observations.py` e normalizadores em `src/prometeus/infrastructure/apify/normalizers/`, com cobertura unitária para variantes de schema, listas/escalares e preservação de proveniência.
- Sanitização por tipo em `src/prometeus/application/sanitization.py`: protegidos 786 timestamps numéricos de séries Google Trends contra corrupção por regex de telefone, mantendo higienização estrita de CPF, e-mail e telefones reais de contato.
- Projeção determinística por finalidade em `src/prometeus/application/evidence_projection.py`: substituído truncamento cego `json.dumps(...)[:14000]` por `build_qualification_context(obs, purpose, budget)`, garantindo que séries temporais (janela, densidade, métricas) e descrições completas de vagas alcancem a IA com diagnósticos explícitos de omissão em estouro de orçamento.
- Relatório de integridade e passagem de dados ao redator em `src/prometeus/domain/dossiers.py` (`IntegrityReport`) e `src/prometeus/application/synthesize_dossier.py`: descrições e competências de todas as 16 vagas aceitas entregues nos fatos de mercado sem falsos "Descrição não disponível".
- Contratos estritos de respostas de julgamento em `src/prometeus/domain/ports/decision_model.py`, `LLMDecisionAdapter` e `TypeSafeJEVClient`: banidos defaults semânticos (`RELEVANT`, `OBSERVED`, score 0, primeira opção do pack) para ausência de escolha, NaN/Inf, booleanos ou distribuições inválidas.

## Fase 0 — Referência e Observabilidade da Qualidade (2026-10-30)

- Criado `docs/testing/market-intelligence-evaluation.md` com dicionário de métricas 1.0.0, ontologia das 5 unidades (`Capture`, `Entity`, `Fact`, `Judgment`, `Claim`), 8 estados de observação e matriz B2B/B2C por categoria de curso.
- Implementado conjunto de referência humano em `tests/evaluation/market_intelligence/` com schema de rótulos, manual de anotação com dupla revisão independente, manifesto com controles positivos, negativos, adjacentes, falsos cognatos e ausência legítima, e modelo de domínio em `src/prometeus/domain/evaluation.py`.
- Adicionado `ExecutionEnvelope` por tentativa em `src/prometeus/domain/execution_envelope.py` e persistência relacional com migration Alembic `0011_execution_envelopes.py`.
- Integrada telemetria em clientes LLM (`OpenAIGenerativeClient`, `ChatGPTPlanGenerativeClient`) e JEV (`TypeSafeJEVClient`), preservando custo e uso desconhecidos como explicitamente indisponíveis em vez de 0,0 real.
- Invalidação de cache configurada em `EvidenceQualificationService` por modelo, projetor ou versão, com reutilização determinística de julgamentos em execuções idênticas e isolamento total de segredos em snapshots.

## Auditoria e planejamento — 2026-10-30

- Auditoria consolidada de aquisição Apify, sanitização, projeção, decisões tradicional/JEV, scoring e metodologia de viabilidade ENS; baseline reproduzido dos 144 registros e apêndices por frente.
- Plano de melhoria em sete fases, com contratos por papel, avaliação humana por finalidade, replay, integridade dos dados, alcançabilidade/calibração de gates, análise econômica e SWOT, homologação tradicional e shadow híbrido. Sem mudanças de runtime, pesos, resultados ou novas coletas nesta auditoria.

- Homologação E2E real concluída com recuperação em 29/10: quinze checkpoints, onze claims verificadas e dossiê publicado; schema restringe também IDs/vínculos de claims (inclusive prós/contras), com enum dos IDs reais na revisão e prompt 3.0.1.

- Correção detectada no E2E real: título de evidência respeita o limite após ocultação de PII, com conteúdo completo preservado; rollback antes de registrar falhas de persistência evita análise presa em RUNNING e remove parâmetros SQL do diagnóstico público.
- Interface reabre acompanhamento por ID após recarregar/fechar o navegador, usando checkpoints e metadados persistidos, sem reiniciar processamento; valida a instituição selecionada.

## Não lançado — auditoria estrutural da etapa 13 (2026-10-29)

- unificados os fatos citáveis de resultado, definições de cobertura/confiança e caráter experimental para redação e verificação, com inclusão no hash factual;
- fonte histórica passa a expor IPD calculado, confiança e escala do pilar presente, corrigindo nomes de features antigos;
- saída de dossiê usa JSON Schema estrito nos transportes OpenAI/OAuth, com referências limitadas aos fatos existentes e listas de suporte não vazias;
- problemas semânticos são reunidos por claim/bloco com referências, escolha e confiança, até quarenta alvos; nenhuma referência é acrescentada automaticamente;
- erros iniciais de contrato entram na mesma única revisão, com rascunhos/diagnósticos preservados e publicação ainda condicionada aos dois gates;
- incluídos script opt-in de auditoria com LLM real, controles reais positivos/negativos e homologação E2E pela interface; artefatos locais de navegador ficam fora do Git.

## Não lançado — contratos factuais da segunda homologação (2026-10-29)

- verificador reconhece `16h` e outras unidades compactas permitidas; booleanos não autorizam números;
- fatos citáveis da proposta passam a incluir o total calculado com parcela/quantidade explícitas, preservando duração acadêmica independente;
- histórico expõe natureza sintética, quantidade de comparáveis, tamanho da família e período; pack de suporte 1.1.0 distingue descrição de registros e comprovação de demanda real;
- `buildNumber` nulo é reconciliado por GET da run/build real, sem presumir o build configurado e sem aceitar versão divergente;
- diagnóstico numérico conserva IDs das fontes citadas para reprodução de falhas; sem alteração retroativa de análises.
- healthcheck do worker consulta apenas o próprio nó e permite tempo de inicialização do comando, preservando falha quando não há resposta; corrigido falso alerta de timeout observado no Docker Desktop.

## Não lançado — revisão delimitada do dossiê (2026-10-29)

- incluída uma tentativa de revisão da redação após recusa factual ou semântica, reutilizando os fatos aprovados e o diagnóstico do rascunho;
- preservado diagnóstico no checkpoint antes da revisão; cópias independentes impedem que o adaptador altere a base factual usada pelo verificador;
- revisão passa novamente por todos os gates; falha persistente ou indisponibilidade mantém o bloqueio sem publicar fallback nem repetir consultas Apify;
- auditoria registra contagem de gerações e recusas anteriores; painel distingue revisão em andamento de bloqueio final; prompt atualizado para 2.2.0.

## Não lançado — diagnóstico da homologação e retornos parciais (2026-10-29)

- rejeições determinísticas do dossiê preservam motivo, referência e trecho limitado no checkpoint, sem publicar o conteúdo recusado ou afrouxar o gate;
- timeout com aborto remoto terminal confirmado permite ler itens já persistidos, mantendo Actor/build/schema, sanitização e qualificação; consulta fica `PARTIAL`, com lacuna explícita e reuso sem nova cobrança;
- custo observado e dataset de timeout confirmado permanecem no checkpoint, mesmo sem itens utilizáveis;
- resposta Instagram `no_items` é auditada como diagnóstico do provedor, sem virar post, mudança de schema ou demanda zero;
- corrigido acesso a `event.currentTarget` após `await` na sincronização histórica e atualizada a versão dos módulos web.

## Não lançado — skills de workflow completo e operação Apify (2026-10-29)

- adicionadas orientação transversal do fluxo e operação geral Apify, mais procedimentos dedicados a Trends, vagas e ofertas/preços, todos vinculados aos critérios de scoring existentes;
- composição de system prompts por etapa/fonte allowlisted, com snapshots/hash e invalidação de qualificação quando as orientações locais mudam;
- corrigida aplicação das skills de síntese, antes anexadas à geração de keywords; keywords agora recebem orientação apropriada de planejamento;
- recuperação recebe diagnóstico por consulta, distinguindo execução bem-sucedida e evidência útil; limites de orçamento/rodadas preservados;
- testes capturam os prompts efetivos de entendimento, keywords, planejamento/recuperação, síntese e qualificação das dez fontes, sem chamar Actors pagos.

## Não lançado — verificação de LLM tradicional e Apify (2026-10-28)

- fixado o deployment local em `AI_MODE=traditional` para a homologação solicitada, com confirmação do adaptador e provedor em API/worker;
- corrigido rótulo de modo em configurações: presença de chave JEV não significa modo híbrido ativo;
- ampliado teste opt-in de metadados reais para os dez Actors configurados e entradas dos builders, sem iniciar coletas pagas; preservados testes locais do fluxo tradicional e falhas de fontes.

## Não lançado — ampliação autorizada do histórico de teste (2026-10-28)

- ampliado o histórico de teste ENS para 33 cursos e 66 ofertas simuladas de 2024–2025: dez por família principal e exemplos separados de Graduação, Imersão e Certificação Avançada;
- conferidos nome e categoria de doze cursos em fontes oficiais ENS; referências acadêmicas não atribuem autenticidade aos funis, grades ou preços simulados;
- incluídos grades, famílias, fechamento/completude e tickets totais explícitos, preservando os cinco IDs e os números anteriores; cenários incluem desempenho variado e cancelamentos;
- API e portfólio identificam a base sintética e expõem metadados para inspeção; carga idempotente sem reset ou recálculo de dossiês anteriores;
- testes verificam integridade da fixture, repetição da carga e cálculo efetivo de IPD/comparação de preço usando os comparáveis selecionados.

## Não lançado — IPD, scoring v2 e orientação por fonte (2026-10-28)

- perfil `portfolio-v2` para novas análises: IPD 20/30/50 por família, até três comparáveis, score observado separado da cobertura e blocos interno/externo/aderência/preço;
- média dos preços totais de cursos comparáveis internos e externos com origem e condições; preços ambíguos, taxas e ofertas próprias não viram benchmark concorrente;
- corrigidos escopo geográfico descritivo, preservação de restrições locais, IDs públicos de vagas e deduplicação após sanitização;
- qualificação por finalidade, contexto preservado e motivos auditáveis; Trends recebe termos independentes e recuperação limitada por orçamento;
- reforçadas cinco skills existentes, contratos de onze capacidades e prompts/rubricas; corrigido envio das rubricas aos adaptadores e preservado pedido explícito de revisão até a recomendação;
- migração aditiva `0010_historical_ipd_metadata`, sem inventar grades/status/unidade de preço; análises concluídas permanecem imutáveis. Homologação real do novo perfil permanece manual.

## Não lançado — auditoria da homologação manual e IPD (2026-10-28)

- auditada a análise manual do MBA, com reconciliação da nota e identificação de falhas em geografia, IDs de vagas, contexto institucional, histórico, precificação e confiança curricular;
- registrada proposta para histórico com até três comparáveis e IPD 20/30/50 por família, avaliação externa separada, preço médio combinado e consolidação versionada; nenhuma mudança de runtime nem recálculo da análise nesta etapa.

## Não lançado — continuidade com coleta parcial (2026-10-28)

- falhas de Actors, timeout, orçamento esgotado e conteúdo inutilizável passam a ser registrados por consulta; a análise continua com as evidências disponíveis, inclusive quando a fonte era prioritária;
- retomada reaproveita resultados terminais sem repetir a cobrança; lacunas permanecem no dossiê e limitam a recomendação determinística;
- removido encerramento artificial do acompanhamento após cinco minutos; o painel tenta recuperar a conexão e mostra lacunas individuais de fontes;
- iniciada homologação real pela interface com o programa MBA Gestão Avançada de Seguros enviado pelo usuário.
- corrigida extração real de PDF no intake; arquivos sem texto não substituem a ementa por metadados. Prazo de pagamento separado da duração acadêmica e preço total calculado em código.
- homologação identificou e corrigiu idioma descritivo enviado ao Google, nota de modalidade confundida com escopo geográfico e perda do formulário durante sincronização; extração do PDF foi conferida por hash, sem corte silencioso no entendimento.
- timeout de polling Apify solicita aborto remoto e mantém Run ID para reconciliação; falha do cancelamento permanece explícita, sem mascarar o timeout original.

## Não lançado — pesquisa qualificada, dossiê executivo e seleção OAuth (2026-10-28)

- corrigidos sanitização recursiva, dependências de coleta, URLs de vídeo, rejeição de metadados sociais e normalização individual de resultados do Google;
- acrescentados catálogo por fonte configurada, qualificação semântica por evidência, deduplicação de entidades e distinção entre ausência, zero observado e amostra rejeitada;
- normalizados Trends e comparação de preços com moeda/periodicidade; pesquisa complementar limitada a uma rodada dentro do orçamento original;
- introduzido contrato de apresentação v2 com destaques, comparação de ofertas, relação ementa/necessidade, critérios pendentes e ações propostas vinculadas a claims;
- removida a reclassificação que escondia falhas numéricas; verificação cobre todos os blocos e o workflow agrega julgamento semântico de suporte;
- atualizado dashboard executivo com rótulos em português, limites da pesquisa, pilares ausentes explicados e inspeção filtrada com navegação por teclado;
- corrigida seleção de modelos ChatGPT OAuth por catálogo real da conta, persistência coerente e rollback que preserva tokens renovados;
- aplicada migração aditiva `0009_dossier_presentation` e atualizados serviços locais, preservando os oito dossiês existentes. Homologação de novas análises reais permanece pendente.

## Não lançado — validação do fluxo e auditoria (2026-10-28)

- alinhada a documentação do fluxo, da fase JEV e da política de redação aos modos tradicional e híbrido do ADR-0008;
- registrada auditoria prévia de coleta, suficiência de evidências, verificação factual e apresentação do dossiê, com consultas locais e reproduções offline; nenhuma correção de runtime foi aplicada nesta etapa.

## Não lançado — runtime factual em tempo real (2026-10-27)

- substituído o fluxo demonstrativo por um workflow real de 15 etapas com preflight, checkpoints, `tool_runs` e bloqueio explícito;
- integrada coleta Apify real para busca, crawling, Meta Ads Library, LinkedIn, LinkedIn Jobs e redes sociais, com Actors/builds pinados, orçamento e proveniência;
- removidos fallbacks, scores, dossiês e tokens OAuth fabricados do runtime e da interface;
- implementado modo tradicional completo sem JEV e preservado o modo híbrido opcional;
- implementado Sign in with ChatGPT para aplicações locais/open source, incluindo PKCE, state, nonce, validação de ID token e escopo, catálogo real de modelos, prova de inferência, armazenamento protegido e refresh rotativo;
- corrigida persistência de configurações de ambiente (.env) para suportar containers Docker com bind mounts e usuários não-root, eliminando falhas de permissão no callback ChatGPT OAuth e nos ajustes da API;
- mantida como única fonte sintética autorizada a base histórica da ENS, claramente identificada e restrita à comparação;
- dossiê passou a exigir evidência persistida, scoring determinístico e verificação de claims antes da entrega.

