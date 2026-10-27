/** Visualização do estado real reportado pelo worker. */

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#039;');
}

function statusLabel(status) {
  const labels = {
    SUBMITTING: 'ENVIANDO', QUEUED: 'NA FILA', RUNNING: 'PROCESSANDO',
    BLOCKED: 'BLOQUEADO', FAILED: 'FALHOU', WAITING_FOR_INPUT: 'AGUARDANDO DADOS',
    TIMEOUT: 'SEM CONFIRMAÇÃO', CONNECTION_ERROR: 'SEM CONEXÃO'
  };
  return labels[status] || status;
}

export function renderLiveView(store) {
  const job = store.getState().liveJob;
  if (!job) {
    return `<div class="prometeus-card"><h2>Nenhuma análise em execução</h2><p>Inicie uma validação para acompanhar as etapas e ferramentas reais.</p></div>`;
  }

  const steps = job.steps || [];
  const toolRuns = job.toolRuns || [];
  const totalCost = toolRuns.reduce((sum, run) => sum + Number(run.cost_usd || 0), 0);
  const blockingReason = job.blocking?.reason || job.error;

  return `
    <div class="view-header">
      <div class="view-title-row"><div>
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
          <span class="prometeus-pill-badge" data-status="${escapeHtml(job.status)}">● ${escapeHtml(statusLabel(job.status))}</span>
          <span class="prometeus-stat-mono" style="font-size:12px;color:var(--prometeus-text-muted);">${escapeHtml(job.id)}</span>
        </div>
        <h1 class="view-title">${escapeHtml(job.name)}</h1>
        <p class="view-subtitle">Este painel mostra somente checkpoints e execuções confirmados pelo backend.</p>
      </div></div>
    </div>

    ${blockingReason ? `<div class="prometeus-card" style="border-color:#ef4444;margin-bottom:20px;"><strong>Processamento interrompido</strong><p>${escapeHtml(blockingReason)}</p></div>` : ''}

    <div class="prometeus-card" style="margin-bottom:24px;">
      <div style="font-size:15px;font-weight:600;color:#fff;margin-bottom:14px;">Pipeline canônico — ${steps.length}/15 checkpoints registrados</div>
      ${steps.length ? `<div class="stepper-container">${steps.map(step => `
        <div class="step-item ${step.status === 'COMPLETED' ? 'completed' : step.status === 'RUNNING' ? 'active' : ''}">
          ${escapeHtml(step.step_number)}. ${escapeHtml(step.name)} — ${escapeHtml(step.status)}
        </div>`).join('')}</div>` : '<p style="color:var(--prometeus-text-muted);">Aguardando o primeiro checkpoint do worker.</p>'}
    </div>

    <div class="prometeus-card" style="margin-bottom:24px;">
      <div style="display:flex;justify-content:space-between;gap:16px;margin-bottom:14px;">
        <strong style="color:#fff;">Ferramentas externas executadas</strong>
        <span class="prometeus-stat-mono">Custo reportado: US$ ${totalCost.toFixed(4)}</span>
      </div>
      ${toolRuns.length ? `<div class="prometeus-table-container"><table class="prometeus-table">
        <thead><tr><th>Fonte</th><th>Consulta</th><th>Actor / build</th><th>Status</th><th>Itens válidos</th><th>Run ID</th></tr></thead>
        <tbody>${toolRuns.map(run => `<tr>
          <td>${escapeHtml(run.capability)}${run.required ? ' *' : ''}</td>
          <td>${escapeHtml(run.query)}</td>
          <td><span class="prometeus-stat-mono">${escapeHtml(run.actor_id)}@${escapeHtml(run.actor_build)}</span></td>
          <td>${escapeHtml(run.status)}${run.error_message ? `<br><small>${escapeHtml(run.error_message)}</small>` : ''}</td>
          <td>${escapeHtml(run.valid_items_count)} / ${escapeHtml(run.raw_items_count)}</td>
          <td><span class="prometeus-stat-mono">${escapeHtml(run.run_id || 'não iniciado')}</span></td>
        </tr>`).join('')}</tbody>
      </table></div>` : '<p style="color:var(--prometeus-text-muted);">Nenhuma ferramenta externa foi iniciada ainda.</p>'}
    </div>

    <div class="prometeus-card">
      <strong style="color:#fff;">Eventos observados</strong>
      <div class="engine-log-box" id="live-log-container" style="height:160px;font-size:12px;margin-top:10px;">
        ${(job.logs || []).map(log => `<div>${escapeHtml(log)}</div>`).join('')}
      </div>
    </div>`;
}

export function bindLiveEvents(_store, container) {
  const logs = container.querySelector('#live-log-container');
  if (logs) logs.scrollTop = logs.scrollHeight;
}
