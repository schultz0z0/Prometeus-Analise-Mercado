# Validação do fluxo e auditoria prévia das melhorias

**Produto:** Prometeus — Inteligência para Produtos Educacionais  
**Mantenedora:** Agência Prometeus  
**Data:** 2026-10-28  
**Escopo:** validar o fluxo enviado pelo responsável do produto e conferir `relatorio.md` antes de alterar o runtime.  
**Resultado:** diagnóstico concluído; documentação dos modos alinhada; melhorias de runtime propostas, ainda não implementadas.

## 1. Validação do fluxo da imagem

O fluxo é adequado como arquitetura de referência, com as responsabilidades abaixo. “LLM tradicional em tudo” significa todas as tarefas de IA; coleta e cálculos continuam sob controle do código.

| Etapa | JEV desativado | JEV ativado | Responsabilidade do código |
|---|---|---|---|
| Briefing e entendimento | LLM tradicional | LLM tradicional | Schema, campos obrigatórios, snapshot |
| Prontidão e pertinência de palavras-chave | LLM tradicional | JEV | Contratos, opções, limites e revisão |
| Planejamento da pesquisa | LLM tradicional | LLM tradicional | Fontes habilitadas, dependências e orçamento |
| Histórico, coleta e preparação | Adaptadores e código | Adaptadores e código | APIs, normalização, deduplicação e proveniência |
| Julgamentos semânticos | LLM tradicional | JEV | Packs atômicos, validação e encaminhamento para revisão |
| Indicadores e score consolidado | Código | Código | Fórmulas, pesos, cobertura e quality gates |
| Dashboard | Dados persistidos | Dados persistidos | Formatação e navegação nas evidências |
| Redação do dossiê | LLM tradicional | LLM tradicional | Fatos permitidos, contrato de saída e verificação |
| Decisão de lançamento | Instituição | Instituição | Permissões e transição de estado validada |

O ADR-0008 e `get_decision_model` já implementam essa seleção. `traditional` ignora a presença de credencial JEV; `hybrid` exige a credencial; `auto` escolhe pela configuração. Uma chave configurada não comprova conectividade. Não confundir seleção automática com fallback silencioso após falha de uma execução híbrida.

Prontidão e palavras-chave aparecem antes da coleta no código, o que é compatível com a imagem como visão resumida. Dashboard e texto devem consumir o mesmo resultado determinístico. O rótulo “motor de decisões” na imagem deve ser entendido como julgamento semântico: decisão institucional e score consolidado não pertencem ao JEV.

**Limites atuais:** o caminho principal faz o julgamento de aderência curricular, mas não uma triagem semântica completa das evidências. O bloco da imagem inclui projeção financeira; não foi encontrado no workflow um modelo de projeção de lançamento com custos, margem e ponto de equilíbrio. O índice mercadológico existente não comprova retorno financeiro. Essa extensão exige contrato próprio de premissas e cálculo determinístico.

## 2. Evidência operacional da análise citada

Consultado o PostgreSQL local em modo de leitura, restringindo cada consulta à análise `e6114f98-fd08-4e78-8b53-8526065dd800`. Não houve nova coleta paga, chamada de inferência, reprocessamento, migração ou alteração dos resultados.

| Capability | Runs | Evidências persistidas |
|---|---:|---:|
| Google Search | 5 | 5 |
| Instagram | 1 | 1 |
| LinkedIn empresas | 1 | 3 |
| LinkedIn Jobs | 2 | 6 |
| Meta Ads Library | 1 | 3 |
| TikTok | 1 | 3 |
| Web crawler | 2 | 4 |
| YouTube comentários | 1 | 1 |
| **Total** | **14** | **26** |

Resultados confirmados:

- 25 evidências têm qualidade 0,10; uma, do Instagram, tem qualidade 1,00.
- As seis vagas têm localizações nos EUA: Lafayette/LA, Shaker Heights/OH, Troy/MI, Philadelphia/PA, Irving/TX e Cedar Rapids/IA.
- As duas chamadas de crawler persistiram as mesmas páginas da Legale e Verbo Jurídico. A segunda declara dependência de `call-4`, mas repete a seleção anterior.
- O primeiro crawler declara dependências de `call-1`, `call-2` e `call-3`; o relatório original simplifica esse detalhe como dependência de `call-2`.
- YouTube persistiu o canal da ENS; Instagram persistiu o diretório da hashtag `riezgos`.
- Não há run de Google Trends nessa análise.
- Score persistido: viabilidade 35,52; cobertura 0,70; confiança 0,6369; recomendação `INSUFFICIENT_EVIDENCE`.
- Há três decisões persistidas nessa análise: prontidão, comparabilidade histórica e aderência curricular. A existência de outros packs no repositório não demonstra sua execução.
- Os contadores brutos de algumas runs são zero apesar de existirem itens válidos. Registrar a divergência na correção da telemetria; sua causa ainda precisa ser investigada.

Esses resultados confirmam a fragilidade da coleta descrita no relatório. Eles não comprovam que o curso tem baixa demanda.

## 3. O que o relatório acerta e o que precisa ser corrigido

| Tema | Validação no código atual | Encaminhamento |
|---|---|---|
| Catálogo de ferramentas | Planejador recebe nomes e regras genéricas; a allowlist inclui todas as capabilities conhecidas, não somente as configuradas | Catálogo versionado com finalidade, entradas, limitações, evidência esperada e critérios de suficiência; expor somente fontes executáveis |
| Dependências | Resolvedor procura URLs de toda a análise e ignora `depends_on`; ordenação só separa buscas de crawler/YouTube | Validar referências, ciclos e ordem; resolver pelo plano e chamadas de origem; excluir URLs já visitadas de forma canônica |
| Google Search | `_persist_result` cria uma evidência por item de dataset, sem decompor a SERP | Normalizar resultados e manter consulta/ranking/proveniência; descoberta de URL não torna qualquer página uma oferta concorrente |
| YouTube | Validador aceita qualquer caminho de youtube.com | Exigir identificador de vídeo e comentário real; metadados de canal e objetos de erro não contam como voz de mercado |
| Vagas | Builder envia `Brasil`; contagem não valida geografia | Corrigir escopo no contrato do Actor e validar localização de saída; preservar itens descartados para auditoria |
| Instagram | Resultado ruim confirmado; causa geral afirmada no relatório não é comprovada pela documentação atual | Reproduzir contra o build pinado antes de trocar entrada; aceitar post real e rejeitar diretório como sinal social |
| Meta Ads | Query não exige intenção educacional; contagem agrega anúncios pelo tipo | Orientar descoberta e classificar anúncio de curso versus serviço B2C; acrescentar “curso” à query não substitui pertinência |
| Trends | Extrator só lê `average_interest` e `growth_trend_pct` no topo | Chamar a fonte e normalizar a série temporal; apenas tornar Trends obrigatório não preenche o pilar |
| Higienização | Há falso positivo por scripts, mas também erro de recursão independente | Separar limpeza de HTML, risco de injeção e qualidade semântica; corrigir contrato da recursão |
| Cobertura | Contagens vazias geram features com zero e nenhum ID; presença considera a existência da chave | Distinguir falha, ausência de coleta, amostra inadequada e zero observado em coleta válida |
| Confiança | Calculadora usa pesos de componentes e tetos fixos; não consome `quality_score` das evidências | Corrigir a afirmação causal do relatório; calibrar qualidade, pertinência e confiança em mudança específica e versionada |
| Verificador | Audita claims, mas números só quando o tipo é quantitativo; texto livre não é integralmente conferido | Verificar todos os números e blocos factuais; referências existentes não bastam para validar suporte semântico |
| Interface | `claim.text` diverge de `statement`; seção lê `evidence_ids`, mas contrato fornece `claim_ids` | Resolver seção → claims → evidências; traduzir termos e preservar inspeção técnica |

### 3.1 Erro adicional no sanitizador

`sanitize_payload` retorna `(payload, quality_score)`. Nas chamadas recursivas, o chamador soma esse segundo retorno em `penalty`. Um objeto filho limpo retorna 1,00 e provoca penalidade máxima no pai.

Reprodução offline com o código atual:

| Payload | Qualidade retornada |
|---|---:|
| `{"title": "Curso"}` | 1,00 |
| `{"metadata": {"title": "Curso"}}` | 0,10 |
| `{"organicResults": [{"title": "Curso"}]}` | 0,10 |

Remover apenas os padrões de HTML não corrige isso. A correção também precisa remover conteúdo de scripts/iframes, não apenas as tags de abertura, e manter detecção de instruções maliciosas após normalização de entidades HTML. Qualidade alta deve indicar utilidade e pertinência, não simplesmente ausência de alerta de segurança.

### 3.2 Cobertura sem evidência

`EvidenceFeatureExtractor().extract([])` seguido de `ScoringService().build_pillar_inputs(...)` marca `paid_competition` e `employability` com `is_present=true` e `evidence_ids=[]`. Assim, ausência de observação pode contribuir para cobertura. O reparo deve preservar o caso legítimo de uma consulta válida com zero resultados, com registro da busca e do seu escopo, em vez de converter todo zero em dado ausente.

### 3.3 Verificação factual incompleta

Reprodução offline: uma claim qualitativa com “Retorno garantido de 999999%.”, citando apenas `scoring_result`, recebeu status `VERIFIED`. A mesma frase no resumo e na seção também não foi bloqueada. O exemplo é propositalmente inventado para testar o verificador; não descreve o curso real.

Por isso, adicionar `highlights: dict[str, Any]` não garante a compatibilidade factual sugerida no relatório. Os novos campos poderiam passar fora das verificações. Usar modelos tipados, referências obrigatórias, validação de todos os blocos exibidos e persistência/API consistentes. Distinguir fato observado, inferência e ação proposta. Um checklist gerado pela LLM não pode declarar uma validação institucional como concluída.

### 3.4 Preservação da informação na síntese

`build_facts` reduz textos individuais a cerca de 300 caracteres e o resumo de cada fato a 600; SERPs aproveitam apenas quatro descrições curtas. Omissões nesse recorte podem impedir a redatora de explicar preço, competências e diferenciais mesmo quando estão no payload. Também há nomes de métricas divergentes entre coleta, extração e síntese.

O contrato factual precisa preservar campos normalizados, unidade, periodicidade, data, escopo geográfico, trechos relevantes e limitações. Preço total, mensalidade e parcela promocional não podem entrar na mesma mediana sem comparabilidade explícita. No caminho atual não foi localizado um estágio geral de replanejamento após avaliar suficiência.

## 4. Validação da documentação externa

Consultadas páginas oficiais dos Actors em 2026-10-28. São referências atuais, não prova do comportamento dos builds antigos citados em `relatorio.md`.

- [LinkedIn Jobs — schema oficial](https://apify.com/curious_coder/linkedin-jobs-scraper/input-schema): documenta URLs de busca, `location` e `geoId`. Isso apoia testar recorte geográfico explícito; não prova que a palavra “Brasil” ou o proxy causaram sozinhos o fallback observado.
- [Instagram — schema oficial](https://apify.com/apify/instagram-scraper/input-schema): descreve `searchType=hashtag` retornando posts, além de `directUrls`. Logo, a afirmação categórica de que busca por hashtag só retorna diretório não vale como regra geral atual. Testar o build 0.0.831 e seu payload real.
- [Google Trends — saída oficial](https://apify.com/apify/google-trends-scraper): mostra série em `interestOverTime_timelineData`, diferente dos campos canônicos exigidos pelo extrator. O endereço antigo `emastra/google-trends-scraper` redirecionou para `apify/google-trends-scraper`; validar identidade e build antes de alterar o pin.
- [Google Search — referência oficial](https://apify.com/apify/google-search-scraper): distingue resultados orgânicos, pagos e demais componentes de uma página de busca. A normalização deve preservar essas naturezas.

Nenhuma integração externa foi modificada ou executada nesta auditoria.

## 5. Desenho proposto para as melhorias

Três caminhos possíveis:

1. **Corrigir a cadeia factual e depois a experiência executiva — recomendado.** Corrige seleção, normalização, suficiência, verificações e apresentação em entregas revisáveis. Preserva a arquitetura e os dois modos de IA.
2. **Aplicar apenas prompts e visual.** Menor esforço, mas conserva contagem de dados irrelevantes, cobertura artificial e verificação incompleta. Insuficiente para o problema observado.
3. **Reconstruir a orquestração inteira.** Permite pesquisa adaptativa mais ampla, mas aumenta custo de migração antes de eliminar erros determinísticos já reproduzidos. Não necessário como primeiro passo.

No caminho recomendado, o fluxo ganha um retorno controlado de “evidência insuficiente” ao planejamento. A LLM propõe consultas alternativas a partir das lacunas; código valida fontes, escopo, diversidade, orçamento restante e limite de rodadas. O sistema encerra ao atingir suficiência, esgotar orçamento/rodadas ou não obter ganho relevante. Falha ou escassez permanecem explícitas, sem inventar métricas.

### Entrega 1 — Integridade e coleta

- Testes de regressão primeiro para sanitização recursiva, dependências, URL de vídeo, SERPs e presença de pilares sem suporte.
- Catálogo por capability, vinculado aos Actors realmente configurados e ao contexto geográfico do briefing.
- Normalização específica por fonte, preservando dados brutos, versão e vínculo de origem.
- Pertinência por evidência e separação de oferta educacional, notícia, serviço B2C, vaga, comentário e metadado; executar os mesmos contratos via LLM tradicional ou JEV conforme o modo.
- Deduplicação por URL/entidade/conteúdo, com política explícita para mesma fonte encontrada em chamadas diferentes.
- Critérios de suficiência por pergunta e pilar, com replanejamento limitado; critérios numéricos de amostra precisam de calibração, não de valores arbitrários inseridos no prompt.

### Entrega 2 — Dossiê factual e executivo

- Contrato versionado e tipado para síntese, pontos fortes, riscos, limitações, concorrentes comparáveis, relação ementa/dor e próximos passos.
- Cada conclusão liga-se a claims e evidências; ações propostas ficam identificadas como propostas e nenhum status de validação é concedido pela redatora.
- Verificação de números e referências em todos os campos visíveis, incluindo resumo e destaques; verificações semânticas delimitadas e tratadas como julgamento, sem presumir certeza por existir um ID.
- Conversões de unidades, percentuais, preços e contagens em código. Novo schema propagado pelo cliente LLM, persistência, API, inspeção e compatibilidade de dossiês existentes.
- Linguagem em português para a decisão educacional; identificadores técnicos continuam disponíveis na auditoria.

### Entrega 3 — Interface e homologação

- KPIs calculados, cards dos seis pilares, pontos fortes/riscos, visões por área, plano de validação e fontes navegáveis.
- Corrigir `statement` e vínculo de seções; contagens distinguem evidências, URLs e fontes independentes.
- Exibir “Evidências insuficientes para recomendar o lançamento” quando essa for a recomendação. “Validação condicionada” isoladamente pode sugerir aprovação inexistente.
- Cobertura de 70% é soma de pesos válidos, não “70% do mercado pesquisado” nem simplesmente quatro de seis dimensões. Mostrar a contagem separadamente.
- Um pilar ausente exibe o motivo, sem barra de desempenho zero que sugira resultado negativo observado.
- Preservar score experimental e identificação da base histórica sintética; não apresentar confiança como probabilidade de sucesso.
- Homologar layout responsivo, impressão e navegação até a evidência de origem.

### Critérios de aceite

- Mesmas fronteiras de responsabilidade nos modos tradicional e híbrido; LLM/JEV não alteram fórmula nem estado diretamente.
- Busca dependente usa exclusivamente suas origens autorizadas; canais, diretórios e erros não são contados como comentários/posts.
- Vagas fora do escopo e anúncios de serviços não sustentam demanda brasileira ou concorrência educacional.
- Pilares ausentes não aumentam cobertura; zero observado é distinguido de ausência de dados.
- Trends é calculado a partir de série válida e janela explícita, sem supor que o Actor entrega campos internos prontos.
- Nenhum número factual contorna a verificação por estar em campo livre ou ser classificado como qualitativo.
- A interface explica o diagnóstico, seus limites e ações; afirmações e KPIs levam às fontes corretas.
- A análise real é reexecutada somente como validação operacional posterior, em nova revisão, com custo registrado e comparação dos resultados. Não prometer melhoria da nota: a meta é melhorar evidência e utilidade.

## 6. Verificações realizadas e limites

Executados no ambiente existente `.venv`, sem instalar dependências:

```powershell
rtk proxy .venv/Scripts/python.exe -m pytest tests/unit/domain/test_hybrid_ai_factory.py tests/unit/domain/test_ai_provider_factory.py tests/integration/test_runtime_preflight.py tests/unit/application/test_evidence_features.py tests/unit/dossiers tests/integration/market_sources/test_sanitization_integration.py -q
# 35 testes passaram.

rtk proxy .venv/Scripts/python.exe -m pytest tests/integration/market_sources/test_dynamic_research_plan.py tests/integration/market_sources/test_real_collection_orchestrator.py tests/integration/scoring/test_evidence_backed_scoring.py tests/integration/dossiers/test_synthesize_dossier_integration.py tests/integration/dossiers/test_no_dossier_fallback.py -q
# 12 testes passaram.
```

Total: **47 testes existentes passaram**, mas não cobrem os contraexemplos registrados nesta auditoria. As reproduções offline foram executadas separadamente com o código atual e não constituem correções nem novos testes de regressão. A primeira tentativa com o Python global falhou na coleta por ausência de `pydantic`; a execução foi corrigida usando o ambiente do projeto.

As consultas operacionais leram `tool_runs`, `market_evidences`, `scoring_results` e `decision_results`, sempre filtradas pela análise indicada. Não foram feitas chamadas remotas aos modelos nem aos Actors. O diagnóstico não homologa a qualidade futura dos resultados; isso exige implementar e testar as correções, validar os builds e repetir uma análise com novas evidências.

Esta etapa preserva `relatorio.md` como material de origem e altera apenas documentação. O desenho acima está preparado para revisão antes da implementação.
