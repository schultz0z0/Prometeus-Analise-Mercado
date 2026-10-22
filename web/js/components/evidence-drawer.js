/**
 * COMPONENT: Evidence Drawer (Off-Canvas de Auditoria e Integridade Forense)
 */

export function renderEvidenceDrawer(store) {
  const state = store.getState();
  const dossier = state.currentDossier;

  return `
    <div class="drawer-backdrop" id="evidence-drawer-backdrop" aria-hidden="true"></div>
    <aside class="drawer-container" id="evidence-drawer-container" role="dialog" aria-labelledby="drawer-title" aria-modal="true" aria-hidden="true">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:20px; padding-bottom:16px; border-bottom:1px solid var(--prometeus-border-subtle);">
        <div>
          <span class="prometeus-pill-badge" style="background:rgba(6,82,197,0.2); color:#8DB5FF; border-color:rgba(141,181,255,0.4);">
            AUDITORIA & RASTREABILIDADE (UC-04)
          </span>
          <h2 id="drawer-title" style="font-size:20px; font-weight:700; color:#ffffff; margin:8px 0 0 0;">
            Cofre de Evidências Auditáveis
          </h2>
        </div>
        <button id="btn-close-drawer" class="prometeus-btn-secondary" style="padding:6px 12px; min-height:32px; font-size:14px;" aria-label="Fechar gaveta">
          ✕
        </button>
      </div>

      <div style="font-size:13px; color:var(--prometeus-text-secondary); margin-bottom:18px;">
        Nenhum número ou parecer da Prometeus é opaco. Cada dado gerado possui registro bruto, data de captura e hash criptográfico de integridade:
      </div>

      <!-- Abas de Evidência -->
      <div style="display:flex; gap:8px; margin-bottom:16px; overflow-x:auto;" id="drawer-tab-list">
        ${dossier.evidences.map((ev, idx) => `
          <button class="drawer-tab-btn ${idx === 0 ? 'active' : ''}" data-idx="${idx}" style="padding:6px 12px; border-radius:var(--prometeus-radius-sm); font-size:12px; font-weight:500; cursor:pointer; background:${idx === 0 ? 'rgba(6,82,197,0.2)' : 'rgba(255,255,255,0.04)'}; border:1px solid ${idx === 0 ? 'var(--prometeus-border-focus)' : 'var(--prometeus-border-subtle)'}; color:${idx === 0 ? '#ffffff' : 'var(--prometeus-text-secondary)'}; white-space:nowrap;">
            ${ev.source.split('—')[0]}
          </button>
        `).join('')}
      </div>

      <!-- Conteúdo da Evidência Ativa -->
      <div id="drawer-evidence-content">
        ${renderEvidenceDetail(dossier.evidences[0])}
      </div>

      <div style="margin-top:auto; padding-top:24px; border-top:1px solid var(--prometeus-border-subtle);">
        <button class="prometeus-btn-primary" style="width:100%;" id="btn-export-json-evidence">
          Exportar Pacote Criptográfico de Evidências (JSON)
        </button>
      </div>
    </aside>
  `;
}

function renderEvidenceDetail(ev) {
  if (!ev) return '';
  return `
    <div style="background:rgba(10,15,28,0.8); border:1px solid var(--prometeus-border-subtle); border-radius:var(--prometeus-radius-md); padding:16px; margin-bottom:18px;">
      <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
        <span class="prometeus-stat-mono" style="font-size:12px; font-weight:700; color:var(--prometeus-accent-ice);">${ev.id}</span>
        <span class="prometeus-pill-badge" data-status="APPROVED">INTEGRIDADE VERIFICADA</span>
      </div>
      <strong style="color:#ffffff; font-size:14px; display:block; margin-bottom:6px;">${ev.source}</strong>
      <p style="font-size:13px; color:var(--prometeus-text-secondary); line-height:1.6; margin:0;">
        "${ev.snippet}"
      </p>
    </div>

    <div style="font-family:var(--prometeus-font-mono); font-size:12px; color:var(--prometeus-text-muted); display:flex; flex-direction:column; gap:8px;">
      <div>
        <strong style="color:var(--prometeus-text-secondary);">URL Canônica:</strong><br>
        <a href="${ev.url}" target="_blank" rel="noopener" style="color:var(--prometeus-accent-ice); word-break:break-all;">${ev.url}</a>
      </div>
      <div>
        <strong style="color:var(--prometeus-text-secondary);">Data/Hora de Coleta:</strong><br>
        <span style="color:#ffffff;">${ev.timestamp}</span>
      </div>
      <div>
        <strong style="color:var(--prometeus-text-secondary);">Hash de Integridade (SHA-256):</strong><br>
        <span style="color:#34D399; word-break:break-all;">${ev.sha256}</span>
      </div>
      <div>
        <strong style="color:var(--prometeus-text-secondary);">Tratamento de Dados:</strong><br>
        <span>Higienizado contra injeções de prompt e normalizado via JEV Schema.</span>
      </div>
    </div>
  `;
}

export function bindEvidenceDrawerEvents(store, container) {
  const backdrop = container.querySelector('#evidence-drawer-backdrop');
  const drawer = container.querySelector('#evidence-drawer-container');
  const closeBtn = container.querySelector('#btn-close-drawer');
  const contentContainer = container.querySelector('#drawer-evidence-content');
  const state = store.getState();
  const dossier = state.currentDossier;

  function closeDrawer() {
    if (!backdrop || !drawer) return;
    backdrop.classList.remove('active');
    drawer.classList.remove('active');
    backdrop.setAttribute('aria-hidden', 'true');
    drawer.setAttribute('aria-hidden', 'true');
  }

  function openDrawer() {
    if (!backdrop || !drawer) return;
    backdrop.classList.add('active');
    drawer.classList.add('active');
    backdrop.setAttribute('aria-hidden', 'false');
    drawer.setAttribute('aria-hidden', 'false');
    closeBtn.focus();
  }

  // Escuta botões globais para abrir o drawer
  document.addEventListener('click', (e) => {
    if (e.target && e.target.closest('#btn-open-evidence-drawer')) {
      openDrawer();
    }
  });

  if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
  if (backdrop) backdrop.addEventListener('click', closeDrawer);

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && drawer && drawer.classList.contains('active')) {
      closeDrawer();
    }
  });

  // Alternância de abas na gaveta
  const tabBtns = container.querySelectorAll('.drawer-tab-btn');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => {
        b.style.background = 'rgba(255,255,255,0.04)';
        b.style.borderColor = 'var(--prometeus-border-subtle)';
        b.style.color = 'var(--prometeus-text-secondary)';
      });
      btn.style.background = 'rgba(6,82,197,0.2)';
      btn.style.borderColor = 'var(--prometeus-border-focus)';
      btn.style.color = '#ffffff';

      const idx = parseInt(btn.getAttribute('data-idx'));
      if (contentContainer && dossier.evidences[idx]) {
        contentContainer.innerHTML = renderEvidenceDetail(dossier.evidences[idx]);
      }
    });
  });

  const exportBtn = container.querySelector('#btn-export-json-evidence');
  if (exportBtn) {
    exportBtn.addEventListener('click', () => {
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(dossier.evidences, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", `evidencias_${dossier.course_id}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    });
  }
}
