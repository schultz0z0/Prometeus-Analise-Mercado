/**
 * VIEW: Minhas Análises & Portfólio de Cursos
 */

export function renderPortfolioView(store) {
  const state = store.getState();
  const courses = state.courses;
  const approvedCount = courses.filter(c => c.recommendation === 'APPROVED' || c.recommendation === 'APPROVED_WITH_ADJUSTMENTS').length;
  const avgScore = (courses.reduce((acc, c) => acc + (c.viability_score || 0), 0) / (courses.length || 1)).toFixed(1);

  return `
    <div class="view-header">
      <div class="view-title-row">
        <div>
          <h1 class="view-title">Portfólio de Inteligência de Cursos</h1>
          <p class="view-subtitle">Acompanhe os diagnósticos de viabilidade de mercado, quórum e concorrência realizados para a sua instituição.</p>
        </div>
        <button class="prometeus-btn-primary" id="btn-goto-validate" style="font-size:14px; padding:12px 22px;">
          <span>✦ Validar Novo Curso</span>
        </button>
      </div>
    </div>

    <!-- Cards de Resumo Executivo -->
    <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:20px; margin-bottom:32px;">
      <div class="prometeus-card">
        <div style="font-size:12px; text-transform:uppercase; color:var(--prometeus-text-muted); font-weight:600; letter-spacing:0.05em;">Total de Diagnósticos</div>
        <div class="metric-big-highlight">${courses.length} cursos</div>
        <div style="font-size:12px; color:var(--prometeus-text-secondary);">Análises salvas no banco</div>
      </div>

      <div class="prometeus-card">
        <div style="font-size:12px; text-transform:uppercase; color:var(--prometeus-text-muted); font-weight:600; letter-spacing:0.05em;">Cursos Aprovados</div>
        <div class="metric-big-highlight" style="color:var(--prometeus-status-approved);">${approvedCount}</div>
        <div style="font-size:12px; color:var(--prometeus-text-secondary);">${((approvedCount / (courses.length || 1)) * 100).toFixed(0)}% de taxa de viabilidade</div>
      </div>

      <div class="prometeus-card">
        <div style="font-size:12px; text-transform:uppercase; color:var(--prometeus-text-muted); font-weight:600; letter-spacing:0.05em;">Média de Viability Score</div>
        <div class="metric-big-highlight" style="color:var(--prometeus-accent-ice);">${avgScore} <span style="font-size:16px; color:var(--prometeus-text-muted);">/100</span></div>
        <div style="font-size:12px; color:var(--prometeus-text-secondary);">Índice ponderado dos 6 pilares</div>
      </div>

      <div class="prometeus-card">
        <div style="font-size:12px; text-transform:uppercase; color:var(--prometeus-text-muted); font-weight:600; letter-spacing:0.05em;">Conector CRM da IES</div>
        <div class="metric-big-highlight" style="font-size:20px; color:#38BDF8; margin-top:14px;">● Conectado</div>
        <div style="font-size:12px; color:var(--prometeus-text-secondary);">${state.settings[state.currentTenantId]?.crm_last_sync || "Sincronizado"}</div>
      </div>
    </div>

    <!-- Tabela de Cursos Analisados -->
    <div class="prometeus-card" style="padding:0; overflow:hidden;">
      <div style="padding:20px 24px; border-bottom:1px solid var(--prometeus-border-subtle); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
        <div style="font-weight:600; font-size:16px; color:#ffffff;">Diagnósticos e Vereditos Recentes</div>
        <div style="display:flex; gap:10px;">
          <input type="text" id="input-search-courses" class="form-input" placeholder="Filtrar por nome ou área..." style="width:240px; padding:6px 12px; font-size:13px;">
        </div>
      </div>

      <div class="prometeus-table-container" style="border:none; border-radius:0;">
        <table class="prometeus-table" id="table-courses">
          <thead>
            <tr>
              <th scope="col">Curso & Grande Área</th>
              <th scope="col">Modalidade</th>
              <th scope="col">Ticket Pretendido</th>
              <th scope="col">Viability Score</th>
              <th scope="col">Veredito da Oferta</th>
              <th scope="col">Demanda de Mercado</th>
              <th scope="col" style="text-align:right;">Ações</th>
            </tr>
          </thead>
          <tbody>
            ${courses.map(course => `
              <tr class="cursor-pointer course-row" data-id="${course.id}">
                <td>
                  <strong style="color:#ffffff; font-size:14px; display:block;">${course.name}</strong>
                  <span style="font-size:12px; color:var(--prometeus-text-muted);">${course.area} • ${course.level}</span>
                </td>
                <td>
                  <span style="font-size:13px; color:var(--prometeus-text-secondary);">${course.modality}</span>
                </td>
                <td class="prometeus-stat-mono" style="font-weight:600; color:#ffffff;">
                  R$ ${course.ticket.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}<span style="font-size:11px; color:var(--prometeus-text-muted);">/mês</span>
                </td>
                <td>
                  <div style="display:flex; align-items:center; gap:8px;">
                    <div style="width:36px; height:36px; border-radius:50%; border:2px solid ${getScoreColor(course.viability_score)}; display:flex; align-items:center; justify-content:center; font-family:var(--prometeus-font-mono); font-size:12px; font-weight:700; color:#ffffff;">
                      ${course.viability_score.toFixed(0)}
                    </div>
                  </div>
                </td>
                <td>
                  <span class="prometeus-pill-badge" data-status="${course.recommendation}">
                    ● ${getRecommendationLabel(course.recommendation)}
                  </span>
                </td>
                <td style="font-size:13px; color:var(--prometeus-text-secondary);">
                  ${course.demand_level}
                </td>
                <td style="text-align:right;">
                  <button class="prometeus-btn-primary btn-open-dossier" data-id="${course.id}" style="padding:6px 12px; font-size:12px; min-height:30px;">
                    Ver Dossiê →
                  </button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

export function bindPortfolioEvents(store, container) {
  const gotoValidateBtn = container.querySelector('#btn-goto-validate');
  if (gotoValidateBtn) {
    gotoValidateBtn.addEventListener('click', () => {
      store.setView('validate');
    });
  }

  const dossierBtns = container.querySelectorAll('.btn-open-dossier');
  dossierBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const courseId = btn.getAttribute('data-id');
      store.setView('dossier', { courseId });
    });
  });

  const rows = container.querySelectorAll('.course-row');
  rows.forEach(row => {
    row.addEventListener('click', () => {
      const courseId = row.getAttribute('data-id');
      store.setView('dossier', { courseId });
    });
  });

  const searchInput = container.querySelector('#input-search-courses');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const term = e.target.value.toLowerCase();
      rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(term) ? '' : 'none';
      });
    });
  }
}

function getScoreColor(score) {
  if (score >= 80) return '#34D399';
  if (score >= 60) return '#FBBF24';
  return '#EF4444';
}

function getRecommendationLabel(rec) {
  switch (rec) {
    case 'APPROVED': return 'APROVADO';
    case 'APPROVED_WITH_ADJUSTMENTS': return 'APROVADO C/ AJUSTES';
    case 'HIGH_RISK': return 'ALTO RISCO';
    default: return rec;
  }
}
