# Avaliação da Inteligência de Mercado — Unidades, Regras e Denominadores

> Versão do Dicionário de Métricas: **1.0.0**  
> Status: **Normativo / Canônico para Homologação ENS**  
> Referência de Auditoria: [Relatório de Auditoria 30/10/2026](../implementation/reports/senior-market-intelligence-audit-2026-10-30.md) e [Baseline Congelado](../implementation/reports/senior-market-intelligence-baseline-2026-10-29.json).

---

## 1. Ontologia de Unidades de Informação

Para eliminar a confusão entre o volume bruto de dados coletados e a dimensão real do mercado, o sistema define cinco unidades canônicas estritas:

| Unidade | Definição Formal | Exemplo no Caso ENS | Regra de Agregação / Limite |
|---|---|---|---|
| **`Capture`** | Uma única observação proveniente de uma fonte, execução de ferramenta (run) e instante temporal específicos. | Uma linha retornada por busca ou um registro de anúncio da Meta Ads Library. | 144 capturas salvas não equivalem a 144 concorrentes ou 144 vagas independentes. |
| **`Entity`** | Objeto do mundo real identificado com chave canônica estável (curso/oferta concorrente, vaga de emprego, anúncio unificado, post ou perfil institucional). | O anúncio da ENS sobre "MBA Gestão de Seguros" repetido 5 vezes em consultas distintas é uma única `Entity`. | Múltiplas capturas da mesma entidade informam histórico/variação, mas contam como uma entidade única no dimensionamento competitivo. |
| **`Fact`** | Extração estruturada de um dado verificável, obrigatoriamente vinculada a `source_url`, JSON pointer/página/trecho exato e data da observação. | Mensalidade de R$ 976,00 em 20 parcelas observada na página oficial do concorrente em 29/10/2026. | Um fato nunca pode ser inferido por suposição ou generalização sem citação do trecho comprovatório. |
| **`Judgment`** | Avaliação delimitada efetuada por um componente de decisão (System One / JEV / LLM estrita) para uma finalidade específica. | Avaliação se uma vaga de "Analista de Sinistros" atesta competências curriculares requeridas para o programa. | Um julgamento não altera fatos nem inventa dados ausentes; possui tipo, score/choice, distribuição e confiança. |
| **`Claim`** | Afirmação explícita contida no parecer ou dossiê final de viabilidade. | "A média de preços de programas concorrentes observados na Grande São Paulo é R$ 18.500,00." | Toda claim material deve ser mapeada para `Fact` ou identificada categoricamente como premissa/hipótese. |

---

## 2. Estados de Observação Estritos

É expressamente proibido igualar dados nulos, ausentes ou zero. O pipeline reconhece oito estados mutuamente exclusivos:

| Estado | Significado Semântico | O que NUNCA pode ser feito |
|---|---|---|
| **`observed`** | Sinal medido diretamente na fonte com valor positivo ou afirmativo. | Não pode ser extrapolado para além do recorte espacial/temporal observado. |
| **`observed_zero`** | A fonte foi consultada com sucesso no recorte correto e retornou explicitamente zero ocorrências ou valor nulo verificado. | **Não equivale a `missing`.** Ter zero vagas encontradas em termo restrito não é o mesmo que a API de vagas ter falhado. |
| **`missing`** | O campo ou dado esperado não consta no payload retornado, embora a fonte tenha respondido. | **Não pode ser convertido em zero.** Salário não informado em anúncio de vaga não significa salário R$ 0,00. |
| **`unsupported`** | A fonte consultada não tem capacidade técnica ou licença para fornecer a dimensão solicitada. | **Não pode gerar penalidade de qualidade à fonte.** O Google Search tradicional não fornece série histórica quantitativa. |
| **`ambiguous`** | O sinal foi retornado, mas há multiplicidade de sentidos, duplicidade conflitante ou falso cognato. | **Não pode ser aceito sem desambiguação** ou rotulação como contexto incerto. |
| **`partial`** | O payload contém apenas parte dos dados planejados (ex.: paginação truncada ou corte de orçamento). | Deve registrar os limites e a taxa de cobertura efetiva em vez de simular completude. |
| **`censored`** | Informação omitida por política de privacidade (LGPD/PII), proteção de termos ou segredo comercial. | Ocultação de CPF/telefone não deve corromper timestamps ou identificadores técnicos. |
| **`failed`** | A requisição à fonte falhou por erro HTTP, timeout, bloqueio ou transporte. | **Não pode ser interpretado como sinal de mercado fraco.** Falha do scraper não é ausência de concorrentes. |

---

## 3. Quatro Objetos Distintos de Medição

O sistema proíbe sintetizar uma nota única genérica de qualidade que misture o mérito comercial do curso com o desempenho técnico dos coletores e modelos:

```
┌────────────────────────────────────────────────────────────────────────┐
│               DISTINÇÃO ONTOLÓGICA DAS QUATRO MEDIÇÕES                  │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Viabilidade do Curso (Score de Mercado):                            │
│    Métrica de negócio: atratividade da oferta educacional ENS          │
│    (demanda, concorrência, preço, currículo, histórico).               │
├────────────────────────────────────────────────────────────────────────┤
│ 2. Qualidade dos Dados (Integridade & Fidelidade):                     │
│    Métrica técnica: ausência de corrupção, preservação de campos       │
│    críticos, sanitização correta e integridade de timestamps.         │
├────────────────────────────────────────────────────────────────────────┤
│ 3. Cobertura de Perguntas (Completude do Plano):                       │
│    Métrica de pesquisa: proporção de perguntas de decisão com         │
│    evidência empírica válida e recorte verificado.                    │
├────────────────────────────────────────────────────────────────────────┤
│ 4. Confiança do Julgamento (Certeza Estatística e Semântica):          │
│    Métrica epistêmica: calibração das inferências e solidez            │
│    probatória, penalizada por lacunas de pilares essenciais.          │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Matriz de Perguntas Obrigatórias por Categoria e Público

Nem todos os públicos exigem os mesmos canais de evidência. A exigência de evidência é proporcional ao tipo de formação e ao modelo de contratação (B2B corporativo vs. B2C indivíduo):

### 4.1. Por Categoria de Programa

| Categoria | Perguntas Obrigatórias de Viabilidade | Evidência Mínima Aceitável | Canais Requeridos | Canais Não Exigidos |
|---|---|---|---|---|
| **MBA / Pós-Graduação** | 1. Há empregabilidade sênior e demanda por competências de gestão/especialização?<br>2. Quais concorrentes diretos credenciados cobrem este tema?<br>3. Qual o patamar de mensalidade e carga horária praticado?<br>4. Há aderência entre ementa e necessidades observadas? | - Mínimo de ofertas com grade verificada.<br>- Vagas de nível especialista/gerencial com descrição de atribuições.<br>- Série de interesse de busca regionalizada. | Sites oficiais de IES, LinkedIn Vagas, Google Search / Trends. | TikTok / comentários virais de entretenimento. |
| **Graduação** | 1. Qual o volume de inscritos e concorrência no Censo da Educação Superior?<br>2. Há mercado regional para absorção dos egressos?<br>3. Qual o ticket de entrada e financiamento disponível? | - Dados oficiais de matrícula / ingressantes.<br>- CBOs formais do mercado de trabalho formal (Caged/RAIS). | INEP, MEC, MTE, sites de vestibulares. | Anúncios de cursos livres de curta duração. |
| **Extensão / Aperfeiçoamento** | 1. Há lacuna pontual de capacitação técnica no mercado?<br>2. O preço total é viável para aquisição por impulso ou reembolso corporativo?<br>3. O formato e duração atendem à rotina do profissional? | - Ofertas ativas e cursos livres comparáveis.<br>- Anúncios de tráfego pago ativos.<br>- Manifestação de dúvidas técnicas da comunidade profissional. | Meta Ads Library, Google Search, Fóruns profissionais, YouTube especializado. | Censo do Ensino Superior / INEP. |
| **Imersão / Bootcamp** | 1. Há urgência de requalificação profissional?<br>2. Os resultados práticos prometidos justificam ticket concentrado? | - Volume de vagas que exigem ferramental prático imediato.<br>- Ofertas intensivas de agentes de capacitação. | LinkedIn Vagas, plataformas de contratação técnica, Meta Ads. | Histórico acadêmico formal de longa duração. |
| **Certificação Avançada** | 1. Há exigência regulatória, selo setorial ou valorização formal por empregadores?<br>2. Quais as taxas de aprovação e benefícios de carreira? | - Normativos setoriais e menção explícita da credencial em perfis/vagas. | Órgãos reguladores (ex.: SUSEP, CNseg), vagas corporativas. | Redes de vídeo curto. |

### 4.2. Por Modelo de Atendimento: B2B vs. B2C

| Dimensão | B2B (Corporativo / In-Company / Patrocinado) | B2C (Varejo / Matrícula Individual) |
|---|---|---|
| **Decisor de Compra** | Diretor de RH, C-Level, Gerente de Treinamento e Desenvolvimento. | O próprio profissional ou estudante. |
| **Sensibilidade a Preço** | Foco em ROI institucional, orçamento de T&D e contrato global de turmas. | Foco no valor da parcela mensal e comprometimento da renda pessoal. |
| **Sinais de Procura Válidos** | Contratações formais, programas de inovação setorial, prêmios emitidos por seguradoras, parcerias sindicais. | Volumes de busca orgânica, leads de campanha de mídia paga, interações em redes sociais. |
| **Canais Probatórios** | Publicações institucionais, relatórios setoriais (SUSEP/CNseg), contratação corporativa via LinkedIn. | Campanhas ativas no Meta Ads, Google Ads / Search, tendências de busca no Trends. |

---

## 5. Reconciliação do Baseline Congelado (Censo dos 144 Registros)

A auditoria offline de 29-30/10/2026 fixou o baseline imutável da análise `73501c53-cc58-47f9-8927-d9e299b4f4b5`. Todos os números reproduzem rigorosamente as seguintes identidades:

### 5.1. Totais Canônicos
$$\text{Total de Capturas} = 144 = 17 \text{ (Indicadores)} + 73 \text{ (Contexto)} + 54 \text{ (Excluídos)}$$

- **Rendimento de Indicadores:** $17 / 144 = 11,8055\%$
- **Registros com `quality_score == 1.0`:** $144 / 144$ (indica apenas ausência de prompt injection, não precisão analítica).
- **Consultas Apify:** 19 tentativas ($15 \text{ com sucesso} + 3 \text{ vazias} + 1 \text{ parcial}$).
- **Custo Apify reportado:** $\text{US\$} \, 0,311142$.

### 5.2. Hashes de Arquivos Insumo Auditados
- `COMO_ESTUDAR.md`: `bafe4597e8e8304d9f971fe7f4f3dbd70153b979298eb081e5207c392a0aec06`
- `consultas_e_checkpoints.json`: `08c10765e18ffff6ad5eaaccad4f0b26aa3949ff3a4d5ad4b9a52f7a066da8a2`
- `decisoes_registradas.json`: `44de8384e1f6ee2a121e9e434ed72ca0ae41d1a8bbb3afc1aed9976bd5ba4249`
- `dossie_publicado.json`: `8aa741260e5c29fd9a8def0f3d9575caab76393f19c7bd8a1a6e36c28b94c7c0`
- `fatos_enviados_ao_redator.json`: `e5827116c2a5f4b03484420c6b7684270eb0d2a72737083ea23242527d418878`
- `LEIA_PRIMEIRO.html`: `49faa454e1fae0222cbfadf1254e18c51cee6e5f27cece01acd990441cbf72b2`
- `manifesto.json`: `a2323637cc26a2aabfe204e3eae8b647635f8d4282e7a9ffcd9714d77a281b9c`
- `parametros_planejados_persistidos.json`: `1faf7dea193a9bb16fefed33c85467ed37d07e6efc7b129d273c9878cc4ff127`
- `registros_para_estudo.json`: `1caaf6d7e2a60443525d9a24a7587185e36a6ea3d16422f279d667f2ace530a1`
- `retornos_originais_e_higienizados.json`: `13ad0f8e3ddb07e92e7710fc97324449687e00b2a65909eb26629066c1e078bb`

### 5.3. Perdas Críticas Documentadas no Baseline
1. **Entradas acima de 14.000 caracteres:** 20 registros cortados arbitrariamente, incluindo 3 séries de Google Trends (786 pontos com timestamps mascarados como telefone).
2. **Descrições de vagas omitidas:** 28 de 30 descrições de vagas do LinkedIn ausentes do resumo factual, incluindo todas as 16 vagas aceitas como indicadores curriculares.
3. **Concentração amostral no YouTube:** 15 de 15 comentários obtidos de um único vídeo, apesar de 10 URLs planejadas.

---

## 6. Procedimento de Teste e Reprodutibilidade

Para verificar offline a aderência dos artefatos a este contrato sem rede ou chamadas a modelos:

```powershell
rtk proxy .venv/Scripts/python.exe docs/implementation/reports/senior-market-intelligence-baseline-checks-2026-10-30.py
```

Qualquer alteração metodológica deve ser precedida de atualização deste documento e criação de novo snapshot versionado.

