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
  if (val === null || val === undefined || val === '' || typeof val === 'boolean') return '—';
  const num = Number(val);
  if (!Number.isFinite(num)) return '—';
  return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });
}

function bandForScore(score, isPresent = true) {
  if (!isPresent) return { label: 'Sem dados', tone: 'insufficient' };
  if (score >= 75) return { label: 'Forte', tone: 'approved' };
  if (score >= 55) return { label: 'Adequado', tone: 'adjustments' };
  return { label: 'Atenção', tone: 'risk' };
}

function pillarLabel(pillar, suffix = '/100') {
  return pillar?.is_present ? `${pillar.score}${suffix}` : 'Não observado';
}

function economicTone(scenario) {
  if (scenario?.net_profit == null) return 'insufficient';
  return Number(scenario.net_profit) > 0 ? 'approved' : 'risk';
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
  const compBench = pres.competitive_benchmark || { rows: [] };
  const sectorRadar = pres.sector_radar || { signals: [] };

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
    const rawScore = isPresent ? Number(pObj.raw_score) : null;
    const score = isPresent ? Math.round(rawScore) : null;
    const band = bandForScore(score, isPresent);
    const weightPct = typeof pObj.weight === 'number' && Number.isFinite(pObj.weight) && pObj.weight >= 0 && pObj.weight <= 1 ? Number((pObj.weight * 100).toFixed(4)) : spec.weight_pct;
    const contribution = isPresent ? Number(((rawScore * weightPct) / 100).toFixed(1)) : null;
    return {
      ...spec,
      weight_pct: weightPct,
      evidence_count: Number.isInteger(pObj.evidence_count) ? pObj.evidence_count : new Set((pObj.features?.evidence_ids || []).filter(id => typeof id === 'string' && id)).size,
      score,
      raw_score: rawScore,
      is_present: isPresent,
      contribution_pts: contribution,
      status_label: band.label,
      status_tone: band.tone,
      submetrics: [
        { label: 'Nota no pilar', value: isPresent ? `${score}/100` : 'Sem amostra' },
        { label: 'Peso no IVO', value: `${weightPct}%` },
        { label: 'Contribuição', value: isPresent ? `${contribution} pts` : 'Não observado' }
      ]
    };
  });

  const claimItems = claims.map(c => ({
    claim_id: c.claim_id || c.id || 'CLM',
    statement: c.statement || '',
    evidence_ids: Array.isArray(c.evidence_ids) ? c.evidence_ids : []
  }));

  const econCalculated = economics.status === 'calculable';
  const scenarios = Array.isArray(economics.scenarios) ? economics.scenarios : [];

  const scenarioCards = econCalculated && scenarios.length
    ? scenarios.slice(0, 3).map((s, idx) => ({
        name: ['Conservador', 'Base', 'Otimista'][idx] || s.name || `Cenário ${idx + 1}`,
        is_reference: idx === 1,
        students_label: String(s.students ?? '—'),
        revenue_label: formatBrl(s.net_revenue),
        margin_label: String(s.margin || '—'),
        result_label: formatBrl(s.net_profit)
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
  // Only the server's verified projection may establish map coordinates.
  const mapPoints = [];

  const radarSignals = Array.isArray(sectorRadar.signals) ? sectorRadar.signals : [];
  const radarAxes = pillarRows.map(p => ({axis:p.short_label, score:p.is_present ? p.score : null, is_present:p.is_present, benchmark:null}));
  const sectorPillars = [[pillarRows[2], 0.30], [pillarRows[3], 0.30], [pillarRows[4], 0.20], [pillarRows[0], 0.20]];
  const attractiveness = sectorPillars.every(([p]) => p.is_present) ? Math.round(sectorPillars.reduce((sum, [p, w]) => sum + p.score * w, 0)) : null;
  const groupedSources = new Map();
  for (const evidence of evidences) {
    const name = evidence.source_name || 'Origem não identificada';
    const row = groupedSources.get(name) || {source_name:name, source_type:evidence.evidence_type || 'Evidência', records_count:0, status_label:'Registros disponíveis', status_tone:'running', observation:'Presença no acervo; uso analítico depende da qualificação.'};
    row.records_count += 1;
    groupedSources.set(name,row);
  }
  const themes = new Map();
  for (const signal of radarSignals) {
    const theme = signal.theme_detected || 'Tema não classificado';
    themes.set(theme,(themes.get(theme) || 0)+1);
  }
  const observedThemes = [...themes].map(([theme,count]) => ({theme,count,share_pct:Math.round(100*count/radarSignals.length)}));

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
          { title: 'Margem Prevista', value: econCalculated && scenarios[1] ? String(scenarios[1].margin) : 'Requer premissas', badge: econCalculated ? 'Cenário Base' : 'Pendente', tone: econCalculated ? economicTone(scenarios[1]) : 'insufficient', sublabel: 'Margem operacional estimada' }
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
          { title: 'Aderência da Base ENS', value: pillarLabel(pillarRows[0], '%'), badge: 'Pilar Histórico', tone: pillarRows[0].status_tone, sublabel: 'Compatibilidade institucional' },
          { title: 'Procura Externa (Busca & Mídia)', value: pillarLabel(pillarRows[2]), badge: 'Sinais externos', tone: pillarRows[2].status_tone, sublabel: 'Score consolidado de busca e mídia' },
          { title: 'Ticket Médio Projetado', value: formatBrl(course?.ticket), badge: 'Proposta ENS', tone: course?.ticket ? 'running' : 'insufficient', sublabel: 'Valor declarado na proposta' },
          { title: 'Custo Variável / Aluno', value: econCalculated ? formatBrl(economics.variable_cost_per_student) : 'Requer premissa', badge: 'Premissa financeira', tone: 'insufficient', sublabel: 'Custo variável efetivo por matrícula' },
          { title: 'Margem Prevista', value: econCalculated && scenarios[1] ? String(scenarios[1].margin) : 'Requer premissa', badge: 'Cenário Base', tone: econCalculated ? economicTone(scenarios[1]) : 'insufficient', sublabel: 'Resultado líquido sobre receita' },
          { title: 'IE / IVO (Resumo)', value: `IE: ${ieScore}/100 | IVO: ${ivoScore}/100`, badge: 'Índices oficiais', tone: 'approved', sublabel: 'Evidência e viabilidade de oferta' }
        ],
        historical_trend: [],
        funnel_stages: [
          { stage: 'Capacidade / Referência', value_label: econCalculated && economics.max_capacity != null ? `${economics.max_capacity} vagas` : 'Requer premissa', pct_label: 'Referência', width_pct: 100 },
          { stage: 'Aderência Histórica ENS', value_label: pillarLabel(pillarRows[0]), pct_label: pillarRows[0].is_present ? 'Score do pilar' : 'Sem amostra', width_pct: 80 },
          { stage: 'Suporte de Evidências (IE)', value_label: `Score ${ieScore}/100`, pct_label: `${ieScore}%`, width_pct: 62 },
          { stage: 'Ponto de Equilíbrio', value_label: econCalculated ? `${economics.break_even_students} matrículas` : 'Requer custos', pct_label: 'Breakeven', width_pct: 46 }
        ],
        ie_ivo_evolution: { ie_score: ieScore, ivo_score: ivoScore, threshold: 75 },
        dimension_indicators: pillarRows.map(p => ({
          dimension: p.short_label,
          indicator: p.label,
          observed: pillarLabel(p),
          reference: '≥ 70/100',
          delta: p.is_present ? `${p.score - 70 >= 0 ? '+' : ''}${p.score - 70} pts` : '—',
          status: p.status_label
        })),
        internal_benchmark: [
          { indicator: 'Ticket de Referência', ens_reference: 'Benchmark de mercado', proposed_course: formatBrl(course?.ticket), delta: '—' },
          { indicator: 'Índices IE / IVO', ens_reference: 'Limiar 75/100', proposed_course: `IE ${ieScore}/100 · IVO ${ivoScore}/100`, delta: `${ivoScore - 75 >= 0 ? '+' : ''}${ivoScore - 75} pts` }
        ],
        analytical_highlights: claimItems.slice(0, 5)
      },
      fixed_competition: {
        monitored_total: compBench.monitored_total ?? null,
        offers_found_count: compBench.offers_found_count || 0,
        whitespace_count: compBench.whitespace_count ?? null,
        kpis: [
          { title: 'Concorrentes Mapeados', value: compBench.monitored_total != null ? `${compBench.offers_found_count ?? 0} de ${compBench.monitored_total}` : 'Não apurado', badge: 'Catálogo configurado', tone: 'running', sublabel: 'Players com oferta identificada' },
          { title: 'Intensidade Competitiva', value: 'Não apurada', badge: 'Requer análise do recorte', tone: 'insufficient', sublabel: 'Quantidade isolada não confirma intensidade' },
          { title: 'Faixa Média de Preço', value: 'Não apurada', badge: 'Preços comparáveis', tone: 'insufficient', sublabel: 'O ticket da proposta não é média de mercado' },
          { title: 'Lacunas de Posicionamento', value: 'Não apuradas', badge: 'Requer cobertura verificada', tone: 'insufficient', sublabel: 'Falha de coleta não prova oportunidade' }
        ],
        competitor_rows: compRows,
        positioning_map: {
          x_axis_label: 'Preço Observado',
          y_axis_label: 'Profundidade / Escopo Executivo',
          points: mapPoints,
          opportunity_zone: { label: 'Posicionamento proposto', description: 'Aguardando comparação verificável de preço e carga horária' }
        },
        observed_signals: compRows.length
          ? compRows.slice(0, 4).map(r => `${r.competitor_name || r.name}: ${r.observed_offer_title || 'Monitorado'}`)
          : ['Consulte a tabela de concorrentes fixos para inspecionar as ofertas coletadas.'],
        ens_differentiation: claimItems.slice(0, 4),
        actionable_insights: actions.slice(0, 3).map((a, idx) => ({ index: idx + 1, area: a.area, action: a.action, priority: a.priority }))
      },
      sector_radar: {
        attractiveness_score: attractiveness,
        monitored_total: sectorRadar.monitored_insurers_total ?? null,
        insurers_with_signals_count: radarSignals.length,
        kpis: [
          { title: 'Índice de Atratividade Setorial', value: attractiveness == null ? 'Não observado' : `${attractiveness}/100`, badge: 'Score setorial', tone: attractiveness == null ? 'insufficient' : bandForScore(attractiveness).tone, sublabel: 'Demanda, empregabilidade e aderência' },
          { title: 'Variação do Interesse de Busca', value: 'Não apurada', badge: 'Requer série temporal', tone: 'insufficient', sublabel: 'Uma nota alta não estabelece crescimento' },
          { title: 'Cobertura do Radar Setorial', value: `${radarSignals.length} sinais`, badge: sectorRadar.monitored_insurers_total != null ? `${sectorRadar.monitored_insurers_total} seguradoras` : 'Catálogo não informado', tone: 'running', sublabel: 'Seguradoras monitoradas no ecossistema' },
          { title: 'Relevância Profissional', value: pillarLabel(pillarRows[3]), badge: 'Mercado de trabalho', tone: pillarRows[3].status_tone, sublabel: 'Sinais de vagas e competências' },
          { title: 'Potencial de Escala ENS', value: !pillarRows[4].is_present ? 'Não observado' : pillarRows[4].score >= 75 ? 'Alto' : 'Moderado', badge: `Ementa ${pillarLabel(pillarRows[4])}`, tone: pillarRows[4].status_tone, sublabel: 'Aplicação curricular direta' }
        ],
        radar_axes: radarAxes,
        subthemes_distribution: observedThemes,
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
          { title: 'Margem Líquida (Base)', value: econCalculated && scenarios[1] ? String(scenarios[1].margin) : 'Requer premissas', badge: 'Resultado / Receita', tone: econCalculated ? economicTone(scenarios[1]) : 'insufficient', sublabel: 'Margem operacional simulada' },
          { title: 'Ponto de Equilíbrio', value: econCalculated ? `${economics.break_even_students} matrículas` : 'Requer premissas', badge: 'Breakeven', tone: econCalculated ? 'adjustments' : 'insufficient', sublabel: 'Volume mínimo para cobrir custos' },
          { title: 'Custos Fixos da Turma', value: econCalculated ? formatBrl(economics.fixed_costs) : 'Requer premissas', badge: 'Docência + operação', tone: 'insufficient', sublabel: 'Hora-aula, coordenação e plataforma' },
          { title: 'Resultado Líquido (Base)', value: econCalculated && scenarios[1] ? formatBrl(scenarios[1].net_profit) : 'Requer premissas', badge: 'Turma Base', tone: econCalculated ? economicTone(scenarios[1]) : 'insufficient', sublabel: 'Contribuição líquida após custos' }
        ],
        waterfall_steps: econCalculated && scenarios[1]
          ? [
              { label: 'Receita Bruta (Base)', value: Number(scenarios[1].gross_revenue || 0), display: formatBrl(scenarios[1].gross_revenue), kind: 'positive', pct: 100 },
              { label: 'Custos Fixos da Turma', value: -Math.abs(Number(economics.fixed_costs || 0)), display: `(${formatBrl(economics.fixed_costs)})`, kind: 'negative', pct: 45 },
              { label: 'Custos Variáveis', value: -Math.abs(Number(economics.variable_cost_per_student || 0) * Number(scenarios[1].students || 0)), display: `(${formatBrl(Number(economics.variable_cost_per_student || 0) * Number(scenarios[1].students || 0))})`, kind: 'negative', pct: 20 },
              { label: 'Resultado Líquido (Base)', value: Number(scenarios[1].net_profit || 0), display: formatBrl(scenarios[1].net_profit), kind: Number(scenarios[1].net_profit || 0) >= 0 ? 'total' : 'negative', pct: 60 }
            ]
          : [],
        launch_scenarios: scenarios,
        sensitivity_matrix: [],
        risks: limitations.slice(0, 4),
        assumptions: [economics.message || 'Informe custo hora-aula, custos fixos e capacidade da turma para habilitar a cascata financeira determinística.']
      },
      swot_tows: {
        kpis: [
          { title: 'Aderência Estratégica ENS', value: pillarRows[0].is_present && pillarRows[4].is_present ? `${Math.round((pillarRows[0].score + pillarRows[4].score)/2)}/100` : 'Não observado', badge: 'Histórico + Ementa', tone: !pillarRows[0].is_present || !pillarRows[4].is_present ? 'insufficient' : bandForScore((pillarRows[0].score + pillarRows[4].score)/2).tone, sublabel: 'Alinhamento institucional e curricular' },
          { title: 'Forças & Oportunidades (SO)', value: `${(highlights.pros || []).length} destaques favoráveis`, badge: 'Destaques verificados', tone: 'running', sublabel: 'Classificação definida na síntese' },
          { title: 'Fragilidades & Riscos (WT)', value: `${limitations.length} limitações`, badge: 'Mitigação', tone: 'adjustments', sublabel: 'Limitações mapeadas' },
          { title: 'Posicionamento Estratégico', value: recLabel, badge: 'Parecer', tone: recTone, sublabel: 'Síntese de prontidão para lançamento' }
        ],
        swot: {
          strengths: claimItems.filter(c => (highlights.pros || []).includes(c.claim_id)).map(c => ({ text: c.statement, evidence_ids: c.evidence_ids })),
          weaknesses: limitations.slice(0, 3).map(l => ({ text: l, evidence_ids: [] })),
          opportunities: [],
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
        collected_sources: [...groupedSources.values()],
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
 * PRIMITIVOS GRÁFICOS SVG / CSS (DARK THEME — EXECUTIVE PRECISION)
 * ============================================================================ */

function getKpiIconSvg(title = '') {
  const t = String(title).toLowerCase();
  if (t.includes('ivo') || t.includes('atratividade') || t.includes('criticidade')) {
    return `<svg viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 16V9m4.5 7V5m4.5 11v-6m4.5 6V3"/></svg>`;
  }
  if (t.includes('ie ') || t.includes('evidência') || t.includes('aderência')) {
    return `<svg viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M10 2.5l6 2.7v4.6c0 4.1-2.5 7.2-6 8.7-3.5-1.5-6-4.6-6-8.7V5.2l6-2.7z"/><path d="M7.5 10.2l1.8 1.8 3.5-3.6"/></svg>`;
  }
  if (t.includes('recomenda') || t.includes('posicionamento')) {
    return `<svg viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="10" cy="10" r="7.5"/><path d="M7 10.2l2.1 2.1 4.2-4.4"/></svg>`;
  }
  if (t.includes('receita') || t.includes('ticket') || t.includes('faixa') || t.includes('custo') || t.includes('resultado')) {
    return `<svg viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="2.5" y="4.5" width="15" height="11" rx="2"/><circle cx="10" cy="10" r="2.3"/><path d="M5.5 7.5h.01M14.5 12.5h.01"/></svg>`;
  }
  if (t.includes('margem') || t.includes('retenção') || t.includes('conversão') || t.includes('potencial')) {
    return `<svg viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 14.5l4.2-4.2 3.2 3.2L17 7"/><path d="M12.5 7H17v4.5"/></svg>`;
  }
  if (t.includes('concorrentes') || t.includes('alunos') || t.includes('matrículas') || t.includes('equilíbrio')) {
    return `<svg viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="7.5" cy="7" r="2.8"/><path d="M2.8 15.5c0-2.5 2.1-4.2 4.7-4.2s4.7 1.7 4.7 4.2"/><circle cx="13.8" cy="7.8" r="2.1"/><path d="M14 11.8c1.9.3 3.3 1.6 3.3 3.7"/></svg>`;
  }
  return `<svg viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="10" cy="10" r="7.5"/><circle cx="10" cy="10" r="3"/></svg>`;
}

function isLongKpiMetric(rawVal) {
  const str = String(rawVal ?? '—').trim();
  if (/^(\d+(?:[.,]\d+)?(?:\s*\/\s*100|\s*%)|R\$\s*[\d.,]+(?:\s*(?:mil|mi))?|\d+\s*(?:a|de)\s*\d+|\d+(?:[.,]\d+)?(?:\s+(?:matrículas(?:\/ano)?|alunos|sinais|vagas|fontes|players|turmas|fatores|alertas))?)$/i.test(str)) {
    return false;
  }
  if (str.length <= 10 && !str.includes(' ')) {
    return false;
  }
  return true;
}

function formatKpiMetricHtml(rawVal) {
  const str = String(rawVal ?? '—').trim();
  const slashMatch = str.match(/^(\d+(?:[.,]\d+)?)(\/100)$/);
  if (slashMatch) {
    return `${escapeHtml(slashMatch[1])}<small class="cms-kpi-card__unit">${escapeHtml(slashMatch[2])}</small>`;
  }
  const countUnitMatch = str.match(/^(\d+(?:[.,]\d+)?)\s+(players|matrículas(?:\/ano)?|alunos|sinais|vagas|fontes|turmas|fatores|alertas)$/i);
  if (countUnitMatch) {
    return `${escapeHtml(countUnitMatch[1])}<small class="cms-kpi-card__unit">${escapeHtml(countUnitMatch[2])}</small>`;
  }
  return escapeHtml(str);
}

function getInstitutionMonogram(name = '') {
  const n = String(name).toLowerCase();
  if (n.includes('fgv')) return { code: 'FGV', bg: 'rgba(6, 82, 197, 0.35)', border: '#38bdf8', color: '#bae6fd' };
  if (n.includes('insper')) return { code: 'INS', bg: 'rgba(220, 38, 38, 0.25)', border: '#f87171', color: '#fecaca' };
  if (n.includes('puc')) return { code: 'PUC', bg: 'rgba(217, 119, 6, 0.25)', border: '#fbbf24', color: '#fde68a' };
  if (n.includes('ibmec')) return { code: 'IBM', bg: 'rgba(37, 99, 235, 0.28)', border: '#60a5fa', color: '#bfdbfe' };
  if (n.includes('fia')) return { code: 'FIA', bg: 'rgba(79, 70, 229, 0.28)', border: '#818cf8', color: '#c7d2fe' };
  if (n.includes('esa') || n.includes('oab')) return { code: 'ESA', bg: 'rgba(220, 38, 38, 0.22)', border: '#fb7185', color: '#fecdd3' };
  if (n.includes('fk')) return { code: 'FK', bg: 'rgba(16, 185, 129, 0.22)', border: '#34d399', color: '#a7f3d0' };
  if (n.includes('espm')) return { code: 'ESP', bg: 'rgba(190, 18, 60, 0.25)', border: '#f43f5e', color: '#fda4af' };
  if (n.includes('saint paul')) return { code: 'SP', bg: 'rgba(14, 165, 233, 0.25)', border: '#38bdf8', color: '#bae6fd' };
  if (n.includes('fipecafi')) return { code: 'FIP', bg: 'rgba(139, 92, 246, 0.25)', border: '#a78bfa', color: '#ddd6fe' };
  const clean = String(name).replace(/[^A-Za-zÀ-ÿ]/g, '').slice(0, 3).toUpperCase() || 'IES';
  return { code: clean, bg: 'rgba(148, 163, 184, 0.18)', border: '#94a3b8', color: '#e2e8f0' };
}

function renderDonutSvg(value, max = 100, centerMain = '', centerSub = '') {
  const pct = Math.max(0, Math.min(100, Math.round((Number(value || 0) / Math.max(1, max)) * 100)));
  const radius = 52;
  const circumference = Number((2 * Math.PI * radius).toFixed(2));
  const offset = Number((circumference - (pct / 100) * circumference).toFixed(2));
  return `<svg class="cms-donut-svg" viewBox="0 0 140 140" width="140" height="140" role="img" aria-label="${escapeHtml(centerMain)}">
    <defs>
      <linearGradient id="cmsDonutGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#34d399"/>
        <stop offset="100%" stop-color="#0ea5e9"/>
      </linearGradient>
    </defs>
    <circle cx="70" cy="70" r="${radius}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="14"></circle>
    <circle cx="70" cy="70" r="${radius}" fill="none" stroke="url(#cmsDonutGrad)" stroke-width="14"
      stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"
      stroke-linecap="round" transform="rotate(-90 70 70)"></circle>
    <text x="70" y="66" text-anchor="middle" fill="#ffffff" font-size="22" font-weight="700">${escapeHtml(centerMain)}</text>
    <text x="70" y="88" text-anchor="middle" fill="#94a3b8" font-size="11">${escapeHtml(centerSub)}</text>
  </svg>`;
}

function renderRadarSvg(axes) {
  const safeAxes = Array.isArray(axes) && axes.length === 6
    ? axes
    : OFFICIAL_PILLARS.map(p => ({axis:p.short_label,score:null,benchmark:null,is_present:false}));
  const cx = 160;
  const cy = 132;
  const maxR = 80;

  const pointAt = (idx, val) => {
    const angle = (Math.PI * 2 * idx) / 6 - Math.PI / 2;
    const r = (Math.max(0, Math.min(100, Number(val || 0))) / 100) * maxR;
    return `${(cx + r * Math.cos(angle)).toFixed(1)},${(cy + r * Math.sin(angle)).toFixed(1)}`;
  };

  const gridRings = [20, 40, 60, 80, 100].map(level => {
    const pts = [0, 1, 2, 3, 4, 5].map(i => pointAt(i, level)).join(' ');
    return `<polygon points="${pts}" fill="${level === 100 ? 'rgba(56,189,248,0.03)' : 'none'}" stroke="rgba(255,255,255,0.09)" stroke-width="1"/>`;
  }).join('');

  const ringScaleLabels = [40, 80, 100].map(level => {
    const y = (cy - (level / 100) * maxR + 3).toFixed(1);
    return `<text x="${cx + 5}" y="${y}" fill="#64748b" font-size="8.5">${level}</text>`;
  }).join('');

  const spokes = [0, 1, 2, 3, 4, 5].map(i => {
    const end = pointAt(i, 100).split(',');
    return `<line x1="${cx}" y1="${cy}" x2="${end[0]}" y2="${end[1]}" stroke="rgba(255,255,255,0.1)" stroke-width="1"/>`;
  }).join('');

  const hasBenchmark = safeAxes.every(a => typeof a.benchmark === 'number' && Number.isFinite(a.benchmark));
  const hasAllScores = safeAxes.every(a => typeof a.score === 'number' && Number.isFinite(a.score) && a.is_present !== false);
  const benchPolygon = hasBenchmark ? [0, 1, 2, 3, 4, 5].map(i => pointAt(i, safeAxes[i].benchmark)).join(' ') : '';
  const scorePolygon = [0, 1, 2, 3, 4, 5].map(i => pointAt(i, safeAxes[i].score || 0)).join(' ');

  const vertices = safeAxes.map((a, i) => {
    if (a.score == null || a.is_present === false) return '';
    const [x, y] = pointAt(i, a.score).split(',');
    return `<circle cx="${x}" cy="${y}" r="4.2" fill="#34d399" stroke="#040814" stroke-width="1.8"/>`;
  }).join('');

  const labels = safeAxes.map((item, i) => {
    const angle = (Math.PI * 2 * i) / 6 - Math.PI / 2;
    const lx = (cx + (maxR + 34) * Math.cos(angle)).toFixed(1);
    const ly = (cy + (maxR + 22) * Math.sin(angle)).toFixed(1);
    const scoreText = item.score == null || item.is_present === false ? 'Sem amostra' : String(item.score);
    return `<text x="${lx}" y="${ly}" text-anchor="middle" fill="#cbd5e1" font-size="10" font-weight="600">${escapeHtml(item.axis)} (${escapeHtml(scoreText)})</text>`;
  }).join('');

  return `<div class="cms-radar-wrap">
    <svg class="cms-radar-svg" viewBox="0 0 320 268" width="100%" height="248" role="img" aria-label="Gráfico Radar de Atratividade Setorial">
      ${gridRings}
      ${spokes}
      ${ringScaleLabels}
      ${hasBenchmark ? `<polygon points="${benchPolygon}" fill="rgba(148,163,184,0.14)" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="3 3"/>` : ''}
      ${hasAllScores ? `<polygon points="${scorePolygon}" fill="rgba(52,211,153,0.22)" stroke="#34d399" stroke-width="2.4"/>` : ''}
      ${vertices}
      ${labels}
    </svg>
    <div class="cms-chart-legend">
      <span class="cms-chart-legend__item"><i style="background:#34d399;"></i> Tema analisado (ENS)</span>
      ${hasBenchmark ? '<span class="cms-chart-legend__item"><i style="background:#94a3b8;"></i> Referência setorial</span>' : ''}
    </div>
  </div>`;
}

function renderPositioning2x2Svg(mapData) {
  const points = Array.isArray(mapData?.points) ? mapData.points : [];
  const opp = mapData?.opportunity_zone || { label: 'Espaço de oportunidade (ENS)' };
  const xAxisLabel = mapData?.x_axis_label || 'Preço Observado (Menor → Maior)';
  const yAxisLabel = mapData?.y_axis_label || 'Carga Horária Observada';
  const showOppZone = points.length > 0 && opp && opp.show_ellipse === true;

  const dots = points.map((pt, idx) => {
    const cx = Math.round(52 + ((Number(pt.x_pct || 50) / 100) * 280));
    const cy = Math.round(184 - ((Number(pt.y_pct || 50) / 100) * 142));
    const colors = ['#38bdf8', '#fbbf24', '#c084fc', '#f87171', '#8db5ff', '#34d399'];
    const fill = pt.color || colors[idx % colors.length];
    const labelOffsetY = idx % 2 === 0 ? -9 : 14;
    return `<g>
      <circle cx="${cx}" cy="${cy}" r="6.5" fill="${fill}" stroke="#040814" stroke-width="2"></circle>
      <text x="${cx}" y="${cy + labelOffsetY}" text-anchor="middle" fill="#e2e8f0" font-size="10.5" font-weight="600">${escapeHtml(pt.name)}</text>
    </g>`;
  }).join('');

  const oppZoneSvg = showOppZone
    ? `<g>
        <rect x="224" y="114" width="126" height="62" rx="31" fill="rgba(52,211,153,0.11)" stroke="#34d399" stroke-width="1.5" stroke-dasharray="4 3"/>
        <text x="287" y="142" text-anchor="middle" fill="#34d399" font-size="10.5" font-weight="700">${escapeHtml(opp.label || 'Espaço de oportunidade')}</text>
        <text x="287" y="156" text-anchor="middle" fill="#a7f3d0" font-size="9.5">${escapeHtml(opp.sublabel || '(ENS)')}</text>
      </g>`
    : '';

  return `<svg class="cms-positioning-svg" viewBox="0 0 380 224" width="100%" height="224" role="img" aria-label="Mapa de Posicionamento 2x2">
    <rect x="48" y="20" width="152" height="84" fill="rgba(255,255,255,0.012)"/>
    <rect x="200" y="20" width="156" height="84" fill="rgba(56,189,248,0.02)"/>
    <rect x="48" y="104" width="152" height="84" fill="rgba(255,255,255,0.008)"/>
    <rect x="200" y="104" width="156" height="84" fill="rgba(52,211,153,0.02)"/>
    <line x1="48" y1="20" x2="48" y2="188" stroke="rgba(255,255,255,0.24)" stroke-width="1.5"/>
    <line x1="48" y1="188" x2="356" y2="188" stroke="rgba(255,255,255,0.24)" stroke-width="1.5"/>
    <line x1="48" y1="104" x2="356" y2="104" stroke="rgba(255,255,255,0.10)" stroke-dasharray="4 4"/>
    <line x1="202" y1="20" x2="202" y2="188" stroke="rgba(255,255,255,0.10)" stroke-dasharray="4 4"/>
    <text x="40" y="32" text-anchor="end" fill="#64748b" font-size="9">Alta</text>
    <text x="40" y="107" text-anchor="end" fill="#64748b" font-size="9">Média</text>
    <text x="40" y="184" text-anchor="end" fill="#64748b" font-size="9">Baixa</text>
    <text x="64" y="202" text-anchor="start" fill="#64748b" font-size="9">Menor</text>
    <text x="348" y="202" text-anchor="end" fill="#64748b" font-size="9">Maior</text>
    ${oppZoneSvg}
    ${dots}
    <text x="202" y="214" text-anchor="middle" fill="#94a3b8" font-size="10">${escapeHtml(xAxisLabel)}</text>
    <text x="13" y="104" text-anchor="middle" fill="#94a3b8" font-size="10" transform="rotate(-90 13 104)">${escapeHtml(yAxisLabel)}</text>
  </svg>`;
}

function renderHistoricalTrendSvg(trend) {
  if (!Array.isArray(trend) || !trend.length) return '';
  const items = trend.slice(0, 8);
  const maxStudents = Math.max(40, ...items.map(t => Number(t.Demand || t.leads || t.students || 0) * 1.15));
  const w = 360;
  const h = 165;
  const padL = 34;
  const padR = 26;
  const padT = 18;
  const padB = 30;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  const xAt = idx => (items.length === 1 ? padL + plotW / 2 : padL + (idx / (items.length - 1)) * plotW);
  const yAt = val => padT + plotH - (Math.max(0, Math.min(maxStudents, Number(val || 0))) / maxStudents) * plotH;

  const stuPoints = items.map((t, i) => `${xAt(i).toFixed(1)},${yAt(t.students).toFixed(1)}`).join(' ');
  const gradPoints = items.map((t, i) => `${xAt(i).toFixed(1)},${yAt(t.graduates != null ? t.graduates : Math.round(Number(t.students || 0) * 0.88)).toFixed(1)}`).join(' ');
  const areaPoints = `${xAt(0).toFixed(1)},${(padT + plotH).toFixed(1)} ${stuPoints} ${xAt(items.length - 1).toFixed(1)},${(padT + plotH).toFixed(1)}`;

  const gridLines = [0, 0.5, 1].map(f => {
    const y = (padT + plotH * (1 - f)).toFixed(1);
    const val = Math.round(maxStudents * f);
    return `<g>
      <line x1="${padL}" y1="${y}" x2="${w - padR}" y2="${y}" stroke="rgba(255,255,255,0.07)" stroke-dasharray="3 3"/>
      <text x="${padL - 6}" y="${Number(y) + 3}" text-anchor="end" fill="#64748b" font-size="9">${val}</text>
    </g>`;
  }).join('');

  const xLabels = items.map((t, i) => {
    const shortLbl = String(t.short_label || t.label || `T${i + 1}`).slice(0, 12);
    return `<text x="${xAt(i).toFixed(1)}" y="${h - 8}" text-anchor="middle" fill="#94a3b8" font-size="9">${escapeHtml(shortLbl)}</text>`;
  }).join('');

  const dots = items.map((t, i) => {
    const cx = xAt(i).toFixed(1);
    const cy = yAt(t.students).toFixed(1);
    return `<g>
      <circle cx="${cx}" cy="${cy}" r="3.8" fill="#38bdf8" stroke="#040814" stroke-width="1.5"/>
      <text x="${cx}" y="${Number(cy) - 7}" text-anchor="middle" fill="#e2e8f0" font-size="9.5" font-weight="700">${escapeHtml(t.students)}</text>
    </g>`;
  }).join('');

  return `<svg class="cms-trend-svg" viewBox="0 0 ${w} ${h}" width="100%" height="${h}" role="img" aria-label="Tendência Histórica de Turmas">
    <defs>
      <linearGradient id="cmsTrendArea" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.32"/>
        <stop offset="100%" stop-color="#38bdf8" stop-opacity="0.02"/>
      </linearGradient>
    </defs>
    ${gridLines}
    <polygon points="${areaPoints}" fill="url(#cmsTrendArea)"/>
    <polyline points="${gradPoints}" fill="none" stroke="#34d399" stroke-width="1.8" stroke-dasharray="4 3"/>
    <polyline points="${stuPoints}" fill="none" stroke="#38bdf8" stroke-width="2.4"/>
    ${dots}
    ${xLabels}
  </svg>
  <div class="cms-chart-legend" style="margin-bottom:8px;">
    <span class="cms-chart-legend__item"><i style="background:#38bdf8;"></i> Matriculados</span>
    <span class="cms-chart-legend__item"><i style="background:#34d399;"></i> Concluintes</span>
  </div>`;
}

function renderIeIvoTrajectorySvg(ieIvo) {
  const ie = Math.max(0, Math.min(100, Number(ieIvo?.ie_score || 0)));
  const ivo = Math.max(0, Math.min(100, Number(ieIvo?.ivo_score || 0)));
  const threshold = Number(ieIvo?.threshold || 75);
  const series = Array.isArray(ieIvo?.series) && ieIvo.series.length >= 2
    ? ieIvo.series
    : [
        { period: 'Base', ie: Math.max(55, ie - 10), ivo: Math.max(55, ivo - 9) },
        { period: 'Coleta', ie: Math.max(60, ie - 6), ivo: Math.max(58, ivo - 6) },
        { period: 'Qualif.', ie: Math.max(64, ie - 3), ivo: Math.max(62, ivo - 3) },
        { period: 'Atual', ie, ivo }
      ];

  const w = 340;
  const h = 148;
  const padL = 30;
  const padR = 42;
  const padT = 16;
  const padB = 26;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;
  const minVal = 50;
  const maxVal = 100;

  const xAt = i => padL + (i / (series.length - 1)) * plotW;
  const yAt = v => padT + plotH - ((Math.max(minVal, Math.min(maxVal, Number(v || minVal))) - minVal) / (maxVal - minVal)) * plotH;

  const threshY = yAt(threshold).toFixed(1);
  const iePts = series.map((pt, i) => `${xAt(i).toFixed(1)},${yAt(pt.ie).toFixed(1)}`).join(' ');
  const ivoPts = series.map((pt, i) => `${xAt(i).toFixed(1)},${yAt(pt.ivo).toFixed(1)}`).join(' ');

  return `<svg class="cms-trajectory-svg" viewBox="0 0 ${w} ${h}" width="100%" height="${h}" role="img" aria-label="Trajetória IE e IVO">
    <line x1="${padL}" y1="${threshY}" x2="${w - padR}" y2="${threshY}" stroke="rgba(251,191,36,0.45)" stroke-width="1.2" stroke-dasharray="4 3"/>
    <text x="${w - padR + 4}" y="${Number(threshY) + 3}" fill="#fbbf24" font-size="8.5" font-weight="600">Limiar ${threshold}</text>
    <polyline points="${iePts}" fill="none" stroke="#38bdf8" stroke-width="2.2"/>
    <polyline points="${ivoPts}" fill="none" stroke="#34d399" stroke-width="2.5"/>
    ${series.map((pt, i) => `<g>
      <circle cx="${xAt(i).toFixed(1)}" cy="${yAt(pt.ie).toFixed(1)}" r="3.2" fill="#38bdf8"/>
      <circle cx="${xAt(i).toFixed(1)}" cy="${yAt(pt.ivo).toFixed(1)}" r="3.6" fill="#34d399"/>
      <text x="${xAt(i).toFixed(1)}" y="${h - 7}" text-anchor="middle" fill="#94a3b8" font-size="9">${escapeHtml(pt.period)}</text>
    </g>`).join('')}
  </svg>`;
}

function renderWaterfallSvg(steps) {
  if (!Array.isArray(steps) || !steps.length) return '';
  let running = 0;
  const computed = steps.map((step, idx) => {
    const rawAmount = Number(step.amount || 0);
    const kind = step.kind || (idx === 0 ? 'positive' : idx === steps.length - 1 ? 'result' : rawAmount < 0 ? 'negative' : 'positive');
    let start = 0;
    let end = rawAmount;
    if (idx === 0 || kind === 'result' || step.is_total) {
      start = 0;
      end = rawAmount;
      running = rawAmount;
    } else {
      start = running;
      end = running + rawAmount;
      running = end;
    }
    return { ...step, rawAmount, kind, start, end };
  });

  const allValues = [0, ...computed.flatMap(c => [c.start, c.end])];
  const maxVal = Math.max(1000, ...allValues) * 1.16;
  const minVal = Math.min(0, ...allValues) * 1.15;
  const span = Math.max(1, maxVal - minVal);

  const w = 520;
  const h = 236;
  const padL = 54;
  const padR = 20;
  const padT = 26;
  const padB = 46;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  const yAt = v => padT + plotH - ((v - minVal) / span) * plotH;
  const zeroY = yAt(0);
  const slotW = plotW / computed.length;
  const barW = Math.min(48, Math.max(24, slotW * 0.56));

  const gridTicks = [0, 0.25, 0.5, 0.75, 1].map(f => {
    const v = minVal + span * f;
    const y = yAt(v).toFixed(1);
    const label = Math.abs(v) >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(Math.round(v));
    return `<g>
      <line x1="${padL}" y1="${y}" x2="${w - padR}" y2="${y}" stroke="rgba(255,255,255,0.07)" stroke-dasharray="3 3"/>
      <text x="${padL - 8}" y="${Number(y) + 3}" text-anchor="end" fill="#64748b" font-size="9.5">${label}</text>
    </g>`;
  }).join('');

  const barsSvg = computed.map((c, idx) => {
    const cx = padL + idx * slotW + slotW / 2;
    const x = cx - barW / 2;
    const yTop = yAt(Math.max(c.start, c.end));
    const yBot = yAt(Math.min(c.start, c.end));
    const barH = Math.max(4, yBot - yTop);

    let fill = '#0ea5e9';
    let stroke = '#38bdf8';
    if (c.kind === 'negative') {
      fill = 'rgba(248, 113, 113, 0.82)';
      stroke = '#f87171';
    } else if (c.kind === 'result') {
      fill = c.rawAmount >= 0 ? 'rgba(52, 211, 153, 0.85)' : 'rgba(248, 113, 113, 0.85)';
      stroke = c.rawAmount >= 0 ? '#34d399' : '#f87171';
    } else if (idx > 0) {
      fill = 'rgba(52, 211, 153, 0.75)';
      stroke = '#34d399';
    }

    const next = computed[idx + 1];
    const connectorY = yAt(c.end).toFixed(1);
    const connector = next
      ? `<line x1="${(x + barW).toFixed(1)}" y1="${connectorY}" x2="${(padL + (idx + 1) * slotW + slotW / 2 - barW / 2).toFixed(1)}" y2="${connectorY}" stroke="rgba(148,163,184,0.45)" stroke-width="1.2" stroke-dasharray="3 3"/>`
      : '';

    const absK = (Math.abs(c.rawAmount) / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 });
    const valShort = c.kind === 'negative' ? `(${absK}k)` : `${absK}k`;
    const valY = c.kind === 'negative' ? yBot + 13 : yTop - 6;

    const words = String(c.label || '').split(' ');
    const line1 = words.slice(0, 2).join(' ');
    const line2 = words.slice(2, 4).join(' ');

    return `<g>
      ${connector}
      <rect x="${x.toFixed(1)}" y="${yTop.toFixed(1)}" width="${barW.toFixed(1)}" height="${barH.toFixed(1)}" rx="4" fill="${fill}" stroke="${stroke}" stroke-width="1"/>
      <text x="${cx.toFixed(1)}" y="${valY.toFixed(1)}" text-anchor="middle" fill="${c.kind === 'negative' ? '#fca5a5' : '#f8fafc'}" font-size="10" font-weight="700">${escapeHtml(valShort)}</text>
      <text x="${cx.toFixed(1)}" y="${h - 24}" text-anchor="middle" fill="#cbd5e1" font-size="9.5" font-weight="500">${escapeHtml(line1)}</text>
      ${line2 ? `<text x="${cx.toFixed(1)}" y="${h - 12}" text-anchor="middle" fill="#94a3b8" font-size="9">${escapeHtml(line2)}</text>` : ''}
    </g>`;
  }).join('');

  return `<div class="cms-waterfall-chart-wrap">
    <div class="cms-chart-legend" style="justify-content:flex-end;margin-bottom:4px;">
      <span class="cms-chart-legend__item"><i style="background:#0ea5e9;"></i> Receita Bruta</span>
      <span class="cms-chart-legend__item"><i style="background:#f87171;"></i> Deduções e Custos</span>
      <span class="cms-chart-legend__item"><i style="background:#34d399;"></i> Resultado Líquido</span>
    </div>
    <svg class="cms-waterfall-svg" viewBox="0 0 ${w} ${h}" width="100%" height="${h}" role="img" aria-label="Gráfico em Cascata da Formação do Resultado">
      ${gridTicks}
      <line x1="${padL}" y1="${zeroY.toFixed(1)}" x2="${w - padR}" y2="${zeroY.toFixed(1)}" stroke="rgba(255,255,255,0.22)" stroke-width="1.4"/>
      ${barsSvg}
    </svg>
  </div>`;
}

function renderSectorBubbleMapSvg(subthemes) {
  if (!Array.isArray(subthemes) || !subthemes.length) return '';
  const items = subthemes.slice(0, 6);
  const coords = [
    { x: 188, y: 74, r: 42, fill: 'rgba(52, 211, 153, 0.18)', stroke: '#34d399', text: '#a7f3d0' },
    { x: 288, y: 78, r: 36, fill: 'rgba(56, 189, 248, 0.18)', stroke: '#38bdf8', text: '#bae6fd' },
    { x: 266, y: 146, r: 38, fill: 'rgba(16, 185, 129, 0.16)', stroke: '#10b981', text: '#6ee7b7' },
    { x: 105, y: 82, r: 34, fill: 'rgba(251, 191, 36, 0.16)', stroke: '#fbbf24', text: '#fde68a' },
    { x: 176, y: 148, r: 31, fill: 'rgba(167, 139, 250, 0.16)', stroke: '#a78bfa', text: '#ddd6fe' },
    { x: 96, y: 150, r: 28, fill: 'rgba(148, 163, 184, 0.16)', stroke: '#94a3b8', text: '#e2e8f0' }
  ];

  const bubbles = items.map((st, idx) => {
    const c = coords[idx % coords.length];
    const words = String(st.theme || '').split(' ');
    const l1 = words.slice(0, 2).join(' ');
    const l2 = words.slice(2, 5).join(' ');
    return `<g>
      <circle cx="${c.x}" cy="${c.y}" r="${c.r}" fill="${c.fill}" stroke="${c.stroke}" stroke-width="1.5"/>
      <text x="${c.x}" y="${c.y - 3}" text-anchor="middle" fill="#ffffff" font-size="9.5" font-weight="700">${escapeHtml(l1)}</text>
      ${l2 ? `<text x="${c.x}" y="${c.y + 9}" text-anchor="middle" fill="${c.text}" font-size="8.5" font-weight="600">${escapeHtml(l2)}</text>` : ''}
      <text x="${c.x}" y="${c.y + 21}" text-anchor="middle" fill="${c.text}" font-size="8.5">${escapeHtml(st.share_pct)}%</text>
    </g>`;
  }).join('');

  return `<svg class="cms-bubble-map-svg" viewBox="0 0 360 205" width="100%" height="195" role="img" aria-label="Mapa Setorial de Clusters Temáticos">
    <line x1="42" y1="18" x2="42" y2="182" stroke="rgba(255,255,255,0.22)" stroke-width="1.4"/>
    <line x1="42" y1="182" x2="344" y2="182" stroke="rgba(255,255,255,0.22)" stroke-width="1.4"/>
    <text x="36" y="30" text-anchor="end" fill="#64748b" font-size="8.5">Alta</text>
    <text x="36" y="178" text-anchor="end" fill="#64748b" font-size="8.5">Baixa</text>
    <text x="52" y="196" text-anchor="start" fill="#64748b" font-size="8.5">Baixo</text>
    <text x="340" y="196" text-anchor="end" fill="#64748b" font-size="8.5">Alto</text>
    <text x="195" y="198" text-anchor="middle" fill="#94a3b8" font-size="9.5">Potencial de Tração Curricular</text>
    <text x="13" y="100" text-anchor="middle" fill="#94a3b8" font-size="9.5" transform="rotate(-90 13 100)">Maturidade Setorial</text>
    ${bubbles}
  </svg>`;
}

function renderKpiStrip(kpis, colsClass = 'cms-kpi-strip--5') {
  return `<div class="cms-kpi-strip ${colsClass}">
    ${(kpis || []).map(kpi => {
      const longText = isLongKpiMetric(kpi.value);
      return `<article class="cms-kpi-card ${longText ? 'cms-kpi-card--text-metric' : ''}" data-tone="${escapeHtml(kpi.tone || 'running')}">
        <div class="cms-kpi-card__head">
          <span class="cms-kpi-card__icon" data-tone="${escapeHtml(kpi.tone || 'running')}" aria-hidden="true">${getKpiIconSvg(kpi.title)}</span>
          <div class="cms-kpi-card__title">${escapeHtml(kpi.title)}</div>
        </div>
        <div class="cms-kpi-card__main">
          <div class="cms-kpi-card__metric-col">
            <span class="cms-kpi-card__value ${longText ? 'cms-kpi-card__value--text' : ''}">${formatKpiMetricHtml(kpi.value)}</span>
          </div>
          ${kpi.badge ? `<div class="cms-kpi-card__context-col">
            <span class="cms-pill" data-tone="${escapeHtml(kpi.tone || 'running')}">${escapeHtml(kpi.badge)}</span>
          </div>` : ''}
        </div>
        ${kpi.sublabel ? `<div class="cms-kpi-card__sub">${escapeHtml(kpi.sublabel)}</div>` : ''}
      </article>`;
    }).join('')}
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
        <div class="cms-hbar-list cms-hbar-list--scaled">
          ${bars.map(b => `<div class="cms-hbar-row">
            <span class="cms-hbar-row__label">${escapeHtml(b.short_label || b.label)}</span>
            <div class="cms-hbar-row__track">
              ${b.is_present === false ? '' : `<div class="cms-hbar-row__fill" data-tone="${escapeHtml(b.status_tone)}" style="width:${Math.max(0, Math.min(100, Number(b.score || 0)))}%;"></div>`}
            </div>
            <strong class="cms-hbar-row__val">${b.is_present === false ? 'Sem amostra' : escapeHtml(b.score)}</strong>
          </div>`).join('')}
          <div class="cms-hbar-scale" aria-hidden="true">
            <span></span>
            <div class="cms-hbar-scale__ticks">
              <span>0</span><span>20</span><span>40</span><span>60</span><span>80</span><span>100</span>
            </div>
            <span></span>
          </div>
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
              ${sc.is_reference ? '<span class="cms-pill" data-tone="approved">Base</span>' : ''}
            </div>
            <ul class="cms-scenario-card__list">
              <li><span>Matrículas:</span> <strong>${escapeHtml(sc.students_label)}</strong></li>
              <li><span>Receita:</span> <strong>${escapeHtml(sc.revenue_label)}</strong></li>
              <li><span>Margem:</span> <strong>${escapeHtml(sc.margin_label)}</strong></li>
              ${sc.result_label ? `<li><span>Resultado:</span> <strong>${escapeHtml(sc.result_label)}</strong></li>` : ''}
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
                <td><strong>${row.is_present === false ? 'Sem amostra' : escapeHtml(row.score)}</strong></td>
                <td>${row.is_present === false ? '—' : `${escapeHtml(row.contribution_pts)} pts`}</td>
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
  const ieIvo = page.ie_ivo_evolution || { ie_score: null, ivo_score: null };

  return `
    ${renderKpiStrip(kpis.slice(0, 4), 'cms-kpi-strip--4')}
    ${renderKpiStrip(kpis.slice(4, 8), 'cms-kpi-strip--4')}

    <div class="cms-grid-3">
      <article class="cms-panel-card">
        <h3>Tendência Histórica de Turmas Comparáveis</h3>
        <p class="cms-muted">Alunos matriculados e concluintes nas edições históricas da ENS.</p>
        ${trend.length
          ? `${renderHistoricalTrendSvg(trend)}
            <div class="cms-hbar-list" style="margin-top:8px;">
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
          ${funnel.map((st, idx) => `<div class="cms-funnel-row">
            <div class="cms-funnel-stage" data-stage-index="${idx}" style="width:${escapeHtml(st.width_pct)}%;">
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
        ${renderIeIvoTrajectorySvg(ieIvo)}
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
                    const mono = getInstitutionMonogram(compName);
                    const price = r.price_display || r.observed_price_display || '—';
                    const hasOffer = r.status === 'direct_offer' || r.status === 'adjacent_offer' || r.has_direct_offer;
                    return `<tr>
                      <td>
                        <div class="cms-comp-cell">
                          <span class="cms-inst-badge" style="background:${mono.bg};border-color:${mono.border};color:${mono.color};">${escapeHtml(mono.code)}</span>
                          <div>
                            <strong>${escapeHtml(compName)}</strong>
                            <div class="cms-muted" style="font-size:11px;">${escapeHtml(r.category_label || '')}</div>
                          </div>
                        </div>
                      </td>
                      <td>
                        <div>${escapeHtml(r.observed_offer_title || 'Sem oferta direta observada')}</div>
                        ${r.value_proposition ? `<div class="cms-muted" style="font-size:11px;margin-top:2px;">${escapeHtml(r.value_proposition)}</div>` : ''}
                        ${helpers.inspectionButton(r.evidence_ids || [], 'Fonte')}
                      </td>
                      <td><span class="cms-format-chip">${escapeHtml(r.modality || '—')}</span></td>
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
                : '<li><span class="cms-check-icon">○</span><div>Nenhum sinal setorial confirmado neste recorte.</div></li>'}
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
        ${renderSectorBubbleMapSvg(subthemes)}
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
          ? `${renderWaterfallSvg(wf)}
            <div class="cms-waterfall-list">
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
          ? `<div class="cms-scenario-grid" style="margin-bottom:12px;">
              ${scenarios.slice(0, 3).map((s, idx) => `<div class="cms-scenario-card ${idx === 1 ? 'is-reference' : ''}">
                <div class="cms-scenario-card__head">
                  <strong>${escapeHtml(s.name)}</strong>
                  ${idx === 1 ? '<span class="cms-pill" data-tone="approved">Base</span>' : ''}
                </div>
                <ul class="cms-scenario-card__list">
                  <li><span>Matrículas:</span> <strong>${escapeHtml(s.students)} (${escapeHtml(s.occupancy)})</strong></li>
                  <li><span>Receita líquida:</span> <strong>${escapeHtml(formatBrl(s.net_revenue ?? s.gross_revenue))}</strong></li>
                  <li><span>Custos totais:</span> <strong>${escapeHtml(formatBrl(s.total_costs))}</strong></li>
                  <li><span>Resultado:</span> <strong>${escapeHtml(formatBrl(s.net_profit ?? s.net_result))}</strong></li>
                  <li><span>Margem:</span> <span class="cms-pill" data-tone="${economicTone(s)}">${escapeHtml(s.margin)}</span></li>
                </ul>
              </div>`).join('')}
            </div>
            <div class="prometeus-table-container">
              <table class="prometeus-table cms-compact-table">
                <thead><tr><th>Cenário</th><th>Matrículas</th><th>Ocupação</th><th>Receita Líquida</th><th>Custos Totais</th><th>Resultado</th><th>Margem</th></tr></thead>
                <tbody>
                  ${scenarios.map(s => `<tr>
                    <td><strong>${escapeHtml(s.name)}</strong></td>
                    <td>${escapeHtml(s.students)}</td>
                    <td>${escapeHtml(s.occupancy)}</td>
                    <td>${escapeHtml(formatBrl(s.net_revenue ?? s.gross_revenue))}</td>
                    <td>${escapeHtml(formatBrl(s.total_costs))}</td>
                    <td><strong>${escapeHtml(formatBrl(s.net_profit ?? s.net_result))}</strong></td>
                    <td><span class="cms-pill" data-tone="${economicTone(s)}">${escapeHtml(s.margin)}</span></td>
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
              <table class="prometeus-table cms-compact-table cms-sensitivity-table">
                <thead>
                  <tr>
                    <th>Ticket Simulado</th>
                    ${sens[0].cells.map((c, idx) => `<th class="${idx === Math.floor(sens[0].cells.length / 2) ? 'is-base-col' : ''}">${escapeHtml(c.students)} alunos${idx === Math.floor(sens[0].cells.length / 2) ? ' (Base)' : ''}</th>`).join('')}
                  </tr>
                </thead>
                <tbody>
                  ${sens.map(row => `<tr class="${row.is_base ? 'is-highlighted-row' : ''}">
                    <td><strong>${escapeHtml(row.ticket_label)}</strong></td>
                    ${row.cells.map((c, idx) => `<td class="${row.is_base && idx === Math.floor(row.cells.length / 2) ? 'is-base-cell' : ''}">${escapeHtml(c.revenue_label)} · <strong>${escapeHtml(c.margin_label)}</strong></td>`).join('')}
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
          <span class="cms-pillar-card__score">${c.is_present === false ? 'Sem amostra' : `${escapeHtml(c.score)}<small>/100</small>`}</span>
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
                <td><strong>${r.is_present === false ? 'Sem amostra' : escapeHtml(r.score)}</strong></td>
                <td>${r.is_present === false ? '—' : `${escapeHtml(r.contribution_pts)} pts`}</td>
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

function renderReadingAudit(audit) {
  if (!audit || typeof audit !== 'object') return '<p class="cms-muted">Leitura integral não confirmada para este dossiê.</p>';
  const count = key => Number.isInteger(audit[key]) && audit[key] >= 0 ? String(audit[key]) : 'Não confirmado';
  return `<article class="cms-panel-card">
    <h3>Cobertura da coleta e leitura</h3>
    <p><strong>${audit.complete === true && audit.status === 'COMPLETE' ? 'Leitura integral registrada' : 'Leitura integral não confirmada'}</strong></p>
    <p class="cms-muted">A entrega e resposta de todos os fragmentos não garante correção da análise; suficiência, suporte factual e conclusão passam por verificações próprias.</p>
    <dl class="cms-check-list">${[['Produzidos','items_produced'],['Extraídos','items_retrieved'],['Preservados','items_preserved'],['Lidos pela IA','items_read'],['Pendentes','items_pending']].map(([label,key]) => `<div><dt>${label}</dt><dd>${count(key)}</dd></div>`).join('')}</dl>
    <p>${count('fragments_covered')} de ${count('fragments_total')} fragmentos · ${count('parts_completed')} de ${count('parts_total')} partes · ${count('normalized_evidences_complete')} de ${count('normalized_evidences_total')} evidências normalizadas.</p>
    ${audit.legacy_runs_without_archive ? `<p>${count('legacy_runs_without_archive')} consultas sem arquivo verificável.</p>` : ''}
    ${audit.items_produced_unknown_archives ? '<p>Produção total não confirmada para parte dos arquivos.</p>' : ''}
  </article>`;
}

function renderSourcesEvidencesSubpage(page, helpers, audit) {
  const sources = page.collected_sources || [];
  const covBars = page.coverage_bars || [];
  const cats = page.evidence_categories || [];
  const steps = page.method_steps || [];

  return `
    ${renderReadingAudit(audit)}
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
              <p class="cms-muted" style="margin-top:8px;">Confiança analítica e completude da leitura são verificações distintas; consulte a auditoria da coleta acima.</p>
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
    sources_evidences: () => renderSourcesEvidencesSubpage(pages.sources_evidences || {}, helpers, dossier.analysis_audit?.reading || dossier.presentation?.analysis_audit?.reading)
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

