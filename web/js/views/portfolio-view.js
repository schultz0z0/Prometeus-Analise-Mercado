/**
 * VIEW: Minhas Análises & Portfólio de Cursos (com Base Histórica da ENS)
 */
import { safeUrl, escapeHtml } from '../dossier-format.js';

function getTierBadge(tier) {
  switch (tier) {
    case 'SUCESSO':
    case 'BEM_SUCEDIDO':
      return `<span class="prometeus-pill-badge" style="background:rgba(16,185,129,0.15); color:#34d399; border:1px solid rgba(16,185,129,0.3);">● SUCESSO CONSOLIDADO</span>`;
    case 'MEDIANO':
      return `<span class="prometeus-pill-badge" style="background:rgba(245,158,11,0.15); color:#fbbf24; border:1px solid rgba(245,158,11,0.3);">● MEDIANO (NO LIMITE)</span>`;
    case 'FRACO':
      return `<span class="prometeus-pill-badge" style="background:rgba(249,115,22,0.15); color:#fb923c; border:1px solid rgba(249,115,22,0.3);">● FRACO (EM DECLÍNIO)</span>`;
    case 'CANCELADO_POR_QUORUM':
      return `<span class="prometeus-pill-badge" style="background:rgba(239,68,68,0.15); color:#f87171; border:1px solid rgba(239,68,68,0.3);">✕ CANCELADO (QUÓRUM)</span>`;
    default:
      return `<span class="prometeus-pill-badge">● HISTÓRICO</span>`;
  }
}

function getRecommendationLabel(rec) {
  switch (rec) {
    case 'APPROVED': return 'Viável / Recomendado';
    case 'APPROVED_WITH_ADJUSTMENTS': return 'Ajuste de Ementa';
    case 'HIGH_RISK': return 'Alto Risco / Inviável';
    case 'REQUIRES_HUMAN_REVIEW': return 'Revisão de Comitê';
    default: return rec;
  }
}

function getScoreColor(score) {
  if (score >= 80) return '#10B981';
  if (score >= 60) return '#F59E0B';
  return '#EF4444';
}

export function renderPortfolioView(store) {
  const state = store.getState();
  const currentTab = state.portfolioTab || 'historical';
  const courses = state.courses || [];
  const historical = state.historicalCourses || [];

  const approvedCount = courses.filter(c => c.recommendation === 'APPROVED' || c.recommendation === 'APPROVED_WITH_ADJUSTMENTS').length;
  const avgScore = (courses.reduce((acc, c) => acc + (c.viability_score || 0), 0) / (courses.length || 1)).toFixed(1);

  // Totais da Base Histórica
  const totalHistEnrolled = historical.reduce((acc, c) => acc + (c.metrics_summary?.total_enrolled || 0), 0);
  const totalHistRevenue = historical.reduce((acc, c) => acc + (c.metrics_summary?.total_revenue_brl || 0), 0);

  return `
    <div class="view-header">
      <div class="view-title-row">
        <div>
          <h1 class="view-title">Inteligência de Mercado & Portfólio da IES</h1>
          <p class="view-subtitle">Consulte a base histórica de teste da <strong>ENS</strong>, com dados sintéticos de 2024 e 2025, e compare com diagnósticos de viabilidade de novos cursos.</p>
        </div>
        <button class="prometeus-btn-primary" id="btn-goto-validate" style="font-size:14px; padding:12px 22px;">
          <span>✦ Validar Novo Curso</span>
        </button>
      </div>

      <!-- Abas de Navegação do Portfólio -->
      <div style="display:flex; gap:12px; margin-top:24px; border-bottom:1px solid var(--prometeus-border-subtle); padding-bottom:8px;">
        <button id="tab-btn-historical" class="prometeus-tab-btn ${currentTab === 'historical' ? 'active' : ''}" style="background:none; border:none; padding:8px 16px; font-size:14px; font-weight:600; cursor:pointer; color:${currentTab === 'historical' ? '#ffffff' : 'var(--prometeus-text-muted)'}; border-bottom:${currentTab === 'historical' ? '2px solid var(--prometeus-accent)' : 'none'};">
          🏛️ Base Histórica ENS (${historical.length} Cursos / 2 Anos)
        </button>
        <button id="tab-btn-diagnostics" class="prometeus-tab-btn ${currentTab === 'diagnostics' ? 'active' : ''}" style="background:none; border:none; padding:8px 16px; font-size:14px; font-weight:600; cursor:pointer; color:${currentTab === 'diagnostics' ? '#ffffff' : 'var(--prometeus-text-muted)'}; border-bottom:${currentTab === 'diagnostics' ? '2px solid var(--prometeus-accent)' : 'none'};">
          ⚡ Novos Diagnósticos de Mercado (${courses.length})
        </button>
      </div>
    </div>

    ${currentTab === 'historical' ? `
      <!-- CARDS EXECUTIVOS: BASE HISTÓRICA ENS -->
      <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:20px; margin-bottom:32px;">
        <div class="prometeus-card">
          <div style="font-size:12px; text-transform:uppercase; color:var(--prometeus-text-muted); font-weight:600; letter-spacing:0.05em;">Cursos Analisados</div>
          <div class="metric-big-highlight">${historical.length} cursos</div>
          <div style="font-size:12px; color:var(--prometeus-text-secondary);">${new Set(historical.map(c => c.family).filter(Boolean)).size} famílias de formação · dados sintéticos</div>
        </div>

        <div class="prometeus-card">
          <div style="font-size:12px; text-transform:uppercase; color:var(--prometeus-text-muted); font-weight:600; letter-spacing:0.05em;">Janela de Ofertas</div>
          <div class="metric-big-highlight" style="color:#38BDF8;">2 Anos</div>
          <div style="font-size:12px; color:var(--prometeus-text-secondary);">1 oferta anual por curso (2024 e 2025)</div>
        </div>

        <div class="prometeus-card">
          <div style="font-size:12px; text-transform:uppercase; color:var(--prometeus-text-muted); font-weight:600; letter-spacing:0.05em;">Matrículas Totais</div>
          <div class="metric-big-highlight" style="color:#34d399;">${totalHistEnrolled} alunos</div>
          <div style="font-size:12px; color:var(--prometeus-text-secondary);">Acumulado histórico na ENS</div>
        </div>

        <div class="prometeus-card">
          <div style="font-size:12px; text-transform:uppercase; color:var(--prometeus-text-muted); font-weight:600; letter-spacing:0.05em;">Receita Realizada</div>
          <div class="metric-big-highlight" style="color:var(--prometeus-accent-ice); font-size:22px; margin-top:8px;">R$ ${(totalHistRevenue / 1000000).toFixed(2)}M</div>
          <div style="font-size:12px; color:var(--prometeus-text-secondary);">Faturamento total no período</div>
        </div>
      </div>

      <!-- TABELA DA BASE HISTÓRICA ENS -->
      <div class="prometeus-card" style="padding:0; overflow:hidden;">
        <div style="padding:20px 24px; border-bottom:1px solid var(--prometeus-border-subtle); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
          <div>
            <div style="font-weight:600; font-size:16px; color:#ffffff;">Catálogo Histórico ENS — Ofertas 2024 e 2025</div>
            <div style="font-size:12px; color:var(--prometeus-text-muted); margin-top:2px;">Massa histórica sintética e explicitamente identificada, usada somente para testar comparação interna.</div>
          </div>
          <div style="display:flex; gap:10px;">
            <button id="btn-reseed-data" class="prometeus-btn-secondary" style="font-size:12px; padding:6px 14px;">
              🔄 Sincronizar PostgreSQL
            </button>
          </div>
        </div>

        <div class="prometeus-table-container" style="border:none; border-radius:0;">
          <table class="prometeus-table" id="table-historical-courses">
            <thead>
              <tr>
                <th scope="col">Curso & Segmento ENS</th>
                <th scope="col">Modalidade</th>
                <th scope="col">Desempenho</th>
                <th scope="col">Oferta Ano 1 (2024)</th>
                <th scope="col">Oferta Ano 2 (2025)</th>
                <th scope="col" style="text-align:right;">Receita Total</th>
              </tr>
            </thead>
            <tbody>
              ${historical.map(c => {
                const f24 = c.funnel_history?.find(f => f.period === '2024') || {};
                const f25 = c.funnel_history?.find(f => f.period === '2025') || {};
                const isCancelled = f25.status === 'CANCELLED_LOW_QUORUM';

                return `
                  <tr class="historical-course-row" style="cursor:default;">
                    <td>
                      <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-family:var(--prometeus-font-mono); font-size:11px; color:#38BDF8; font-weight:700;">${c.external_id}</span>
                      </div>
                      <strong style="color:#ffffff; font-size:14px; display:block; margin-top:2px;">${c.name}</strong>
                      <span style="font-size:12px; color:var(--prometeus-text-muted);">${c.category} • ${c.segment || c.category}</span>
                      ${safeUrl(c.academic_reference?.source_url) ? `<div style="font-size:12px; margin-top:6px;"><a href="${escapeHtml(safeUrl(c.academic_reference.source_url))}" target="_blank" rel="noopener noreferrer">Nome e categoria: fonte ENS</a><span style="color:var(--prometeus-text-muted);"> · Indicadores e preços simulados</span></div>` : ''}
                    </td>
                    <td>
                      <span style="font-size:13px; color:var(--prometeus-text-secondary);">${c.modality}</span>
                      <div style="font-size:11px; color:var(--prometeus-text-muted);">${c.workload_hours}h</div>
                    </td>
                    <td>
                      ${getTierBadge(c.tier || (isCancelled ? 'CANCELADO_POR_QUORUM' : c.status === 'active' ? 'SUCESSO' : 'MEDIANO'))}
                      <div style="font-size:11px; color:var(--prometeus-text-muted); margin-top:4px;">Quórum mín: <strong>${c.quorum_min || 18} alunos</strong></div>
                    </td>
                    <td>
                      <div style="font-size:13px; color:#ffffff; font-weight:600;">
                        ${f24.enrolled || 0} alunos
                        <span style="font-size:11px; color:var(--prometeus-text-muted); font-weight:normal;">(${f24.leads || 0} leads)</span>
                      </div>
                      <div style="font-size:12px; color:var(--prometeus-text-secondary);">Ticket: R$ ${(f24.ticket || f24.average_ticket_brl || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</div>
                    </td>
                    <td>
                      ${isCancelled ? `
                        <div style="font-size:13px; color:#f87171; font-weight:700;">
                          ✕ CANCELADA (${f25.enrolled || 0} de ${c.quorum_min || 15})
                        </div>
                        <div style="font-size:11px; color:#fca5a5; max-width:200px;">Quórum não atingido; turma não viabilizada.</div>
                      ` : `
                        <div style="font-size:13px; color:#ffffff; font-weight:600;">
                          ${f25.enrolled || 0} alunos
                          <span style="font-size:11px; color:var(--prometeus-text-muted); font-weight:normal;">(${f25.leads || 0} leads)</span>
                        </div>
                        <div style="font-size:12px; color:var(--prometeus-text-secondary);">Ticket: R$ ${(f25.ticket || f25.average_ticket_brl || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</div>
                      `}
                    </td>
                    <td style="text-align:right;" class="prometeus-stat-mono">
                      <strong style="color:${isCancelled ? '#f87171' : '#ffffff'}; font-size:14px;">
                        R$ ${(c.metrics_summary?.total_revenue_brl || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                      </strong>
                      <div style="font-size:11px; color:var(--prometeus-text-muted);">${c.metrics_summary?.total_enrolled || 0} alunos no total</div>
                    </td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      </div>
    ` : `
      <!-- CARDS EXECUTIVOS: NOVOS DIAGNÓSTICOS -->
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
          <div class="metric-big-highlight" style="font-size:20px; color:#38BDF8; margin-top:14px;">Base de teste</div>
          <div style="font-size:12px; color:var(--prometeus-text-secondary);">Somente histórico ENS sintético autorizado</div>
        </div>
      </div>

      <!-- TABELA DE NOVOS DIAGNÓSTICOS -->
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
                    ${course.ticket === null ? 'Não informado' : `R$ ${Number(course.ticket).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`}<span style="font-size:11px; color:var(--prometeus-text-muted);">${course.ticket === null ? '' : '/mês'}</span>
                  </td>
                  <td>
                    <div style="display:flex; align-items:center; gap:8px;">
                      <div style="width:36px; height:36px; border-radius:50%; border:2px solid ${getScoreColor(course.viability_score)}; display:flex; align-items:center; justify-content:center; font-family:var(--prometeus-font-mono); font-size:12px; font-weight:700; color:#ffffff;">
                        ${Number(course.viability_score).toFixed(0)}
                      </div>
                    </div>
                  </td>
                  <td>
                    <span class="prometeus-pill-badge" data-status="${course.recommendation}">
                      ● ${getRecommendationLabel(course.recommendation)}
                    </span>
                  </td>
                  <td style="font-size:13px; color:var(--prometeus-text-secondary);">
                    ${course.coverage_index === null ? 'Não disponível' : `Cobertura ${(Number(course.coverage_index) * 100).toFixed(0)}%`}
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
    `}
  `;
}

export function bindPortfolioEvents(store, container) {
  const gotoValidateBtn = container.querySelector('#btn-goto-validate');
  if (gotoValidateBtn) {
    gotoValidateBtn.addEventListener('click', () => {
      store.setView('validate');
    });
  }

  // Abas do Portfólio
  const tabHistorical = container.querySelector('#tab-btn-historical');
  if (tabHistorical) {
    tabHistorical.addEventListener('click', () => {
      store.setPortfolioTab('historical');
    });
  }

  const tabDiagnostics = container.querySelector('#tab-btn-diagnostics');
  if (tabDiagnostics) {
    tabDiagnostics.addEventListener('click', () => {
      store.setPortfolioTab('diagnostics');
    });
  }

  // Botão de re-seed
  const reseedBtn = container.querySelector('#btn-reseed-data');
  if (reseedBtn) {
    reseedBtn.addEventListener('click', async () => {
      reseedBtn.textContent = 'Sincronizando...';
      reseedBtn.disabled = true;
      const ok = await store.seedInstitutionalData(false);
      if (ok) {
        alert('Base histórica da ENS sincronizada com sucesso no PostgreSQL!');
      } else {
        alert('Falha ao sincronizar.');
      }
      reseedBtn.textContent = '🔄 Sincronizar PostgreSQL';
      reseedBtn.disabled = false;
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
