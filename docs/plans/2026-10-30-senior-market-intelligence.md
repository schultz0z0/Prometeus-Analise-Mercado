# Plano de implementação — inteligência de mercado sênior ENS

> Execução futura: aplicar desenvolvimento orientado a testes e execução por tarefas, com revisão entre fases. Este documento é um plano; não declara a implementação concluída.

**Objetivo:** tornar mensurável, fiel e analiticamente útil o percurso briefing → pesquisa → dados → julgamento → scoring → parecer de viabilidade ENS, validando primeiro LLM tradicional e depois JEV + LLM.

**Arquitetura:** manter monólito modular, worker e limites de estado/fórmulas/orçamento em código. Introduzir observações tipadas, contratos por papel e avaliação por etapa. Especialistas são componentes do workflow com entradas/saídas verificáveis; não uma rede irrestrita de agentes autônomos.

**Stack:** Python, Pydantic, SQLAlchemy/PostgreSQL, Celery, provedores LLM/JEV atuais, Apify com Actors/builds allowlisted e frontend existente. Ferramenta externa de avaliação é opcional; não migrar autenticação ou orquestração como pré-requisito.

**Base:** [auditoria consolidada](../implementation/reports/senior-market-intelligence-audit-2026-10-30.md), [baseline congelado](../implementation/reports/senior-market-intelligence-baseline-2026-10-29.json) e [pacote de estudo](../Estudo_Prometeus_144_registros_73501c53_2026-10-29/COMO_ESTUDAR.md). Achados A01–A16 remetem ao relatório. Prioridade não equivale a estimativa de prazo: escopo e revisão humana determinam o calendário.

## Regras de execução

- Não alterar evidências/nota/dossiê de análises concluídas. Replays produzem artefatos separados; nova análise ou perfil recebe identidade/versão própria e vínculo ao baseline.
- Não baixar gates nem alterar pesos para fazer o teste aprovar. Preservar IPD 20/30/50 e até três comparáveis; mudanças de interpretação/perfil exigem validação explícita ENS e snapshot novo.
- Uma chamada paga só ocorre depois de testes offline da camada e com orçamento efetivo validado. Falha de parser não justifica comprar de novo o dado já salvo.
- Manter OAuth configurado e modelos autorizados; nenhuma chave nova é pré-requisito deste plano. Execuções reais devem registrar modelo, modo e tentativas.
- Dados de web/documentos são não confiáveis. PII textual é minimizada; campos técnicos tipados são preservados. Não colocar prompts, payloads ou credenciais em logs gerais.
- Não introduzir LangGraph, Agents SDK, MCP ou banco vetorial como dependência obrigatória sem problema e ganho demonstrados. Embeddings/reranking são candidatos a comparar contra baseline simples.
- Cada tarefa: escrever regressão, confirmar falha, implementar mínimo, confirmar teste, revisar efeitos, atualizar documentação. Commits são localizados por tarefa apenas na etapa de execução; este plano não autoriza commit dos trabalhos anteriores misturados.

## Visão por fases

| Fase | Prioridade | Entrega | Gate para avançar |
|---|---|---|---|
| 0 | imediata | Baseline, critérios e conjunto de referência | Contratos/denominadores claros e amostra adjudicada |
| 1 | bloqueadora | Fidelidade dos dados e respostas de IA estritas | Nenhuma perda crítica silenciosa nos 144; respostas inválidas nunca viram decisões válidas |
| 2 | alta | Inputs Apify, amostragem e recuperação corretos | Pergunta, recorte e input efetivo reconciliados; URLs com outcome |
| 3 | alta | Pesquisa/curadoria e analistas por finalidade | Qualidade por tarefa avaliada no gold; comparáveis e competências rastreáveis |
| 4 | alta | Gates alcançáveis, economia e SWOT | Regras versionadas e revisão ENS; fórmulas verificadas e cenários explícitos |
| 5 | alta | Dossiê sênior, avaliação e homologação tradicional | Integridade + factualidade + utilidade revisadas separadamente |
| 6 | posterior | Híbrido JEV validado em shadow | Não inferioridade por tarefa acordada; sem fallback semântico |

Dependências: 0 → 1 → 2 → 3; desenho de 4 pode começar após 0, mas validação depende de 1–3; 5 depende de 1–4. A correção do contrato JEV entra em 1; sua homologação real fica para 6. Não esperar o motor financeiro inteiro para reparar a perda de descrições ou os timestamps.

## Fase 0 — referência e observabilidade da qualidade

### Tarefa 0.1 — Fixar unidade, regras e denominadores

Criar `docs/testing/market-intelligence-evaluation.md` e um dicionário de métricas versionado. Registrar:

- `Capture`: uma observação de uma fonte/run/instante; `Entity`: curso/oferta/vaga/anúncio/comentário identificado; `Fact`: extração com fonte/trecho; `Judgment`: avaliação por finalidade; `Claim`: afirmação do parecer.
- Perguntas obrigatórias por categoria de curso e B2B/B2C, com evidência mínima apropriada; não exigir os mesmos canais para todos os públicos.
- Estados `observed`, `observed_zero`, `missing`, `unsupported`, `ambiguous`, `partial`, `censored` e `failed`, sem equivalência entre eles.
- Score do curso, qualidade dos dados, cobertura de perguntas e confiança do julgamento como objetos distintos.

Aceitação: todos os números do baseline se reproduzem com os mesmos arquivos e hashes; 144 = 17 + 73 + 54; metadados de teste/sintéticos/observados estão separados.

### Tarefa 0.2 — Rotular e adjudicar um conjunto de referência

Criar `tests/evaluation/market_intelligence/` com manifesto e schema de rótulos; armazenar conteúdo bruto sob a política institucional, mantendo fixtures pequenas e higienizadas no repositório quando permitido.

Campos por exemplo: fonte/entity/capture, recorte, campos críticos esperados, trechos, finalidade, utilidade (`direct`, `adjacent`, `context`, `irrelevant`, `insufficient`), categoria exata/família, ambiguidade, alegações permitidas, motivos e anotadores. A referência é humana e não o próprio output da IA antiga.

Dois revisores: especialista ENS de mercado/portfólio e revisor de dados/metodologia. Adjudicar desacordos materiais; marcar desconhecido quando a fonte não resolve. Incluir controles positivos, negativos, adjacentes, falsos cognatos e ausência legítima. Dividir por entidade/curso/domínio/período, não por captura duplicada.

Aceitação: manual de anotação com exemplos e desacordos registrados. Precisão/recall só são publicados depois de existir denominador rotulado. Os 144 iniciam a referência, mas não bastam para provar generalização a todo o portfólio ENS.

### Tarefa 0.3 — Auditoria por execução e orçamento observável

Arquivos: `src/prometeus/infrastructure/db/models.py`, `application/decision_service.py`, `application/create_analysis.py`, clientes LLM/JEV e migração nova após a cabeça Alembic real.

Adicionar `ExecutionEnvelope` por tentativa: análise/tenant, etapa, input hash, IDs/trechos de origem, schema/normalizador/projetor/sanitizador/pack/prompt/skills e versões, modelo efetivo, modo, tempo, resultado, tokens/uso quando retornados, custo medido ou explicitamente indisponível. Retenção institucional e acesso controlado; separar conteúdo de logs de operação.

Teste: troca de modelo/projetor/normalizador altera chave de cache; mesmo input/versões permite reuso; tentativa recusada permanece auditável; nenhum segredo no snapshot. Uso/custo desconhecido não é 0,0 “real”.

## Fase 1 — integridade e contratos antes de pesquisar mais

### Tarefa 1.1 — Observações canônicas por fonte

Criar `src/prometeus/domain/evidence_observations.py` e `infrastructure/apify/normalizers/`; manter compatibilidade com payload bruto.

Objetos: `OfferObservation`, `PriceObservation`, `JobObservation`, `TrendSeries`, `AdObservation`, `SocialObservation`, `PageAcquisition`. Cada campo material tem valor/unidade/status, JSON pointer ou página/trecho e data. Guardar bruto imutável e transformações versionadas; não inferir moeda, data, país ou tipo de formação ausentes.

Regressões em `tests/unit/application/test_source_observations.py` (novo): variantes de schema/build, `descriptionText`, listas aninhadas, datas numéricas, salário textual, preço parcelado, `hasData` e `isPartial` escalar/lista. Reordenar chaves ou acrescentar metadados irrelevantes não pode apagar campos críticos.

### Tarefa 1.2 — Sanitização por tipo e projeção por finalidade

Modificar `application/sanitization.py` e `application/qualify_market_evidence.py`. Substituir `json.dumps(... )[:14000]` por `build_qualification_context(observation, purpose, budget)` com política explícita de campos, trechos e métricas resumidas deterministicamente. Contexto longo deve ser particionado ou reduzido por campo; jamais cortar JSON arbitrariamente.

Testes primeiro:

1. Preservação exata dos timestamps dos 786 pontos Trends e de seus indicadores numéricos; campos de contato realmente pessoais continuam redigidos.
2. Série de 262 pontos recebe janela, contagem válida/ausente/parcial, densidade, métricas e evidências de pertinência dentro do contexto.
3. Descrições e requisitos das 16 vagas aceitas alcançam sua projeção; 28 descrições originais ficam disponíveis para fins aplicáveis.
4. Entrada maior que orçamento gera particionamento ou diagnóstico de omissão, nunca descarte silencioso do campo principal.
5. HTML/injection continuam tratados como dado não confiável; propriedade técnica não recebe privilégio de instrução.

Criar `tests/integration/market_sources/test_observation_retention.py`. Gate: zero corrupção crítica e zero corte silencioso no replay dos 144; preservar PII tests existentes. Não prometer retenção de todos os bytes em toda chamada: garantir os campos críticos por tarefa e informar omissões.

### Tarefa 1.3 — Integridade entre observações e base do redator

Modificar `application/synthesize_dossier.py`; redator consome fatos de observações tipadas, não uma lista oportunista de nomes de campos de cada Actor.

Entregar `EvidenceBrief`: perguntas, achados por finalidade, extratos de competência, ofertas e preços atribuídos, séries/métricas com denominadores, contraprovas e lacunas por causa. `IntegrityReport` compara source → observation → brief. “Descrição não disponível” só é permitido se não houver descrição extraível ou se houver falha explicitada.

Teste mínimo: todos os 16 registros de vagas usados em indicadores têm suas responsabilidades/requisitos disponíveis para o analista curricular; a disponibilidade não significa aderência automática. Revisor compara brief com observações, não apenas o texto final com o próprio brief.

### Tarefa 1.4 — Respostas inválidas jamais se tornam julgamento

Modificar `domain/ports/decision_model.py`, `infrastructure/llm/decision_adapter.py`, `infrastructure/jev/client.py` e `application/decision_service.py`.

Criar schema comum estrito: número finito e não booleano, faixas explícitas, choice obrigatório existente no pack, distribuição com labels permitidos, probabilidades válidas e normalização declarada, revisão/NOUL preservados. Não preencher primeira opção quando `choice` faltar. Suporte a variantes do fornecedor deve ser mapeamento documentado, nunca resposta semântica fabricada.

Novo `tests/contract/decisions/test_decision_response_integrity.py`: missing choice, unknown label, bool, NaN/Inf, negativo, soma inválida, score fora da faixa, revisão explícita, resposta parcial e indisponibilidade. Nenhum desses vira `RELEVANT`, `OBSERVED`, zero de score ou confiança 1 por default. Usar transporte estruturado da LLM quando suportado, mantendo validação em código.

Gate fase 1: falhas conhecidas reproduzidas em vermelho e corrigidas; replay determinístico integral; suite existente sem regressões; relatório de perdas antes/depois. Não executar reclassificação paga enquanto essas regressões não passarem.

## Fase 2 — uso correto da Apify e aquisição por pergunta

### Tarefa 2.1 — Capability e input efetivo reconciliados

Arquivos: `application/tool_capabilities.py`, `infrastructure/apify/registry.py`, `schemas.py`, `client.py`, `application/collect_market_evidence.py`.

Contrato por capability/build: pergunta que pode responder, input/output schema/hash, unidades de limite (`per_video`, `per_query`, `retained_total`), filtros suportados/traduzidos/pós-filtrados/indisponíveis, custo/teto, recência e modos de falha. Validar documentação oficial e schema do build pinado antes de alterar mappers.

Persistir `effective_actor_input` sem segredos e `effective_scope`. Corrigir broadening silencioso LinkedIn para “seguros”; preservá-lo apenas como ação explicitamente contextual. Aplicar janelas suportadas de Jobs/Meta/YouTube; quando não suportadas, pós-filtrar data observada e marcar desconhecido. Idioma ou IP de proxy não provam país.

Testes: cada parâmetro planejado tem tradução ou motivo de não aplicação; schema do input efetivo válido no build testado; texto da query não substitui filtros; todas as UFs brasileiras e localidades ambíguas cobertas pelo contrato geográfico.

### Tarefa 2.2 — Amostra e paginação em unidades corretas

Regressão de YouTube: dez URLs e `maxComments` por vídeo não podem virar quinze itens do primeiro vídeo sem diagnóstico. Separar limite remoto de coleta, paginação recebida e amostra retida; quotas por fonte/entidade/canal, com proveniência e taxa de aproveitamento. Dataset maior que itens lidos informa truncamento e critério.

Fontes com payload duplicado usam `Capture` separado de `Entity`: IDs de anúncios/vagas/comentários, URL de oferta com parâmetros semânticos e versão da condição. Preservar múltiplas capturas e contradições, mas não contar a mesma entidade como novos concorrentes.

Novo `tests/integration/market_sources/test_sampling_and_lineage.py`: três vídeos elegíveis, capturas duplicadas, paginação, teto financeiro, entidades com atualizações e falha parcial. Gate: nenhum cap por entidade interpretado como total; contagens e origem sempre reconciliadas.

### Tarefa 2.3 — URLs priorizadas e arquivos com outcome

Separar descoberta e aquisição em `collect_market_evidence.py`: priorizar por pergunta, tema/categoria, instituição, documento, fonte própria/externa e diversidade. Avaliar ranking com gold e baseline determinístico antes de adotar outro modelo.

Confirmação de páginas escolhidas usa profundidade zero quando aplicável ao Actor; exploração de catálogo é ação distinta. Cada URL tem `fetched`, `not_found`, `unsupported_type`, `blocked`, `budget_skipped` ou `extraction_failed`. PDF precisa caminho de extração com MIME, páginas/trechos, origem e data; não ativar Actors de resumo adicionais sem orçamento.

Testes: PDF priorizado tem outcome; 404 não vira oferta válida; URL interna malformada não consome silenciosamente a cota; informações de página não atual não viram oferta ativa.

### Tarefa 2.4 — Recuperação por causa e ganho marginal

Modificar `research_sufficiency.py`, `collection_diagnostics.py` e `plan_course_research.py`.

Antes de nova chamada, classificar lacuna `source_failure`, `unsupported_source`, `normalization_loss`, `context_projection_loss`, `qualification_uncertain`, `true_no_signal` ou `missing_primary_data`. Ação correspondente: reparar/reprocessar dado existente, ampliar fonte/recorte, pedir dado ENS, fazer pesquisa primária ou parar com limite explícito.

Dedup de consultas usa input efetivo normalizado, não só descrição de query. Reservar teto por pergunta/fonte e máximo de rodadas em código. Stop por redundância, baixo valor incremental, orçamento ou evidência suficiente; não por contagem genérica de chamadas.

Gate: dado persistido não é recomprado para resolver parser; cada follow-up tem lacuna, mudança de estratégia, custo e resultado incremental. Testar offline antes de um canary pago pequeno.

## Fase 3 — fortalecer o raciocínio de mercado

### Tarefa 3.1 — Plano orientado a decisão

Modificar `domain/research.py`, `application/plan_course_research.py`, `skills/planning-market-research/` e `skills/conducting-course-analysis/`. Acrescentar matriz pergunta → hipótese/contraprova → evidência desejada → fonte capaz → recorte → amostra → orçamento → suficiência → fallback/stop.

Trilhas separadas: concorrentes diretos por categoria/tema, ofertas adjacentes/substitutas, necessidades profissionais, busca educacional versus tema setorial, contexto econômico, dados primários ENS. Marcas indicadas pelo usuário são referências, não limite exclusivo da descoberta.

Revisar skills com especialista ENS. Cada mudança precisa de exemplos positivos/negativos e avaliação, não apenas transporte do texto no system prompt. Verificar que as skills efetivamente recebidas correspondem à etapa.

### Tarefa 3.2 — Curadoria por finalidade

Substituir um `accepted` universal por `EvidenceUseAssessment` por uso: descoberta, preço, concorrência direta/adjacente, competências, empregabilidade, demanda educacional, contexto próprio e setor. Qualidade baixa para uma finalidade não apaga outra.

O resultado registra fatores observáveis/trechos e motivo útil, sem exigir cadeia interna de raciocínio. Inconclusivo requer causa e próximo passo, e não confiança alta genérica que dispensa revisão material. Aumentar recall não pode promover conteúdo incompatível.

Reavaliar os 144 em sandbox após correções, com conjunto gold congelado. Publicar matriz de confusão por finalidade, falsos descartes/aceites, abstenção e custo. Não sobrescrever `_qualification` da análise original.

### Tarefa 3.3 — Comparabilidade, ofertas e currículo

Arquivos: `application/internal_history.py`, `pricing_reference.py`, `run_course_analysis.py`, `config/decision-packs/`, taxonomia institucional e respectivas skills.

Contratos: categoria comercial exata separada de família estatística; tema, público, nível, modalidade, carga e competências avaliados por dimensão. Cobrir MBA, Pós, graduação, extensão, imersão e certificação avançada. Pré-filtro determinístico + recuperação de candidatos + julgamento delimitado; comparar lexical/embeddings em avaliação, sem obrigatoriedade de nova infraestrutura.

IPD preserva regra ENS: no máximo três próximos, podendo devolver menos ou nenhum, referência da família/janela encerrada e fórmula 20/30/50 em código. Presença de grade não prova proximidade; confiança precisa refletir comparabilidade e natureza sintética. Mostrar exposição de mídia, capacidade e período quando disponíveis.

Preço: média por curso de mesmo tema/categoria, internos e concorrentes, conforme regra acordada; mostrar quantidades/médias por origem, dispersão e lacunas. Valor sem prazo/atribuição não vira total. Curso sem preço continua útil para outros usos. Não remover parâmetros semânticos da URL ao deduplicar.

Currículo: módulo → resultado de aprendizagem → competência/necessidade → fonte e trecho → cobertura/gap → ação. Composição da nota em código e interpretação coordenada pela ENS. Testes negativos incluem culinária/extensão, direitos humanos/litigância predatória, MBA/curso livre e textos de rodapé.

### Tarefa 3.4 — Demanda de alunos e contexto ENS

Adicionar `LearnerDemandCase`: comprador versus beneficiário, B2B/B2C, elegibilidade, intenção de formação, alternativas, barreiras, disposição declarada versus comportamento e cenário de alcance/funil.

Priorizar CRM/coortes reais, sinais de busca educacional e entrevistas/pilotos. SUSEP/CNseg/RAIS/Caged/IBGE/INEP informam contexto adequado; nenhum vira matrícula por multiplicador arbitrário. Validar fonte e recorte por indicador. Não iniciar campanhas, entrevistas com terceiros ou pesquisa comercial automaticamente nesta fase de código.

Gate fase 3: avaliação humana por finalidade e exemplos fora do desenvolvimento; metas iniciais de recall crítico ≥95%/precisão ≥90% são candidatas a acordo ENS, com denominadores e intervalos. Não usar percentual de registros aceitos nem taxa de APPROVED como meta.

## Fase 4 — critérios de decisão, SWOT e economia

### Tarefa 4.1 — Matriz de alcançabilidade e calibração

Criar `tests/integration/scoring/test_feature_reachability.py` e um inventário feature → normalizador/fonte → disponibilidade → qualidade → custo → efeito em confiança/gate. O controle positivo começa de payload realista do fornecedor e chega ao cálculo, não de features criadas só no teste.

Separar completude, pertinência, fonte, recência, diversidade, força inferencial e confiança do modelo. Rever agregação e gates com ENS e dados reais, mantendo antigo perfil disponível. Não mudar 75% para 59% por conveniência. Explicar casos em que mais dados reduzem confiança média e quando isso deve alterar recomendação.

Backtest temporal por oferta/coorte sem vazamento; comparar contra baseline humano e regra simples. Sintéticos exercitam fórmulas/contratos, não calibram sucesso comercial. Revisar sinal da concorrência paga por hipótese testável, sem simplesmente inverter a curva.

### Tarefa 4.2 — Motor econômico-financeiro

Criar `domain/economics.py`, `application/economics_service.py`, contratos de intake e testes `tests/unit/economics/` e `tests/integration/economics/`.

Inputs com origem e unidade: preço total, parcelas, descontos, inadimplência/estornos, tributos/taxas, docência/coordenação/produção, custo variável, mídia/comercial, capacidade, prazo e pagamentos. Usar Decimal e cronograma; separar duração acadêmica e recebimento.

Calcular margem de contribuição, resultado por turma, equilíbrio compatível com capacidade e fluxo mensal. Se aquisição é custo fixo de campanha, não descontar novamente CAC derivado dela; se CAC é por matrícula, explicitar a função. Margem não positiva e equilíbrio acima da capacidade são resultados, não exceções ocultas. NPV/payback só com taxa e cronograma validados.

Fixtures financeiras devem ser validadas com finanças ENS; cenários conservador/base/otimista identificam premissas, não probabilidades inventadas. Dados ausentes produzem `not_calculable` e solicitação objetiva. Score de preço não substitui essa avaliação.

### Tarefa 4.3 — Parecer estratégico e SWOT/TOWS

Criar schema de `MarketAssessment` e `StrategicAssessment`: pergunta, achado, evidências favoráveis/contrárias, premissas, materialidade, alternativas, lacuna e próximo teste. SWOT com dimensão interna/externa, fonte/trecho, natureza observada/inferida/hipótese, validade e efeito na decisão. TOWS relaciona estratégias a ações e responsáveis.

Testes: lacuna de dados não vira fraqueza comercial; nome ENS não prova reputação ou qualidade docente; vaga não vira demanda por curso; crescimento de prêmio de seguro não vira potencial de matrícula; fonte própria não vira concorrente externo.

Gate fase 4: fórmulas e unidades exatas em fixtures verificadas, critérios aprovados/versionados, ausência econômica explícita e nenhuma recomendação atribuída à LLM/JEV fora das regras em código.

## Fase 5 — redator, revisores e homologação do modo tradicional

### Tarefa 5.1 — Separar os três tipos de revisão

1. **Integridade dos dados:** source → observation → brief; conteúdo essencial não sumiu.
2. **Qualidade analítica sênior:** pesquisa adequada à pergunta, independência, materialidade, alternativas, proxies e contraprovas.
3. **Factualidade da redação:** números/unidades/identidades/claims e inferências sustentadas.

Contratos próprios, diagnósticos acionáveis e revisão limitada por causa. Um revisor sênior não precisa refazer todas as buscas; pede ação concreta ao módulo responsável. O redator recebe os pareceres e não escolhe pesos ou inventa a conclusão para melhorar o texto.

Modificar `domain/dossiers.py`, `application/dossier_generation_contract.py`, `synthesize_dossier.py`, `dossier_verifier.py`, `config/prompts/dossier-v1.yaml` e frontend. Versionar schema e compatibilidade de dossiês anteriores. Preservar estatísticas por origem, referências, exportação e desconhecidos.

### Tarefa 5.2 — Runner de avaliação e release de qualidade

Criar `scripts/evaluate_market_intelligence.py` e packs em `tests/evaluation/market_intelligence/`. Interface proposta, **ainda não existente**:

```powershell
rtk proxy .venv/Scripts/python.exe scripts/evaluate_market_intelligence.py --mode offline --manifest tests/evaluation/market_intelligence/manifest.json --output var/diagnostics/evaluation-candidate
```

O modo offline proíbe rede/modelos e valida transformações/contratos. O modo de modelo real é opt-in distinto, com limite de chamadas e custo/cota registrado; não repetir Actors. Comparar baseline/candidato com mesmo corpus/gold, mostrar confiança/abstenção e falhas por camada. Promptfoo pode ser usado como runner opcional, sujeito a validação de integração, sem dependência da plataforma legada OpenAI Evals.

Adicionar casos de redator certo/revisor errado, redator errado/revisor certo e base incompleta/revisor factual satisfeito. Repetições controladas de decisões probabilísticas medem variabilidade, sem multiplicar execuções até aparecer um resultado favorável.

### Tarefa 5.3 — Canary e E2E real com avaliação de utilidade

Só após gates offline/gold, validar integração real em lote pequeno com orçamento explícito. Usar briefings de pelo menos três contextos distintos como ponto de partida, ampliando por categoria: caso com boa evidência, caso adjacente/ambíguo e insuficiência legítima. Três casos não demonstram desempenho estatístico geral.

E2E pela interface: upload, extração, entendimento, plano, inputs efetivos, coleta, qualidade, análise, score/economia, redação, três revisões, publicação, evidências, reload e exportação. Validar conteúdo por painel ENS; conclusão técnica e nota analítica são gates separados. Não chamar “100% homologado” ao terminar uma execução.

Critérios propostos: todas as claims materiais rastreáveis; nenhuma omissão material sem pendência; pontuação humana ≥4/5 em resposta à decisão, triangulação, contraprovas, limites e próximos passos, com adjudicação de discordâncias. Não substituir painel humano por autoavaliação da mesma LLM.

## Fase 6 — JEV híbrido, após baseline tradicional

Usar o mesmo schema de observação, contexto, packs, rubricas e conjunto não visto; substituir apenas decisões atômicas selecionadas. Corrigir a leitura de resposta na fase 1 não equivale a homologar fornecedor JEV.

Rodar shadow sem alterar resultado de produção: precisão/recall por finalidade, abstenção, calibração, score/choice, custo, latência e divergências. Fixar versão de modelo; limiar de não inferioridade é acordado por tarefa e risco antes da comparação, sem escolher depois para favorecer um provedor.

Agregação, fórmulas, orçamento, estados, autorização e recomendações permanecem em código. Planejamento, narrativa e integração do parecer continuam com LLM tradicional. Se uma tarefa não apresentar benefício mensurável com JEV, manter a rota tradicional nessa tarefa quando o desenho aprovado permitir.

## Plano de skills e ferramentas

Revisar primeiro as dez skills existentes; mapear regra → etapa → trecho/contrato → teste de comportamento. Skills adicionais candidatas: `evaluating-education-market`, `analyzing-course-competition`, `mapping-workforce-competencies`, `assessing-learner-demand`, `reviewing-market-assessments`, `explaining-course-economics`. Os nomes são proposta, não arquivos instalados.

Preferir núcleo geral de método ENS + procedimentos por fonte complexa + contratos por Actor. Não criar uma skill longa e quase idêntica para cada Actor simples. Separar conhecimento versionado (taxonomia/recorte/fontes) de regras executáveis (budget, fórmula, validação) e de dados de pesquisa.

Reaproveitar procedimentos oficiais Apify e frameworks competitivos após auditoria de licença, versão, conteúdo e avaliação. MCP Apify é opcional para manutenção/discovery; produção continua allowlisted. Instalar uma skill no Codex não a disponibiliza automaticamente ao runtime Prometeus: exige registry, snapshot e teste de uso efetivo.

Novas fontes só entram quando respondem a uma lacuna nomeada: Keyword Planner para volume educacional; Indeed/empregadores para triangulação; dados ENS reais para aquisição/economia; fontes setoriais para contexto. Não adicionar canais sociais genéricos para aumentar número de ferramentas.

## Verificação em cada fase

Comandos existentes, ajustados aos arquivos de teste da tarefa:

```powershell
rtk proxy .venv/Scripts/python.exe -m pytest tests/unit tests/contract tests/integration -q --tb=short
rtk proxy .venv/Scripts/python.exe -m mypy src
rtk proxy .venv/Scripts/python.exe -m ruff check src tests
rtk proxy .venv/Scripts/python.exe scripts/validate_docs.py
rtk git diff --check
```

Não executar a suíte completa a cada edição de documentação. Regressões da camada primeiro; ampliar os testes quando mudar comportamento transversal. Chamadas reais não pertencem ao teste padrão e nunca devem acontecer em CI de terceiros por acidente.

Cada fase entrega relatório: o que mudou, achados cobertos, dados de teste, medidas antes/depois, falhas remanescentes, versões, custo e decisão de prosseguir. Novos ADRs são necessários para alteração de governança/scoring ou extração de módulo; não para cada correção de normalizador.

## Dados e decisões ENS que ainda serão necessários

- Rubrica humana de relevância e comparabilidade, sobretudo categoria exata versus família estatística.
- Exportação real mínima por curso/oferta/coorte: funil, janela, cancelamentos, preço/receita, gasto de aquisição e modalidade; sem PII individual desnecessária.
- Custos e capacidade da nova oferta, cronograma e política de descontos/recebimento.
- Critérios de risco e aprovação institucional, hipóteses de piloto e quem adjudica os casos gold.
- Acesso autorizado a novas fontes apenas quando a fase correspondente demonstrar necessidade.

Essas dependências não impedem corrigir já as perdas determinísticas e preparar o replay. São necessárias para chamar a solução final de análise comercial validada, em vez de demonstração técnica com histórico sintético.
