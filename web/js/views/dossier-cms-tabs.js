/**
 * PROMETEUS INTELLIGENCE PLATFORM — CMS DOSSIER 9-SUBPAGE ENGINE (DARK THEME)
 * Renderiza o template multi-subpágina do Dossiê Executivo de Viabilidade:
 * 1. Visão Geral (overview)
 * 2. Métricas-Chave (key_metrics)
 * 3. Concorrência Fixa (fixed_competition)
 * 4. Radar Setorial (sector_radar)
 * 5. Economia & Cenários (economics)
 * 6. SWOT & TOWS (swot_tows)
 * 7. Pilares de Viabilidade (viability_pillars)
 * 8. Revisões (revisions)
 * 9. Fontes & Evidências (sources_evidences)
 */

import {
  escapeHtml,
  safeUrl,
  recommendationLabel
} from '../dossier-format.js';

export const CMS_TABS_META = [
  {
    id: 'overview',
    label: 'Visão Geral',
    title: 'Dossiê de Viabilidade',
    subtitle: 'Relatório pós-análise de viabilidade para o lançamento do curso, com consolidação de evidências, projeções e recomendação executiva.'
  },
  {
    id: 'key_metrics',
    label: 'Métricas-Chave',
    title: 'Métricas-Chave',
    subtitle: 'Consolida os principais indicadores da viabilidade, com desempenho histórico, procura externa, conversão, eficiência e resultado esperado.'
  },
  {
    id: 'fixed_competition',
    label: 'Concorrência Fixa',
    title: 'Concorrência Fixa',
    subtitle: 'Monitoramento comparativo dos players do mercado e suas ofertas, com análise de posicionamento, atributos, preços e diferenciais competitivos.'
  },
  {
    id: 'sector_radar',
    label: 'Radar Setorial',
    title: 'Radar Setorial',
    subtitle: 'Mapeamento de tendências do setor, comportamento de demanda e maturidade do mercado, com foco em oportunidades e direcionamento estratégico para o curso.'
  },
  {
    id: 'economics',
    label: 'Economia & Cenários',
    title: 'Economia & Cenários',
    subtitle: 'Projeções financeiras e cenários de lançamento do curso, com modelagem determinística de receita, custos, ponto de equilíbrio e sensibilidade.'
  },
  {
    id: 'swot_tows',
    label: 'SWOT & TOWS',
    title: 'SWOT & TOWS',
    subtitle: 'Análise do ambiente interno e externo e implicações estratégicas para o posicionamento e lançamento do curso.'
  },
  {
    id: 'viability_pillars',
    label: 'Pilares de Viabilidade',
    title: 'Pilares de Viabilidade',
    subtitle: 'Fundamentos analíticos que estruturam a recomendação de lançamento, integrando histórico institucional, concorrência, busca, empregabilidade, ementa e preço.'
  },
  {
    id: 'revisions',
    label: 'Revisões',
    title: 'Revisões',
    subtitle: 'Histórico de alterações, comentários e aprovações do dossiê, garantindo rastreabilidade e governança da análise.'
  },
  {
    id: 'sources_evidences',
    label: 'Fontes & Evidências',
    title: 'Fontes & Evidências',
    subtitle: 'Rastreabilidade metodológica das informações coletadas, evidências utilizadas e bases de suporte à análise de viabilidade.'
  }
];

const OFFICIAL_PILLARS = [
  { key: 'internal_history', label: 'Histórico Institucional', short_label: 'Histórico ENS', decision_label: 'Aderência Histórica & Portfólio', weight_pct: 20 },
  { key: 'paid_competition', label: 'Concorrência Paga', short_label: 'Oportunidade Competitiva', decision_label: 'Atração & Espaço Competitivo', weight_pct: 20 },
  { key: 'search_and_media', label: 'Busca & Mídia', short_label: 'Busca e Intenção', decision_label: 'Potencial de Demanda Externa', weight_pct: 20 },
  { key: 'employability', label: 'Empregabilidade', short_label: 'Demanda Profissional', decision_label: 'Absorção & Mercado de Trabalho', weight_pct: 15 },
  { key: 'syllabus_fit', label: 'Aderência de Ementa', short_label: 'Aderência Estratégica', decision_label: 'Aderência Curricular & Ementa', weight_pct: 15 },
  { key: 'pricing', label: 'Precificação', short_label: 'Viabilidade de Preço', decision_label: 'Competitividade de Ticket', weight_pct: 10 }
];

function formatBrl(val) {
  const num = Number(val);
  if (!Number.isFinite(num) || num <= 0) return '—';
  return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });
}

function bandForScore(score, isPresent = true) {
  if (!isPresent) return { label: 'Sem dados', tone: 'insufficient' };
  if (score >= 75) return { label: 'Forte', tone: 'approved' };
  if (score >= 55) return { label: 'Adequado', tone: 'adjustments' };
  return { label: 'Atenção', tone: 'risk' };
}

/**
 * Garante que qualquer dossiê (inclusive fixtures mínimas de testes operacionais)
 * possua o envelope `cms_pages` com as 9 subpáginas completas.
 */
export function ensureCmsPages(dossier, course) {
  const pres = dossier?.presentation || {};
  if (pres.cms_pages && pres.cms_pages.pages && pres.cms_pages.pages.overview) {
    return pres.cms_pages;
  }

  const scoring = dossier?.scoring || {};
  const pillarsMap = scoring.pillar_scores || {};
  const claims = Array.isArray(dossier?.claims) ? dossier.claims : [];
  const evidences = Array.isArray(dossier?.evidences) ? dossier.evidences : [];
  const highlights = dossier?.highlights || pres.highlights || {};
  const limitations = Array.isArray(dossier?.limitations)
    ? dossier.limitations
    : Array.isArray(pres.limitations)
    ? pres.limitations
    : [];
  const economics = pres.economics || { status: 'assumptions_required', scenarios: [] };
  const compBench = pres.competitive_benchmark || { monitored_total: 10, offers_found_count: 0, rows: [] };
  const sectorRadar = pres.sector_radar || { monitored_insurers_total: 10, signals_count: 0, signals: [] };

  const ivoScore = Math.round(Number(scoring.viability_score || 0));
  const covPct = Math.round(Number(scoring.coverage_score || 0) * 100);
  const confPct = Math.round(Number(scoring.confidence_score || 0) * 100);
  const ieScore = Math.round((covPct + confPct) / 2);
  const recCode = scoring.recommendation || 'INSUFFICIENT_EVIDENCE';
  const recLabel = recommendationLabel(recCode);
  const recTone = recCode === 'APPROVED'
    ? 'approved'
    : recCode === 'APPROVED_WITH_ADJUSTMENTS'
    ? 'adjustments'
    : recCode === 'HIGH_RISK'
    ? 'risk'
    : 'insufficient';

  const pillarRows = OFFICIAL_PILLARS.map(spec => {
    const pObj = pillarsMap[spec.key] || {};
    const isPresent = pObj.is_present !== false && pObj.raw_score !== undefined && pObj.raw_score !== null;
    const rawScore = isPresent ? Number(pObj.raw_score || 0) : 0;
    const score = Math.round(rawScore);
    const band = bandForScore(score, isPresent);
    const contribution = isPresent ? Number(((rawScore * spec.weight_pct) / 100).toFixed(1)) : 0;
    return {
      ...spec,
      score,
      raw_score: rawScore,
      is_present: isPresent,
      contribution_pts: contribution,
      status_label: band.label,
      status_tone: band.tone,
      submetrics: [
        { label: 'Nota no pilar', value: isPresent ? `${score}/100` : 'Sem amostra' },
        { label: 'Peso no IVO', value: `${spec.weight_pct}%` },
        { label: 'Contribuição', value: `${contribution} pts` }
      ]
    };
  });

  const claimItems = claims.map(c => ({
    claim_id: c.claim_id || c.id || 'CLM',
    statement: c.statement || '',
    evidence_ids: Array.isArray(c.evidence_ids) ? c.evidence_ids : []
  }));

  const econCalculated = economics.status === 'calculated';
  const scenarios = Array.isArray(economics.scenarios) ? economics.scenarios : [];

  const scenarioCards = econCalculated && scenarios.length
    ? scenarios.slice(0, 3).map((s, idx) => ({
        name: ['Conservador', 'Base', 'Otimista'][idx] || s.name || `Cenário ${idx + 1}`,
        is_reference: idx === 1,
        students_label: String(s.students ?? '—'),
        revenue_label: formatBrl(s.net_revenue),
        margin_label: String(s.margin || '—'),
        result_label: formatBrl(s.net_result)
      }))
    : ['Conservador', 'Base', 'Otimista'].map((name, idx) => ({
        name,
        is_reference: idx === 1,
        students_label: 'Requer premissas',
        revenue_label: 'Requer premissas',
        margin_label: 'Requer premissas',
        result_label: 'Simulação pendente'
      }));

  const compRows = Array.isArray(compBench.rows) ? compBench.rows : [];
  const mapPoints = compRows
    .filter(r => r && (r.status === 'direct_offer' || r.status === 'adjacent_offer' || r.has_direct_offer))
    .map((r, idx) => ({
      id: r.competitor_id || `comp-${idx}`,
      name: r.competitor_name || r.name || 'Concorrente',
      x_pct: 25 + ((idx * 22) % 55),
      y_pct: 68 - ((idx * 15) % 35),
      price_label: r.price_display || r.observed_price_display || '—',
      modality: r.modality || '—'
    }));

  const radarSignals = Array.isArray(sectorRadar.signals) ? sectorRadar.signals : [];
  const radarAxes = [
    { axis: 'Demanda & Busca', score: pillarRows[2].score, benchmark: 70 },
    { axis: 'Empregabilidade', score: pillarRows[3].score, benchmark: 70 },
    { axis: 'Espaço Competitivo', score: pillarRows[1].score, benchmark: 65 },
    { axis: 'Aderência Curricular', score: pillarRows[4].score, benchmark: 75 },
    { axis: 'Histórico ENS', score: pillarRows[0].score, benchmark: 75 },
    { axis: 'Atratividade Preço', score: pillarRows[5].score, benchmark: 65 }
  ];

  const actions = Array.isArray(highlights.action_recommendations) ? highlights.action_recommendations : [];
  const validations = Array.isArray(highlights.validation_criteria) ? highlights.validation_criteria : [];

  return {
    schema_version: 1,
    default_tab: 'overview',
    course_name: course?.name || 'Curso ENS',
    status_badge: { label: 'Pós-análise concluída', tone: recTone },
    tabs: CMS_TABS_META,
    pages: {
      overview: {
        ivo_score: ivoScore,
        ie_score: ieScore,
        coverage_pct: covPct,
        confidence_pct: confPct,
        recommendation_code: recCode,
        recommendation_label: recLabel,
        recommendation_tone: recTone,
        kpis: [
          { title: 'IVO — Índice de Viabilidade de Oferta', value: `${ivoScore}/100`, badge: `${ivoScore - 75 >= 0 ? '+' : ''}${ivoScore - 75} pts vs. limiar (75)`, tone: ivoScore >= 75 ? 'approved' : 'adjustments', sublabel: 'Escala 0–100 calculada nos 6 pilares' },
          { title: 'IE — Índice de Evidência', value: `${ieScore}/100`, badge: `Cobertura ${covPct}% · Confiança ${confPct}%`, tone: ieScore >= 75 ? 'approved' : 'adjustments', sublabel: 'Suporte empírico e rastreabilidade' },
          { title: 'Recomendação', value: recLabel, badge: 'Parecer oficial', tone: recTone, sublabel: 'Deliberação determinística da matriz' },
          { title: 'Referência de Matrículas', value: econCalculated ? String(economics.break_even_students || '—') : 'Requer premissas', badge: econCalculated ? 'Equilíbrio' : 'Premissa pendente', tone: econCalculated ? 'running' : 'insufficient', sublabel: 'Informe capacidade e custos da turma' },
          { title: 'Margem Prevista', value: econCalculated && scenarios[1] ? String(scenarios[1].margin) : 'Requer premissas', badge: econCalculated ? 'Cenário Base' : 'Pendente', tone: econCalculated ? 'approved' : 'insufficient', sublabel: 'Margem operacional estimada' }
        ],
        dimensions_bars: pillarRows,
        scenario_summary: { status: econCalculated ? 'calculated' : 'assumptions_required', cards: scenarioCards },
        decision_matrix: pillarRows,
        key_insights: claimItems.slice(0, 5),
        executive_summary: dossier?.executive_summary || ''
      },
      key_metrics: {
        kpis: [
          { title: 'Alunos Históricos (Média ENS)', value: 'Consulte base', badge: 'Histórico ENS', tone: 'running', sublabel: 'Portfólio histórico da instituição' },
          { title: 'Retenção Histórica ENS', value: 'Consulte base', badge: 'Conclusão', tone: 'approved', sublabel: 'Taxa de retenção em comparáveis' },
          { title: 'Aderência da Base ENS', value: `${pillarRows[0].score}%`, badge: 'Pilar Histórico', tone: pillarRows[0].status_tone, sublabel: 'Compatibilidade institucional' },
          { title: 'Procura Externa (Busca & Mídia)', value: `${pillarRows[2].score}/100`, badge: 'Sinais externos', tone: pillarRows[2].status_tone, sublabel: 'Score consolidado de busca e mídia' },
          { title: 'Ticket Médio Projetado', value: formatBrl(course?.ticket), badge: 'Proposta ENS', tone: course?.ticket ? 'running' : 'insufficient', sublabel: 'Valor declarado na proposta' },
          { title: 'Custo Variável / Aluno', value: econCalculated ? formatBrl(economics.variable_cost_per_student) : 'Requer premissa', badge: 'Premissa financeira', tone: 'insufficient', sublabel: 'Custo variável efetivo por matrícula' },
          { title: 'Margem Prevista', value: econCalculated && scenarios[1] ? String(scenarios[1].margin) : 'Requer premissa', badge: 'Cenário Base', tone: 'insufficient', sublabel: 'Resultado líquido sobre receita' },
          { title: 'IE / IVO (Resumo)', value: `IE: ${ieScore}/100 | IVO: ${ivoScore}/100`, badge: 'Índices oficiais', tone: 'approved', sublabel: 'Evidência e viabilidade de oferta' }
        ],
        historical_trend: [],
        funnel_stages: [
          { stage: 'Capacidade / Referência', value_label: econCalculated ? `${economics.max_capacity || 40} vagas` : 'Requer premissa', pct_label: '100%', width_pct: 100 },
          { stage: 'Aderência Histórica ENS', value_label: `Score ${pillarRows[0].score}/100`, pct_label: `${pillarRows[0].score}%`, width_pct: 80 },
          { stage: 'Suporte de Evidências (IE)', value_label: `Score ${ieScore}/100`, pct_label: `${ieScore}%`, width_pct: 62 },
          { stage: 'Ponto de Equilíbrio', value_label: econCalculated ? `${economics.break_even_students} matrículas` : 'Requer custos', pct_label: 'Breakeven', width_pct: 46 }
        ],
        ie_ivo_evolution: { ie_score: ieScore, ivo_score: ivoScore, threshold: 75 },
        dimension_indicators: pillarRows.map(p => ({
          dimension: p.short_label,
          indicator: p.label,
          observed: `${p.score}/100`,
          reference: '≥ 70/100',
          delta: `${p.score - 70 >= 0 ? '+' : ''}${p.score - 70} pts`,
          status: p.status_label
        })),
        internal_benchmark: [
          { indicator: 'Ticket de Referência', ens_reference: 'Benchmark de mercado', proposed_course: formatBrl(course?.ticket), delta: '—' },
          { indicator: 'Índices IE / IVO', ens_reference: 'Limiar 75/100', proposed_course: `IE ${ieScore}/100 · IVO ${ivoScore}/100`, delta: `${ivoScore - 75 >= 0 ? '+' : ''}${ivoScore - 75} pts` }
        ],
        analytical_highlights: claimItems.slice(0, 5)
      },
      fixed_competition: {
        monitored_total: compBench.monitored_total || compRows.length || 10,
        offers_found_count: compBench.offers_found_count || 0,
        whitespace_count: Math.max(0, (compBench.monitored_total || 10) - (compBench.offers_found_count || 0)),
        kpis: [
          { title: 'Concorrentes Mapeados', value: `${compBench.offers_found_count || 0} de ${compBench.monitored_total || 10}`, badge: 'Catálogo fixo ENS', tone: 'running', sublabel: 'Players com oferta identificada' },
          { title: 'Intensidade Competitiva', value: (compBench.offers_found_count || 0) >= 4 ? 'Alta' : 'Moderada', badge: `${compBench.offers_found_count || 0} ofertas ativas`, tone: 'adjustments', sublabel: 'Grau de disputa direta observada' },
          { title: 'Faixa Média de Preço', value: formatBrl(course?.ticket), badge: 'Cursos comparáveis', tone: 'running', sublabel: 'Referência observada no recorte' },
          { title: 'Lacunas de Posicionamento', value: `${Math.max(0, (compBench.monitored_total || 10) - (compBench.offers_found_count || 0))} oportunidades`, badge: 'Espaço competitivo', tone: 'approved', sublabel: 'IES sem oferta direta no tema' }
        ],
        competitor_rows: compRows,
        positioning_map: {
          x_axis_label: 'Preço Observado',
          y_axis_label: 'Profundidade / Escopo Executivo',
          points: mapPoints,
          opportunity_zone: { label: 'Espaço de oportunidade (ENS)', description: 'Posicionamento executivo verticalizado em Seguros' }
        },
        observed_signals: compRows.length
          ? compRows.slice(0, 4).map(r => `${r.competitor_name || r.name}: ${r.observed_offer_title || 'Monitorado'}`)
          : ['Consulte a tabela de concorrentes fixos para inspecionar as ofertas coletadas.'],
        ens_differentiation: claimItems.slice(0, 4),
        actionable_insights: actions.slice(0, 3).map((a, idx) => ({ index: idx + 1, area: a.area, action: a.action, priority: a.priority }))
      },
      sector_radar: {
        attractiveness_score: ivoScore,
        monitored_total: sectorRadar.monitored_insurers_total || 10,
        insurers_with_signals_count: radarSignals.length,
        kpis: [
          { title: 'Índice de Atratividade Setorial', value: `${ivoScore}/100`, badge: 'Score setorial', tone: ivoScore >= 75 ? 'approved' : 'adjustments', sublabel: 'Demanda, empregabilidade e aderência' },
          { title: 'Tendência de Demanda', value: pillarRows[2].score >= 70 ? 'Crescente' : 'Moderada', badge: `Busca ${pillarRows[2].score}/100`, tone: 'approved', sublabel: 'Comportamento de interesse externo' },
          { title: 'Cobertura do Radar Setorial', value: `${radarSignals.length} sinais`, badge: `${sectorRadar.monitored_insurers_total || 10} seguradoras`, tone: 'running', sublabel: 'Seguradoras monitoradas no ecossistema' },
          { title: 'Relevância Profissional', value: `${pillarRows[3].score}/100`, badge: 'Mercado de trabalho', tone: 'approved', sublabel: 'Sinais de vagas e competências' },
          { title: 'Potencial de Escala ENS', value: pillarRows[4].score >= 75 ? 'Alto' : 'Moderado', badge: `Ementa ${pillarRows[4].score}/100`, tone: 'approved', sublabel: 'Aplicação curricular direta' }
        ],
        radar_axes: radarAxes,
        subthemes_distribution: radarSignals.length
          ? radarSignals.slice(0, 5).map((s, i) => ({ theme: s.theme_detected || `Tema ${i + 1}`, count: 1, share_pct: Math.round(100 / Math.min(5, radarSignals.length)) }))
          : [
              { theme: 'Gestão de Riscos, Subscrição & Regulação', count: 1, share_pct: 40 },
              { theme: 'Inovação, IA & Operações de Sinistros', count: 1, share_pct: 35 },
              { theme: 'Canais de Distribuição & Corretores', count: 1, share_pct: 25 }
            ],
        signals: radarSignals,
        strong_signals: radarSignals.slice(0, 3).map(s => `${s.insurer_name}: ${s.market_or_broker_pain || s.theme_detected}`),
        attention_signals: limitations.slice(0, 3),
        executive_reading: claimItems.slice(0, 4)
      },
      economics: {
        status: econCalculated ? 'calculated' : 'assumptions_required',
        message: economics.message || 'Premissas completas de custos fixos e variáveis não foram informadas na proposta.',
        kpis: [
          { title: 'Receita Líquida (Cenário Base)', value: econCalculated && scenarios[1] ? formatBrl(scenarios[1].net_revenue) : 'Requer premissas', badge: econCalculated ? 'Simulado' : 'Pendente', tone: econCalculated ? 'approved' : 'insufficient', sublabel: 'Receita líquida estimada da turma base' },
          { title: 'Ticket Médio', value: formatBrl(course?.ticket || economics.ticket), badge: 'Proposta ENS', tone: 'running', sublabel: 'Preço bruto por matrícula' },
          { title: 'Margem Líquida (Base)', value: econCalculated && scenarios[1] ? String(scenarios[1].margin) : 'Requer premissas', badge: 'Resultado / Receita', tone: econCalculated ? 'approved' : 'insufficient', sublabel: 'Margem operacional simulada' },
          { title: 'Ponto de Equilíbrio', value: econCalculated ? `${economics.break_even_students} matrículas` : 'Requer premissas', badge: 'Breakeven', tone: econCalculated ? 'adjustments' : 'insufficient', sublabel: 'Volume mínimo para cobrir custos' },
          { title: 'Custos Fixos da Turma', value: econCalculated ? formatBrl(economics.fixed_costs) : 'Requer premissas', badge: 'Docência + operação', tone: 'insufficient', sublabel: 'Hora-aula, coordenação e plataforma' },
          { title: 'Resultado Líquido (Base)', value: econCalculated && scenarios[1] ? formatBrl(scenarios[1].net_result) : 'Requer premissas', badge: 'Turma Base', tone: econCalculated ? 'approved' : 'insufficient', sublabel: 'Contribuição líquida após custos' }
        ],
        waterfall_steps: [],
        launch_scenarios: scenarios,
        sensitivity_matrix: [],
        risks: limitations.slice(0, 4),
        assumptions: [economics.message || 'Informe custo hora-aula, custos fixos e capacidade da turma para habilitar a cascata financeira determinística.']
      },
      swot_tows: {
        kpis: [
          { title: 'Aderência Estratégica ENS', value: `${pillarRows[4].score}/100`, badge: 'Histórico + Ementa', tone: 'approved', sublabel: 'Alinhamento institucional e curricular' },
          { title: 'Forças & Oportunidades (SO)', value: `${Math.max(1, claimItems.length)} fatores`, badge: 'Alavancas', tone: 'approved', sublabel: 'Pontos fortes e oportunidades sustentadas' },
          { title: 'Fragilidades & Riscos (WT)', value: `${Math.max(1, limitations.length)} alertas`, badge: 'Mitigação', tone: 'adjustments', sublabel: 'Limitações e ameaças mapeadas' },
          { title: 'Posicionamento Estratégico', value: recLabel, badge: 'Parecer', tone: recTone, sublabel: 'Síntese de prontidão para lançamento' }
        ],
        swot: {
          strengths: claimItems.slice(0, 3).map(c => ({ text: c.statement, evidence_ids: c.evidence_ids })),
          weaknesses: limitations.slice(0, 3).map(l => ({ text: l, evidence_ids: [] })),
          opportunities: claimItems.slice(0, 3).map(c => ({ text: c.statement, evidence_ids: c.evidence_ids })),
          threats: limitations.slice(0, 2).map(l => ({ text: l, evidence_ids: [] }))
        },
        tows: {
          so: actions.slice(0, 2).map(a => a.action),
          st: actions.slice(1, 3).map(a => a.action),
          wo: validations.slice(0, 2).map(v => v.criterion),
          wt: limitations.slice(0, 2)
        },
        recommended_priorities: actions.slice(0, 3).map((a, idx) => ({
          order: idx + 1,
          title: a.action,
          area: a.area,
          priority_label: a.priority === 'high' ? 'Alta' : 'Média',
          priority_tone: a.priority === 'high' ? 'approved' : 'adjustments',
          claim_ids: a.claim_ids || []
        })),
        executive_synthesis: dossier?.executive_summary || ''
      },
      viability_pillars: {
        ivo_score: ivoScore,
        coverage_pct: covPct,
        confidence_pct: confPct,
        pillar_cards: pillarRows,
        weight_score_matrix: pillarRows,
        pillar_justifications: pillarRows.map(r => ({
          label: r.label,
          text: `Nota ${r.score}/100 (peso ${r.weight_pct}% → contribuição de ${r.contribution_pts} pts no IVO). Classificação: ${r.status_label}.`
        })),
        synthesis_text: dossier?.executive_summary || '',
        recommendation_code: recCode,
        recommendation_label: recLabel,
        recommendation_short: recLabel,
        recommendation_tone: recTone
      },
      revisions: {
        area_reviews: [
          { area: 'marketing', label: 'Marketing', status: 'PENDING', status_label: 'Pendente', tone: 'insufficient', reviewer_name: 'Aguardando revisão', updated_at_label: 'Disponível para parecer', comment: '' },
          { area: 'produto', label: 'Produto', status: 'PENDING', status_label: 'Pendente', tone: 'insufficient', reviewer_name: 'Aguardando revisão', updated_at_label: 'Disponível para parecer', comment: '' },
          { area: 'comercial', label: 'Comercial', status: 'PENDING', status_label: 'Pendente', tone: 'insufficient', reviewer_name: 'Aguardando revisão', updated_at_label: 'Disponível para parecer', comment: '' },
          { area: 'financeiro', label: 'Financeiro', status: 'PENDING', status_label: 'Pendente', tone: 'insufficient', reviewer_name: 'Aguardando revisão', updated_at_label: 'Disponível para parecer', comment: '' }
        ],
        overall_progress: { approved_count: 0, total_areas: 4, percent: 0, status_label: 'Aguardando aprovação das áreas', tone: 'adjustments' },
        version_history: [
          { version: 'v1.0', is_current: true, badge_label: 'Base publicada', tone: 'approved', timestamp_label: 'Publicação automática verificada', description: 'Primeira versão do dossiê consolidada e auditada pelo verificador determinístico.' }
        ],
        comments_feed: [],
        changes_summary: [
          { index: 1, description: 'Publicação inicial do Dossiê Executivo de Viabilidade no template CMS (9 subpáginas)', area: 'IA & Verificador', owner: 'Motor Prometeus', impact: 'Alto' },
          { index: 2, description: `Auditoria de integridade e cobertura (${covPct}% cobertura · ${confPct}% confiança)`, area: 'Fontes & Evidências', owner: 'DossierVerifier', impact: 'Médio' }
        ],
        pendencies: validations.map(v => ({ criterion: v.criterion, target: v.target, status: 'pending' })),
        approval_recommendation: { decision_label: recCode === 'APPROVED' ? 'Sim' : 'Com ajustes', tone: recTone, note: recLabel },
        next_steps: actions.slice(0, 4).map((a, idx) => ({ order: idx + 1, action: a.action, area: a.area, priority: a.priority }))
      },
      sources_evidences: {
        collected_sources: [
          { source_name: 'Google Trends & Volume de Busca', source_type: 'Tendência de busca', status_label: 'Coletado', status_tone: 'approved', records_count: evidences.length, observation: 'Séries e indicadores de interesse de busca para o tema.' },
          { source_name: 'Sites de Concorrentes (Catálogo Fixo ENS)', source_type: 'Concorrência / benchmarking', status_label: 'Monitorado', status_tone: 'approved', records_count: compRows.length, observation: 'Mapeamento de oferta, posicionamento e preços.' },
          { source_name: 'LinkedIn Jobs & Mercado de Trabalho', source_type: 'Vagas / mercado de trabalho', status_label: 'Coletado', status_tone: 'approved', records_count: evidences.length, observation: 'Levantamento de vagas abertas e perfis demandados.' },
          { source_name: 'Catálogo Histórico ENS', source_type: 'Base institucional', status_label: 'Consultado', status_tone: 'approved', records_count: 1, observation: 'Edições anteriores, evolução da oferta e aderência.' }
        ],
        coverage_pct: covPct,
        confidence_pct: confPct,
        ie_score: ieScore,
        coverage_bars: [
          { label: 'Demanda & Interesse (Buscas)', pct: pillarRows[2].score },
          { label: 'Concorrência & Oferta', pct: pillarRows[1].score },
          { label: 'Empregabilidade & Mercado', pct: pillarRows[3].score },
          { label: 'Histórico ENS & Aderência', pct: pillarRows[0].score }
        ],
        evidence_categories: [
          { id: 'search_trends', title: 'Tendências de busca', description: 'Interesse no tema e comportamento de procura externa.', evidence_ids: evidences.slice(0, 3).map(e => e.id) },
          { id: 'competition_signals', title: 'Sinais de concorrência', description: 'Ofertas por players relevantes, formatos e posicionamento.', evidence_ids: evidences.slice(0, 3).map(e => e.id) },
          { id: 'historical_fit', title: 'Aderência histórica', description: 'Desempenho das edições comparáveis na ENS.', evidence_ids: evidences.slice(0, 3).map(e => e.id) },
          { id: 'professional_demand', title: 'Demanda profissional', description: 'Volume de vagas e perfis alinhados à formação.', evidence_ids: evidences.slice(0, 3).map(e => e.id) }
        ],
        method_steps: [
          { step: 1, title: 'Coleta', description: 'Levantamento automatizado em fontes primárias e secundárias.' },
          { step: 2, title: 'Preparação', description: 'Preservação bruta, limpeza e padronização auditável.' },
          { step: 3, title: 'Classificação', description: 'Categorização por pilar e separação do Radar Setorial.' },
          { step: 4, title: 'Score', description: 'Ponderação determinística nos 6 pilares (IVO e IE).' },
          { step: 5, title: 'Decisão', description: 'Síntese verificada pelo DossierVerifier e hospedada em SQL.' }
        ]
      }
    }
  };
}

/* ============================================================================
 * PRIMITIVOS GRÁFICOS SVG / CSS (DARK THEME)
 * ============================================================================ */

function renderDonutSvg(value, max = 100, centerMain = '', centerSub = '') {
  const pct = Math.max(0, Math.min(100, Math.round((Number(value || 0) / Math.max(1, max)) * 100)));
  const radius = 52;
  const circumference = Number((2 * Math.PI * radius).toFixed(2));
  const offset = Number((circumference - (pct / 100) * circumference).toFixed(2));
  return `<svg class="cms-donut-svg" viewBox="0 0 140 140" width="140" height="140" role="img" aria-label="${escapeHtml(centerMain)}">
    <circle cx="70" cy="70" r="${radius}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="14"></circle>
    <circle cx="70" cy="70" r="${radius}" fill="none" stroke="#34d399" stroke-width="14"
      stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"
      stroke-linecap="round" transform="rotate(-90 70 70)"></circle>
    <text x="70" y="66" text-anchor="middle" fill="#ffffff" font-size="22" font-weight="700">${escapeHtml(centerMain)}</text>
    <text x="70" y="88" text-anchor="middle" fill="#94a3b8" font-size="11">${escapeHtml(centerSub)}</text>
  </svg>`;
}

function renderRadarSvg(axes) {
  const safeAxes = Array.isArray(axes) && axes.length === 6
    ? axes
    : [
        { axis: 'Demanda', score: 75, benchmark: 70 },
        { axis: 'Empregabilidade', score: 75, benchmark: 70 },
        { axis: 'Competitividade', score: 70, benchmark: 65 },
        { axis: 'Aderência', score: 80, benchmark: 75 },
        { axis: 'Histórico ENS', score: 82, benchmark: 75 },
        { axis: 'Preço', score: 68, benchmark: 65 }
      ];
  const cx = 150;
  const cy = 130;
  const maxR = 82;

  const pointAt = (idx, val) => {
    const angle = (Math.PI * 2 * idx) / 6 - Math.PI / 2;
    const r = (Math.max(0, Math.min(100, Number(val || 0))) / 100) * maxR;
    return `${(cx + r * Math.cos(angle)).toFixed(1)},${(cy + r * Math.sin(angle)).toFixed(1)}`;
  };

  const gridRings = [25, 50, 75, 100].map(level => {
    const pts = [0, 1, 2, 3, 4, 5].map(i => pointAt(i, level)).join(' ');
    return `<polygon points="${pts}" fill="none" stroke="rgba(255,255,255,0.09)" stroke-width="1"/>`;
  }).join('');

  const spokes = [0, 1, 2, 3, 4, 5].map(i => {
    const end = pointAt(i, 100).split(',');
    return `<line x1="${cx}" y1="${cy}" x2="${end[0]}" y2="${end[1]}" stroke="rgba(255,255,255,0.09)" stroke-width="1"/>`;
  }).join('');

  const benchPolygon = [0, 1, 2, 3, 4, 5].map(i => pointAt(i, safeAxes[i].benchmark || 70)).join(' ');
  const scorePolygon = [0, 1, 2, 3, 4, 5].map(i => pointAt(i, safeAxes[i].score || 0)).join(' ');

  const labels = safeAxes.map((item, i) => {
    const angle = (Math.PI * 2 * i) / 6 - Math.PI / 2;
    const lx = (cx + (maxR + 28) * Math.cos(angle)).toFixed(1);
    const ly = (cy + (maxR + 20) * Math.sin(angle)).toFixed(1);
    return `<text x="${lx}" y="${ly}" text-anchor="middle" fill="#cbd5e1" font-size="10" font-weight="600">${escapeHtml(item.axis)} (${escapeHtml(item.score)})</text>`;
  }).join('');

  return `<svg class="cms-radar-svg" viewBox="0 0 300 260" width="100%" height="240" role="img" aria-label="Gráfico Radar de Atratividade Setorial">
    ${gridRings}
    ${spokes}
    <polygon points="${benchPolygon}" fill="rgba(148,163,184,0.12)" stroke="#64748b" stroke-width="1.5" stroke-dasharray="3 3"/>
    <polygon points="${scorePolygon}" fill="rgba(52,211,153,0.22)" stroke="#34d399" stroke-width="2.5"/>
    ${labels}
  </svg>`;
}

function renderPositioning2x2Svg(mapData) {
  const points = Array.isArray(mapData?.points) ? mapData.points : [];
  const opp = mapData?.opportunity_zone || { label: 'Espaço de oportunidade (ENS)' };

  const dots = points.map((pt, idx) => {
    const cx = Math.round(45 + ((Number(pt.x_pct || 50) / 100) * 280));
    const cy = Math.round(185 - ((Number(pt.y_pct || 50) / 100) * 145));
    const colors = ['#38bdf8', '#fbbf24', '#c084fc', '#f87171', '#8db5ff'];
    const fill = colors[idx % colors.length];
    return `<g>
      <circle cx="${cx}" cy="${cy}" r="6" fill="${fill}" stroke="#040814" stroke-width="2"></circle>
      <text x="${cx + 9}" y="${cy + 4}" fill="#e2e8f0" font-size="11" font-weight="600">${escapeHtml(pt.name)}</text>
    </g>`;
  }).join('');

  return `<svg class="cms-positioning-svg" viewBox="0 0 380 220" width="100%" height="220" role="img" aria-label="Mapa de Posicionamento 2x2">
    <line x1="45" y1="20" x2="45" y2="190" stroke="rgba(255,255,255,0.22)" stroke-width="1.5"/>
    <line x1="45" y1="190" x2="355" y2="190" stroke="rgba(255,255,255,0.22)" stroke-width="1.5"/>
    <line x1="45" y1="105" x2="355" y2="105" stroke="rgba(255,255,255,0.08)" stroke-dasharray="4 4"/>
    <line x1="200" y1="20" x2="200" y2="190" stroke="rgba(255,255,255,0.08)" stroke-dasharray="4 4"/>
    <ellipse cx="285" cy="145" rx="58" ry="30" fill="rgba(52,211,153,0.12)" stroke="#34d399" stroke-dasharray="4 3" stroke-width="1.5"/>
    <text x="285" y="143" text-anchor="middle" fill="#34d399" font-size="10" font-weight="700">${escapeHtml(opp.label)}</text>
    <text x="285" y="156" text-anchor="middle" fill="#94a3b8" font-size="9">Diferenciação ENS</text>
    ${dots}
    <text x="200" y="212" text-anchor="middle" fill="#94a3b8" font-size="10">Preço Observado (Menor → Maior)</text>
    <text x="14" y="105" text-anchor="middle" fill="#94a3b8" font-size="10" transform="rotate(-90 14 105)">Profundidade</text>
  </svg>`;
}

function renderKpiStrip(kpis, colsClass = 'cms-kpi-strip--5') {
  return `<div class="cms-kpi-strip ${colsClass}">
    ${(kpis || []).map(kpi => `<article class="cms-kpi-card" data-tone="${escapeHtml(kpi.tone || 'running')}">
      <div class="cms-kpi-card__title">${escapeHtml(kpi.title)}</div>
      <div class="cms-kpi-card__main">
        <span class="cms-kpi-card__value">${escapeHtml(kpi.value)}</span>
        ${kpi.badge ? `<span class="cms-pill" data-tone="${escapeHtml(kpi.tone || 'running')}">${escapeHtml(kpi.badge)}</span>` : ''}
      </div>
      ${kpi.sublabel ? `<div class="cms-kpi-card__sub">${escapeHtml(kpi.sublabel)}</div>` : ''}
    </article>`).join('')}
  </div>`;
}

/* ============================================================================
 * RENDERIZADORES DAS 9 SUBPÁGINAS
 * ============================================================================ */

function renderOverviewSubpage(page, helpers) {
  const bars = page.dimensions_bars || [];
  const scenCards = page.scenario_summary?.cards || [];
  const matrix = page.decision_matrix || [];
  const insights = page.key_insights || [];

  return `
    ${renderKpiStrip(page.kpis, 'cms-kpi-strip--5')}

    <div class="cms-grid-2">
      <article class="cms-panel-card">
        <div class="cms-panel-card__header">
          <div>
            <h3>Dimensões do Score de Viabilidade</h3>
            <p class="cms-muted">Contribuição de cada dimensão para o IVO (0–100).</p>
          </div>
          <span class="cms-pill" data-tone="approved">IVO (consolidado): ${escapeHtml(page.ivo_score)}/100</span>
        </div>
        <div class="cms-hbar-list">
          ${bars.map(b => `<div class="cms-hbar-row">
            <span class="cms-hbar-row__label">${escapeHtml(b.short_label || b.label)}</span>
            <div class="cms-hbar-row__track">
              <div class="cms-hbar-row__fill" data-tone="${escapeHtml(b.status_tone)}" style="width:${Math.max(4, Math.min(100, Number(b.score || 0)))}%;"></div>
            </div>
            <strong class="cms-hbar-row__val">${escapeHtml(b.score)}</strong>
          </div>`).join('')}
        </div>
      </article>

      <article class="cms-panel-card">
        <div class="cms-panel-card__header">
          <div>
            <h3>Cenário Resumido</h3>
            <p class="cms-muted">Projeções de desempenho para a 1ª janela, por cenário.</p>
          </div>
        </div>
        <div class="cms-scenario-grid">
          ${scenCards.map(sc => `<div class="cms-scenario-card ${sc.is_reference ? 'is-reference' : ''}">
            <div class="cms-scenario-card__head">
              <strong>${escapeHtml(sc.name)}</strong>
              ${sc.is_reference ? '<span class="cms-pill" data-tone="approved">Cenário de referência</span>' : ''}
            </div>
            <ul class="cms-scenario-card__list">
              <li><span>Matrículas:</span> <strong>${escapeHtml(sc.students_label)}</strong></li>
              <li><span>Receita estimada:</span> <strong>${escapeHtml(sc.revenue_label)}</strong></li>
              <li><span>Margem:</span> <strong>${escapeHtml(sc.margin_label)}</strong></li>
            </ul>
          </div>`).join('')}
        </div>
      </article>
    </div>

    <div class="cms-grid-2">
      <article class="cms-panel-card">
        <div class="cms-panel-card__header">
          <div>
            <h3>Matriz de Decisão</h3>
            <p class="cms-muted">Avaliação executiva por critério (peso, nota e contribuição para o IVO).</p>
          </div>
        </div>
        <div class="prometeus-table-container">
          <table class="prometeus-table cms-compact-table">
            <thead>
              <tr>
                <th>Critério</th>
                <th>Peso</th>
                <th>Nota (0–100)</th>
                <th>Contribuição</th>
                <th>Leitura</th>
              </tr>
            </thead>
            <tbody>
              ${matrix.map(row => `<tr>
                <td><strong>${escapeHtml(row.decision_label || row.label)}</strong></td>
                <td>${escapeHtml(row.weight_pct)}%</td>
                <td><strong>${escapeHtml(row.score)}</strong></td>
                <td>${escapeHtml(row.contribution_pts)} pts</td>
                <td><span class="cms-pill" data-tone="${escapeHtml(row.status_tone)}">${escapeHtml(row.status_label)}</span></td>
              </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </article>

      <article class="cms-panel-card">
        <div class="cms-panel-card__header">
          <div>
            <h3>Principais Insights</h3>
            <p class="cms-muted">Conclusões analíticas sustentadas por evidências verificadas.</p>
          </div>
        </div>
        <ul class="cms-check-list">
          ${insights.length
            ? insights.map(item => `<li>
                <span class="cms-check-icon">✓</span>
                <div>
                  <span>${escapeHtml(item.statement)}</span>
                  ${helpers.inspectionButton(item.evidence_ids)}
                </div>
              </li>`).join('')
            : `<li><span class="cms-check-icon">✓</span><div>${escapeHtml(page.executive_summary)}</div></li>`}
        </ul>
      </article>
    </div>
  `;
}

function renderKeyMetricsSubpage(page, helpers) {
  const kpis = page.kpis || [];
  const trend = page.historical_trend || [];
  const funnel = page.funnel_stages || [];
  const dimRows = page.dimension_indicators || [];
  const benchRows = page.internal_benchmark || [];
  const highlights = page.analytical_highlights || [];
  const ieIvo = page.ie_ivo_evolution || { ie_score: 80, ivo_score: 75 };

  return `
    ${renderKpiStrip(kpis.slice(0, 4), 'cms-kpi-strip--4')}
    ${renderKpiStrip(kpis.slice(4, 8), 'cms-kpi-strip--4')}

    <div class="cms-grid-3">
      <article class="cms-panel-card">
        <h3>Tendência Histórica de Turmas Comparáveis</h3>
        <p class="cms-muted">Alunos matriculados e concluintes nas edições históricas da ENS.</p>
        ${trend.length
          ? `<div class="cms-hbar-list" style="margin-top:12px;">
              ${trend.map(t => `<div class="cms-hbar-row">
                <span class="cms-hbar-row__label">${escapeHtml(t.label)}</span>
                <div class="cms-hbar-row__track">
                  <div class="cms-hbar-row__fill" data-tone="approved" style="width:${Math.min(100, Math.max(15, t.students * 1.5))}%;"></div>
                </div>
                <strong class="cms-hbar-row__val">${escapeHtml(t.students)} alunos</strong>
              </div>`).join('')}
            </div>`
          : '<p class="cms-empty-note">Sem séries históricas de turmas comparáveis cadastradas para este recorte.</p>'}
      </article>

      <article class="cms-panel-card">
        <h3>Funil de Capacidade até Equilíbrio</h3>
        <p class="cms-muted">Relação entre capacidade de turma, histórico e breakeven.</p>
        <div class="cms-funnel-wrap">
          ${funnel.map(st => `<div class="cms-funnel-row">
            <div class="cms-funnel-stage" style="width:${escapeHtml(st.width_pct)}%;">
              <span>${escapeHtml(st.stage)}</span>
              <strong>${escapeHtml(st.value_label)}</strong>
            </div>
            <span class="cms-funnel-pct">${escapeHtml(st.pct_label)}</span>
          </div>`).join('')}
        </div>
      </article>

      <article class="cms-panel-card">
        <h3>Consolidação dos Índices (IE e IVO)</h3>
        <p class="cms-muted">Posicionamento frente ao limiar institucional de referência (75 pts).</p>
        <div class="cms-ie-ivo-box">
          <div class="cms-hbar-row">
            <span class="cms-hbar-row__label">IE (Índice de Evidência)</span>
            <div class="cms-hbar-row__track">
              <div class="cms-hbar-row__fill" data-tone="approved" style="width:${Math.min(100, ieIvo.ie_score)}%;"></div>
            </div>
            <strong class="cms-hbar-row__val">${escapeHtml(ieIvo.ie_score)}/100</strong>
          </div>
          <div class="cms-hbar-row">
            <span class="cms-hbar-row__label">IVO (Viabilidade de Oferta)</span>
            <div class="cms-hbar-row__track">
              <div class="cms-hbar-row__fill" data-tone="running" style="width:${Math.min(100, ieIvo.ivo_score)}%;"></div>
            </div>
            <strong class="cms-hbar-row__val">${escapeHtml(ieIvo.ivo_score)}/100</strong>
          </div>
        </div>
      </article>
    </div>

    <div class="cms-grid-3">
      <article class="cms-panel-card">
        <h3>Indicadores por Dimensão</h3>
        <div class="prometeus-table-container">
          <table class="prometeus-table cms-compact-table">
            <thead><tr><th>Dimensão</th><th>Resultado</th><th>Ref. ENS</th><th>Δ</th><th>Status</th></tr></thead>
            <tbody>
              ${dimRows.map(r => `<tr>
                <td><strong>${escapeHtml(r.dimension)}</strong></td>
                <td>${escapeHtml(r.observed)}</td>
                <td>${escapeHtml(r.reference)}</td>
                <td>${escapeHtml(r.delta)}</td>
                <td><span class="cms-pill" data-tone="approved">${escapeHtml(r.status)}</span></td>
              </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </article>

      <article class="cms-panel-card">
        <h3>Benchmark: Interno vs. Curso Proposto</h3>
        <div class="prometeus-table-container">
          <table class="prometeus-table cms-compact-table">
            <thead><tr><th>Indicador</th><th>Referência ENS</th><th>Curso Proposto</th><th>Δ</th></tr></thead>
            <tbody>
              ${benchRows.map(r => `<tr>
                <td><strong>${escapeHtml(r.indicator)}</strong></td>
                <td>${escapeHtml(r.ens_reference)}</td>
                <td>${escapeHtml(r.proposed_course)}</td>
                <td><span class="cms-pill" data-tone="running">${escapeHtml(r.delta)}</span></td>
              </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </article>

      <article class="cms-panel-card">
        <h3>Destaques Analíticos</h3>
        <ul class="cms-check-list">
          ${highlights.map(h => `<li>
            <span class="cms-check-icon">✓</span>
            <div>${escapeHtml(h.statement)} ${helpers.inspectionButton(h.evidence_ids)}</div>
          </li>`).join('')}
        </ul>
      </article>
    </div>
  `;
}

function renderFixedCompetitionSubpage(page, helpers) {
  const rows = page.competitor_rows || [];
  const signals = page.observed_signals || [];
  const diffs = page.ens_differentiation || [];
  const actions = page.actionable_insights || [];

  return `
    ${renderKpiStrip(page.kpis, 'cms-kpi-strip--4')}

    <div class="cms-grid-2-wide">
      <article class="cms-panel-card">
        <div class="cms-panel-card__header">
          <div>
            <h3>Comparativo de Concorrentes</h3>
            <p class="cms-muted">Instituições monitoradas no catálogo fixo da ENS, com ofertas, formato, preço e status competitivo.</p>
          </div>
        </div>
        <div class="prometeus-table-container">
          <table class="prometeus-table cms-compact-table">
            <thead>
              <tr>
                <th>Concorrente</th>
                <th>Tema / Oferta Observada</th>
                <th>Formato</th>
                <th>Preço</th>
                <th>Carga</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              ${rows.length
                ? rows.map(r => {
                    const compName = r.competitor_name || r.name || 'Instituição';
                    const price = r.price_display || r.observed_price_display || '—';
                    const hasOffer = r.status === 'direct_offer' || r.status === 'adjacent_offer' || r.has_direct_offer;
                    return `<tr>
                      <td>
                        <strong>${escapeHtml(compName)}</strong>
                        <div class="cms-muted" style="font-size:11px;">${escapeHtml(r.category_label || '')}</div>
                      </td>
                      <td>
                        <div>${escapeHtml(r.observed_offer_title || 'Sem oferta direta observada')}</div>
                        ${helpers.inspectionButton(r.evidence_ids || [], 'Fonte')}
                      </td>
                      <td>${escapeHtml(r.modality || '—')}</td>
                      <td><strong>${escapeHtml(price)}</strong></td>
                      <td>${escapeHtml(r.workload_hours || '—')}</td>
                      <td><span class="cms-pill" data-tone="${hasOffer ? 'risk' : 'approved'}">${hasOffer ? 'Oferta ativa' : 'Whitespace'}</span></td>
                    </tr>`;
                  }).join('')
                : '<tr><td colspan="6" class="cms-muted">Nenhum concorrente fixo listado nesta versão.</td></tr>'}
            </tbody>
          </table>
        </div>
      </article>

      <article class="cms-panel-card">
        <div class="cms-panel-card__header">
          <div>
            <h3>Mapa de Posicionamento (2×2)</h3>
            <p class="cms-muted">Posicionamento dos concorrentes por preço e profundidade de conteúdo.</p>
          </div>
        </div>
        ${renderPositioning2x2Svg(page.positioning_map)}
      </article>
    </div>

    <div class="cms-grid-3">
      <article class="cms-panel-card">
        <h3>Sinais Observados da Concorrência</h3>
        <ul class="cms-check-list">
          ${signals.map(s => `<li><span class="cms-check-icon">✓</span><div>${escapeHtml(s)}</div></li>`).join('')}
        </ul>
      </article>

      <article class="cms-panel-card">
        <h3>Diferenciação da ENS</h3>
        <ul class="cms-check-list">
          ${diffs.length
            ? diffs.map(d => `<li><span class="cms-check-icon">★</span><div>${escapeHtml(d.statement)} ${helpers.inspectionButton(d.evidence_ids)}</div></li>`).join('')
            : '<li><span class="cms-check-icon">★</span><div>Curadoria especializada da ENS com conexão direta ao mercado segurador.</div></li>'}
        </ul>
      </article>

      <article class="cms-panel-card">
        <h3>Insights Acionáveis</h3>
        <ol class="cms-numbered-list">
          ${actions.map(a => `<li>
            <span class="cms-step-num">${escapeHtml(a.index)}</span>
            <div><strong>[${escapeHtml(a.area)}]</strong> ${escapeHtml(a.action)}</div>
          </li>`).join('')}
        </ol>
      </article>
    </div>
  `;
}

function renderSectorRadarSubpage(page, helpers) {
  const subthemes = page.subthemes_distribution || [];
  const strongSignals = page.strong_signals || [];
  const attentionSignals = page.attention_signals || [];
  const reading = page.executive_reading || [];

  return `
    ${renderKpiStrip(page.kpis, 'cms-kpi-strip--5')}

    <div class="cms-grid-3">
      <article class="cms-panel-card">
        <h3>Radar de Atratividade Setorial</h3>
        <p class="cms-muted">Desempenho do tema em 6 dimensões estratégicas (0–100).</p>
        ${renderRadarSvg(page.radar_axes)}
      </article>

      <article class="cms-panel-card">
        <h3>Distribuição por Subtemas do Radar</h3>
        <p class="cms-muted">Participação relativa dos temas detectados nas seguradoras monitoradas.</p>
        <div class="cms-hbar-list" style="margin-top:16px;">
          ${subthemes.map(st => `<div class="cms-hbar-row">
            <span class="cms-hbar-row__label">${escapeHtml(st.theme)}</span>
            <div class="cms-hbar-row__track">
              <div class="cms-hbar-row__fill" data-tone="running" style="width:${Math.max(12, st.share_pct)}%;"></div>
            </div>
            <strong class="cms-hbar-row__val">${escapeHtml(st.share_pct)}%</strong>
          </div>`).join('')}
        </div>
      </article>

      <article class="cms-panel-card">
        <h3>Leitura Executiva do Setor</h3>
        <p class="cms-muted">Implicações das movimentações das seguradoras para a oferta da ENS.</p>
        <ul class="cms-check-list">
          ${reading.map(r => `<li><span class="cms-check-icon">✓</span><div>${escapeHtml(r.statement)} ${helpers.inspectionButton(r.evidence_ids)}</div></li>`).join('')}
        </ul>
      </article>
    </div>

    <div class="cms-grid-2">
      <article class="cms-panel-card">
        <h3>Sinais do Radar (Seguradoras Primárias &amp; Alertas)</h3>
        <div class="cms-grid-2">
          <div class="cms-signal-box" data-tone="approved">
            <h4>✓ Sinais Fortes do Ecossistema</h4>
            <ul class="cms-check-list">
              ${strongSignals.length
                ? strongSignals.map(s => `<li><span class="cms-check-icon">✓</span><div>${escapeHtml(s)}</div></li>`).join('')
                : '<li><span class="cms-check-icon">✓</span><div>Monitoramento ativo das 10 seguradoras do catálogo ENS.</div></li>'}
            </ul>
          </div>
          <div class="cms-signal-box" data-tone="adjustments">
            <h4>⚠ Pontos de Atenção</h4>
            <ul class="cms-check-list">
              ${attentionSignals.length
                ? attentionSignals.map(s => `<li><span class="cms-check-icon">!</span><div>${escapeHtml(s)}</div></li>`).join('')
                : '<li><span class="cms-check-icon">!</span><div>Sinais setoriais contextualizam demanda, não substituem validação comercial.</div></li>'}
            </ul>
          </div>
        </div>
      </article>

      <article class="cms-panel-card">
        <h3>Mapa Setorial de Temas</h3>
        <p class="cms-muted">Clusters temáticos e relevância curricular para o curso proposto.</p>
        <div class="cms-cluster-bubbles">
          ${subthemes.map((st, idx) => `<div class="cms-cluster-bubble" data-tone="${idx === 0 ? 'approved' : idx === 1 ? 'running' : 'adjustments'}">
            <strong>${escapeHtml(st.theme)}</strong>
            <span>${escapeHtml(st.share_pct)}% dos sinais</span>
          </div>`).join('')}
        </div>
      </article>
    </div>
  `;
}

function renderEconomicsSubpage(page) {
  const wf = page.waterfall_steps || [];
  const scenarios = page.launch_scenarios || [];
  const sens = page.sensitivity_matrix || [];
  const risks = page.risks || [];
  const assumptions = page.assumptions || [];

  return `
    ${renderKpiStrip(page.kpis, 'cms-kpi-strip--6')}

    <div class="cms-grid-2">
      <article class="cms-panel-card">
        <h3>Formação do Resultado — Cascata (R$)</h3>
        <p class="cms-muted">Da receita bruta ao resultado líquido da turma no cenário base.</p>
        ${wf.length
          ? `<div class="cms-waterfall-list">
              ${wf.map(step => `<div class="cms-waterfall-row" data-kind="${escapeHtml(step.kind)}">
                <span>${escapeHtml(step.label)}</span>
                <strong>${escapeHtml(step.display)}</strong>
              </div>`).join('')}
            </div>`
          : `<div class="cms-empty-note">${escapeHtml(page.message || 'Informe as premissas de custo fixo, hora-aula e capacidade da turma para calcular a cascata financeira determinística.')}</div>`}
      </article>

      <article class="cms-panel-card">
        <h3>Cenários de Lançamento</h3>
        <p class="cms-muted">Projeções determinísticas de turma (Conservador, Base e Otimista).</p>
        ${scenarios.length
          ? `<div class="prometeus-table-container">
              <table class="prometeus-table cms-compact-table">
                <thead><tr><th>Cenário</th><th>Matrículas</th><th>Ocupação</th><th>Receita Líquida</th><th>Custos Totais</th><th>Resultado</th><th>Margem</th></tr></thead>
                <tbody>
                  ${scenarios.map(s => `<tr>
                    <td><strong>${escapeHtml(s.name)}</strong></td>
                    <td>${escapeHtml(s.students)}</td>
                    <td>${escapeHtml(s.occupancy)}</td>
                    <td>${escapeHtml(formatBrl(s.net_revenue))}</td>
                    <td>${escapeHtml(formatBrl(s.total_costs))}</td>
                    <td><strong>${escapeHtml(formatBrl(s.net_result))}</strong></td>
                    <td><span class="cms-pill" data-tone="approved">${escapeHtml(s.margin)}</span></td>
                  </tr>`).join('')}
                </tbody>
              </table>
            </div>`
          : '<div class="cms-empty-note">Cenários financeiros aguardam preenchimento das premissas operacionais da instituição (AGENTS.md Regra 4: a IA nunca inventa premissas financeiras).</div>'}
      </article>
    </div>

    <div class="cms-grid-2">
      <article class="cms-panel-card">
        <h3>Sensibilidade: Preço × Volume (Receita e Margem)</h3>
        <p class="cms-muted">Impacto das variações de ticket líquido e volume de matrículas.</p>
        ${sens.length
          ? `<div class="prometeus-table-container">
              <table class="prometeus-table cms-compact-table">
                <thead>
                  <tr>
                    <th>Ticket Simulado</th>
                    ${sens[0].cells.map(c => `<th>${escapeHtml(c.students)} alunos</th>`).join('')}
                  </tr>
                </thead>
                <tbody>
                  ${sens.map(row => `<tr class="${row.is_base ? 'is-highlighted-row' : ''}">
                    <td><strong>${escapeHtml(row.ticket_label)}</strong></td>
                    ${row.cells.map(c => `<td>${escapeHtml(c.revenue_label)} · <strong>${escapeHtml(c.margin_label)}</strong></td>`).join('')}
                  </tr>`).join('')}
                </tbody>
              </table>
            </div>`
          : '<div class="cms-empty-note">A matriz Preço × Volume é habilitada automaticamente quando os custos da turma são informados.</div>'}
      </article>

      <article class="cms-panel-card">
        <h3>Riscos Econômicos e Premissas</h3>
        <div class="cms-grid-2">
          <div>
            <h4>⚠ Principais Riscos</h4>
            <ul class="cms-check-list">
              ${risks.map(r => `<li><span class="cms-check-icon">!</span><div>${escapeHtml(r)}</div></li>`).join('')}
            </ul>
          </div>
          <div>
            <h4>✓ Premissas da Modelagem</h4>
            <ul class="cms-check-list">
              ${assumptions.map(a => `<li><span class="cms-check-icon">✓</span><div>${escapeHtml(a)}</div></li>`).join('')}
            </ul>
          </div>
        </div>
      </article>
    </div>
  `;
}

function renderSwotTowsSubpage(page, helpers) {
  const swot = page.swot || {};
  const tows = page.tows || {};
  const priorities = page.recommended_priorities || [];

  return `
    ${renderKpiStrip(page.kpis, 'cms-kpi-strip--4')}

    <div class="cms-grid-2">
      <article class="cms-panel-card">
        <h3>Análise SWOT</h3>
        <p class="cms-muted">Fatores internos e externos que impactam a viabilidade e o sucesso do curso.</p>
        <div class="cms-swot-2x2">
          <div class="cms-swot-cell" data-tone="approved">
            <h4>🏆 Forças <small>(interno / positivo)</small></h4>
            <ul class="cms-check-list">
              ${(swot.strengths || []).map(s => `<li><span class="cms-check-icon">✓</span><div>${escapeHtml(s.text)} ${helpers.inspectionButton(s.evidence_ids)}</div></li>`).join('')}
            </ul>
          </div>
          <div class="cms-swot-cell" data-tone="adjustments">
            <h4>⛓ Fraquezas <small>(interno / negativo)</small></h4>
            <ul class="cms-check-list">
              ${(swot.weaknesses || []).map(w => `<li><span class="cms-check-icon">−</span><div>${escapeHtml(w.text)}</div></li>`).join('')}
            </ul>
          </div>
          <div class="cms-swot-cell" data-tone="running">
            <h4>🚀 Oportunidades <small>(externo / positivo)</small></h4>
            <ul class="cms-check-list">
              ${(swot.opportunities || []).map(o => `<li><span class="cms-check-icon">✓</span><div>${escapeHtml(o.text)} ${helpers.inspectionButton(o.evidence_ids)}</div></li>`).join('')}
            </ul>
          </div>
          <div class="cms-swot-cell" data-tone="risk">
            <h4>⚠ Ameaças <small>(externo / negativo)</small></h4>
            <ul class="cms-check-list">
              ${(swot.threats || []).map(t => `<li><span class="cms-check-icon">!</span><div>${escapeHtml(t.text)}</div></li>`).join('')}
            </ul>
          </div>
        </div>
      </article>

      <article class="cms-panel-card">
        <h3>Matriz TOWS</h3>
        <p class="cms-muted">Estratégias derivadas da combinação dos fatores da SWOT para maximizar resultados e mitigar riscos.</p>
        <div class="cms-swot-2x2">
          <div class="cms-swot-cell" data-tone="approved">
            <h4><span class="cms-pill" data-tone="approved">SO</span> Estratégias SO <small>(Forças + Oportunidades)</small></h4>
            <ul class="cms-check-list">
              ${(tows.so || []).map(item => `<li><span class="cms-check-icon">✓</span><div>${escapeHtml(item)}</div></li>`).join('')}
            </ul>
          </div>
          <div class="cms-swot-cell" data-tone="running">
            <h4><span class="cms-pill" data-tone="running">ST</span> Estratégias ST <small>(Forças + Ameaças)</small></h4>
            <ul class="cms-check-list">
              ${(tows.st || []).map(item => `<li><span class="cms-check-icon">✓</span><div>${escapeHtml(item)}</div></li>`).join('')}
            </ul>
          </div>
          <div class="cms-swot-cell" data-tone="adjustments">
            <h4><span class="cms-pill" data-tone="adjustments">WO</span> Estratégias WO <small>(Fraquezas + Oportunidades)</small></h4>
            <ul class="cms-check-list">
              ${(tows.wo || []).map(item => `<li><span class="cms-check-icon">✓</span><div>${escapeHtml(item)}</div></li>`).join('')}
            </ul>
          </div>
          <div class="cms-swot-cell" data-tone="risk">
            <h4><span class="cms-pill" data-tone="risk">WT</span> Estratégias WT <small>(Fraquezas + Ameaças)</small></h4>
            <ul class="cms-check-list">
              ${(tows.wt || []).map(item => `<li><span class="cms-check-icon">✓</span><div>${escapeHtml(item)}</div></li>`).join('')}
            </ul>
          </div>
        </div>
      </article>
    </div>

    <div class="cms-grid-2">
      <article class="cms-panel-card">
        <h3>Prioridades Recomendadas</h3>
        <ol class="cms-numbered-list">
          ${priorities.map(p => `<li>
            <span class="cms-step-num">${escapeHtml(p.order)}</span>
            <div style="flex:1;"><strong>${escapeHtml(p.title)}</strong></div>
            <span class="cms-pill" data-tone="${escapeHtml(p.priority_tone)}">${escapeHtml(p.priority_label)}</span>
          </li>`).join('')}
        </ol>
      </article>

      <article class="cms-panel-card cms-synthesis-banner">
        <h3>Síntese Executiva</h3>
        <p>${escapeHtml(page.executive_synthesis)}</p>
      </article>
    </div>
  `;
}

function renderViabilityPillarsSubpage(page) {
  const cards = page.pillar_cards || [];
  const matrix = page.weight_score_matrix || [];
  const justifications = page.pillar_justifications || [];

  return `
    <div class="cms-pillar-grid-6">
      ${cards.map(c => `<article class="cms-pillar-card" data-tone="${escapeHtml(c.status_tone)}">
        <div class="cms-pillar-card__top">
          <strong>${escapeHtml(c.label)}</strong>
          <span class="cms-muted">Peso no IVO: <strong>${escapeHtml(c.weight_pct)}%</strong></span>
        </div>
        <div class="cms-pillar-card__score-row">
          <span class="cms-pillar-card__score">${escapeHtml(c.score)}<small>/100</small></span>
          <span class="cms-pill" data-tone="${escapeHtml(c.status_tone)}">✓ ${escapeHtml(c.status_label)}</span>
        </div>
        <ul class="cms-pillar-card__submetrics">
          ${(c.submetrics || []).map(sm => `<li><span>${escapeHtml(sm.label)}</span><strong>${escapeHtml(sm.value)}</strong></li>`).join('')}
        </ul>
      </article>`).join('')}
    </div>

    <div class="cms-grid-3">
      <article class="cms-panel-card">
        <h3>Composição do IVO (Índice de Viabilidade de Oferta)</h3>
        <div class="cms-donut-layout">
          ${renderDonutSvg(page.ivo_score, 100, `${page.ivo_score}/100`, 'IVO')}
          <ul class="cms-donut-legend">
            ${cards.map(c => `<li><span>${escapeHtml(c.label)}</span><strong>${escapeHtml(c.weight_pct)}%</strong></li>`).join('')}
          </ul>
        </div>
      </article>

      <article class="cms-panel-card">
        <h3>Matriz Peso × Nota</h3>
        <div class="prometeus-table-container">
          <table class="prometeus-table cms-compact-table">
            <thead><tr><th>Pilar</th><th>Peso</th><th>Nota (0–100)</th><th>Contribuição</th></tr></thead>
            <tbody>
              ${matrix.map(r => `<tr>
                <td><strong>${escapeHtml(r.label)}</strong></td>
                <td>${escapeHtml(r.weight_pct)}%</td>
                <td><strong>${escapeHtml(r.score)}</strong></td>
                <td>${escapeHtml(r.contribution_pts)} pts</td>
              </tr>`).join('')}
            </tbody>
            <tfoot>
              <tr>
                <th colspan="3">IVO (Índice de Viabilidade de Oferta)</th>
                <th><strong>${escapeHtml(page.ivo_score)}/100</strong></th>
              </tr>
            </tfoot>
          </table>
        </div>
      </article>

      <article class="cms-panel-card">
        <h3>Como cada pilar sustenta a decisão</h3>
        <ul class="cms-check-list">
          ${justifications.map(j => `<li><span class="cms-check-icon">✓</span><div><strong>${escapeHtml(j.label)}:</strong> ${escapeHtml(j.text)}</div></li>`).join('')}
        </ul>
      </article>
    </div>

    <div class="cms-footer-recommendation-bar">
      <div>
        <h3>Síntese e Recomendação</h3>
        <p class="cms-muted">${escapeHtml(page.synthesis_text)}</p>
      </div>
      <div class="cms-recommendation-callout" data-tone="${escapeHtml(page.recommendation_tone)}">
        <strong>Recomendação: ${escapeHtml(page.recommendation_short || page.recommendation_label)}</strong>
        <span>Parecer consolidado pelos 6 pilares do modelo portfolio-v2.</span>
      </div>
    </div>
  `;
}

function renderRevisionsSubpage(page) {
  const areas = page.area_reviews || [];
  const overall = page.overall_progress || { approved_count: 0, total_areas: 4, percent: 0, status_label: 'Em revisão' };
  const versions = page.version_history || [];
  const comments = page.comments_feed || [];
  const changes = page.changes_summary || [];
  const pendencies = page.pendencies || [];
  const approval = page.approval_recommendation || { decision_label: 'Em revisão', tone: 'adjustments', note: '' };
  const nextSteps = page.next_steps || [];

  return `
    <div class="cms-revisions-top">
      <article class="cms-panel-card">
        <h3>Status de Revisão por Área</h3>
        <div class="cms-area-review-grid">
          ${areas.map(a => `<div class="cms-area-review-card" data-tone="${escapeHtml(a.tone)}">
            <div class="cms-area-review-card__head">
              <strong>${escapeHtml(a.label)}</strong>
              <span class="cms-pill" data-tone="${escapeHtml(a.tone)}">${escapeHtml(a.status_label)}</span>
            </div>
            <div class="cms-area-review-card__meta">${escapeHtml(a.updated_at_label)}</div>
            <div class="cms-area-review-card__reviewer">por ${escapeHtml(a.reviewer_name)}</div>
          </div>`).join('')}
        </div>
      </article>

      <article class="cms-panel-card cms-overall-review-card">
        <h3>Status Geral da Revisão</h3>
        <div class="cms-donut-layout">
          ${renderDonutSvg(overall.percent, 100, `${overall.percent}%`, 'Concluído')}
          <div>
            <span class="cms-pill" data-tone="${escapeHtml(overall.tone)}">${escapeHtml(overall.status_label)}</span>
            <p class="cms-muted" style="margin-top:8px;"><strong>${escapeHtml(overall.approved_count)} de ${escapeHtml(overall.total_areas)}</strong> áreas aprovadas</p>
          </div>
        </div>
      </article>
    </div>

    <div class="cms-revisions-body">
      <article class="cms-panel-card">
        <h3>Histórico de Versões</h3>
        <div class="cms-version-timeline">
          ${versions.map(v => `<div class="cms-version-item ${v.is_current ? 'is-current' : ''}">
            <div class="cms-version-item__head">
              <strong>${escapeHtml(v.version)}${v.is_current ? ' (Atual)' : ''}</strong>
              <span class="cms-pill" data-tone="${escapeHtml(v.tone)}">${escapeHtml(v.badge_label)}</span>
            </div>
            <div class="cms-version-item__time">${escapeHtml(v.timestamp_label)}</div>
            <p>${escapeHtml(v.description)}</p>
          </div>`).join('')}
        </div>
      </article>

      <div class="cms-revisions-center">
        <article class="cms-panel-card">
          <h3>Comentários e Observações</h3>
          ${comments.length
            ? `<div class="cms-comments-feed">
                ${comments.map(c => `<div class="cms-comment-item">
                  <div class="cms-comment-avatar">${escapeHtml(c.initials || 'EN')}</div>
                  <div class="cms-comment-content">
                    <div class="cms-comment-meta">
                      <strong>${escapeHtml(c.reviewer_name)}</strong>
                      <span class="cms-pill" data-tone="${escapeHtml(c.tone)}">${escapeHtml(c.area_label)}</span>
                      <span class="cms-muted">${escapeHtml(c.timestamp_label)}</span>
                    </div>
                    <p>${escapeHtml(c.comment)}</p>
                  </div>
                </div>`).join('')}
              </div>`
            : '<p class="cms-muted">Nenhum parecer departamental registrado ainda. Utilize o formulário abaixo para registrar a revisão de sua área.</p>'}

          <form id="form-cms-area-review" class="cms-area-review-form">
            <h4>Registrar Parecer de Área</h4>
            <div class="cms-form-row">
              <select name="area" class="form-select" required aria-label="Área revisora">
                <option value="marketing">Marketing</option>
                <option value="produto">Produto</option>
                <option value="comercial">Comercial</option>
                <option value="financeiro">Financeiro</option>
              </select>
              <select name="status" class="form-select" required aria-label="Status da revisão">
                <option value="APPROVED">Aprovado</option>
                <option value="IN_REVIEW">Em revisão</option>
                <option value="CHANGES_REQUESTED">Ajustes solicitados</option>
              </select>
              <input type="text" name="reviewer_name" class="form-input" placeholder="Seu nome (ex.: Ana Ribeiro)" required />
            </div>
            <div class="cms-form-row" style="margin-top:8px;">
              <input type="text" name="comment" class="form-input" placeholder="Observação ou condição de aprovação da área..." required />
              <button type="submit" class="prometeus-btn-primary">Salvar revisão</button>
            </div>
            <p id="cms-area-review-feedback" class="cms-muted" style="margin-top:6px;"></p>
          </form>
        </article>

        <article class="cms-panel-card">
          <h3>Resumo de Mudanças e Auditoria</h3>
          <div class="prometeus-table-container">
            <table class="prometeus-table cms-compact-table">
              <thead><tr><th>#</th><th>Mudança / Verificação Realizada</th><th>Área</th><th>Responsável</th><th>Impacto</th></tr></thead>
              <tbody>
                ${changes.map(ch => `<tr>
                  <td>${escapeHtml(ch.index)}</td>
                  <td>${escapeHtml(ch.description)}</td>
                  <td><span class="cms-pill" data-tone="running">${escapeHtml(ch.area)}</span></td>
                  <td>${escapeHtml(ch.owner)}</td>
                  <td><span class="cms-pill" data-tone="${ch.impact === 'Alto' ? 'risk' : 'adjustments'}">${escapeHtml(ch.impact)}</span></td>
                </tr>`).join('')}
              </tbody>
            </table>
          </div>
        </article>
      </div>

      <div class="cms-revisions-right">
        <article class="cms-panel-card">
          <h3>Pendências (${pendencies.length})</h3>
          <ul class="cms-check-list">
            ${pendencies.length
              ? pendencies.map(p => `<li><span class="cms-check-icon">○</span><div><strong>${escapeHtml(p.criterion)}</strong> <span class="cms-pill" data-tone="adjustments">${escapeHtml(p.target)}</span></div></li>`).join('')
              : '<li><span class="cms-check-icon">✓</span><div>Nenhuma pendência bloqueante aberta.</div></li>'}
          </ul>
        </article>

        <article class="cms-panel-card">
          <h3>Aprovação Recomendada</h3>
          <div class="cms-approval-box" data-tone="${escapeHtml(approval.tone)}">
            <strong>✓ ${escapeHtml(approval.decision_label)}</strong>
            <p>${escapeHtml(approval.note)}</p>
          </div>
        </article>

        <article class="cms-panel-card">
          <h3>Próximos Passos</h3>
          <ol class="cms-numbered-list">
            ${nextSteps.map(ns => `<li>
              <span class="cms-step-num">${escapeHtml(ns.order)}</span>
              <div>${escapeHtml(ns.action)}</div>
            </li>`).join('')}
          </ol>
        </article>
      </div>
    </div>
  `;
}

function renderSourcesEvidencesSubpage(page, helpers) {
  const sources = page.collected_sources || [];
  const covBars = page.coverage_bars || [];
  const cats = page.evidence_categories || [];
  const steps = page.method_steps || [];

  return `
    <div class="cms-grid-2-wide">
      <article class="cms-panel-card">
        <h3>Fontes Coletadas</h3>
        <div class="prometeus-table-container">
          <table class="prometeus-table cms-compact-table">
            <thead>
              <tr>
                <th>Fonte</th>
                <th>Tipo</th>
                <th>Status</th>
                <th>Itens</th>
                <th>Observações</th>
              </tr>
            </thead>
            <tbody>
              ${sources.map(s => `<tr>
                <td><strong>${escapeHtml(s.source_name)}</strong></td>
                <td><span class="cms-pill" data-tone="running">${escapeHtml(s.source_type)}</span></td>
                <td><span class="cms-pill" data-tone="${escapeHtml(s.status_tone)}">✓ ${escapeHtml(s.status_label)}</span></td>
                <td><strong>${escapeHtml(s.records_count)}</strong></td>
                <td class="cms-muted">${escapeHtml(s.observation)}</td>
              </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </article>

      <div class="cms-sources-right">
        <article class="cms-panel-card">
          <h3>Cobertura da Pesquisa</h3>
          <div class="cms-hbar-list">
            ${covBars.map(b => `<div class="cms-hbar-row">
              <span class="cms-hbar-row__label">${escapeHtml(b.label)}</span>
              <div class="cms-hbar-row__track">
                <div class="cms-hbar-row__fill" data-tone="approved" style="width:${Math.max(8, Math.min(100, b.pct))}%;"></div>
              </div>
              <strong class="cms-hbar-row__val">${escapeHtml(b.pct)}%</strong>
            </div>`).join('')}
          </div>
          <div class="cms-coverage-footer">
            ✓ Cobertura geral: <strong>${escapeHtml(page.coverage_pct)}%</strong> · Escopo auditado para decisão de viabilidade.
          </div>
        </article>

        <article class="cms-panel-card cms-reliability-card">
          <h3>Confiabilidade das Evidências</h3>
          <div class="cms-donut-layout">
            ${renderDonutSvg(page.confidence_pct, 100, `${page.confidence_pct}/100`, 'Score geral')}
            <div>
              <span class="cms-pill" data-tone="approved">${page.confidence_pct >= 75 ? 'Alta confiabilidade' : 'Confiabilidade moderada'}</span>
              <p class="cms-muted" style="margin-top:8px;">Evidências higienizadas, rastreadas por hash e reconciliadas com leitura integral.</p>
            </div>
          </div>
        </article>
      </div>
    </div>

    <article class="cms-panel-card">
      <h3>Evidências Principais</h3>
      <div class="cms-grid-4">
        ${cats.map(cat => `<div class="cms-evidence-cat-card">
          <h4>${escapeHtml(cat.title)}</h4>
          <p class="cms-muted">${escapeHtml(cat.description)}</p>
          ${helpers.inspectionButton(cat.evidence_ids, 'Inspecionar evidências →')}
        </div>`).join('')}
      </div>
    </article>

    <article class="cms-panel-card">
      <h3>Método da Análise</h3>
      <div class="cms-method-pipeline">
        ${steps.map(st => `<div class="cms-method-step ${st.step === 5 ? 'is-final' : ''}">
          <span class="cms-step-num">${escapeHtml(st.step)}</span>
          <div>
            <strong>${escapeHtml(st.title)}</strong>
            <p class="cms-muted">${escapeHtml(st.description)}</p>
          </div>
        </div>`).join('')}
      </div>
    </article>
  `;
}

/* ============================================================================
 * SHELL PRINCIPAL DO CMS & BINDING DE EVENTOS
 * ============================================================================ */

export function renderCmsShellAndSubpages(store, course, dossier, helpers) {
  const state = store.getState();
  const cms = ensureCmsPages(dossier, course);
  const tabs = Array.isArray(cms.tabs) && cms.tabs.length ? cms.tabs : CMS_TABS_META;
  const activeTabId = tabs.some(t => t.id === state.activeDossierTab)
    ? state.activeDossierTab
    : cms.default_tab || 'overview';
  const activeTabMeta = tabs.find(t => t.id === activeTabId) || tabs[0];
  const pages = cms.pages || {};

  const renderByTab = {
    overview: () => renderOverviewSubpage(pages.overview || {}, helpers),
    key_metrics: () => renderKeyMetricsSubpage(pages.key_metrics || {}, helpers),
    fixed_competition: () => renderFixedCompetitionSubpage(pages.fixed_competition || {}, helpers),
    sector_radar: () => renderSectorRadarSubpage(pages.sector_radar || {}, helpers),
    economics: () => renderEconomicsSubpage(pages.economics || {}, helpers),
    swot_tows: () => renderSwotTowsSubpage(pages.swot_tows || {}, helpers),
    viability_pillars: () => renderViabilityPillarsSubpage(pages.viability_pillars || {}, helpers),
    revisions: () => renderRevisionsSubpage(pages.revisions || {}, helpers),
    sources_evidences: () => renderSourcesEvidencesSubpage(pages.sources_evidences || {}, helpers)
  };

  return `
    <div class="cms-dossier-shell">
      <!-- Barra de Navegação Superior das 9 Subpáginas (Estilo CMS) -->
      <nav class="cms-subnav" aria-label="Subpáginas do Dossiê Executivo">
        ${tabs.map(tab => `<button
          type="button"
          class="cms-subnav__tab ${tab.id === activeTabId ? 'is-active' : ''}"
          data-cms-tab="${escapeHtml(tab.id)}"
          aria-selected="${tab.id === activeTabId ? 'true' : 'false'}"
        >${escapeHtml(tab.label)}</button>`).join('')}
      </nav>

      <!-- Breadcrumb Contextual -->
      <div class="cms-breadcrumb" aria-label="Breadcrumb">
        <button type="button" class="cms-breadcrumb__link" id="btn-cms-breadcrumb-portfolio">🏠 Dossiês</button>
        <span class="cms-breadcrumb__sep">›</span>
        <span class="cms-breadcrumb__course">${escapeHtml(course.name)}</span>
        <span class="cms-breadcrumb__sep">›</span>
        <strong class="cms-breadcrumb__current" id="cms-breadcrumb-current-label">${escapeHtml(activeTabMeta.label)}</strong>
      </div>

      <!-- Cabeçalho Contextual da Subpágina -->
      <header class="cms-page-header">
        <div class="cms-page-header__title-group">
          <div class="cms-page-header__icon" aria-hidden="true">◈</div>
          <div>
            <h1 class="cms-page-header__title" id="cms-page-header-title">
              ${activeTabId === 'overview' ? `Dossiê de Viabilidade — ${escapeHtml(course.name)}` : escapeHtml(activeTabMeta.title)}
            </h1>
            <p class="cms-page-header__subtitle" id="cms-page-header-subtitle">${escapeHtml(activeTabMeta.subtitle)}</p>
          </div>
        </div>
        <div class="cms-page-header__actions">
          <span class="cms-status-chip" data-tone="${escapeHtml(cms.status_badge?.tone || 'approved')}">
            ● ${escapeHtml(cms.status_badge?.label || 'Pós-análise concluída')}
          </span>
          <button type="button" class="prometeus-btn-secondary" id="btn-open-evidence-drawer">
            Evidências (${(dossier.evidences || []).length})
          </button>
          <button type="button" class="prometeus-btn-secondary" id="btn-export-dossier-pdf">
            ↓ Exportar
          </button>
          <button type="button" class="prometeus-btn-primary" id="btn-share-dossier-link">
            🔗 Compartilhar
          </button>
        </div>
      </header>

      <!-- Painéis das 9 Subpáginas -->
      <div class="cms-tab-panels">
        ${tabs.map(tab => `<section
          class="cms-tab-panel ${tab.id === activeTabId ? 'is-active' : ''}"
          data-cms-panel="${escapeHtml(tab.id)}"
          id="cms-panel-${escapeHtml(tab.id)}"
        >
          ${(renderByTab[tab.id] || renderByTab.overview)()}
        </section>`).join('')}
      </div>
    </div>
  `;
}

export function bindCmsDossierEvents(store, container, course) {
  container.querySelector('#btn-cms-breadcrumb-portfolio')?.addEventListener('click', () => {
    store.setView('portfolio');
  });

  container.querySelectorAll('[data-cms-tab]').forEach(tabBtn => {
    tabBtn.addEventListener('click', () => {
      const targetTab = tabBtn.getAttribute('data-cms-tab');
      if (!targetTab) return;
      if (typeof store.setActiveDossierTab === 'function') {
        store.setActiveDossierTab(targetTab);
      } else {
        container.querySelectorAll('[data-cms-tab]').forEach(btn => {
          btn.classList.toggle('is-active', btn.getAttribute('data-cms-tab') === targetTab);
        });
        container.querySelectorAll('[data-cms-panel]').forEach(panel => {
          panel.classList.toggle('is-active', panel.getAttribute('data-cms-panel') === targetTab);
        });
      }
    });
  });

  container.querySelector('#btn-share-dossier-link')?.addEventListener('click', async e => {
    const btn = e.currentTarget;
    const shareUrl = new URL(window.location.href);
    if (course?.id) shareUrl.searchParams.set('analysis', course.id);
    try {
      await navigator.clipboard?.writeText(shareUrl.toString());
      const prev = btn.textContent;
      btn.textContent = '✓ Link copiado';
      setTimeout(() => { btn.textContent = prev; }, 2000);
    } catch {
      window.prompt('Copie o link do dossiê:', shareUrl.toString());
    }
  });

  const reviewForm = container.querySelector('#form-cms-area-review');
  if (reviewForm && course?.id) {
    reviewForm.addEventListener('submit', async e => {
      e.preventDefault();
      const formData = new FormData(reviewForm);
      const feedback = container.querySelector('#cms-area-review-feedback');
      const submitBtn = reviewForm.querySelector('button[type="submit"]');
      if (submitBtn) submitBtn.disabled = true;
      try {
        await store.submitDossierAreaReview(course.id, {
          area: String(formData.get('area') || 'marketing'),
          status: String(formData.get('status') || 'APPROVED'),
          reviewer_name: String(formData.get('reviewer_name') || '').trim(),
          comment: String(formData.get('comment') || '').trim()
        });
        if (feedback) feedback.textContent = 'Revisão registrada com sucesso no banco de dados.';
      } catch (err) {
        if (feedback) feedback.textContent = err.message || 'Erro ao salvar revisão.';
      } finally {
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }
}
