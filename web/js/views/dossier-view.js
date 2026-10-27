/** Dossiê verificado, renderizado sem estimativas criadas no navegador. */

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#039;');
}

function displayNumber(value, digits = 1) {
  return Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : 'não disponível';
}

function recommendationLabel(value) {
  return ({
    APPROVED: 'APROVADO',
    APPROVED_WITH_ADJUSTMENTS: 'APROVADO COM AJUSTES',
    HIGH_RISK: 'ALTO RISCO',
    REQUIRES_HUMAN_REVIEW: 'REVISÃO HUMANA'
  })[value] || value || 'SEM RECOMENDAÇÃO';
}

export function renderDossierView(store) {
  const state = store.getState();
  const course = state.courses.find(item => item.id === state.activeCourseId);
  const dossier = state.currentDossier || course?.dossier;
  if (!course || !dossier) {
    return `<div class="prometeus-card"><h2>Dossiê indisponível</h2><p>Nenhum dossiê verificado foi carregado. A interface não cria um resultado substituto.</p><button class="prometeus-btn-secondary" id="btn-back-portfolio">← Voltar</button></div>`;
  }

  const scoring = dossier.scoring || {};
  const pillars = Object.entries(scoring.pillar_scores || {});
  const sections = Array.isArray(dossier.sections) ? dossier.sections : [];
  const claims = Array.isArray(dossier.claims) ? dossier.claims : [];
  const evidences = Array.isArray(dossier.evidences) ? dossier.evidences : [];

  return `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;gap:12px;flex-wrap:wrap;">
      <button class="prometeus-btn-secondary" id="btn-back-portfolio">← Voltar ao portfólio</button>
      <div style="display:flex;gap:10px;">
        <button class="prometeus-btn-secondary" id="btn-open-evidence-drawer">Inspecionar evidências</button>
        <button class="prometeus-btn-primary" id="btn-export-dossier-pdf">Imprimir / salvar PDF</button>
      </div>
    </div>

    <div class="dossier-verdict-banner">
      <div class="verdict-info">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
          <span class="prometeus-pill-badge" data-status="${escapeHtml(scoring.recommendation)}">● ${escapeHtml(recommendationLabel(scoring.recommendation))}</span>
          <span class="prometeus-pill-badge" data-status="${escapeHtml(dossier.status)}">${escapeHtml(dossier.status)}</span>
          <span class="prometeus-stat-mono">${escapeHtml(course.id)}</span>
        </div>
        <h1 class="verdict-course-name">${escapeHtml(course.name)}</h1>
        <div class="verdict-meta">
          ${course.level ? `<span>Nível: <strong>${escapeHtml(course.level)}</strong></span>` : ''}
          ${course.modality ? `<span>Modalidade: <strong>${escapeHtml(course.modality)}</strong></span>` : ''}
          ${course.ticket !== null ? `<span>Preço informado: <strong>R$ ${Number(course.ticket).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</strong></span>` : ''}
        </div>
      </div>
      <div style="text-align:right;">
        <div style="font-size:12px;text-transform:uppercase;color:var(--prometeus-text-muted);">Viability Score</div>
        <div class="prometeus-stat-mono" style="font-size:44px;font-weight:700;color:#fff;">${displayNumber(scoring.viability_score)} <small>/100</small></div>
        <div style="font-size:12px;color:var(--prometeus-text-secondary);">Cobertura: ${displayNumber(Number(scoring.coverage_score) * 100, 0)}% · Confiança: ${displayNumber(Number(scoring.confidence_score) * 100, 0)}%</div>
      </div>
    </div>

    <div class="prometeus-card" style="margin:24px 0;">
      <h2 style="font-size:17px;color:#fff;">Síntese executiva</h2>
      <p style="line-height:1.7;color:var(--prometeus-text-secondary);">${escapeHtml(dossier.executive_summary)}</p>
      <div class="prometeus-stat-mono" style="font-size:11px;color:var(--prometeus-text-muted);">Modelo: ${escapeHtml(dossier.model_name)} · Prompt: ${escapeHtml(dossier.prompt_version)} · Facts hash: ${escapeHtml(dossier.facts_hash)}</div>
    </div>

    <div class="prometeus-card" style="margin-bottom:24px;">
      <h2 style="font-size:17px;color:#fff;">Pilares calculados a partir das evidências observadas</h2>
      ${pillars.length ? `<div class="prometeus-table-container"><table class="prometeus-table">
        <thead><tr><th>Pilar</th><th>Score</th><th>Confiança</th><th>Evidências</th></tr></thead>
        <tbody>${pillars.map(([name, pillar]) => `<tr>
          <td>${escapeHtml(name)}</td>
          <td>${displayNumber(pillar.raw_score)}</td>
          <td>${displayNumber(Number(pillar.confidence) * 100, 0)}%</td>
          <td>${(pillar.evidence_ids || []).map(escapeHtml).join(', ') || 'não informada'}</td>
        </tr>`).join('')}</tbody>
      </table></div>` : '<p>Nenhum pilar retornado.</p>'}
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px;margin-bottom:24px;">
      ${sections.map(section => `<section class="prometeus-card">
        <h2 style="font-size:16px;color:#fff;">${escapeHtml(section.title)}</h2>
        <p style="line-height:1.7;color:var(--prometeus-text-secondary);">${escapeHtml(section.content)}</p>
        <small>Evidências: ${(section.evidence_ids || []).map(escapeHtml).join(', ') || 'não informadas'}</small>
      </section>`).join('') || '<div class="prometeus-card">Nenhuma seção analítica retornada.</div>'}
    </div>

    <div class="prometeus-card" style="margin-bottom:24px;">
      <h2 style="font-size:17px;color:#fff;">Afirmações verificadas</h2>
      ${claims.length ? claims.map(claim => `<div style="padding:12px 0;border-bottom:1px solid var(--prometeus-border-subtle);">
        <strong>${escapeHtml(claim.text)}</strong><br>
        <small>Status: ${escapeHtml(claim.verification_status)} · Evidências: ${(claim.evidence_ids || []).map(escapeHtml).join(', ') || 'nenhuma'}</small>
      </div>`).join('') : '<p>Nenhuma afirmação retornada.</p>'}
    </div>

    <div class="prometeus-card">
      <h2 style="font-size:17px;color:#fff;">Fontes coletadas (${evidences.length})</h2>
      ${evidences.length ? evidences.map(evidence => `<div style="padding:10px 0;border-bottom:1px solid var(--prometeus-border-subtle);">
        <a href="${escapeHtml(evidence.source_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(evidence.title || evidence.source_name)}</a>
        <div><small>${escapeHtml(evidence.collector)} · qualidade ${displayNumber(evidence.quality_score, 2)} · US$ ${displayNumber(evidence.cost_usd, 4)}</small></div>
      </div>`).join('') : '<p>Nenhuma evidência anexada.</p>'}
    </div>`;
}

export function bindDossierEvents(store, container) {
  container.querySelector('#btn-back-portfolio')?.addEventListener('click', () => store.setView('portfolio'));
  container.querySelector('#btn-export-dossier-pdf')?.addEventListener('click', () => window.print());
}
