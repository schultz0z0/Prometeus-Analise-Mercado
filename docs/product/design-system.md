# Design System — Prometeus UI

**Versão:** 1.0.0  
**Status:** Aprovado para especificação de frontend e dashboards  
**Referência de Marca:** [Diretrizes de Marca Prometeus](brand-guidelines.md) | [Manual da Marca](../../assets/brand/manual/)

---

## 1. Visão Geral e Princípios de Interface

O **Prometeus UI** é o sistema de design construído para expressar a sofisticação, precisão matemática e profundidade analítica do Prometeus. Ele resolve o desafio de apresentar dados complexos de inteligência de mercado (funis, concorrência, dores sociais, radar de 6 pilares e evidências de auditoria) de forma intuitiva, elegante e ágil para coordenadores acadêmicos, diretores de novos produtos e comitês de ensino.

### Princípios de Design

1. **Dark Canvas Imersivo (Profundidade & Foco):** O fundo escuro profundo (`#040814`) reduz a fadiga visual e destaca imediatamente gráficos, notas e scores coloridos com alto contraste.
2. **Precisão & Rastreabilidade Visual:** Todo número ou gráfico deve permitir clique ou hover para revelar sua evidência de origem (`evidence_id`), data de coleta e grau de suporte.
3. **Glassmorphism Estrutural:** Painéis e cartões flutuam sobre o fundo usando transparências controladas (`rgba(26, 35, 56, 0.7)`), desfoque óptico (`backdrop-blur-xl`) e bordas com luminosidade sutil (`border-white/10`).
4. **Hierarquia Tipográfica Clara:** Família **Outfit** para títulos e navegação, associada a **Geist Mono** para valores numéricos, hashes, porcentagens e identificadores de job.
5. **Marca Inviolável com Suporte a Multi-Instituição:** A identidade visual da Prometeus é permanente no topo e nos componentes centrais; a instituição cliente (ex.: ENS) é representada como contexto operacional ativo.

---

## 2. Design Tokens

### 2.1 Cores (Color Tokens)

#### Base e Superfícies
- `--prometeus-bg-canvas`: `#040814` (fundo principal)
- `--prometeus-bg-canvas-subtle`: `#070A10` (camada base alternativa)
- `--prometeus-surface-card`: `rgba(26, 35, 56, 0.75)` (fundo padrão de cards e painéis)
- `--prometeus-surface-elevated`: `#1A2338` (fundo de modais e menus suspensos)
- `--prometeus-surface-glass`: `rgba(255, 255, 255, 0.04)` (chips e botões secundários)

#### Marca e Destaque
- `--prometeus-primary`: `#0652C5` (Azul Prometeus — botões principais e foco)
- `--prometeus-primary-hover`: `#0860E8` (hover de ação primária)
- `--prometeus-primary-glow`: `rgba(6, 82, 197, 0.45)` (sombra luminosa de botões e gauges)
- `--prometeus-accent-ice`: `#8DB5FF` (Azul Céu — links, tags ativas e sparkles `✦`)
- `--prometeus-border-subtle`: `rgba(255, 255, 255, 0.10)` (bordas de cards e divisórias)
- `--prometeus-border-focus`: `rgba(141, 181, 255, 0.50)` (borda de foco ativo)

#### Tipografia
- `--prometeus-text-primary`: `#FFFFFF` (títulos e valores centrais)
- `--prometeus-text-secondary`: `#94A3B8` (subtítulos, descrições e labels)
- `--prometeus-text-muted`: `#64748B` (metadados secundários, rodapés e carimbos de data)
- `--prometeus-text-accent`: `#8DB5FF` (links destacados e badges)

#### Semântica & Feedback
- `--prometeus-status-approved`: `#34D399` (verde esmeralda — viabilidade alta / job concluído)
- `--prometeus-status-adjustments`: `#F59E0B` (âmbar dourado — aprovado com ajustes / revisão)
- `--prometeus-status-risk`: `#EF4444` (vermelho vivo — alto risco de mercado / falha)
- `--prometeus-status-running`: `#38BDF8` (azul claro pulsante — em processamento)
- `--prometeus-status-blocked`: `#A855F7` (roxo suave — aguardando dependência/JEV)

---

### 2.2 Tipografia (Typography Tokens)

- **Fonte Display & UI:** `Outfit, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- **Fonte Mono/Dados:** `"Geist Mono", "JetBrains Mono", Menlo, monospace`

| Nível | Família | Tamanho | Peso | Line Height | Aplicação |
|---|---|---|---|---|---|
| `display-1` | Outfit | `48px` (3rem) | 700 (Bold) | `1.1` | Destaque do Viability Score em tela cheia |
| `heading-1` | Outfit | `32px` (2rem) | 700 (Bold) | `1.2` | Título da Análise / Nome do Curso |
| `heading-2` | Outfit | `24px` (1.5rem) | 600 (SemiBold) | `1.3` | Seções do Dossiê e Títulos de Cartões |
| `heading-3` | Outfit | `18px` (1.125rem) | 600 (SemiBold) | `1.4` | Títulos de Pilares e Cabeçalhos de Colunas |
| `body-normal` | Outfit | `15px` (0.9375rem) | 400 (Regular) | `1.6` | Texto consultivo, parecer da LLM e justificativas |
| `body-medium` | Outfit | `14px` (0.875rem) | 500 (Medium) | `1.5` | Labels de formulário, botões e tabs |
| `caption` | Outfit | `12px` (0.75rem) | 400 (Regular) | `1.4` | Tags de evidência, datas e limitações metodológicas |
| `mono-stat` | Geist Mono | `14px` | 600 (SemiBold) | `1.0` | Indicadores numéricos tabulares (ex.: `86.4%`) |

---

### 2.3 Espaçamento, Raios de Borda e Sombras

- **Escala de Espaçamento:** `space-1 (4px)`, `space-2 (8px)`, `space-3 (12px)`, `space-4 (16px)`, `space-6 (24px)`, `space-8 (32px)`, `space-12 (48px)`
- **Border Radius:**
  - `radius-sm`: `6px` (tags internas e badges compactos)
  - `radius-md`: `10px` (inputs, botões e células)
  - `radius-lg`: `16px` (cards de métricas e painéis)
  - `radius-xl`: `24px` (modais e containers de dossiê)
  - `radius-full`: `9999px` (pills de status e avatares)
- **Elevação e Sombras:**
  - `shadow-card`: `0 8px 32px 0 rgba(0, 0, 0, 0.36)`
  - `shadow-glow-primary`: `0 0 24px rgba(6, 82, 197, 0.45)`
  - `shadow-glow-success`: `0 0 20px rgba(52, 211, 153, 0.35)`

---

## 3. Componentes Estruturais e de Negócio

### 3.1 Header Corporativo (Navigation Shell)
- **Logo Prometeus:** Logotipo principal no canto esquerdo com link de retorno;
- **Tenant Context Badge:** No centro/direita, badge elegante em formato pill:
  ```html
  <div class="tenant-badge">
    <span class="tenant-icon">🏫</span>
    <span class="tenant-label">Ambiente Dedicado:</span>
    <strong class="tenant-name">ENS — Escola de Negócios e Seguros</strong>
  </div>
  ```
- **Job Status Indicator:** Indicador vivo do job em tempo real (ex.: `● Online` ou `⟳ Analisando 8/15`).

---

### 3.2 O Gauge do Viability Score (Card Principal de Destaque)
Apresenta o resultado executivo final para a diretoria:
- **Anel Circular Progressivo:** Arco svg com gradiente em azul `#0652C5` e `#8DB5FF` que se preenche proporcionalmente ao score (0 a 100);
- **Valor Central:** Número grande `display-1` (ex.: `86.4`) com sufixo `/100`;
- **Status da Recomendação:** Badge de destaque imediato:
  - `APROVADO`: Verde esmeralda com brilho sutil;
  - `APROVADO COM AJUSTES`: Âmbar dourado;
  - `ALTO RISCO`: Vermelho;
  - `EVIDÊNCIAS INSUFICIENTES`: Cinza ardósia;
- **Metadados de Confiabilidade:** Dois medidores laterais horizontais:
  - **Coverage Index:** Barra percentual com o peso dos dados válidos coletados (ex.: `92%`);
  - **Confidence Index:** Medidor da estabilidade e coerência estatística das evidências (ex.: `0.85`).

---

### 3.3 Radar e Cards dos 6 Pilares de Análise
Grade responsiva apresentando a decomposição matemática auditável:

| Pilar | Peso | Indicador Visual | Detalhe Exibido |
|---|---:|---|---|
| **Histórico Interno** | 20% | Barra de progresso + Badge de comparáveis | Número de turmas históricas encontradas e conversão média |
| **Concorrência Paga** | 20% | Contador de anúncios ativos | Volume de anunciantes no Meta Ads e longevidade |
| **Busca & Viabilidade** | 20% | Gráfico de tendência (sparkline) | Volume mensal de buscas e CPC médio estimado |
| **Empregabilidade** | 15% | Contador de vagas e badges de ferramentas | Volume de vagas abertas e exigências de mercado |
| **Aderência da Ementa** | 15% | Matriz booleana de conformidade | Dores de alunos atendidas vs. lacunas curriculares |
| **Precificação** | 10% | Gráfico de faixa de mercado | Preço pretendido versus mediana da concorrência |

---

### 3.4 Card de Afirmações Fatuais e Recomendações (Factual Claim Card)
Projetado para garantir a rastreabilidade exigida pela governança:
- **Corpo da Afirmação:** Texto formal e consultivo redigido pela LLM generativa;
- **Badge de Nível de Suporte:**
  - `OBSERVADO`: Dados diretos com origem primária;
  - `SUGESTIVO`: Inferência baseada em proxies de mercado;
  - `HIPÓTESE`: Recomendação estratégica para validação humana;
- **Botão de Inspecionar Fonte:** Abre o *Evidence Drawer* exibindo a citação bruta, URL, data de coleta e hash da evidência.

---

### 3.5 Stepper de Progresso do Workflow (15 Etapas)
Utilizado durante o processamento assíncrono para dar visibilidade ao usuário:
- Linha temporal conectando as etapas:
  1. *Contexto* ➔ 2. *Intake* ➔ 3. *Readiness* ➔ 4. *Keywords* ➔ 5. *Plano* ➔ 6. *Histórico* ➔ 7. *Mercado* ➔ 8. *Higienização* ➔ 9. *Decisões JEV* ➔ 10. *Scoring* ➔ 11. *Quality Gate* ➔ 12. *Síntese* ➔ 13. *Verificação* ➔ 14. *Entrega*.
- Etapas concluídas ganham checkmark verde `✓`; etapa ativa pulsa em azul; etapas pendentes ficam em cinza atenuado.

---

## 4. Estrutura de Arquivos e Implementação

Os tokens e estilos do Design System estão disponíveis em:
- Arquivo de tokens canônico: [`config/design-system/tokens.json`](../../config/design-system/tokens.json)
- Folha de estilos CSS: [`config/design-system/tokens.css`](../../config/design-system/tokens.css)
- Assets da marca: [`assets/brand/`](../../assets/brand/)
- Manual de referência visual: [`assets/brand/manual/`](../../assets/brand/manual/)
