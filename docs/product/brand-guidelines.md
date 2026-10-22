# Diretrizes de Marca e Identidade Visual — Prometeus

Este documento consolida o **Manual da Marca Prometeus** e a identidade visual em produção no site institucional [`agenciaprometeus.com.br`](https://agenciaprometeus.com.br). Serve como especificação canônica para qualquer interface, relatório, material ou comunicação do produto.

---

## 1. Conceito e Essência da Marca

### 1.1 Significado Mitológico e Proposta de Valor
O nome **Prometeus** é inspirado em *Prometeu*, figura da mitologia grega associada ao conhecimento, à antecipação estratégica e ao fogo entregue à humanidade para romper a escuridão.
Assim como Prometeu trouxe o fogo para iluminar novos caminhos, a **Prometeus** existe para:
> **"Levar tecnologia e inteligência a empresas, ampliando o potencial das pessoas."**

### 1.2 Tagline e Posicionamento
- **Slogan Mestre:** `Tecnologia que amplia pessoas`
- **Pilares de Atuação:** `Automação • Pessoas • Resultados`
- **Descritor do Produto:** `Inteligência para Produtos Educacionais`

---

## 2. O Símbolo e a Geometria

```text
       ▲
      / \        Curvas fluidas inspiradas no fogo (conhecimento)
     /   \
    │  P  │      Silhueta que forma a letra 'P' estilizada
     \___/
      │ │
      ▼ ▼        Dois planos sobrepostos em tons de azul (#0652C5 e #8DB5FF)
```

O símbolo em **"P"** combina:
1. **A chama do fogo:** curvas ascendentes que representam iluminação, criatividade e conhecimento contínuo;
2. **A letra P:** estrutura sólida e geométrica de tecnologia e inovação;
3. **Planos tridimensionais (dobra de fita):** uma lâmina em azul vibrante e outra em azul celeste, conferindo profundidade, movimento e perspectiva de futuro.

### 2.1 Processo Construtivo
- **Passo 01 — Forma da chama:** arcos circulares tangentes que representam a energia do fogo;
- **Passo 02 — Construção do P:** combinação da haste vertical com o loop superior da letra;
- **Passo 03 — Ajustes e proporções:** refinamento das espessuras e curvatura interna;
- **Passo 04 — Símbolo final:** forma limpa, moderna, perfeitamente legível desde 16×16px (favicon) até grandes fachadas.

---

## 3. Assinaturas da Marca

Os arquivos gráficos oficiais estão versionados em [`assets/brand/`](../../assets/brand/):

| Versão | Arquivo | Aplicação Recomendada |
|---|---|---|
| **Principal (Dark Canvas)** | `prometeus-logo-primary.png` | Símbolo azul vibrante + palavra `pro` em azul `#0652C5` e `meteus` em branco `#FFFFFF`. Fundo preferencial: `#040814` a `#070A10`. |
| **Secundária (Monocromática)** | `prometeus-logo-secondary-white.png` | 100% branca translúcida sobre fundos fotográficos, mídias complexas ou materiais impressos monocromáticos. |
| **Símbolo Isolado** | `prometeus-symbol.png` | Favicon, avatares, apps mobile, docks de navegação e carregamentos. |
| **Versão Reduzida** | `prometeus-logo-small.png` | Cabeçalhos compactos e rodapés de relatórios. |

### 3.1 Área de Respiro (Margem de Segurança)
- O espaçamento mínimo em torno do logotipo deve corresponder à altura do caractere `x` (ou a curvatura da haste inferior do símbolo);
- Nenhum elemento de texto, botão ou linha de tabela deve invadir a zona de respiro.

### 3.2 Redução Mínima
- **Logotipo completo com texto:** altura mínima de `32px` em telas digitais;
- **Símbolo isolado:** dimensão mínima de `16×16px` (favicon) ou `24×24px` (UI buttons).

---

## 4. Paleta de Cores Oficial

A paleta traduz sofisticação, precisão tecnológica e profundidade analítica.

### 4.1 Cores Principais

| Nome | HEX | RGB | Função |
|---|---|---|---|
| **Azul Profundo (Deep Obsidian)** | `#040814` | `rgb(4, 8, 20)` | Base da marca, fundo mestre da aplicação, solidez e profundidade infinita. |
| **Azul Prometeus (Electric Cobalt)** | `#0652C5` | `rgb(6, 82, 197)` | Cor de ação, inovação, avanço e conexão. Botões primários, seleções ativas e destaques de gráficos. |

### 4.2 Cores de Apoio e Superfícies

| Nome | HEX | RGB | Função |
|---|---|---|---|
| **Azul Escuro (Card Surface)** | `#1A2338` | `rgb(26, 35, 56)` | Fundo de cartões, painéis, modais e containers com elevação. |
| **Azul Cinza (Border & Neutral)** | `#3B4B6B` | `rgb(59, 75, 107)` | Bordas secundárias, linhas divisórias, ícones secundários e textos de apoio. |
| **Azul Céu (Ice Accent)** | `#8DB5FF` | `rgb(141, 181, 255)` | Links, texto de ênfase em dark mode, badges secundários e sparkles `✦`. |
| **Cinza Claro (Light Surface)** | `#E2E8F0` | `rgb(226, 232, 240)` | Superfícies de alto contraste, bordas sutis e divisórias claras. |
| **Branco Absoluto** | `#FFFFFF` | `rgb(255, 255, 255)` | Tipografia primária, títulos, botões de ação reversa e máxima legibilidade. |

### 4.3 Cores Semânticas de Sistema (Status & Feedback)

| Função | HEX | Aplicação no Prometeus |
|---|---|---|
| **Sucesso / Aprovado** | `#34D399` (Emerald 400) | Viability Score >= 75, status `COMPLETED`, recomendação `APPROVED`. |
| **Alerta / Ajustes** | `#F59E0B` (Amber 500) | Recomendação `APPROVED_WITH_ADJUSTMENTS`, `REQUIRES_HUMAN_REVIEW`, limites limítrofes. |
| **Risco / Falha** | `#EF4444` (Rose 500) | `HIGH_RISK`, status `FAILED`, quebras de integridade da proposta. |
| **Informativo / Espera** | `#38BDF8` (Sky 400) | `QUEUED`, `RUNNING`, `WAITING_FOR_INPUT`, jobs assíncronos. |
| **Bloqueado / Neutro** | `#94A3B8` (Slate 400) | `BLOCKED`, `INSUFFICIENT_EVIDENCE`, dados ausentes ou em cache expirado. |

---

## 5. Tipografia

### 5.1 Família Primária: Outfit
- **Origem:** Google Fonts / Arquivo em `Desktop/Outfit`;
- **Classificação:** Geométrica contemporânea, equilibrada e altamente legível;
- **Pesos Oficiais:**
  - `Regular (400)`: parágrafos, descrições, tabelas e textos corridos;
  - `Medium (500)`: links, labels de formulários e cabeçalhos de tabelas;
  - `SemiBold (600)`: sub-títulos, métricas secundárias e botões;
  - `Bold (700)`: títulos H1/H2, números de destaque de Viability Score.

### 5.2 Família Monospaçada (Dados e Métricas): Geist Mono / JetBrains Mono
- Usada para hashes de evidências, IDs de análise (`anl_...`), percentuais tabulares e comandos da CLI.

---

## 6. Aplicação em Superfícies e Estética Visual

1. **Dark Mode Primário:** Toda a experiência do Prometeus é nativamente desenvolvida em modo escuro profundo (`#040814` a `#070A10`), transmitindo sensação cinematográfica, foco analítico e conforto visual prolongado;
2. **Glassmorphism e Profundidade:** Cartões utilizam `background: rgba(26, 35, 56, 0.65)` com `backdrop-filter: blur(16px)` e bordas finas com brilho sutil `border: 1px solid rgba(255, 255, 255, 0.08)`;
3. **Glow de Ação:** Botões e indicadores ativos possuem brilho atmosférico na cor Azul Prometeus (`box-shadow: 0 0 24px rgba(6, 82, 197, 0.45)`);
4. **Respeito à Autoria no White-label:** Em qualquer deployment (incluindo ENS), a barra de navegação superior e o rodapé ostentam a assinatura da marca Prometeus. A instituição cliente recebe destaque como *Ambiente Ativo*, nunca ocultando a autoria do produto.
