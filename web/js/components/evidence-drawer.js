/** Gaveta de auditoria com navegação por origem e retorno de foco. */
import { escapeHtml, safeUrl, channelLabel } from '../dossier-format.js';
let bindings;

function renderEvidenceDetail(evidence) {
  if (!evidence) return '<p>Nenhuma evidência disponível.</p>';
  return `<div class="prometeus-card">
    <span class="prometeus-stat-mono">${escapeHtml(evidence.id)}</span>
    <h3>${escapeHtml(evidence.title || evidence.source_name)}</h3>
    <pre class="dossier-evidence-payload">${escapeHtml(JSON.stringify(evidence.sanitized_data || {}, null, 2))}</pre>
    ${safeUrl(evidence.source_url) ? `<a href="${escapeHtml(safeUrl(evidence.source_url))}" target="_blank" rel="noopener noreferrer">Abrir fonte original</a>` : '<p>URL original indisponível.</p>'}
    <div style="margin-top:12px;font-size:12px;color:var(--prometeus-text-muted);">
      Coletor: ${escapeHtml(evidence.collector)} · Coletado em: ${escapeHtml(evidence.collected_at)} · Qualidade: ${escapeHtml(evidence.quality_score)}
    </div>
  </div>`;
}

export function renderEvidenceDrawer(store) {
  const dossier = store.getState().currentDossier || {};
  const evidences = dossier.evidences || [];
  return `<div class="drawer-backdrop" id="evidence-drawer-backdrop" aria-hidden="true"></div>
    <aside class="drawer-container" id="evidence-drawer-container" role="dialog" aria-labelledby="drawer-title" aria-modal="true" aria-hidden="true" inert>
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px;">
        <div><span class="prometeus-pill-badge">AUDITORIA</span><h2 id="drawer-title">Evidências persistidas</h2></div>
        <button id="btn-close-drawer" class="prometeus-btn-secondary" aria-label="Fechar">×</button>
      </div>
      <p style="color:var(--prometeus-text-secondary);">Conteúdo higienizado, proveniência e URL registrados pelo backend. A interface não cria fontes substitutas.</p>
      <p id="drawer-selection-note" role="status"></p>
      <div id="drawer-source-tabs" class="dossier-drawer-tabs"></div>
      <div id="drawer-evidence-content">${renderEvidenceDetail(evidences[0])}</div>
      <details class="dossier-audit-details"><summary>Metadados da análise</summary><dl><dt>Análise</dt><dd>${escapeHtml(dossier.analysis_id)}</dd><dt>Estado de verificação</dt><dd>${escapeHtml(dossier.status)}</dd><dt>Modelo</dt><dd>${escapeHtml(dossier.model_name)}</dd><dt>Versão do prompt</dt><dd>${escapeHtml(dossier.prompt_version)}</dd><dt>Hash dos fatos</dt><dd>${escapeHtml(dossier.facts_hash)}</dd></dl></details>
      ${evidences.length ? '<button class="prometeus-btn-primary" id="btn-export-json-evidence" style="margin-top:20px;">Exportar evidências (JSON)</button>' : ''}
    </aside>`;
}

export function bindEvidenceDrawerEvents(store, container) {
  bindings?.abort();
  bindings = new AbortController();
  const { signal } = bindings;
  const backdrop = container.querySelector('#evidence-drawer-backdrop');
  const drawer = container.querySelector('#evidence-drawer-container');
  let trigger = null;
  const evidences = store.getState().currentDossier?.evidences || [];
  const close = () => {
    backdrop?.classList.remove('active'); drawer?.classList.remove('active');
    drawer?.setAttribute('aria-hidden', 'true');
    drawer?.setAttribute('inert', '');
    if (trigger?.isConnected) trigger.focus();
  };
  const open = (ids, origin) => {
    if (!drawer) return;
    trigger = origin || document.activeElement;
    const selected = ids ? evidences.filter(evidence => ids.includes(evidence.id)) : evidences;
    const tabs = container.querySelector('#drawer-source-tabs');
    if (tabs) {
      tabs.innerHTML = selected.map((evidence, index) => `<button type="button" class="drawer-tab-btn prometeus-btn-secondary" data-idx="${index}" aria-pressed="${index === 0}">${escapeHtml(channelLabel(evidence.source_name))} ${index + 1}</button>`).join('');
      tabs.querySelectorAll('button').forEach(button => button.addEventListener('click', () => {
        container.querySelector('#drawer-evidence-content').innerHTML = renderEvidenceDetail(selected[Number(button.dataset.idx)]);
        tabs.querySelectorAll('button').forEach(tab => tab.setAttribute('aria-pressed', String(tab === button)));
      }));
    }
    const content = container.querySelector('#drawer-evidence-content');
    if (content) content.innerHTML = renderEvidenceDetail(selected[0]);
    const note = container.querySelector('#drawer-selection-note');
    if (note) note.textContent = ids ? `${selected.length} evidências de mercado vinculadas. Referências de scoring, histórico e julgamentos constam no registro analítico.` : `${evidences.length} evidências persistidas nesta análise.`;
    backdrop?.classList.add('active'); drawer?.classList.add('active');
    drawer.setAttribute('aria-hidden', 'false');
    drawer.removeAttribute('inert');
    container.querySelector('#btn-close-drawer')?.focus();
  };
  document.querySelector('#btn-open-evidence-drawer')?.addEventListener('click', event => open(null, event.currentTarget));
  document.addEventListener('prometeus:inspect-evidence', event => open(event.detail.ids, event.detail.trigger), { signal });
  container.querySelector('#btn-close-drawer')?.addEventListener('click', close);
  backdrop?.addEventListener('click', close);
  document.addEventListener('keydown', event => {
    if (!drawer?.classList.contains('active')) return;
    if (event.key === 'Escape') { event.preventDefault(); close(); }
    if (event.key === 'Tab') {
      const targets = [...drawer.querySelectorAll('button:not([disabled]), a[href], summary, [tabindex="0"]')].filter(element => element.getClientRects().length);
      const first = targets[0], last = targets[targets.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }
  }, { signal });
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
