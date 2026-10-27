/** Gaveta de evidências retornadas e persistidas pelo backend. */

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#039;');
}

function renderEvidenceDetail(evidence) {
  if (!evidence) return '<p>Nenhuma evidência disponível.</p>';
  return `<div class="prometeus-card">
    <span class="prometeus-stat-mono">${escapeHtml(evidence.id)}</span>
    <h3>${escapeHtml(evidence.title || evidence.source_name)}</h3>
    <p>${escapeHtml(JSON.stringify(evidence.sanitized_data || {}))}</p>
    <a href="${escapeHtml(evidence.source_url)}" target="_blank" rel="noopener noreferrer">Abrir fonte original</a>
    <div style="margin-top:12px;font-size:12px;color:var(--prometeus-text-muted);">
      Coletor: ${escapeHtml(evidence.collector)} · Coletado em: ${escapeHtml(evidence.collected_at)} · Qualidade: ${escapeHtml(evidence.quality_score)}
    </div>
  </div>`;
}

export function renderEvidenceDrawer(store) {
  const evidences = store.getState().currentDossier?.evidences || [];
  return `<div class="drawer-backdrop" id="evidence-drawer-backdrop" aria-hidden="true"></div>
    <aside class="drawer-container" id="evidence-drawer-container" role="dialog" aria-labelledby="drawer-title" aria-modal="true" aria-hidden="true">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px;">
        <div><span class="prometeus-pill-badge">AUDITORIA</span><h2 id="drawer-title">Evidências persistidas</h2></div>
        <button id="btn-close-drawer" class="prometeus-btn-secondary" aria-label="Fechar">×</button>
      </div>
      <p style="color:var(--prometeus-text-secondary);">Conteúdo higienizado, proveniência e URL registrados pelo backend. A interface não cria fontes substitutas.</p>
      <div style="display:flex;gap:8px;overflow-x:auto;margin-bottom:16px;">
        ${evidences.map((evidence, index) => `<button class="drawer-tab-btn prometeus-btn-secondary" data-idx="${index}">${escapeHtml(evidence.source_name)}</button>`).join('')}
      </div>
      <div id="drawer-evidence-content">${renderEvidenceDetail(evidences[0])}</div>
      ${evidences.length ? '<button class="prometeus-btn-primary" id="btn-export-json-evidence" style="margin-top:20px;">Exportar evidências (JSON)</button>' : ''}
    </aside>`;
}

export function bindEvidenceDrawerEvents(store, container) {
  const backdrop = container.querySelector('#evidence-drawer-backdrop');
  const drawer = container.querySelector('#evidence-drawer-container');
  const close = () => { backdrop?.classList.remove('active'); drawer?.classList.remove('active'); };
  document.querySelector('#btn-open-evidence-drawer')?.addEventListener('click', () => {
    backdrop?.classList.add('active'); drawer?.classList.add('active');
  });
  container.querySelector('#btn-close-drawer')?.addEventListener('click', close);
  backdrop?.addEventListener('click', close);

  const evidences = store.getState().currentDossier?.evidences || [];
  container.querySelectorAll('.drawer-tab-btn').forEach(button => {
    button.addEventListener('click', () => {
      const target = container.querySelector('#drawer-evidence-content');
      if (target) target.innerHTML = renderEvidenceDetail(evidences[Number(button.dataset.idx)]);
    });
  });
  container.querySelector('#btn-export-json-evidence')?.addEventListener('click', () => {
    const blob = new Blob([JSON.stringify(evidences, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `evidencias_${store.getState().activeCourseId}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  });
}
