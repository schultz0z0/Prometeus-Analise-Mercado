# PRD — Prometeus

**Versão:** 5.1.0-draft  
**Data:** 2026-10-22  
**Status:** aprovado para validação técnica e planejamento; implementação ainda não iniciada  
**Empresa desenvolvedora e mantenedora:** Agência Prometeus  
**Primeira instituição:** ENS — Escola de Negócios e Seguros

## 1. Resumo executivo

**Prometeus — Inteligência para Produtos Educacionais** é um serviço headless que transforma propostas acadêmicas em dossiês auditáveis de viabilidade. O produto combina histórico institucional, pesquisa de mercado, sinais de concorrência, demanda de busca, empregabilidade, social listening e análise curricular.

O JEV executa julgamentos semânticos delimitados e tipados. Código convencional calcula scores, aplica regras e controla estados. Uma LLM generativa converte o dossiê estruturado em parecer executivo, recomendações curriculares, posicionamento e materiais de apoio comercial.

O produto não decide sozinho se um curso será lançado. Ele organiza evidências, explicita incerteza e recomenda uma ação para aprovação humana.

## 2. Problema

Instituições de ensino recebem propostas de cursos orientadas principalmente pela perspectiva acadêmica. A decisão de lançamento nem sempre cruza:

- desempenho de cursos historicamente semelhantes;
- demanda atual e sazonalidade;
- custo provável de aquisição;
- competição e posicionamento;
- preço praticado pelo mercado;
- empregabilidade associada;
- dores expressas por potenciais alunos;
- aderência da ementa a essas evidências.

O resultado pode ser investimento em produtos com pouca demanda, posicionamento fraco ou baixa diferenciação.

## 3. Objetivo do produto

Permitir que diretoria, novos produtos, coordenação acadêmica e marketing tomem decisões de lançamento mais rápidas, explicáveis e orientadas por evidências.

### Resultado principal

Para cada proposta, entregar um dossiê versionado contendo:

- recomendação e status;
- Viability Score;
- Confidence Index;
- Coverage Index;
- sub-scores por pilar;
- evidências e limitações;
- comparáveis históricos;
- riscos e contraprovas;
- ajustes recomendados de ementa;
- faixa de posicionamento e preço;
- hipóteses de comunicação comercial;
- registro da decisão humana.

## 4. Usuários e responsabilidades

### Usuário principal

Diretor ou gerente de novos produtos, responsável por decidir se a proposta avança para o comitê.

### Usuários colaboradores

- Coordenação acadêmica: fornece e revisa proposta e ementa.
- Marketing/Growth: avalia demanda, CAC, posicionamento e mensagens.
- Diretoria: aprova investimento e lançamento.
- Administrador técnico: configura integrações, credenciais e políticas.
- Auditor/analista: examina evidências, versões e decisões.

## 5. Escopo funcional

### 5.1 Entrada

- Receber proposta estruturada pelo chatbot.
- Aceitar referência a documentos convertidos pelo chatbot ou serviço autorizado.
- Validar completude estrutural e semântica.
- Solicitar esclarecimentos quando necessário.

### 5.2 Inteligência interna

- Consultar leads, inscritos, matriculados e outros indicadores disponíveis.
- Normalizar dados de CRMs heterogêneos.
- Encontrar cursos comparáveis e explicar a similaridade.
- Calcular conversões e estatísticas com contexto temporal.

### 5.3 Inteligência externa

- Tendência e volume de busca.
- CPC, competição e previsões de mídia quando autorizadas.
- Concorrentes, ofertas, preços e diferenciais.
- Anúncios e criativos públicos quando a coleta for permitida.
- Demanda de vagas e competências.
- Vídeos, comentários e sinais públicos de voz do cliente.

### 5.4 Inteligência acadêmica e comercial

- Classificar dores e desejos.
- Avaliar cobertura da ementa.
- Sugerir ajustes curriculares sem alegar conformidade regulatória automática.
- Sugerir posicionamento, naming e ganchos como hipóteses a testar.

### 5.5 Entrega e aprendizado

- Expor MCP, REST e webhooks.
- Oferecer CLI operacional (Typer + Rich) para diagnóstico, validação de configuração e execução local; não é interface de usuário final.
- Manter execução assíncrona e consulta de progresso.
- Registrar decisão humana, justificativa e ajustes.
- Associar posteriormente resultados reais ao dossiê original.

## 6. Fora de escopo inicial

- Dashboard web próprio.
- Automação da aprovação final.
- Compra ou gestão automática de mídia.
- Alteração direta no CRM da instituição.
- Scraping próprio com navegadores mantidos pela equipe quando existir alternativa contratada.
- Garantia automática de conformidade MEC ou jurídica.
- Multi-tenancy compartilhado entre instituições.

## 7. Arquitetura de inteligência

### JEV — obrigatório

Usado para Choice, Score e Noul em perguntas atômicas: classificação de modalidade, relevância, similaridade semântica, categorização de comentários, aderência curricular e flags de risco. Cada decisão registra modelo, decision pack, resposta, probabilidades e confiança.

JEV não gera palavras-chave, texto executivo ou fórmulas. Ele escolhe, pontua ou avalia candidatos previamente definidos.

### Código determinístico

Responsável por contratos, cálculos, pesos, normalização, cobertura, políticas, autorização, estados, retries, idempotência e auditoria.

### LLM generativa

Responsável por gerar candidatos textuais e sintetizar o dossiê. Toda geração usa apenas fatos aprovados e passa por validação posterior.

## 8. Scoring

Baseline inicial, sujeito a backtest:

| Pilar | Peso |
|---|---:|
| Histórico interno | 20% |
| Concorrência paga | 20% |
| Busca e viabilidade de mídia | 20% |
| Empregabilidade | 15% |
| Aderência da ementa | 15% |
| Precificação | 10% |

Viability Score, Confidence Index e Coverage Index são independentes. Uma análise parcial não é promovida automaticamente a recomendação final.

### Status e recomendação

Conforme [ADR-0005](../architecture/adr/0005-status-vs-recommendation.md), ciclo de vida e recomendação são campos distintos.

**`status` (ciclo de vida):** `QUEUED`, `RUNNING`, `WAITING_FOR_INPUT`, `BLOCKED`, `COMPLETED`, `FAILED`, `CANCELLED`.

**`recommendation` (somente quando `COMPLETED`):** `APPROVED`, `APPROVED_WITH_ADJUSTMENTS`, `HIGH_RISK`, `INSUFFICIENT_EVIDENCE`, `REQUIRES_HUMAN_REVIEW`.

A recomendação é calculada em código e nunca equivale a aprovação humana. Os limiares iniciais são hipóteses. Consulte [Modelo de scoring](../scoring/scoring-model.md).

## 9. Requisitos não funcionais

- Isolamento físico por deployment institucional.
- Criptografia em trânsito e proteção de segredos.
- Idempotência em criação, webhooks e ferramentas externas.
- Rastreabilidade completa de entradas, evidências e versões.
- Recuperação de jobs interrompidos.
- Timeouts e circuit breakers por fornecedor.
- Retenção configurável por instituição.
- Exportação e exclusão compatíveis com políticas LGPD.
- Observabilidade de duração, custo, cobertura e falhas por etapa.
- Testes unitários, contratuais, de integração, avaliação de IA e E2E.

## 10. Métricas de sucesso

### Produto

- Redução do tempo de preparação para comitê.
- Percentual de propostas analisadas pelo serviço.
- Percentual de evidências consultadas pelos usuários.
- Taxa e motivo de override humano.
- Aceitação das recomendações curriculares.

### Modelo e decisão

- Poder preditivo em backtests.
- Lift do grupo recomendado sobre o baseline histórico.
- Calibração das confianças JEV por decision pack.
- Cobertura média e incidência de análises parciais.
- Taxa de afirmações generativas rejeitadas pelo validador.

### Operação

- P95 de criação de job inferior a 1 segundo.
- P95 por etapa monitorado, sem prometer E2E inferior a 10 segundos.
- Custo por análise e por fonte.
- Disponibilidade dos conectores e taxa de retries.
- Taxa de entrega de webhook.

## 11. Critérios de lançamento do piloto

1. Contratos da ENS aprovados e testados.
2. Decision packs JEV avaliados com dataset rotulado.
3. Backtest executado com amostra suficiente acordada.
4. Evidências rastreáveis em 100% das afirmações quantitativas.
5. Nenhum segredo ou dado pessoal em logs.
6. Restore de backup ensaiado.
7. Runbooks e alertas testados.
8. Shadow mode concluído antes de recomendações operacionais.

## 12. Riscos principais

- Dados internos incompletos ou inconsistentes.
- Proxies de mercado confundidos com demanda comprovada.
- Cobertura limitada de APIs e mudanças em fornecedores.
- Viés de seleção em redes sociais e vagas.
- Decision packs JEV mal formulados ou não calibrados.
- Geração de recomendações sem sustentação.
- Prompt injection em conteúdo coletado.
- Dependência de fornecedor em early access.
- Regras regulatórias desatualizadas.

## 13. Roadmap

O roadmap completo está em [docs/roadmap/roadmap.md](../roadmap/roadmap.md). A visão expandida é preservada; ela será entregue por gates de evidência e risco, não reduzida a um MVP descartável.

## 14. Relação com o PRD de origem

O documento [PRD_AGENTE_VALIDACAO_CURSOS.md](../../PRD_AGENTE_VALIDACAO_CURSOS.md) (v2.0) é histórico. Principais mudanças deliberadas:

| Tema no PRD v2.0 | Decisão vigente | Motivo |
|---|---|---|
| E2E < 10 s | P95 de aceite < 1 s; workflow assíncrono | Coleta externa leva minutos ([ADR-0004](../architecture/adr/0004-async-workflow.md)) |
| Redução de 85% no custo | Custo medido por análise e fonte | Meta sem baseline medido |
| JEV “alimenta” o score | Score calculado só em código | Auditabilidade ([ADR-0003](../architecture/adr/0003-jev-required.md)) |
| Meta Ad Library API oficial | Actor Apify avaliado para Brasil | API oficial não cobre anúncios comerciais BR |
| 4 sub-scores | 6 pilares + Confidence e Coverage | Visão expandida e evidência mínima |
| Status único `APROVADO_COM_AJUSTES` | `status` + `recommendation` | [ADR-0005](../architecture/adr/0005-status-vs-recommendation.md) |
| REST + CLI | REST + MCP + webhooks; CLI operacional | Integração com o chatbot existente |
| Fases 1–5 técnicas | Fases 00–09 com gates | Validação de premissas antes de integrações |

Taxonomia de dores sociais, matriz booleana de ementa e seções de naming/ganchos do PRD v2.0 continuam válidas como insumo para os decision packs `social_comment_v1` e `syllabus_coverage_v1` e para a política da LLM.
