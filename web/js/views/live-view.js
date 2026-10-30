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
  const sourceLabels = {instagram:'Instagram',linkedin_jobs:'LinkedIn Jobs',linkedin:'LinkedIn',google_search:'Busca Google',web_crawler:'Páginas da web',meta_ads_library:'Biblioteca de anúncios Meta',tiktok:'TikTok',youtube_comments:'Comentários do YouTube',google_trends:'Google Trends'};
  const sourceGaps = toolRuns.filter(run => ['FAILED', 'EMPTY', 'PARTIAL'].includes(run.status));
  const verification = steps.find(step => step.output_summary?.verification)?.output_summary.verification;
  const revisingDossier = job.status === 'RUNNING' && steps.some(step => step.output_summary?.dossier_revision?.status === 'RUNNING');

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
    ${verification?.issues?.length ? `<div class="prometeus-card" role="status" style="margin-bottom:20px;"><strong>${revisingDossier ? 'Revisando a redação do dossiê' : 'O texto do dossiê precisa de revisão'}</strong><p>${revisingDossier ? 'A análise continua com os dados já coletados. O texto será validado novamente antes da publicação.' : 'O resultado não foi publicado. A validação encontrou estes problemas:'}</p><ul>${verification.issues.map(issue => `<li>${escapeHtml(issue.message)}${issue.text_excerpt ? `<blockquote>${escapeHtml(issue.text_excerpt)}</blockquote>` : ''}</li>`).join('')}</ul></div>` : ''}
    ${job.connectionWarning ? `<div class="prometeus-card" role="status" style="margin-bottom:20px;"><p>${escapeHtml(job.connectionWarning)}</p></div>` : ''}
    ${sourceGaps.length ? `<div class="prometeus-card" role="status" style="border-color:#d99d35;margin-bottom:20px;"><strong>Coleta com dados parciais</strong><p>A análise usa as evidências disponíveis. Estas lacunas serão informadas no dossiê e consideradas na recomendação:</p><ul>${sourceGaps.map(run => `<li>${escapeHtml(sourceLabels[run.capability] || run.capability)}: ${run.status === 'PARTIAL' ? 'consulta interrompida com retorno parcial; itens recuperados sujeitos à validação' : run.status === 'FAILED' ? 'falha na consulta' : run.observation_status === 'observed_empty' ? 'consulta concluída sem resultados' : 'nenhum conteúdo utilizável'} — ${escapeHtml(run.query)}${run.error_message ? ` (${escapeHtml(run.error_message)})` : ''}.</li>`).join('')}</ul><p>Uma lacuna de coleta não comprova ausência de demanda.</p></div>` : ''}

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
