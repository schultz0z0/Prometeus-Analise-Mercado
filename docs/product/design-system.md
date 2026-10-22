# Design System — Prometeus UI

**Versão:** 2.0.0  
**Status:** Aprovado e Especificado para Frontend e Dashboards SaaS EdTech  
**Referência de Marca:** [Diretrizes de Marca Prometeus](brand-guidelines.md) | [Brand & Naming](brand-and-naming.md)  
**Tokens Canônicos:** [`config/design-system/tokens.json`](../../config/design-system/tokens.json) | [`config/design-system/tokens.css`](../../config/design-system/tokens.css)

---

## 1. Visão Geral e Princípios Fundamentais

O **Prometeus UI** é o sistema de design canônico construído para expressar sofisticação, precisão matemática e autoridade analítica. Ele resolve o desafio de apresentar diagnósticos complexos de viabilidade de cursos (funis de busca, concorrência no Meta Ads, vagas CBO/CAGED, conformidade regulatória MEC/INEP e decomposição de 6 pilares) de maneira intuitiva, ágil e executiva.

### 1.1 Síntese Metodológica dos Plugins de Design

O sistema foi refinado integrando as quatro referências de design instaladas:

1. **Impeccable (Modo Operate):** 
   - *Foco na Tarefa:* O design serve ao fluxo analítico do decisor acadêmico. A ferramenta desaparece no trabalho diário;
   - *O Teste de Qualidade (Product Slop Test):* Eliminação de movimentos supérfluos, proibição de fontes decorativas em rótulos/tabelas e recusa a componentes extravagantes que desviem da interpretação dos dados;
   - *Vocabulário Interativo Completo:* Todo controle interativo implementa obrigatoriamente 7 estados (`default`, `hover`, `focus-visible`, `active`, `disabled`, `loading`, `error`);
   - *Transições de Estado, não Decoração:* Movimento apenas para dar feedback e comunicar mudança de estado (150ms a 250ms), sem coreografias lentas de carregamento de página.

2. **Web Interface Guidelines (Vercel Standards):**
   - *Contraste Rígido:* Conformidade WCAG 2.1 AA/AAA em todas as combinações de texto e superfície (mínimo de 4.5:1 para texto normal e 3:1 para elementos gráficos essenciais);
   - *Foco Teclado Visível:* Indicador de foco evidente com anel duplo ou deslocamento (`outline-offset: 2px`) em azul celeste (`#8DB5FF`);
   - *Alvos de Toque & Clique:* Mínimo de 36×36px em controles densos de desktop e 44×44px em telas sensíveis ao toque;
   - *Sem Troca Abrupta de Layout (CLS):* Skeletons estruturais mantêm a geometria exata dos blocos de dados antes da hidratação dos dados em tempo real;
   - *Acessibilidade Semântica:* Elementos com labels descritivos, `aria-describedby` para erros/ajudas e classe utilitária `.sr-only` para leitura de tela em medidores gráficos.

3. **UI/UX Pro Max (Diretrizes Analíticas e Tokens Científicos):**
   - *Escala Tonal Completa:* Paletas balanceadas de 50 a 950 para a marca, neutros e status semânticos;
   - *Densidade Analítica 8:* Grade baseada em múltiplos de 4px calibrada para máxima legibilidade sem desperdício de espaço vertical;
   - *Especificações Visuais de Gráficos:* Gráfico de Radar de 6 eixos com 20% de opacidade de preenchimento e 100% no contorno; Gauge circular com zona de tolerância e tabela alternativa acessível;
   - *Curvas GSAP de Timing:* Implementação de curvas cúbicas equivalentes a `power1.out` e `power2.inOut` para microinterações e shimmer `sine.inOut`.

4. **Huashu Design (Direção de Arte & Fidelidade de Ativos):**
   - *Autenticidade contra Clichês de IA:* Rejeição a paletas pasteis genéricas, serifas despropositadas ou estética genérica. A interface brota organicamente da identidade Prometeus: fundo Dark Canvas (`#040814`) com a chama em Azul Cobalto (`#0652C5`) e toques luminosos de Azul Céu (`#8DB5FF`);
   - *Fidelidade Pixel-Perfect dos Ativos Canônicos:* Uso estrito dos logotipos oficiais vetorizados e rasterizados em alta resolução preservando as proporções geométricas do manual.

---

## 2. Princípios de Marca e Regra White-Label

A governança do Prometeus estabelece uma separação técnica estrita:
- **White-label no Backend & Dados:** Bancos de dados, pipelines de coleta, adaptadores de scraping e modelos de scoring operam com isolamento por tenant/instituição (ex.: ENS, FGV, PUC);
- **Frontend Canônico da Prometeus:** A aplicação web, o design system, o logotipo no cabeçalho e a assinatura visual **pertencem sempre e integralmente à Prometeus**. A instituição cliente é indicada como o contexto ativo de trabalho (tenant badge).

---

## 3. Design Tokens de Produção

### 3.1 Cores e Superfícies

| Token | Valor CSS | Aplicação |
|---|---|---|
| `--prometeus-bg-canvas` | `#040814` | Fundo master da aplicação (Deep Obsidian) |
| `--prometeus-bg-canvas-subtle` | `#070A10` | Fundo alternativo de alta profundidade |
| `--prometeus-surface-card` | `rgba(26, 35, 56, 0.75)` | Superfície padrão de cards e painéis com backdrop-blur |
| `--prometeus-surface-elevated` | `#1A2338` | Superfície de modais, menus suspensos e gavetas laterais |
| `--prometeus-surface-glass` | `rgba(255, 255, 255, 0.04)` | Botões secundários, chips e badges neutros |
| `--prometeus-primary` | `#0652C5` | Azul canônico Prometeus — botões principais e ação primária |
| `--prometeus-primary-hover` | `#0860E8` | Estado hover de botões primários |
| `--prometeus-primary-active` | `#05419E` | Estado ativo (clique) de botões primários |
| `--prometeus-primary-glow` | `rgba(6, 82, 197, 0.45)` | Sombra luminosa de destaque |
| `--prometeus-accent-ice` | `#8DB5FF` | Azul celeste — links, anel de foco, tags ativas e sparkles |
| `--prometeus-border-subtle` | `rgba(255, 255, 255, 0.08)` | Bordas divisórias de tabelas e grids |
| `--prometeus-border-card` | `rgba(255, 255, 255, 0.10)` | Contorno estrutural de cartões e painéis |
| `--prometeus-border-strong` | `rgba(255, 255, 255, 0.20)` | Contorno de cards no estado hover |
| `--prometeus-border-focus` | `rgba(141, 181, 255, 0.60)` | Indicador visível de foco acessível |

### 3.2 Status e Recomendações (Alinhado ao ADR-0005)

O Design System reflete rigorosamente a separação entre **Status de Execução** (ciclo de vida) e **Recomendação Final** (cálculo de viabilidade):

| Código ADR-0005 | Cor do Texto | Fundo Translúcido | Borda Semântica | Significado de Negócio |
|---|---|---|---|---|
| `APPROVED` | `#34D399` | `rgba(52, 211, 153, 0.12)` | `rgba(52, 211, 153, 0.35)` | Viabilidade comprovada e recomendada |
| `APPROVED_WITH_ADJUSTMENTS` | `#FBBF24` | `rgba(245, 158, 11, 0.12)` | `rgba(245, 158, 11, 0.35)` | Aprovado condicionado a adequações |
| `HIGH_RISK` | `#F87171` | `rgba(239, 68, 68, 0.12)` | `rgba(239, 68, 68, 0.35)` | Desaconselhado / Métricas críticas negativas |
| `RUNNING` | `#38BDF8` | `rgba(56, 189, 248, 0.12)` | `rgba(56, 189, 248, 0.35)` | Pipeline de análise em processamento ativo |
| `BLOCKED` | `#C084FC` | `rgba(168, 85, 247, 0.12)` | `rgba(168, 85, 247, 0.35)` | Aguardando ação humana / JEV / limite externo |
| `INSUFFICIENT_EVIDENCE` | `#94A3B8` | `rgba(100, 116, 139, 0.12)` | `rgba(100, 116, 139, 0.35)` | Dados insuficientes para cálculo de score |

### 3.3 Tipografia e Escala de Leitura

- **Família Display & Interface:** `Outfit, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- **Família Numérica e Monospaçada:** `"Geist Mono", "JetBrains Mono", Menlo, monospace`

| Nível | Tamanho | Peso | Line Height | Uso Específico |
|---|---|---|---|---|
| `display-score` | `48px` (3.0rem) | 700 (Bold) | `1.1` | Número central do Viability Score |
| `heading-1` | `32px` (2.0rem) | 700 (Bold) | `1.2` | Título da Análise / Nome do Curso Avaliado |
| `heading-2` | `24px` (1.5rem) | 600 (SemiBold) | `1.3` | Seções do Dossiê e Títulos de Cartões Principais |
| `heading-3` | `18px` (1.125rem) | 600 (SemiBold) | `1.4` | Títulos dos 6 Pilares e Cabeçalhos de Painéis |
| `body-base` | `15px` (0.9375rem) | 400 (Regular) | `1.5` | Texto corrido de pareceres e análises da LLM |
| `body-medium` | `14px` (0.875rem) | 500 (Medium) | `1.4` | Rótulos de formulário, botões e tabs |
| `caption` | `12px` (0.75rem) | 400 (Regular) | `1.4` | Metadados de evidência, datas e rodapés |
| `mono-data` | `13px` (0.8125rem) | 600 (SemiBold) | `1.0` | Indicadores numéricos, porcentagens e identificadores de hash |

---

## 4. Componentes Estruturais da Interface

### 4.1 Shell de Navegação (Header Corporativo)
- **Logotipo Primário Prometeus:** No canto superior esquerdo com link para a raiz da aplicação (`assets/brand/prometeus-logo-primary.png`);
- **Tenant Context Badge:** No centro-direita, exibe o cliente em formato pill translúcido:
  ```html
  <div class="prometeus-tenant-badge" role="status" aria-label="Ambiente corporativo ativo">
    <span class="tenant-icon" aria-hidden="true">🏛️</span>
    <span class="tenant-label">Ambiente Dedicado:</span>
    <strong>ENS — Escola de Negócios e Seguros</strong>
  </div>
  ```
- **Live Status Indicator:** Mostra a conectividade com o motor de análise em tempo real (ex.: `● Sistema Operacional`).

---

### 4.2 Stepper do Workflow em 15 Etapas
Guia o coordenador acadêmico durante a execução do pipeline de análise dividido em 3 fases:

1. **Fase 1 — Intake e Normalização:** `1. Contexto` ➔ `2. Intake` ➔ `3. Readiness` ➔ `4. Keywords` ➔ `5. Plano`
2. **Fase 2 — Coleta & Análise Multi-Fonte:** `6. Histórico Interno` ➔ `7. Mercado & Concorrência` ➔ `8. Higienização` ➔ `9. Decisões JEV` ➔ `10. Scoring Numérico`
3. **Fase 3 — Validação, Síntese e Entrega:** `11. Quality Gate` ➔ `12. Síntese Executiva` ➔ `13. Verificação Factual` ➔ `14. Dossiê Final` ➔ `15. Concluído`

**Comportamento dos Estados:**
- *Concluído:* Círculo preenchido em verde `#34D399` com ícone `✓`;
- *Ativo / Processando:* Anel em azul `#0652C5` pulsando com indicador `38BDF8`;
- *Pendente:* Círculo atenuado em `#334155` com número monospaçado;
- *Acessibilidade:* Cada etapa possui atributo `aria-current="step"` quando ativa e texto para leitores de tela indicando progresso percentual.

---

### 4.3 O Gauge do Viability Score (Card Principal de Decisão)
Componente central que condensa o parecer executivo para o comitê acadêmico:
- **Arco SVG Circular Dual-Track:**
  - Pista de fundo cinza escuro translúcida (`rgba(255,255,255,0.06)`);
  - Arco frontal dinâmico com gradiente linear `#0652C5` ➔ `#8DB5FF`, desenhado via `stroke-dasharray` proporcional à pontuação (0 a 100);
- **Valor Central Monospaçado:** Tipografia `display-score` (ex.: `86.4`) com sufixo secundário `/100`;
- **Pill Badge da Recomendação:** Exibição clara de `APROVADO`, `APROVADO COM AJUSTES` ou `ALTO RISCO`;
- **Medidores de Confiabilidade:**
  - *Coverage Index:* Barra horizontal indicando a completude dos dados das fontes primárias (ex.: `92%`);
  - *Confidence Index:* Grau de consistência cruzada entre fontes (ex.: `0.85`).
- **Acessibilidade:** Elemento possui `role="meter"`, `aria-valuenow="86.4"`, `aria-valuemin="0"`, `aria-valuemax="100"` e descrição alternativa em texto invisível (`.sr-only`).

---

### 4.4 Radar dos 6 Pilares de Viabilidade
Visualização multivariada para comparação simultânea dos 6 pilares de inteligência:
1. **Histórico Interno (Peso: 20%)**: Matrículas passadas, taxa de evasão e conversão;
2. **Concorrência Paga (Peso: 20%)**: Anúncios ativos na Meta Ads Library e longevidade;
3. **Busca & Viabilidade (Peso: 20%)**: Volume de busca no Google Trends e intenção comercial;
4. **Empregabilidade & Vagas (Peso: 15%)**: Postos de trabalho no CBO/CAGED e LinkedIn/Catho;
5. **Aderência da Ementa (Peso: 15%)**: Matriz de dores de mercado vs. competências do curso;
6. **Maturidade Regulatória (Peso: 10%)**: Conformidade com diretrizes do MEC e INEP.

**Regras Gráficas:**
- Geometria hexagonal em SVG;
- Área preenchida com azul primário a 20% de opacidade (`rgba(6, 82, 197, 0.20)`) e borda com 100% de opacidade (`#0652C5`);
- Cada vértice contém um ponto focal interativo (`hover`) que exibe tooltip com score individual e peso;
- **Fallback Acessível Obrigatório:** Imediatamente abaixo do radar, uma tabela semântica oculta para leitor de tela (ou expansível via teclado) apresenta os dados brutos e notas dos 6 pilares.

---

### 4.5 Card de Afirmação Factual & Evidence Drawer
Mecanismo obrigatório de auditoria e rastreabilidade:
- **Corpo da Afirmação:** Parágrafo consultivo gerado pela LLM analisando o mercado;
- **Badge de Grau de Suporte:**
  - `OBSERVADO`: Dado primário e direto extraído de fonte oficial (ex.: MEC ou CAGED);
  - `SUGESTIVO`: Inferência baseada em cruzamento de dados secundários;
  - `HIPÓTESE`: Projeção estratégica com premissas explícitas;
- **Botão "Inspecionar Evidência":**
  - Abre uma gaveta lateral deslizante (*Evidence Drawer*, `z-index: 30`) que não é cortada por `overflow: hidden`;
  - Contém abas estruturadas por fonte: `MEC/INEP`, `Google Trends`, `Meta Ads`, `Catho/LinkedIn`, `Reclame Aqui`;
  - Exibe o trecho bruto capturado, URL canônica, timestamp ISO-8601 e hash SHA-256 de integridade;
  - Fecha ao pressionar `Escape` e devolve o foco do teclado para o botão de origem.

---

### 4.6 Tabela Analítica de Cursos Concorrentes
Componente denso de comparação direta de mercado:
- Cabeçalho fixo (`sticky top`) com rótulos em caixa alta e fonte reduzida (11px);
- Células numéricas (mensalidade, carga horária, nota MEC) formatadas com `Geist Mono`;
- Linhas alternadas com destaque sutil ao passar o cursor (`:hover`);
- Suporte a navegação por teclado (`Tab`, setas para rolagem horizontal).

---

### 4.7 Estados de Carregamento, Erro e Vazio (Impeccable Standards)

1. **Skeleton Shimmer (Carregamento):**
   - Não utiliza spinners soltos no meio do conteúdo;
   - Simula a forma exata dos cards e gauges através de um gradiente linear animado (`prometeus-skeleton`);
   - Pausa a animação quando fora da tela visível ou sob modo de movimento reduzido.
2. **Empty State (Estado Vazio Educativo):**
   - Nunca exibe apenas "Nenhum resultado encontrado";
   - Contextualiza o motivo (ex.: *"Nenhum curso histórico de MBA em ESG encontrado para a regional Sudeste"*);
   - Oferece ação corretiva direta (ex.: *"Expandir filtros para território nacional"* ou *"Cadastrar nova pesquisa"*).
3. **Error State (Tratamento de Falha):**
   - Exibe mensagem em linguagem humana clara indicando o código do erro e o serviço afetado (ex.: *"Não foi possível consultar a API do Meta Ads. Os outros 5 pilares permanecem disponíveis"*);
   - Botão primário para reexecução imediata (*"Tentar novamente"*).

---

## 5. Implementação e Arquitetura de Arquivos

Os recursos do Prometeus Design System estão versionados nos seguintes diretórios:

- **Tokens JSON Canônicos:** [`config/design-system/tokens.json`](../../config/design-system/tokens.json)
- **Folha de Estilos de Produção:** [`config/design-system/tokens.css`](../../config/design-system/tokens.css)
- **Logotipos e Símbolos Oficiais:** [`assets/brand/`](../../assets/brand/)
- **Manual da Marca em Alta Resolução:** [`assets/brand/manual/`](../../assets/brand/manual/)
- **Documentação de Governança de Marca:** [`docs/product/brand-and-naming.md`](brand-and-naming.md)
- **Diretrizes Gráficas Completas:** [`docs/product/brand-guidelines.md`](brand-guidelines.md)
