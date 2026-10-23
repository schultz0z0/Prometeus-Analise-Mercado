/**
 * PROMETEUS INTELLIGENCE PLATFORM — MOCK DATA CANÔNICO
 * Representa os contratos reais de API da Prometeus e dos adaptadores da IES.
 */

export const INITIAL_TENANTS = [
  { id: "ens", name: "ENS — Escola de Negócios e Seguros", code: "ENS", segment: "Seguros, Finanças e Riscos" },
  { id: "fgv", name: "FGV Educação Executiva", code: "FGV", segment: "Administração e Economia" },
  { id: "puc", name: "PUC Minas Virtual", code: "PUC", segment: "Tecnologia e Negócios" }
];

export const INITIAL_SETTINGS = {
  ens: {
    crm_api_url: "https://api.ens.edu.br/v1/cursos-historico",
    crm_token: "ens_live_sec_884912fa89b",
    crm_status: "CONNECTED",
    crm_last_sync: "Sincronizado: 5 cursos (2 anos de ofertas: 2024 e 2025)",
    apify_token: "",
    apify_status: "NOT_CONFIGURED",
    ga_property_id: "GA4-ENS-PROMETEUS-2026",
    meta_ads_token: "",
    meta_ads_status: "NOT_CONFIGURED",
    llm_provider: "ChatGPT Codex (OAuth Oficial)",
    quorum_min: 18,
    target_margin: 42,
    reference_cac: 480
  }
};

export const INITIAL_COURSES = [
  {
    id: "JOB-2026-ENS-884",
    name: "MBA em Inteligência Artificial Aplicada a Seguros e Gestão de Riscos",
    area: "Ciências de Dados & Mercado Financeiro",
    level: "MBA Executivo",
    modality: "EAD Síncrono",
    ticket: 980.00,
    duration_months: 12,
    status: "COMPLETED",
    recommendation: "APPROVED_WITH_ADJUSTMENTS",
    viability_score: 86.4,
    coverage_index: 92.0,
    confidence_index: 0.88,
    demand_level: "MUITO ALTA (+88% YoY)",
    competition_pressure: "MODERADA / ALTA",
    breakeven_students: 18,
    projected_students: 32,
    net_revenue_projected: 142800.00,
    created_at: "2026-10-22T09:40:00Z",
    human_decision: {
      status: "APPROVED_WITH_ADJUSTMENTS",
      decision_by: "Prof. Dr. Arnaldo Silveira (Diretor Acadêmico)",
      decided_at: "2026-10-22T11:15:00Z",
      notes: "Aprovado pelo comitê. Aceitamos integralmente a substituição do módulo teórico 3 pelas oficinas práticas de SUSEP e modelos preditivos em Python sugeridas pela Prometeus."
    }
  },
  {
    id: "JOB-2026-ENS-881",
    name: "Pós-Graduação em ESG, Finanças Sustentáveis e Mercado Segurador",
    area: "Gestão, Sustentabilidade & Seguros",
    level: "Pós-Graduação Lato Sensu",
    modality: "100% EAD",
    ticket: 1150.00,
    duration_months: 12,
    status: "COMPLETED",
    recommendation: "APPROVED",
    viability_score: 91.2,
    coverage_index: 95.0,
    confidence_index: 0.91,
    demand_level: "ALTÍSSIMA (+120% YoY)",
    competition_pressure: "BAIXA (Oceano Azul)",
    breakeven_students: 15,
    projected_students: 38,
    net_revenue_projected: 224000.00,
    created_at: "2026-10-20T14:20:00Z",
    human_decision: {
      status: "APPROVED",
      decision_by: "Dra. Carolina Mendes (Coordenação de Novos Produtos)",
      decided_at: "2026-10-21T10:00:00Z",
      notes: "Prioridade máxima de lançamento para o primeiro semestre. Baixa concorrência mapeada e altíssima demanda corporativa."
    }
  },
  {
    id: "JOB-2026-ENS-875",
    name: "Especialização em Direito Digital e Prevenção a Fraudes em Apólices",
    area: "Direito, Compliance & Tecnologia",
    level: "Pós-Graduação Lato Sensu",
    modality: "Híbrido",
    ticket: 790.00,
    duration_months: 10,
    status: "COMPLETED",
    recommendation: "APPROVED_WITH_ADJUSTMENTS",
    viability_score: 74.8,
    coverage_index: 88.0,
    confidence_index: 0.84,
    demand_level: "MODERADA (+35% YoY)",
    competition_pressure: "MÉDIA",
    breakeven_students: 22,
    projected_students: 27,
    net_revenue_projected: 39500.00,
    created_at: "2026-10-18T11:00:00Z",
    human_decision: null
  },
  {
    id: "JOB-2026-ENS-869",
    name: "Tecnólogo em Gestão de Seguros Tradicional",
    area: "Negócios & Operações",
    level: "Graduação Tecnológica",
    modality: "Presencial",
    ticket: 420.00,
    duration_months: 24,
    status: "COMPLETED",
    recommendation: "HIGH_RISK",
    viability_score: 41.5,
    coverage_index: 82.0,
    confidence_index: 0.79,
    demand_level: "EM QUEDA (-22% YoY)",
    competition_pressure: "MUITO ALTA (Guerra de Preços)",
    breakeven_students: 40,
    projected_students: 19,
    net_revenue_projected: -38000.00,
    created_at: "2026-10-15T16:30:00Z",
    human_decision: {
      status: "REJECTED",
      decision_by: "Comitê de Ensino",
      decided_at: "2026-10-16T14:00:00Z",
      notes: "Proposta rejeitada. Mercado presencial tradicional saturado e com projeção de prejuízo operacional."
    }
  }
];

export const DETAILED_DOSSIER = {
  course_id: "JOB-2026-ENS-884",
  pillars: [
    { name: "Histórico Interno (ENS CRM)", weight: "20%", score: 85.0, status: "Forte", detail: "3 turmas correlatas identificadas com 14.2% de conversão média." },
    { name: "Concorrência Paga (Meta Ads)", weight: "20%", score: 78.0, status: "Moderada/Alta", detail: "22 anúncios ativos mapeados em 4 instituições de ponta." },
    { name: "Busca & Tendência (Google)", weight: "20%", score: 92.0, status: "Altíssima", detail: "Crescimento de +88% em pesquisas orgânicas e CPC médio de R$ 3,40." },
    { name: "Empregabilidade (CBO / LinkedIn)", weight: "15%", score: 88.0, status: "Aquecida", detail: "1.420 vagas ativas com média salarial de R$ 12.800 para especialistas em dados/seguros." },
    { name: "Aderência da Ementa (JEV)", weight: "15%", score: 90.0, status: "Alinhada com Ajustes", detail: "Resolve 4 de 5 dores críticas mineradas; 1 módulo precisa de virada prática." },
    { name: "Maturidade Regulatória (MEC)", weight: "10%", score: 82.0, status: "Conforme", detail: "360h compatíveis com Resolução CNE/CES nº 1/2018 para Lato Sensu." }
  ],
  radar_points: {
    historico: 85,
    concorrencia: 78,
    busca: 92,
    empregabilidade: 88,
    ementa: 90,
    regulatorio: 82
  },
  competitors: [
    { institution: "Fundação Getulio Vargas (FGV)", course: "Master em Analytics e Data Science nos Negócios", modality: "EAD Síncrono", price: "R$ 1.250,00/mês", active_ads: 14, weakness: "Pouca profundidade na regulação de seguros da SUSEP." },
    { institution: "PUC Minas Virtual", course: "Pós-Graduação em Inteligência Artificial e Aprendizado de Máquina", modality: "100% EAD Assíncrono", price: "R$ 680,00/mês", active_ads: 8, weakness: "Muito genérico; não dialoga com o mercado segurador e financeiro." },
    { institution: "FIA Business School", course: "Analytics Aplicado a Riscos e Fraudes Corporativas", modality: "Híbrido (SP)", price: "R$ 1.480,00/mês", active_ads: 19, weakness: "Formato rígido presencial/híbrido com ticket muito elevado." }
  ],
  social_listening_pains: [
    { pain: "Cursos concorrentes são excessivamente teóricos com slides antigos e fórmulas sem código.", count: 184, percent: "38%" },
    { pain: "Falta de foco no dia a dia regulatório (SUSEP, Lei do Open Insurance e LGPD de dados sensíveis).", count: 122, percent: "25%" },
    { pain: "Desejo expresso por projetos práticos em Python para precificação atuarial e detecção de fraudes.", count: 98, percent: "20%" },
    { pain: "Preço muito alto nos cursos de elite (FGV/FIA) sem flexibilidade de horário.", count: 82, percent: "17%" }
  ],
  curriculum_adjustments: [
    {
      module: "Módulo 3: Fundamentos Teóricos de Modelagem Estatística (40h)",
      problem: "Altamente abstrato; repete conteúdo que os alunos já viram na graduação.",
      solution: "Substituir por: 'Laboratório Prático de Modelos Preditivos em Python e Precificação Dinâmica de Apólices' (40h).",
      impact: "Aumenta a diferenciação competitiva em 40% frente à FGV e PUC."
    },
    {
      module: "Módulo 5: Tópicos Especiais em Governança (30h)",
      problem: "Ementa vaga sem menção às resoluções recentes.",
      solution: "Atualizar para: 'Compliance Tecnológico SUSEP, Open Insurance e Auditoria de Algoritmos' (30h).",
      impact: "Torna a ENS a única escola do Brasil a emitir certificação alinhada à nova regulação."
    }
  ],
  commercial_kit: {
    recommended_names: [
      { name: "MBA em Inteligência Artificial e Analytics para Seguros", note: "Opção mais forte em SEO e busca de marca (Volume: 2.400 buscas/mês)." },
      { name: "MBA Executivo em IA, Gestão Atuarial e Fraudes em Seguros", note: "Excelente para conversão no LinkedIn e público corporativo B2B." },
      { name: "Pós-Graduação em Data Science e Regulação no Mercado Segurador", note: "Foco técnico para atuários, estatísticos e engenheiros de dados." }
    ],
    ad_hooks: [
      "Pare de ver IA como teoria. Aprenda a prever sinistros e combater fraudes com Python e regras SUSEP.",
      "O mercado de seguros tem 1.400+ vagas abertas para quem domina dados. Seu próximo passo na ENS.",
      "Enquanto a concorrência ensina teorias de 2018, a ENS ensina os modelos reais que as maiores seguradoras usam hoje."
    ]
  },
  evidences: [
    {
      id: "EV-2026-MEC-883",
      source: "MEC / INEP — Sistema e-MEC",
      url: "https://emec.mec.gov.br/consulta/cadastro/2026",
      timestamp: "2026-10-22T09:41:15Z",
      sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      snippet: "Registro de conformidade de carga horária e corpo docente qualificado (Art. 7º Resolução CNE/CES nº 1/2018). Sem impedimentos regulatórios."
    },
    {
      id: "EV-2026-ADS-441",
      source: "Meta Ads Library API (Graph API v21.0)",
      url: "https://graph.facebook.com/v21.0/ads_archive",
      timestamp: "2026-10-22T09:41:22Z",
      sha256: "9a01f84b65c9284fa920e8812cfa81203019842af1249b01984fba019842a198",
      snippet: "FGV mantém 14 campanhas ativas com gasto estimado superior a R$ 35.000/mês para 'Analytics em Negócios'. Criativos apelam para transição de carreira."
    },
    {
      id: "EV-2026-CBO-102",
      source: "Ministério do Trabalho e Emprego — CBO & CAGED",
      url: "http://www.mtecbo.gov.br/cbosite/pages/pesquisas/BuscaPorTitulo.jsf",
      timestamp: "2026-10-22T09:41:35Z",
      sha256: "f4019284bc91240a18401924b10924a102941092840192840192840192840192",
      snippet: "CBO 2124-05 (Especialista em Ciência de Dados) registrou saldo positivo de 1.420 admissões no setor K (Atividades Financeiras e de Seguros) no acumulado do ano."
    }
  ]
};

export const INITIAL_HISTORICAL_COURSES = [
  {
    external_id: "ENS-MBA-SEG-01",
    name: "MBA em Gestão Estratégica de Seguros e Resseguros",
    category: "MBA Executivo",
    segment: "Gestão Executiva & Resseguros",
    modality: "Online (Síncrono)",
    workload_hours: 360,
    status: "active",
    tier: "SUCESSO",
    quorum_min: 20,
    metrics_summary: {
      total_periods: 2,
      total_leads: 2730,
      total_enrolled: 186,
      average_ticket_brl: 16350.00,
      total_revenue_brl: 3051000.00,
      avg_conversion_rate: 0.0680
    },
    funnel_history: [
      { period: "2024", leads: 1250, applicants: 260, enrolled: 84, ticket: 15800.00, revenue: 1327200.00, status: "COMPLETED", notes: "Superou quórum em 420%. Margem líquida de 48%." },
      { period: "2025", leads: 1480, applicants: 310, enrolled: 102, ticket: 16900.00, revenue: 1723800.00, status: "COMPLETED", notes: "Expansão recorde com 102 matriculados via convênios corporativos." }
    ]
  },
  {
    external_id: "ENS-ESP-CYBER-02",
    name: "Especialização em Subscrição de Riscos Cibernéticos e Fraudes Digitais",
    category: "Pós-Graduação Lato Sensu",
    segment: "Cibersegurança & Fraudes Digitais",
    modality: "Online (Síncrono)",
    workload_hours: 180,
    status: "active",
    tier: "SUCESSO",
    quorum_min: 18,
    metrics_summary: {
      total_periods: 2,
      total_leads: 1740,
      total_enrolled: 126,
      average_ticket_brl: 9800.00,
      total_revenue_brl: 1245600.00,
      avg_conversion_rate: 0.0721
    },
    funnel_history: [
      { period: "2024", leads: 780, applicants: 155, enrolled: 54, ticket: 9200.00, revenue: 496800.00, status: "COMPLETED", notes: "Quórum de 300%. Forte adesão de seguradoras e bancos." },
      { period: "2025", leads: 960, applicants: 198, enrolled: 72, ticket: 10400.00, revenue: 748800.00, status: "COMPLETED", notes: "Crescimento de +33% YoY impulsionado por alta de incidentes no país." }
    ]
  },
  {
    external_id: "ENS-EXT-SIN-03",
    name: "Extensão Executiva em Gestão e Regulação Técnica de Sinistros",
    category: "Extensão Universitária",
    segment: "Operações & Perícia de Sinistros",
    modality: "Híbrido",
    workload_hours: 90,
    status: "active",
    tier: "MEDIANO",
    quorum_min: 18,
    metrics_summary: {
      total_periods: 2,
      total_leads: 1010,
      total_enrolled: 46,
      average_ticket_brl: 5400.00,
      total_revenue_brl: 248800.00,
      avg_conversion_rate: 0.0456
    },
    funnel_history: [
      { period: "2024", leads: 490, applicants: 72, enrolled: 22, ticket: 5200.00, revenue: 114400.00, status: "COMPLETED", notes: "Atingiu quórum no limite de sustentabilidade (22 alunos vs 18 mín.)." },
      { period: "2025", leads: 520, applicants: 76, enrolled: 24, ticket: 5600.00, revenue: 134400.00, status: "COMPLETED", notes: "Turma estável com margem moderada de 26%." }
    ]
  },
  {
    external_id: "ENS-CAP-VEND-04",
    name: "Capacitação em Técnicas Tradicionais de Vendas para Corretores Locais",
    category: "Aperfeiçoamento Profissional",
    segment: "Comercial & Vendas Presenciais",
    modality: "Presencial",
    workload_hours: 40,
    status: "active",
    tier: "FRACO",
    quorum_min: 15,
    metrics_summary: {
      total_periods: 2,
      total_leads: 600,
      total_enrolled: 28,
      average_ticket_brl: 1850.00,
      total_revenue_brl: 51600.00,
      avg_conversion_rate: 0.0466
    },
    funnel_history: [
      { period: "2024", leads: 340, applicants: 42, enrolled: 16, ticket: 1800.00, revenue: 28800.00, status: "COMPLETED", notes: "Turma abriu no limite (16 alunos vs breakeven 15). Margem residual." },
      { period: "2025", leads: 260, applicants: 29, enrolled: 12, ticket: 1900.00, revenue: 22800.00, status: "COMPLETED", notes: "Queda de 23% na procura. Turma operou com 12 alunos em prejuízo." }
    ]
  },
  {
    external_id: "ENS-APERF-DIR-05",
    name: "Aperfeiçoamento em Doutrina e Teoria Pura do Direito Securitário",
    category: "Aperfeiçoamento Jurídico",
    segment: "Doutrina & Teoria Jurídica Pura",
    modality: "Presencial",
    workload_hours: 60,
    status: "archived",
    tier: "CANCELADO_POR_QUORUM",
    quorum_min: 15,
    metrics_summary: {
      total_periods: 2,
      total_leads: 325,
      total_enrolled: 21,
      average_ticket_brl: 4200.00,
      total_revenue_brl: 58500.00,
      avg_conversion_rate: 0.0618
    },
    funnel_history: [
      { period: "2024", leads: 210, applicants: 24, enrolled: 15, ticket: 3900.00, revenue: 58500.00, status: "COMPLETED", notes: "Turma 2024 abriu exatamente no ponto de equilíbrio (15 alunos)." },
      { period: "2025", leads: 115, applicants: 11, enrolled: 6, ticket: 4500.00, revenue: 0.00, status: "CANCELLED_LOW_QUORUM", notes: "OFERTA 2025 CANCELADA: Apenas 6 alunos matriculados de 15 necessários. Valores estornados e oferta presencial descontinuada." }
    ]
  }
];
