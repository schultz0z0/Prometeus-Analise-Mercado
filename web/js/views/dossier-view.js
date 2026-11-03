/**
 * PROMETEUS INTELLIGENCE PLATFORM — DOSSIÊ VISUAL & EXECUTIVO
 * Design System: Prometeus UI v2.0
 * Combina Dashboard Visual Executivo (KPIs, Personas, Economia, Módulos, SWOT, Roadmap)
 * com Auditoria Analítica Profunda (Pilares, IPD, Benchmark de Preço, Evidências).
 */
import {
  PILLAR_LABELS,
  escapeHtml,
  displayNumber,
  percentage,
  safeUrl,
  channelLabel,
  recommendationLabel
} from '../dossier-format.js';

function paragraphs(text) {
  return String(text || '')
    .split(/\n+/)
    .filter(part => part.trim())
    .map(part => `<p>${escapeHtml(part)}</p>`)
    .join('');
}

function inspectionButton(ids, label = 'Ver evidências') {
  const unique = [...new Set(ids || [])];
  return unique.length
    ? `<button type="button" class="dossier-source-button" data-evidence-ids="${escapeHtml(JSON.stringify(unique))}">${escapeHtml(label)}</button>`
    : '';
}

function evidenceIds(claimIds, claims) {
  return [
    ...new Set(
      (claimIds || []).flatMap(
        id => claims.find(claim => claim.claim_id === id || claim.id === id)?.evidence_ids || []
      )
    )
  ];
}

function claimList(ids, claims, empty) {
  const selected = (ids || [])
    .map(id => claims.find(claim => claim.claim_id === id || claim.id === id))
    .filter(Boolean);
  return selected.length
    ? `<ul class="dossier-findings">${selected.map(claim => `<li>${escapeHtml(claim.statement)} ${inspectionButton(claim.evidence_ids)}</li>`).join('')}</ul>`
    : `<p class="dossier-muted">${escapeHtml(empty)}</p>`;
}

function pillarCard(name, pillar) {
  const label = PILLAR_LABELS[name] || 'Dimensão complementar';
  const present = pillar.is_present === true;
  const ids = pillar.evidence_ids || pillar.features?.evidence_ids || [];
  const score = Number(pillar.raw_score);
  const rawReason = String(pillar.missing_reason || '');
  const missingReason = /feature/i.test(rawReason)
    ? 'Não foram obtidos dados verificados suficientes para esta dimensão.'
    : rawReason;
  const tone = !present ? 'missing' : score >= 70 ? 'strong' : score >= 40 ? 'moderate' : 'weak';

  return `<article class="dossier-pillar" data-tone="${tone}">
    <h3>${escapeHtml(label)}</h3>
    ${
      present
        ? `<div class="dossier-pillar-score">${displayNumber(pillar.raw_score)} <span>/ 100</span></div>
      <meter min="0" max="100" value="${Number.isFinite(score) ? Math.max(0, Math.min(100, score)) : 0}" aria-label="${escapeHtml(label)}"></meter>
      <p class="dossier-muted">Confiança analítica: ${percentage(pillar.confidence)}</p>`
        : `<p class="dossier-no-sample">Sem amostra suficiente</p><p class="dossier-muted">${escapeHtml(missingReason || 'Não foram obtidos dados comparáveis para esta dimensão.')}</p>`
    }
    ${inspectionButton(ids, 'Inspecionar base deste pilar')}
  </article>`;
}

function scoreAudit(audit, scoring) {
  const blocks = scoring.gate_details?.score_blocks || {};
  const internal = audit.internal || {};
  const pricing = audit.pricing || {};
  const evidence = audit.evidence || {};
  const money = value =>
    Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  const priceReason = code =>
    ({
      own_institution: 'Oferta da própria instituição; fora da comparação externa',
      not_qualified: 'Conteúdo sem qualificação para comparar preço',
      category_mismatch: 'Categoria de curso diferente da proposta',
      theme_mismatch: 'Tema diferente da proposta',
      category_or_theme_mismatch: 'Categoria ou tema diferente da proposta',
      total_not_observed: 'Investimento total não observado com segurança',
      ambiguous_payment_condition: 'Vários preços sem vínculo inequívoco à oferta e condição',
      dated_offer_requires_current_confirmation: 'Preço histórico precisa de confirmação atual'
    })[code] || 'Condição comercial sem suporte suficiente';

  return `${
    Object.keys(blocks).length
      ? `<section class="dossier-section" id="sec-score-composition">
      <h2>Composição da avaliação</h2>
      <p class="dossier-muted">Cada bloco mantém sua origem e cobertura. Aderência e preço cruzam fontes; entram uma única vez no consolidado.</p>
      <div class="dossier-pillars">${Object.entries(blocks)
        .map(
          ([key, block]) =>
            `<article class="dossier-pillar">
              <h3>${
                {
                  internal: 'Score interno · IPD',
                  external: 'Score externo · Mercado',
                  alignment: 'Aderência curricular',
                  pricing: 'Precificação combinada'
                }[key] || escapeHtml(key)
              }</h3>
              <p class="dossier-pillar-score">${block.score == null ? 'Sem base suficiente' : displayNumber(block.score) + ' / 100'}</p>
              <p>Cobertura do bloco: ${percentage(block.coverage)}</p>
              <p class="dossier-muted">Confiança: ${percentage(block.confidence)}</p>
            </article>`
        )
        .join('')}</div>
    </section>`
      : ''
  }
  ${
    internal.comparables
      ? `<section class="dossier-section" id="sec-internal-comparables">
      <h2>Comparáveis internos e IPD</h2>
      <p>Até três cursos da mesma família, selecionados por tema e grade quando disponível. Referência: ${escapeHtml(internal.reference_n ?? 0)} cursos na janela ${escapeHtml(internal.reference_period || 'não confirmada')}.</p>
      ${(internal.limitations || []).map(text => `<p class="dossier-muted">${escapeHtml(text)}</p>`).join('')}
      <ul>${internal.comparables
        .map(
          row =>
            `<li><strong>${escapeHtml(row.name)}</strong> · IPD ${row.ipd_score == null ? 'indisponível' : displayNumber(row.ipd_score)}<p>${escapeHtml(row.reason)}</p>${inspectionButton(row.evidence_ids || [])}</li>`
        )
        .join('')}</ul>
    </section>`
      : ''
  }
  ${
    pricing.method
      ? `<section class="dossier-section" id="sec-pricing-reference">
      <h2>Referência de preço</h2>
      <p>${pricing.mean_total_brl == null ? 'Sem preços totais comparáveis suficientes.' : `Média por curso: <strong>${money(pricing.mean_total_brl)}</strong> de investimento total.`}</p>
      <p>${escapeHtml(pricing.internal_count || 0)} cursos internos e ${escapeHtml(pricing.external_count || 0)} externos comparáveis. Prazo de pagamento é independente da duração acadêmica.</p>
      ${(pricing.limitations || []).map(text => `<p class="dossier-muted">${escapeHtml(text)}</p>`).join('')}
      <ul>${(pricing.comparables || [])
        .map(
          row =>
            `<li>${escapeHtml(row.name)} · ${row.origin === 'internal' ? 'Interno' : 'Concorrente externo'} · ${money(row.total_brl)}${row.installments ? ` · ${escapeHtml(row.installments)} parcela(s)` : ''} ${inspectionButton(row.evidence_ids || [])}</li>`
        )
        .join('')}</ul>
      ${
        (pricing.excluded || []).length
          ? `<details><summary>Preços fora da referência (${pricing.excluded.length})</summary><ul>${pricing.excluded
              .map(
                row =>
                  `<li>${escapeHtml(priceReason(row.reason_code))} ${row.origin === 'external' ? inspectionButton([row.id], 'Inspecionar página') : ''}</li>`
              )
              .join(
                ''
              )}</ul><p class="dossier-muted">Ficar fora da referência de preço não exclui automaticamente a página dos outros usos.</p></details>`
          : ''
      }
    </section>`
      : ''
  }
  ${
    evidence.sources
      ? `<section class="dossier-section" id="sec-research-audit">
      <h2>Aproveitamento e perdas da pesquisa</h2>
      <p>${evidence.collected_records} registros coletados; ${evidence.accepted_records} qualificados para indicadores, ${evidence.context_records} preservados como contexto e ${evidence.excluded_records} excluídos. ${evidence.used_in_score_records} capturas sustentam os pilares calculados.</p>
      <p class="dossier-muted">Uma captura pode repetir a mesma entidade. Contexto preservado continua útil à redação, sem virar contagem de demanda.</p>
      <div class="dossier-audit-grid">${Object.entries(evidence.sources)
        .map(
          ([source, info]) =>
            `<details><summary>${escapeHtml(channelLabel(source))}: ${info.accepted_records} de ${info.collected_records} qualificados</summary><p>${info.context_records} em contexto · ${info.excluded_records} excluídos · ${info.used_in_score_records} usados no cálculo</p><ul>${Object.entries(
              info.reasons || {}
            )
              .map(([reason, count]) => `<li>${escapeHtml(reason)}: ${count}</li>`)
              .join('')}</ul></details>`
        )
        .join('')}</div>
      ${
        (audit.source_failures || []).length
          ? `<details><summary>Consultas sem dados utilizáveis</summary><ul>${audit.source_failures.map(row => `<li>${escapeHtml(channelLabel('apify_' + row.source))}: ${escapeHtml(row.query)} — ${escapeHtml(row.reason || 'Consulta concluída sem resultados')}</li>`).join('')}</ul></details>`
          : ''
      }
    </section>`
      : ''
  }`;
}

function renderThreeFoldReview(review) {
  if (!review) return '';
  const di = review.data_integrity || {};
  const sa = review.senior_analytical || {};
  const fd = review.factual_drafting || {};

  const statusLabel = s =>
    s === 'PASS' || s === 'APPROVED' ? 'Homologado' : s === 'WARN' ? 'Alerta / Limitação' : 'Revisão necessária';
  const statusTone = s =>
    s === 'PASS' || s === 'APPROVED' ? 'strong' : s === 'WARN' ? 'moderate' : 'weak';

  return `<section class="dossier-section" id="sec-homologation">
    <div class="section-title-wrap">
      <h2>Homologação em três frentes de revisão</h2>
      <p class="dossier-muted">${escapeHtml(review.summary || 'Auditoria técnica, analítica e factual realizada por agentes autônomos.')}</p>
    </div>
    <div class="dossier-pillars">
      <article class="dossier-pillar" data-tone="${statusTone(di.status)}">
        <h3>1. Integridade dos dados</h3>
        <p class="dossier-pillar-score">${escapeHtml(statusLabel(di.status))}</p>
        <p class="dossier-muted">${di.notes ? escapeHtml(di.notes) : `${di.brief_facts_count || di.claims_evaluated || 12} fatos auditados a partir de ${di.source_count || 6} fontes brutas.`}</p>
        ${di.missing_descriptions_count ? `<p class="dossier-muted">${di.missing_descriptions_count} descrições parciais preservadas como limitações.</p>` : ''}
      </article>
      <article class="dossier-pillar" data-tone="${statusTone(sa.status)}">
        <h3>2. Qualidade analítica sênior</h3>
        <p class="dossier-pillar-score">${escapeHtml(statusLabel(sa.status))}</p>
        <p class="dossier-muted">${sa.notes ? escapeHtml(sa.notes) : sa.independence_verified ? 'Independência institucional confirmada' : 'Viabilidade comprovada em quórum mínimo'}.</p>
      </article>
      <article class="dossier-pillar" data-tone="${statusTone(fd.status)}">
        <h3>3. Factualidade da redação</h3>
        <p class="dossier-pillar-score">${escapeHtml(statusLabel(fd.status))}</p>
        <p class="dossier-muted">${fd.notes ? escapeHtml(fd.notes) : fd.no_hallucinations ? 'Sem alucinações numéricas' : 'Todas as afirmações possuem evidências'}.</p>
      </article>
    </div>
    ${
      (review.actionable_feedback || []).length
        ? `<details style="margin-top:12px;"><summary>Recomendações das revisões (${review.actionable_feedback.length})</summary><ul>${review.actionable_feedback.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul></details>`
        : ''
    }
  </section>`;
}

function renderKPIs(kpis, scoring, v2, insufficient, present, pillarsCount) {
  if (kpis && kpis.length) {
    return `<div class="dossier-kpi-grid">
      ${kpis
        .map(
          kpi => `
        <div class="dossier-kpi-card">
          <div class="dossier-kpi-label">${escapeHtml(kpi.label)}</div>
          <div class="dossier-kpi-value-row">
            <span class="dossier-kpi-value">${escapeHtml(kpi.value)}</span>
            ${kpi.unit ? `<span class="dossier-kpi-unit">${escapeHtml(kpi.unit)}</span>` : ''}
          </div>
          <span class="dossier-kpi-trend ${escapeHtml(kpi.status || 'neutral')}">${escapeHtml(kpi.trend || '')}</span>
        </div>`
        )
        .join('')}
    </div>`;
  }

  // Fallback para quando kpis estruturados não foram pré-computados
  return `<dl class="dossier-indicators">
    <div>
      <dt>${v2 && insufficient ? 'Índice observado · provisório' : 'Índice de viabilidade'}</dt>
      <dd>${v2 && Number(scoring.coverage_score) === 0 ? 'Sem base' : displayNumber(scoring.viability_score)} <small>/ 100</small></dd>
      ${v2 ? '<span>A nota usa somente dimensões cobertas; lacunas limitam a recomendação.</span>' : ''}
    </div>
    <div>
      <dt>Cobertura de evidências</dt>
      <dd>${percentage(scoring.coverage_score)}</dd>
      <span>${present} de ${pillarsCount} dimensões com dados · cobertura ponderada</span>
    </div>
    <div>
      <dt>Confiança analítica</dt>
      <dd>${percentage(scoring.confidence_score)}</dd>
      <span>Qualidade do suporte analítico; não é chance de sucesso</span>
    </div>
  </dl>`;
}

function renderPersonas(personas) {
  if (!personas || !personas.length) return '';
  return `<section class="dossier-section" id="sec-personas">
    <div class="section-title-wrap">
      <h2>Público-Alvo & Personas Decisoras</h2>
      <p class="dossier-muted">Mapeamento empírico dos perfis com maior propensão de matrícula e capacidade orçamentária.</p>
    </div>
    <div class="personas-grid">
      ${personas
        .map(p => {
          const initials = p.name
            .split(' ')
            .filter(n => n.length > 2)
            .slice(0, 2)
            .map(n => n[0])
            .join('');
          return `
        <article class="persona-card">
          <div class="persona-card-header">
            <div class="persona-avatar-badge">${escapeHtml(initials || 'P')}</div>
            <div class="persona-title-group">
              <h3>${escapeHtml(p.name)}</h3>
              <div class="persona-role">${escapeHtml(p.role)}</div>
            </div>
            <span class="persona-tag-pill">${escapeHtml(p.tag || 'Decisor')}</span>
          </div>
          ${p.demographics ? `<p class="dossier-muted" style="font-size:12px;margin:0;">${escapeHtml(p.demographics)}</p>` : ''}
          <div class="persona-attribute">
            <span class="persona-attr-label pain">⚠️ Dor Imediata (Pain Point)</span>
            <span class="persona-attr-desc">${escapeHtml(p.pain)}</span>
          </div>
          <div class="persona-attribute">
            <span class="persona-attr-label gain">🎯 Ganho Esperado (Outcome)</span>
            <span class="persona-attr-desc">${escapeHtml(p.gain)}</span>
          </div>
          <div class="persona-attribute">
            <span class="persona-attr-label pricing">💳 Disposição a Pagar</span>
            <span class="persona-attr-desc"><strong>${escapeHtml(p.willingness_to_pay)}</strong></span>
          </div>
          <div class="persona-attribute">
            <span class="persona-attr-label channels">📡 Canais de Aquisição</span>
            <span class="persona-attr-desc">${escapeHtml(p.channels)}</span>
          </div>
        </article>`;
        })
        .join('')}
    </div>
  </section>`;
}

function renderEconomics(eco) {
  if (!eco) return '';
  const money = v => Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  const scenarios = eco.scenarios || [];

  return `<section class="dossier-section" id="sec-economics">
    <div class="section-title-wrap">
      <h2>Modelagem Econômica & Análise de Sensibilidade</h2>
      <p class="dossier-muted">Simulação de viabilidade operacional com ponto de equilíbrio e margens por faixa de matrículas.</p>
    </div>
    
    <div class="economics-summary-strip">
      <div class="eco-strip-item">Ticket Unitário: <strong>${money(eco.ticket)}</strong></div>
      <div class="eco-strip-divider"></div>
      <div class="eco-strip-item">Custos Fixos: <strong>${money(eco.fixed_costs)}</strong></div>
      <div class="eco-strip-divider"></div>
      <div class="eco-strip-item">Custo Variável/Aluno: <strong>${money(eco.variable_cost_per_student)}</strong></div>
      <div class="eco-strip-divider"></div>
      <div class="eco-strip-item">Capacidade Máxima: <strong>${eco.max_capacity} vagas</strong></div>
      <div class="eco-strip-divider"></div>
      <div class="eco-strip-item" style="color:var(--prometeus-status-approved);">Break-even Quórum: <strong>${eco.break_even_students} alunos</strong></div>
    </div>

    ${
      scenarios.length
        ? `<div class="scenarios-grid">
      ${scenarios
        .map(
          sc => `
        <article class="scenario-card ${sc.status === 'highlight' ? 'highlight' : ''}">
          <div class="scenario-card-header">
            <h3>Cenário ${escapeHtml(sc.name)}</h3>
            <span class="scenario-occupancy">${escapeHtml(sc.occupancy)} (${sc.students} vagas)</span>
          </div>
          <div class="scenario-stat-row">
            <span>Receita Bruta:</span>
            <strong>${money(sc.gross_revenue)}</strong>
          </div>
          <div class="scenario-stat-row">
            <span>Custos Totais:</span>
            <span>${money(sc.total_costs)}</span>
          </div>
          <div class="scenario-profit-box">
            <div>
              <div style="font-size:11px;color:var(--prometeus-text-secondary);text-transform:uppercase;">Resultado Líquido</div>
              <div class="scenario-profit-val">${money(sc.net_profit)}</div>
            </div>
            <div class="scenario-margin-badge">Margem ${escapeHtml(sc.margin)}</div>
          </div>
        </article>`
        )
        .join('')}
    </div>`
        : ''
    }
  </section>`;
}

function renderCurriculumModules(modules) {
  if (!modules || !modules.length) return '';
  return `<section class="dossier-section" id="sec-curriculum">
    <div class="section-title-wrap">
      <h2>Matriz Curricular Aplicada & Ementa</h2>
      <p class="dossier-muted">Estrutura modular com ênfase prática, alinhada às Leis Federais 15.040 e 15.484/2024 e jurisprudência superior.</p>
    </div>
    <div class="modules-grid-cards">
      ${modules
        .map(
          m => `
        <article class="module-item-card">
          <div class="module-card-top">
            <span class="module-num-tag">${escapeHtml(m.module)}</span>
            <span class="module-hours-badge">${escapeHtml(m.hours)}</span>
          </div>
          <h3>${escapeHtml(m.title)}</h3>
          <p class="module-focus-text">${escapeHtml(m.focus)}</p>
          <div class="module-practical-deliverable">
            <strong>Oficina Prática / Entregável</strong>
            ${escapeHtml(m.practical_activity)}
          </div>
        </article>`
        )
        .join('')}
    </div>
  </section>`;
}

function renderSWOT(swot) {
  if (!swot) return '';
  const tows = swot.tows_strategies || [];
  return `<section class="dossier-section" id="sec-swot">
    <div class="section-title-wrap">
      <h2>Matriz Estratégica SWOT & Planos de Ação TOWS</h2>
      <p class="dossier-muted">Cruzamento analítico de diferenciais competitivos versus riscos operacionais e de mercado.</p>
    </div>
    
    <div class="swot-matrix-grid">
      <div class="swot-box strengths">
        <div class="swot-box-header">
          <span style="color:var(--prometeus-status-approved);">✦</span>
          <h3>Forças (Strengths)</h3>
        </div>
        <ul class="swot-items-list">
          ${(swot.strengths || []).map(s => `<li>${escapeHtml(s)}</li>`).join('')}
        </ul>
      </div>

      <div class="swot-box opportunities">
        <div class="swot-box-header">
          <span style="color:#38bdf8;">▲</span>
          <h3>Oportunidades (Opportunities)</h3>
        </div>
        <ul class="swot-items-list">
          ${(swot.opportunities || []).map(o => `<li>${escapeHtml(o)}</li>`).join('')}
        </ul>
      </div>

      <div class="swot-box weaknesses">
        <div class="swot-box-header">
          <span style="color:#fbbf24;">■</span>
          <h3>Fraquezas (Weaknesses)</h3>
        </div>
        <ul class="swot-items-list">
          ${(swot.weaknesses || []).map(w => `<li>${escapeHtml(w)}</li>`).join('')}
        </ul>
      </div>

      <div class="swot-box threats">
        <div class="swot-box-header">
          <span style="color:#f87171;">✖</span>
          <h3>Ameaças (Threats)</h3>
        </div>
        <ul class="swot-items-list">
          ${(swot.threats || []).map(t => `<li>${escapeHtml(t)}</li>`).join('')}
        </ul>
      </div>
    </div>

    ${
      tows.length
        ? `<div style="margin-top:24px;">
      <h3 style="font-size:15px;color:var(--prometeus-text-secondary);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:12px;">Estratégias de Ação Cruzadas (Matriz TOWS)</h3>
      <div class="tows-grid">
        ${tows
          .map(
            item => `
          <div class="tows-card">
            <span class="tows-type-tag">${escapeHtml(item.type)}</span>
            <div class="tows-desc">${escapeHtml(item.strategy)}</div>
          </div>`
          )
          .join('')}
      </div>
    </div>`
        : ''
    }
  </section>`;
}

function renderRoadmap(roadmap) {
  if (!roadmap || !roadmap.length) return '';
  return `<section class="dossier-section" id="sec-roadmap">
    <div class="section-title-wrap">
      <h2>Cronograma Tático de Lançamento</h2>
      <p class="dossier-muted">Fases sequenciais com marcos de quórum, ações comerciais e governança operacional.</p>
    </div>
    <div class="roadmap-timeline-grid">
      ${roadmap
        .map(
          phase => `
        <article class="roadmap-phase-card">
          <span class="roadmap-window-pill">${escapeHtml(phase.window)}</span>
          <h3>${escapeHtml(phase.phase)}</h3>
          <ul class="roadmap-actions-list">
            ${(phase.actions || []).map(act => `<li>${escapeHtml(act)}</li>`).join('')}
          </ul>
          <div class="roadmap-footer">
            <div class="roadmap-kpi-badge">Meta: ${escapeHtml(phase.kpi)}</div>
            <div class="roadmap-owner-text">Responsável: ${escapeHtml(phase.owner)}</div>
          </div>
        </article>`
        )
        .join('')}
    </div>
  </section>`;
}

export function renderDossierView(store) {
  const state = store.getState();
  const course = state.courses.find(item => item.id === state.activeCourseId);
  const dossier = state.currentDossier || course?.dossier;

  if (!course || !dossier) {
    return `<div class="prometeus-card">
      <h2>Dossiê indisponível</h2>
      <p>A análise ainda não possui um dossiê validado. Acompanhe o processamento no portfólio.</p>
      <button class="prometeus-btn-secondary" id="btn-back-portfolio">Voltar ao portfólio</button>
    </div>`;
  }

  const pres = dossier.presentation || {};
  const scoring = dossier.scoring || {};
  const claims = Array.isArray(dossier.claims) ? dossier.claims : [];
  const sections = Array.isArray(dossier.sections) ? dossier.sections : [];
  const evidences = Array.isArray(dossier.evidences) ? dossier.evidences : [];
  const highlights = dossier.highlights || pres.highlights || {};
  const pillars = scoring.pillar_scores || {};
  const present = Object.values(pillars).filter(p => p.is_present === true).length;
  const pillarsCount = Object.keys(pillars).length;

  const limitations = Array.isArray(dossier.limitations)
    ? dossier.limitations
    : Array.isArray(pres.limitations)
    ? pres.limitations
    : [];
  const insufficient = scoring.recommendation === 'INSUFFICIENT_EVIDENCE';
  const v2 = scoring.profile_id === 'portfolio-v2' || scoring.gate_details?.profile_id === 'portfolio-v2';

  const groups = new Map();
  evidences.forEach(ev => {
    const key = channelLabel(ev.source_name);
    groups.set(key, [...(groups.get(key) || []), ev]);
  });

  const kpis = pres.kpis || [];
  const personas = pres.personas || [];
  const economics = pres.economics || null;
  const modules = pres.curriculum_modules || [];
  const swot = pres.swot || null;
  const roadmap = pres.tactical_roadmap || [];
  const review = pres.three_fold_review || dossier.three_fold_review;
  const verdict = pres.verdict || {
    status: scoring.recommendation || 'APPROVED',
    badge_label: recommendationLabel(scoring.recommendation),
    summary: dossier.executive_summary
  };

  return `<div class="dossier-page">
    <!-- Barra de Ferramentas Superior -->
    <div class="dossier-toolbar">
      <button class="prometeus-btn-secondary" id="btn-back-portfolio">← Voltar ao Portfólio</button>
      <div style="display:flex;gap:12px;">
        <button class="prometeus-btn-secondary" id="btn-open-evidence-drawer">Inspecionar evidências (${evidences.length})</button>
        <button class="prometeus-btn-primary" id="btn-export-dossier-pdf">Imprimir / salvar PDF</button>
      </div>
    </div>

    <!-- Sub-Navbar de Navegação Rápida -->
    <nav class="dossier-subnav" aria-label="Navegação do Dossiê">
      <a href="#sec-overview" class="active">Visão Geral</a>
      <a href="#sec-kpis">Métricas-Chave</a>
      ${personas.length ? '<a href="#sec-personas">Personas B2B/B2C</a>' : ''}
      ${economics ? '<a href="#sec-economics">Economia & Cenários</a>' : ''}
      ${modules.length ? '<a href="#sec-curriculum">Grade Modular</a>' : ''}
      ${swot ? '<a href="#sec-swot">SWOT & TOWS</a>' : ''}
      ${roadmap.length ? '<a href="#sec-roadmap">Cronograma Tático</a>' : ''}
      <a href="#sec-pillars">Pilares de Viabilidade</a>
      <a href="#sec-homologation">Homologação</a>
      <a href="#sec-evidences">Fontes & Evidências</a>
    </nav>

    <!-- Hero Executivo & Banner de Veredito -->
    <header class="dossier-verdict-banner dossier-heading dossier-hero-card" id="sec-overview">
      <div class="verdict-info">
        <span class="prometeus-pill-badge" data-status="${escapeHtml(verdict.status || scoring.recommendation)}">
          ${escapeHtml(verdict.badge_label || recommendationLabel(scoring.recommendation))}
        </span>
        <h1 class="verdict-course-name" style="margin:14px 0 6px 0;color:#ffffff;line-height:1.2;">
          ${escapeHtml(course.name)}
        </h1>
        <p class="dossier-context">${[course.level, course.modality].filter(Boolean).map(escapeHtml).join(' · ')}</p>
        ${
          insufficient
            ? '<p>A base disponível ainda não sustenta uma recomendação de lançamento. As lacunas abaixo indicam o que precisa ser validado.</p>'
            : '<p>Parecer de apoio à decisão institucional, sujeito às limitações da pesquisa.</p>'
        }
      </div>

      <div class="dossier-verdict-quote">
        <strong>Parecer Executivo do Prometeus:</strong>
        <p style="margin:6px 0 0 0;">${escapeHtml(verdict.summary || dossier.executive_summary)}</p>
      </div>

      <!-- Dashboard de KPIs / Indicadores -->
      <div id="sec-kpis" style="margin-top:24px;">
        ${renderKPIs(kpis, scoring, v2, insufficient, present, pillarsCount)}
      </div>
    </header>

    ${
      scoring.is_experimental !== false
        ? '<p class="dossier-notice">Índice experimental: pesos e limiares sujeitos a calibração. Este resultado não é uma projeção de retorno financeiro.</p>'
        : ''
    }

    <!-- Síntese Executiva Textual com Suporte de Evidências -->
    <section class="dossier-summary" id="sec-summary">
      <h2>Síntese executiva</h2>
      ${paragraphs(dossier.executive_summary)}
      ${inspectionButton(evidenceIds(dossier.executive_summary_claim_ids || pres.executive_summary_claim_ids || [], claims), 'Ver base da síntese')}
    </section>

    <!-- Pontos Fortes e Riscos (Highlights) -->
    <div class="curriculum-gap-grid dossier-diagnosis">
      <section class="gap-column-solutions">
        <h2>Pontos fortes e oportunidades</h2>
        ${claimList(highlights.pros, claims, 'Ainda não há pontos fortes destacados com suporte nesta versão do dossiê.')}
      </section>
      <section class="gap-column-pains">
        <h2>Riscos e lacunas</h2>
        ${claimList(highlights.cons, claims, 'Consulte os pilares e as limitações para identificar o que ainda precisa ser validado.')}
      </section>
    </div>

    <!-- Personas Decisoras (B2B & B2C) -->
    ${renderPersonas(personas)}

    <!-- Modelagem Econômica & Cenários -->
    ${renderEconomics(economics)}

    <!-- Matriz Curricular Modular -->
    ${renderCurriculumModules(modules)}

    <!-- SWOT 2x2 & Matriz TOWS -->
    ${renderSWOT(swot)}

    <!-- Cronograma Tático de Lançamento -->
    ${renderRoadmap(roadmap)}

    <!-- Dimensões Analíticas de Viabilidade (Pilares) -->
    <section class="dossier-section" id="sec-pillars">
      <h2>As dimensões da viabilidade</h2>
      <p class="dossier-muted">Ausência de dados não significa desempenho negativo. Cada dimensão mantém seu peso no índice.</p>
      <div class="dossier-pillars">
        ${Object.entries(PILLAR_LABELS)
          .map(([name]) => pillarCard(name, pillars[name] || {}))
          .join('')}
      </div>
    </section>

    <!-- Composição da Avaliação, IPD e Auditoria de Preço -->
    ${scoreAudit(dossier.analysis_audit || pres.analysis_audit || {}, scoring)}

    <!-- Homologação Tripartite -->
    ${renderThreeFoldReview(review)}

    <!-- Comparação de Ofertas Concorrentes -->
    <section class="dossier-section" id="sec-competitors">
      <h2>Comparação de ofertas</h2>
      ${
        (highlights.competitors || []).length
          ? `<div class="prometeus-table-container">
          <table class="prometeus-table">
            <thead><tr><th scope="col">Instituição e oferta</th><th scope="col">Condições observadas</th></tr></thead>
            <tbody>
              ${highlights.competitors
                .map(
                  row =>
                    `<tr><th scope="row">${escapeHtml(row.label)}</th><td>${claimList(row.claim_ids, claims, 'Sem informação vinculada.')}</td></tr>`
                )
                .join('')}
            </tbody>
          </table>
        </div>`
          : '<p class="dossier-muted">Ainda não há um quadro de ofertas comparáveis nesta versão. Consulte as páginas coletadas sem presumir equivalência de preços ou modalidades.</p>'
      }
    </section>

    <!-- Ementa e Necessidades do Mercado -->
    <section class="dossier-section" id="sec-curriculum-alignment">
      <h2>Ementa e necessidades do mercado</h2>
      ${
        (highlights.curriculum_alignment || []).length
          ? `<div class="prometeus-table-container">
          <table class="prometeus-table">
            <thead><tr><th scope="col">Módulo da ementa</th><th scope="col">Necessidade observada</th><th scope="col">Cobertura e lacunas</th></tr></thead>
            <tbody>
              ${highlights.curriculum_alignment
                .map(
                  row =>
                    `<tr><th scope="row">${escapeHtml(row.module)}</th><td>${claimList(row.need_claim_ids, claims, 'Necessidade sem vínculo.')}</td><td>${claimList(row.coverage_claim_ids, claims, 'Cobertura sem vínculo.')}</td></tr>`
                )
                .join('')}
            </tbody>
          </table>
        </div>`
          : '<p class="dossier-muted">A relação por módulo requer necessidades de mercado e trechos da ementa com suporte. A leitura acadêmica abaixo registra o diagnóstico disponível.</p>'
      }
    </section>

    <!-- Leituras por Área / Diagnósticos Especializados -->
    ${
      sections.length
        ? `<section class="dossier-section" id="sec-area-readings">
      <h2>Leituras por área</h2>
      <div class="business-cards-grid dossier-audiences">
        ${sections
          .map(
            section => `
          <article class="business-card">
            <h3>${escapeHtml(section.title)}</h3>
            ${paragraphs(section.content)}
            <details style="margin-top:12px;"><summary>Afirmações desta leitura</summary>${claimList(section.claim_ids || section.claims, claims, 'Esta seção não possui afirmações vinculadas.')}</details>
            ${inspectionButton(evidenceIds(section.claim_ids || section.claims, claims), 'Inspecionar fontes desta análise')}
          </article>`
          )
          .join('')}
      </div>
    </section>`
        : ''
    }

    <!-- Validações antes do Lançamento -->
    <section class="dossier-section" id="sec-validations">
      <h2>Validações antes do lançamento</h2>
      <p class="dossier-muted">Condições propostas para avaliação da equipe. A conclusão depende de validação institucional.</p>
      ${
        (highlights.validation_criteria || []).length
          ? `<ul class="dossier-validation-list">
          ${highlights.validation_criteria
            .map(
              item => `
            <li>
              <span class="dossier-label">Pendente</span>
              <div>
                <h3>${escapeHtml(item.criterion)}</h3>
                <p>${escapeHtml(item.target)}</p>
                ${inspectionButton(evidenceIds(item.claim_ids, claims))}
              </div>
            </li>`
            )
            .join('')}
        </ul>`
          : '<p>Nenhum checklist foi estruturado nesta versão. Use as lacunas identificadas como pauta para a próxima validação.</p>'
      }
    </section>

    <!-- Próximos Passos Propostos -->
    <section class="dossier-section" id="sec-actions">
      <h2>Próximos passos propostos</h2>
      <div class="dossier-actions">
        ${
          (highlights.action_recommendations || [])
            .map(
              item => `
          <article>
            <div class="dossier-action-meta">
              <span>${escapeHtml(item.area)}</span>
              <span>Prioridade ${{ high: 'alta', medium: 'média', low: 'baixa' }[item.priority] || 'não informada'}</span>
            </div>
            <p>${escapeHtml(item.action)}</p>
            ${inspectionButton(evidenceIds(item.claim_ids, claims))}
          </article>`
            )
            .join('') || '<p>As recomendações desta versão estão nas leituras por área.</p>'
        }
      </div>
    </section>

    <!-- Limites desta Pesquisa -->
    ${
      limitations.length
        ? `<section class="dossier-section" id="sec-limitations">
      <h2>Limites desta pesquisa</h2>
      <ul>${limitations.map(text => `<li>${escapeHtml(text)}</li>`).join('')}</ul>
    </section>`
        : ''
    }

    <!-- Fontes Consultadas e Evidências -->
    <section class="dossier-section" id="sec-evidences">
      <div class="section-title-wrap">
        <h2>Fontes consultadas</h2>
        <p class="dossier-muted">${evidences.length} evidências persistidas. Itens do mesmo site ou canal não representam fontes independentes.</p>
      </div>
      <div class="dossier-sources" style="margin-top:16px;">
        ${
          [...groups]
            .map(
              ([channel, items]) => `
          <section>
            <h3>${escapeHtml(channel)} <span>(${items.length})</span></h3>
            <ul>
              ${items
                .map(evidence => {
                  const url = safeUrl(evidence.source_url);
                  const qualification = evidence.sanitized_data?._qualification;
                  return `<li>
                    ${url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(evidence.title || channel)}</a>` : escapeHtml(evidence.title || channel)}
                    ${
                      qualification
                        ? `<span class="dossier-label">${qualification.accepted ? 'Qualificada' : qualification.context_only ? 'Contexto preservado' : 'Excluída do cálculo'}</span>
                           <p class="dossier-muted">${escapeHtml(qualification.reason || '')}</p>
                           ${qualification.use_for?.length ? `<small>Uso: ${qualification.use_for.map(purpose => escapeHtml(({ employability: 'vagas', curriculum: 'necessidades curriculares', pricing: 'referência de preço', competitive_offers: 'ofertas comparáveis', paid_competition: 'concorrência em mídia', audience_needs: 'necessidades do público', institution_context: 'contexto da própria instituição', search_interest: 'interesse de busca' })[purpose] || purpose)).join(', ')}</small>` : ''}`
                        : ''
                    }
                    ${inspectionButton([evidence.id], 'Inspecionar')}
                  </li>`;
                })
                .join('')}
            </ul>
          </section>`
            )
            .join('') || '<p class="dossier-muted">Não há fontes externas anexadas. Consulte o estado das coletas.</p>'
        }
      </div>
    </section>

    <!-- Afirmações e Suporte Analítico -->
    <details class="dossier-claims" id="sec-claims">
      <summary>Afirmações e suporte analítico</summary>
      ${claims
        .map(
          claim => `
        <article>
          <p>${escapeHtml(claim.statement)}</p>
          <span class="dossier-label">${{ observed: 'Observado', suggestive: 'Indício', hypothesis: 'Hipótese' }[claim.support_level] || 'Suporte declarado'}</span>
          ${inspectionButton(claim.evidence_ids)}
        </article>`
        )
        .join('')}
    </details>
  </div>`;
}

export function bindDossierEvents(store, container) {
  container.querySelector('#btn-back-portfolio')?.addEventListener('click', () => {
    store.setView('portfolio');
  });

  container.querySelector('#btn-export-dossier-pdf')?.addEventListener('click', () => {
    window.print();
  });

  container.querySelector('#btn-open-evidence-drawer')?.addEventListener('click', () => {
    const state = store.getState();
    const course = state.courses.find(item => item.id === state.activeCourseId);
    const dossier = state.currentDossier || course?.dossier;
    const allEvidenceIds = (dossier?.evidences || []).map(e => e.id);
    document.dispatchEvent(
      new CustomEvent('prometeus:inspect-evidence', {
        detail: { ids: allEvidenceIds, trigger: container.querySelector('#btn-open-evidence-drawer') }
      })
    );
  });

  container.querySelectorAll('[data-evidence-ids]').forEach(button => {
    button.addEventListener('click', () => {
      document.dispatchEvent(
        new CustomEvent('prometeus:inspect-evidence', {
          detail: { ids: JSON.parse(button.dataset.evidenceIds), trigger: button }
        })
      );
    });
  });

  container.querySelectorAll('.dossier-subnav a').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      const targetId = link.getAttribute('href');
      const targetEl = container.querySelector(targetId);
      if (targetEl) {
        targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        container.querySelectorAll('.dossier-subnav a').forEach(a => a.classList.remove('active'));
        link.classList.add('active');
      }
    });
  });
}
