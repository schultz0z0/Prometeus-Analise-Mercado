# Relatório de Auditoria Técnica e Plano de Melhoria: Coleta Apify & Experiência Visual do Dossiê

**Produto:** Prometeus — Inteligência para Produtos Educacionais  
**Referência de Auditoria Real:** Análise `e6114f98-fd08-4e78-8b53-8526065dd800` (*MBA em Gestão Jurídica em contratos de seguro e inovação* — ENS)  
**Objetivo deste Documento:** Servir como especificação técnica completa (Blueprint de Implementação) para refatorar (1) a inteligência e eficácia de coleta das tools da Apify e (2) o contrato de dados, linguagem executiva e interface visual (Dashboard) do Dossiê da Oferta no frontend.

---

## Parte 1 — Auditoria da Coleta Apify: Como Funciona Hoje e Por Que Perdeu Eficácia

### 1.1. As tools da Apify possuem `description` ou `system_prompt` individual hoje?

**Não.** Atualmente, o planejador de pesquisa (`CourseResearchPlanner.plan` em `src/prometeus/application/plan_course_research.py` combinado com `skills/planning-market-research/SKILL.md`) envia para a LLM **apenas um array de strings** com os nomes das capabilities ativas:

```json
["google_search", "instagram", "linkedin", "linkedin_jobs", "meta_ads_library", "tiktok", "web_crawler", "youtube_comments"]
```

A LLM **não recebe uma descrição semântica individual de cada ferramenta** (o que cada Actor faz, que tipo de busca funciona melhor em cada rede, limitações do scraper ou formato esperado da query). Ela recebe apenas regras genéricas no prompt de `plan_course_research.py` (linhas 146–159), como *"Use queries curtas de 2 a 3 palavras"*.

Como consequência, a LLM usa quase o mesmo termo (`"direito securitário"` ou `"seguros"`) para ferramentas com naturezas completamente distintas (Google Search, Meta Ads Library, TikTok, LinkedIn Empresas, Instagram), gerando ruído severo na coleta.

---

### 1.2. Diagnóstico Real: O que aconteceu em cada uma das 14 coletas da Análise `e6114f98-fd08-4e78-8b53-8526065dd800`

Abaixo está a auditoria exata do que foi enviado e do que retornou no banco PostgreSQL (`tool_runs` e `market_evidences`) durante o teste real do **MBA em Gestão Jurídica em Contratos de Seguro e Inovação**:

| Capability | Actor Pinado | Query Gerada | O que Retornou na Prática | Causa Raiz do Problema |
| :--- | :--- | :--- | :--- | :--- |
| **`linkedin_jobs`** (2 runs) | `curious_coder/linkedin-jobs-scraper@1.7.18` | `"advogado seguros"` e `"compliance seguros"` (`location: "Brasil"`) | **6 vagas nos EUA em inglês** (`Attorney- Insurance Defense` em Lafayette/LA, `Senior Claims Attorney` em Ohio, `Claims Regulatory Compliance Manager` no Texas). | O `_linkedin_jobs_input` (`registry.py:121`) passa `location="Brasil"` (com "s"). O Actor monta a URL `linkedin.com/jobs/search/?keywords=...&location=Brasil` e acessa via proxy dos EUA. No LinkedIn acessado por IP americano, `location=Brasil` sem `geoId=106057199` ou sem `location="Brazil"` (em inglês) sofre fallback silencioso para **United States**. |
| **`meta_ads_library`** (1 run) | `igolaizola/facebook-ad-library-scraper@0.0.59` | `"direito securitário"` | **3 anúncios de advogados B2C** captando clientes no WhatsApp para processar seguradoras (`"Anis Advogado Especialista em Seguro"`, `"Indenize Benefícios"`). | Falta de orientação de intenção educacional na tool: buscar apenas `"direito securitário"` na Biblioteca de Anúncios retorna escritórios de advocacia anunciando para segurados, e não **instituições de ensino** anunciando cursos (`"pós-graduação direito"`, `"MBA jurídico"`, `"curso seguros"`). |
| **`instagram`** (1 run) | `apify/instagram-scraper@0.0.831` | `"seguros"` (`searchType: "hashtag"`, `resultsType: "posts"`) | **1 item de diretório de hashtag em espanhol** (`title: "riezgos"`, `url: "https://www.instagram.com/explore/tags/riezgos"`), sem nenhum post real. | No Actor `apify/instagram-scraper`, usar `search` + `searchType="hashtag"` faz uma busca no diretório de sugestões de tags do Instagram e retorna metadados da tag, não os posts. Para extrair publicações reais, é necessário passar `directUrls: ["https://www.instagram.com/explore/tags/direitosecuritario/"]` com `resultsType: "posts"`. |
| **`web_crawler`** (2 runs) | `apify/website-content-crawler@0.3.102` | `"pós-graduação seguros"` (`depends_on: call-2`) e `"Lei 15040 seguros"` (`depends_on: call-4`) | **4 evidências duplicadas (2 pares idênticos):** ambas as runs crawlearam exatamente as mesmas 2 URLs (`legale.com.br` e `verbojuridico.com.br`). | Bug em `CollectMarketEvidenceService._resolve_dependent_urls` (`collect_market_evidence.py:151`): embora a LLM tenha gerado `"depends_on": ["call-4"]`, o método **ignora `depends_on`** e busca URLs em todas as evidências da análise ordenadas por `collected_at`, pegando sempre `discovered[:max_items]` (as 2 primeiras URLs da 1ª busca do Google). |
| **`youtube_comments`** (1 run) | `streamers/youtube-comments-scraper@0.0.257` | `"direito securitário"` (`depends_on: call-5`) | **1 item contendo apenas o cabeçalho do canal da ENS** (`https://www.youtube.com/channel/UCWKYHpO2GdJ7nfxuNx3XctQ`), com 0 comentários de alunos/profissionais. | Pelo mesmo bug de `_resolve_dependent_urls`, em vez de usar as URLs descobertas pela `call-5` (`site:youtube.com/watch direito securitário`), o coletor pegou a primeira URL do domínio `youtube.com` que apareceu na `call-3` (`"ENS seguros"`), que era a URL `/channel/...`. Além disso, `_is_usable_discovered_url` aceita qualquer URL `youtube.com` em vez de exigir `/watch?v=` ou `youtu.be/`. |
| **`google_search`** (5 runs) | `apify/google-search-scraper@0.0.474` | `"direito securitário"`, `"pós-graduação seguros"`, `"ENS seguros"`, `"Lei 15040 seguros"`, `"site:youtube.com/watch..."` | **5 evidências consolidadas** (1 por página SERP), todas com `source_url = "http://www.google.com/search?q=..."` e `quality_score = 0.1`. | O Actor retorna 1 objeto SERP contendo `organicResults: [10 sites]`. O método `_persist_result` (`collect_market_evidence.py:328`) salva o objeto SERP inteiro como uma única evidência em vez de desempacotar cada item de `organicResults` como uma evidência de oferta/mercado com sua `url`, `title` e `description` reais. |
| **`google_trends`** (0 runs) | `emastra/google-trends-scraper@0.1.33` | *Não foi chamado* | Pilar `search_and_media` ficou com **score `0.0`** (`is_present: false`). | Como `google_trends` não está listado em `REQUIRED_MARKET_SOURCES` no `.env`, o planejador omitiu a chamada. Sem `google_trends` (ou `google_analytics`), `EvidenceFeatureExtractor` não gera `average_interest` nem `growth_trend_pct`, zerando automaticamente o pilar `search_and_media` (que tem peso de 20% no score global). |
| **Qualidade das Evidências (`EvidenceSanitizer`)** | Todos os Actors (exceto Instagram) | — | **25 das 26 evidências receberam `quality_score = 0.10`** (nota mínima). | Em `src/prometeus/application/sanitization.py` (linhas 16–24), `INJECTION_PATTERNS` trata tags `<script>`, `<iframe>` e `javascript:` como tentativa de *Prompt Injection*. Como os payloads brutos da Apify incluem campos como `descriptionHtml` ou `html`, o sanitizador penaliza dados normais em `-0.90`, derrubando `quality_score` para `0.1` e reduzindo a confiança dos pilares. |

---

### 1.3. Plano de Correção Técnica da Coleta Apify (Para Implementação)

#### A. Criar Catálogo Descritivo de Capabilities (`TOOL_CAPABILITY_DESCRIPTIONS`) para o Planejador
No arquivo `src/prometeus/application/plan_course_research.py` (e em `skills/planning-market-research/SKILL.md`), substituir a lista simples de nomes por um catálogo estruturado injetado no `system_prompt` do planejador, instruindo a LLM sobre **como formular a query ideal para cada ferramenta**:

1. **`google_search`**: Busca orgânica e patrocinada no Google Brasil (`gl=br`, `hl=pt-BR`).
   - *Como planejar queries:* Planejar pelo menos 3 chamadas distintas:
     1. **Concorrência Direta e Preços:** `"pós-graduação <tema> mensalidade valor R$"` ou `"MBA <tema> investimento grade"`.
     2. **Demanda e Regulamentação/Tendência:** Termo técnico ou marco legal central da ementa (ex.: `"Lei 15.040/2024 seguros"`).
     3. **Descoberta de Vídeos para Comentários:** `"site:youtube.com/watch <tema>"`.
2. **`web_crawler`**: Crawler profundo em Playwright para extrair preços (`R$`), carga horária, módulos e promessas comerciais das páginas de concorrentes.
   - *Como planejar:* Deve referenciar explicitamente em `parameters.depends_on` o `id` da chamada `google_search` de **Concorrência Direta**.
3. **`meta_ads_library`**: Biblioteca de Anúncios da Meta no Brasil.
   - *Como planejar queries:* **Nunca** usar apenas o substantivo jurídico/técnico isolado (que retorna serviços B2C). Sempre combinar o prefixo educacional + área: ex.: `"pós-graduação direito"`, `"MBA seguros"`, `"pós-graduação jurídico"`.
4. **`linkedin_jobs`**: Busca de vagas abertas no LinkedIn Brasil.
   - *Como planejar queries:* Usar cargos reais do mercado brasileiro em português (ex.: `"Advogado de Seguros"`, `"Especialista Jurídico Sinistros"`, `"Compliance Securitário"`).
5. **`linkedin`**: Busca de empresas e instituições do setor no LinkedIn Brasil.
   - *Como planejar queries:* Termo curto do setor de atuação das empresas empregadoras ou concorrentes (ex.: `"seguradora"`, `"seguros"`, `"previdência"`).
6. **`instagram`**: Extração de publicações públicas por hashtag no Instagram.
   - *Como planejar queries:* Uma única hashtag em português sem espaços e sem acentos, focada na comunidade profissional (ex.: `"direitosecuritario"`, `"mercadodeseguros"`, `"advocaciasecuritaria"`).
7. **`tiktok`**: Vídeos curtos de criadores e especialistas da área no Brasil.
   - *Como planejar queries:* Termo de nicho profissional em português de 2 palavras (ex.: `"direito securitário"`, `"contrato seguro"`).
8. **`youtube_comments`**: Comentários reais em vídeos de aulas, palestras e debates no YouTube.
   - *Como planejar:* Referenciar em `parameters.depends_on` o `id` da chamada `google_search` que usou `site:youtube.com/watch`.
9. **`google_trends`**: Série temporal de interesse de busca no Google Brasil (`geo=BR`).
   - *Como planejar queries:* Termo amplo da categoria (1 a 2 palavras, ex.: `"direito securitário"` ou `"pós-graduação direito"`), pois termos muito longos retornam volume zero no Google Trends. **Deve ser incluído sempre no plano** para alimentar o pilar `search_and_media`.

#### B. Corrigir os Input Builders em `src/prometeus/infrastructure/apify/registry.py`
1. **`_linkedin_jobs_input` (`registry.py:121`):**
   - Converter `"Brasil"` / `"BR"` para `"Brazil"` (em inglês), pois o resolver geográfico do LinkedIn acessado via proxy internacional exige `"Brazil"`.
   - Verificar se o Actor `curious_coder/linkedin-jobs-scraper` aceita `urls` diretas de busca com `geoId=106057199` (GeoID oficial do Brasil no LinkedIn):
     ```python
     from urllib.parse import quote_plus
     search_url = f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(call.query)}&location=Brazil&geoId=106057199"
     ```
   - Além disso, no coletor/extrator (`evidence_features.py` ou `collect_market_evidence.py`), filtrar ou sinalizar vagas cujo campo `location` seja claramente fora do Brasil (ex.: estados dos EUA como `, LA`, `, OH`, `, TX`, `, MI`, `, PA`, `, IA`) para que não distorçam o pilar de empregabilidade nacional.
2. **`_instagram_input` (`registry.py:133`):**
   - Para `apify/instagram-scraper@0.0.831`, quando o objetivo é coletar posts de uma hashtag, enviar `directUrls`:
     ```python
     tag = search_query.lower()
     return {
         "directUrls": [f"https://www.instagram.com/explore/tags/{tag}/"],
         "resultsType": "posts",
         "resultsLimit": call.max_items,
     }
     ```
3. **`_meta_ads_input` (`registry.py:80`):**
   - Se a `call.query` não contiver nenhum termo educacional (`pós`, `pos`, `mba`, `curso`, `especialização`, `faculdade`, `escola`), prefixar automaticamente com `"pós-graduação "` ou `"curso "` para evitar capturar anúncios de serviços jurídicos B2C.

#### C. Corrigir Resolução de URLs Dependentes e Desempacotamento SERP em `src/prometeus/application/collect_market_evidence.py`
1. **Respeitar `depends_on` em `_resolve_dependent_urls` (`collect_market_evidence.py:151`):**
   - Ler `depends_on = call.parameters.get("depends_on", [])`.
   - Se `depends_on` estiver preenchido (ex.: `["call-4"]`), filtrar `MarketEvidenceModel` pelos `ToolRunModel` correspondentes àqueles `planned_call_id`s primeiro, e também excluir URLs que já foram crawleadas por chamadas anteriores de `web_crawler` na mesma análise!
2. **Filtrar URLs de Vídeo Reais para `youtube_comments` (`collect_market_evidence.py:128`):**
   - Em `_is_usable_discovered_url`, para `capability == "youtube_comments"`, exigir que a URL seja de **vídeo** (`/watch` com `v=` na query string ou domínio `youtu.be/`), rejeitando URLs de canais (`/channel/`, `/@`, `/c/`, `/user/`).
3. **Desempacotar `organicResults` do Google Search (`collect_market_evidence.py:328`):**
   - Quando `call.capability == "google_search"`, se um item retornado pela Apify contiver `organicResults` (lista de dicts com `title`, `url`, `description`), desempacotar os `max_items` primeiros resultados orgânicos em instâncias individuais de `MarketEvidence` (com `source_url = entry["url"]`, `title = entry["title"]`). Isso dará URLs reais para o dossiê e aumentará a precisão da extração de preços e concorrentes.

#### D. Corrigir Falso-Positivo de Penalidade em `src/prometeus/application/sanitization.py`
- Separar **limpeza de tags HTML** (que é normal em campos como `descriptionHtml` e `html` vindos de scrapers) de **ataques reais de Prompt Injection** (`ignore previous instructions`, `system prompt`, `you are now an unrestricted`, `<|im_start|>`).
- Remover `<script>`, `<iframe>` e `javascript:` da soma de `penalty` de `quality_score` (continuar limpando-os do texto, mas sem derrubar `quality_score` de `1.0` para `0.1`).

---

## Parte 2 — Auditoria do Dossiê e Interface Visual (Frontend + Contrato LLM)

### 2.1. Por que o Dossiê atual parece "Texto sem Maquiagem" e com Linguagem de Desenvolvedor?

A auditoria nas screenshots enviadas e no código de `config/prompts/dossier-v1.yaml` e `web/js/views/dossier-view.js` revelou **6 problemas estruturais**:

1. **Prompt do Dossiê força jargão de backend no texto (`config/prompts/dossier-v1.yaml`):**
   - A Regra 4 do `dossier-v1.yaml` instrui explicitamente a LLM:
     > *"Use 'claim_type': 'quantitative' APENAS para a claim principal de scoring (citando 'scoring_result' e os valores exatos de viability_score, coverage_score ou pillar_summaries)."*
   - Além disso, o `DossierFacts` passa `recommendation: "INSUFFICIENT_EVIDENCE"` e `pillar_summaries: {"pricing": 0.0, "syllabus_fit": 78.0, ...}`. A LLM obedece literalmente e escreve no resumo executivo:
     > *"O scoring registra viability_score de 35.52 e coverage_score de 0.7, com recomendação INSUFFICIENT_EVIDENCE..."*
2. **Contrato JSON empobrecido (`src/prometeus/domain/dossiers.py`):**
   - O modelo `DossierOutput` possui apenas `executive_summary: str` (um blocão de texto único) e `sections: list[DossierSection]` (onde cada seção tem apenas `title: str` e `content: str`).
   - Não existem estruturas de dados para **Prós (Pontos Fortes)**, **Contras (Riscos e Fragilidades)**, **Critérios de Validação (Checklist Go/No-Go)**, ** Recomendações Práticas em Tópicos**, **Matriz Ementa vs. Dores do Mercado** ou **Quadro Comparativo de Concorrentes**.
3. **Vazamento de Metadados de Engenharia para o Usuário Final (`web/js/views/dossier-view.js`):**
   - Linha 50: Exibe o UUID técnico da análise (`e6114f98-fd08-4e78-8b53-8526065dd800`) no topo do banner.
   - Linha 49: Exibe o status técnico do banco (`VERIFIED`) em inglês ao lado da recomendação.
   - Linha 69: Exibe no rodapé da Síntese Executiva: `Modelo: gpt-6.1-sol · Prompt: dossier-v1 · Facts hash: 455ea2f21fd22c6c4bd0a150e09728772a88638a58ddeff3feaf5cab9597f3a0`.
4. **Falta de Tradução de Enums e Nomes de Pilares (`web/js/views/dossier-view.js`):**
   - Na função `recommendationLabel(value)` (linhas 13–20), não há mapeamento para `INSUFFICIENT_EVIDENCE`, exibindo a constante crua em inglês (`● INSUFFICIENT_EVIDENCE`).
   - Na tabela de pilares (linhas 76–81), `pillar_scores` é iterado imprimindo as chaves técnicas em inglês (`pricing`, `syllabus_fit`, `employability`, `internal_history`, `paid_competition`, `search_and_media`) e despejando uma lista de dezenas de UUIDs (`04c949fc-3c93-4453-82a9-ba81090a56dd, ...`) na coluna "Evidências".
5. **Bug de Propriedade nas Afirmações Verificadas (`web/js/views/dossier-view.js:96`):**
   - O frontend faz `${escapeHtml(claim.text)}`, mas o backend (`DossierClaim`) envia o campo como `claim.statement`! Por isso, na seção "Afirmações verificadas", o texto principal de cada afirmação fica em branco, aparecendo apenas `Status: verified · Evidências: UUID`.
6. **Classes CSS de Dashboard já existem em `web/styles/app.css`, mas foram ignoradas em `dossier-view.js`:**
   - O arquivo `web/styles/app.css` (linhas 421–532) **já possui estilização pronta** para `.business-cards-grid`, `.business-card`, `.metric-big-highlight`, `.curriculum-gap-grid`, `.gap-column-pains` (vermelho translúcido), `.gap-column-solutions` (verde translúcido) e `.gap-item`, mas `dossier-view.js` não utiliza nenhuma dessas classes!

---

### 2.2. Especificação da Solução: Novo Dossiê Executivo Visual (Backend + Frontend)

#### Passo 1: Proibir Jargão Técnico e Enriquecer a Linguagem no Prompt (`config/prompts/dossier-v1.yaml`)

Atualizar as instruções do `system_prompt` em `config/prompts/dossier-v1.yaml`:
- **Linguagem 100% Executiva para Decisores Educacionais (Reitores, Diretores, Coordenadores e CMO):**
  - **PROIBIDO** usar nomes de variáveis ou constantes de código no texto (`viability_score`, `coverage_score`, `confidence_score`, `syllabus_fit`, `paid_competition`, `internal_history`, `search_and_media`, `INSUFFICIENT_EVIDENCE`, `APPROVED_WITH_ADJUSTMENTS`, `scoring_result`, `call-1`, `evidence_id`).
  - Usar sempre a terminologia de negócios em português:
    - `viability_score` → **Índice de Viabilidade Mercadológica (35,5/100)**
    - `coverage_score` → **Cobertura de Evidências (70%)**
    - `confidence_score` → **Grau de Confiança Analítica (64%)**
    - `INSUFFICIENT_EVIDENCE` → **Validação Condicionada (Evidências de Mercado Insuficientes para Escala)**
    - `syllabus_fit` → **Aderência Curricular ao Mercado**
    - `internal_history` → **Histórico e Portfólio Institucional**
    - `paid_competition` → **Pressão Competitiva e Mídia Paga**
    - `employability` → **Empregabilidade e Demanda de Vagas**
    - `pricing` → **Competitividade de Preço e Ticket**
    - `search_and_media` → **Interesse de Busca e Demanda Orgânica**
- **Formatação Escaneável no Conteúdo das Seções:**
  - Instruir a LLM a estruturar o `content` de cada seção (`sec-executive`, `sec-academic`, `sec-marketing`) ou subcampos estruturados com **tópicos curtos, destaques, diagnóstico direto e recomendações acionáveis**, evitando blocos monolíticos de texto corrido.

#### Passo 2: Expandir o Contrato de Saída do Dossiê (ou Estruturar Blocos Visuais)

Para transformar o Dossiê em um verdadeiro **Dashboard de Tomada de Decisão**, o JSON gerado em `dossier-v1.yaml` (e exposto por `GET /v1/analyses/{id}/dossier`) deve fornecer blocos visuais claros (seja via novos campos opcionais em `DossierOutput` ou via estrutura padronizada nas seções/claims):

```json
{
  "executive_summary": "Síntese executiva em linguagem de negócios (2 a 3 parágrafos curtos, sem jargão de código)...",
  "highlights": {
    "pros": [
      "Forte aderência da matriz curricular (360h) ao novo marco legal de seguros (Lei 15.040/2024).",
      "Elevada sinergia com o portfólio histórico da ENS (aderência de 75/100 e conversão histórica média de 6,35%).",
      "Existência de debates jurídicos ativos sobre regulação de sinistros, resseguros e saúde suplementar."
    ],
    "cons": [
      "Ausência de preços públicos abertos nos concorrentes diretos impede o benchmarking automático de mensalidade.",
      "Volume de busca orgânica específico para o título exato ainda é de nicho, exigindo captação ativa B2B.",
      "Amostra de vagas abertas capturada concentrou-se em posições internacionais, faltando comprovação de volume de vagas jurídicas no Brasil."
    ],
    "validation_criteria": [
      {
        "criterion": "Pesquisa de Sensibilidade de Preço (Ticket R$ 970/mês)",
        "target": "Confirmar disposição a pagar junto a ex-alunos e escritórios parceiros da ENS",
        "status": "PENDENTE"
      },
      {
        "criterion": "Teste de Demanda com Parcerias B2B (Seguradoras e Departamentos Jurídicos)",
        "target": "Validar lote mínimo de matrículas corporativas antes da abertura de turma aberta",
        "status": "RECOMENDADO"
      },
      {
        "criterion": "Adequação da Grade ao Marco Legal (Lei 15.040/2024)",
        "target": "Aderência curricular de 78/100 já comprovada na análise pedagógica",
        "status": "VALIDADO"
      }
    ],
    "action_recommendations": [
      {
        "area": "Posicionamento & Marketing",
        "action": "Ancorar a campanha na atualização obrigatória para a Lei 15.040/2024 (Novo Marco Legal dos Seguros), mirando advogados securitários e gestores de sinistros.",
        "priority": "ALTA"
      },
      {
        "area": "Coordenação Acadêmica",
        "action": "Converter os módulos de Regulação de Sinistros, Fraude e Resseguros em laboratórios práticos de análise de apólices e casos reais.",
        "priority": "MÉDIA"
      },
      {
        "area": "Comercial & Precificação",
        "action": "Realizar cotação oculta (mystery shopping) na pós-graduação concorrente (Verbo Jurídico) e testar oferta de pré-matrícula com condição para parceiros ENS.",
        "priority": "ALTA"
      }
    ]
  }
}
```

*(Nota: Para manter 100% de compatibilidade com o `DossierVerifier` atual em `src/prometeus/application/dossier_verifier.py`, `highlights` pode ser um campo opcional `highlights: dict[str, Any] = Field(default_factory=dict)` em `DossierOutput` e uma coluna JSON ou embutido em `sections` no `DossierModel`, ou derivado no endpoint `GET /v1/analyses/{id}/dossier`).*

---

#### Passo 3: Redesenhar `web/js/views/dossier-view.js` como um Dashboard Executivo Visual

Substituir a página estática de texto corrido em `web/js/views/dossier-view.js` por um **Dashboard Executivo em 6 Blocos Visuais**, aproveitando o Design System já existente em `web/styles/tokens.css` e `web/styles/app.css`:

1. **Bloco 1 — Hero Banner de Veredito & KPIs Principais (`.dossier-verdict-banner` melhorado):**
   - **Badges traduzidos e semânticos:**
     - `APPROVED` → `● LANÇAMENTO RECOMENDADO` (Verde)
     - `APPROVED_WITH_ADJUSTMENTS` → `● VIÁVEL COM AJUSTES` (Amarelo/Âmbar)
     - `INSUFFICIENT_EVIDENCE` → `● VALIDAÇÃO CONDICIONADA (DADOS PARCIAIS)` (Azul/Gelo)
     - `HIGH_RISK` → `● ALTO RISCO MERCADOLÓGICO` (Vermelho)
     - `REQUIRES_HUMAN_REVIEW` → `● REQUER DELIBERAÇÃO DO COMITÊ` (Roxo)
   - **Ocultar da visão principal:** UUID da análise, `VERIFIED`, `facts_hash`, `prompt_version` e `model_name` (mover metadados técnicos de auditoria para dentro do drawer **"Inspecionar evidências"**).
   - **3 Mini-Cards de KPIs à direita:**
     - **Índice de Viabilidade:** `35,5 / 100` (com barra visual colorida)
     - **Cobertura de Mercado:** `70%` (4 de 6 dimensões mapeadas)
     - **Confiança dos Dados:** `64%` (Baseada em 26 fontes verificadas)

2. **Bloco 2 — Painel de Diagnóstico Rápido: Prós vs. Contras (Layout Duas Colunas `.curriculum-gap-grid`):**
   - **Coluna Esquerda (`.gap-column-solutions` — Borda/Fundo Verde):** **✅ Pontos Fortes & Oportunidades Comprovadas** (lista visual com ícones e badges dos pilares que pontuaram bem, como Aderência Curricular `78/100` e Histórico Institucional `66,6/100`).
   - **Coluna Direita (`.gap-column-pains` — Borda/Fundo Vermelho/Âmbar):** **⚠️ Fragilidades, Riscos & Lacunas de Evidência** (lista visual clara explicando por que determinados pilares ficaram zerados ou baixos e quais são os riscos reais para a instituição).

3. **Bloco 3 — Radar Visual dos 6 Pilares de Viabilidade (Substituindo a Tabela Crua de UUIDs):**
   - Em vez de uma tabela com nomes em inglês (`syllabus_fit`) e 27 UUIDs copiados na célula, renderizar um **Grid de 6 Cards de Pilares** (2x3) com:
     - **Ícone + Nome Amigável em Português:**
       - 🎓 *Aderência Curricular ao Mercado* (`syllabus_fit`) — **78,0 / 100**
       - 🏛️ *Histórico & Sinergia Institucional* (`internal_history`) — **66,6 / 100**
       - 📢 *Concorrência em Mídia Paga* (`paid_competition`) — **37,5 / 100**
       - 💼 *Empregabilidade & Vagas* (`employability`) — **20,0 / 100**
       - 💰 *Competitividade de Preço* (`pricing`) — **Sem amostra pública**
       - 📈 *Tendência de Busca & Demanda* (`search_and_media`) — **Sem amostra pública**
     - **Barra de Progresso Horizontal (`0%` a `100%`)** colorida conforme a nota (`>=70` verde, `40-69` âmbar, `<40` vermelho/cinza).
     - **Badge de Confiança + Contagem Amigável de Fontes:** Ex.: `Confiança: 68% · Sustentado por 27 evidências` (com botão clicável que abre o drawer de evidências filtrado, sem exibir os UUIDs na tela).

4. **Bloco 4 — Visão por Área Decisora (Cards Visuais com Tópicos para Diretoria, Acadêmico e Marketing):**
   - Renderizar as 3 seções (`sec-executive`, `sec-academic`, `sec-marketing`) usando `.business-cards-grid` e `.business-card`:
     - **🧭 Visão Executiva & Posicionamento**
     - **📚 Adequação Acadêmica & Matriz Curricular**
     - **🎯 Estratégia Comercial, Público-Alvo & Captação**
   - Formatar o texto dividindo parágrafos longos em **bullet points escaneáveis**, destacando palavras-chave e exibindo embaixo as **Afirmações Verificadas (`claim.statement`)** vinculadas àquela seção como *chips/tópicos de fatos comprovados*.

5. **Bloco 5 — Critérios de Validação (Checklist Go / No-Go) & Plano de Recomendações Práticas:**
   - **Checklist de Critérios de Validação:** Quais condições precisam ser cumpridas pelo time comercial/acadêmico antes de liberar o orçamento total de lançamento (com badges `VALIDADO`, `PENDENTE`, `ATENÇÃO`).
   - **Cards de Recomendações Práticas:** Ações recomendadas separadas por área (`Comercial`, `Acadêmico`, `Marketing`) com tag de prioridade (`Prioridade Alta` / `Média`).

6. **Bloco 6 — Vitrine de Fontes de Mercado Coletadas (Agrupadas por Canal):**
   - Em vez de uma lista corrida com `apify:apify/google-search-scraper@0.0.474`, agrupar as fontes em **Abas ou Badges por Canal** (`🔍 Google & Sites Concorrentes`, `📢 Meta Ads`, `💼 LinkedIn & Vagas`, `📱 TikTok, Instagram & YouTube`), mostrando o título limpo, link clicável para a fonte original e badge de canal amigável.

---

## Parte 3 — Resumo dos Arquivos a Modificar (Checklist para a Outra IDE)

| Ordem | Arquivo | O que alterar |
| :---: | :--- | :--- |
| **1** | `src/prometeus/application/plan_course_research.py` e `skills/planning-market-research/SKILL.md` | Adicionar catálogo descritivo por tool (`TOOL_CAPABILITY_DESCRIPTIONS`) no prompt do planejador, instruindo como formular queries específicas por rede (ex.: prefixo educacional no `meta_ads_library`, cargos em PT-BR no `linkedin_jobs`, inclusão de `google_trends`). |
| **2** | `src/prometeus/infrastructure/apify/registry.py` | Em `_linkedin_jobs_input`, usar `location="Brazil"` (e/ou URL com `geoId=106057199`); em `_instagram_input`, usar `directUrls` de hashtag para extrair posts reais; em `_meta_ads_input`, garantir termo educacional na query. |
| **3** | `src/prometeus/application/collect_market_evidence.py` | Em `_resolve_dependent_urls`, respeitar `call.parameters["depends_on"]` e evitar repetir URLs já crawleadas; em `_is_usable_discovered_url`, exigir `/watch?v=` ou `youtu.be/` para `youtube_comments`; em `_persist_result`, desempacotar `organicResults` do `google_search` em evidências individuais com suas URLs reais. |
| **4** | `src/prometeus/application/sanitization.py` | Não aplicar penalidade de Prompt Injection (`-0.35`) quando tags HTML comuns (`<script>`, `<iframe>`, `javascript:`) aparecerem em campos brutos de scrapers; apenas limpar o HTML, preservando o `quality_score` real da evidência. |
| **5** | `config/prompts/dossier-v1.yaml` e `src/prometeus/domain/dossiers.py` | Proibir jargões de backend (`viability_score`, `coverage_score`, `INSUFFICIENT_EVIDENCE`, `scoring_result`) no texto visível; exigir linguagem executiva de negócios educacionais e incluir estrutura de `highlights` (`pros`, `cons`, `validation_criteria`, `action_recommendations`). |
| **6** | `web/js/views/dossier-view.js` e `web/styles/app.css` | Corrigir `claim.text` → `claim.statement`; traduzir `INSUFFICIENT_EVIDENCE` e nomes dos 6 pilares para português; remover UUIDs e hashes técnicos da tela principal; implementar o layout de Dashboard com cards de KPIs, barras de progresso por pilar, colunas de Prós vs. Contras, Checklist de Critérios de Validação e Recomendações em tópicos. |

