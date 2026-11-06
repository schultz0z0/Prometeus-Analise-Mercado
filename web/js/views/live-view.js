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
    TIMEOUT: 'SEM CONFIRMAÇÃO', CONNECTION_ERROR: 'SEM CONEXÃO',
    RETRY_SCHEDULED: 'Retentativa agendada', IN_DOUBT: 'Execução pendente de confirmação',
    SUCCEEDED: 'Concluída', EMPTY: 'Concluída sem resultados', PARTIAL: 'Coleta parcial'
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
  const committedCost = toolRuns.reduce((sum, run) => sum + (run.authorization_status === 'committed' ? Number(run.authorized_cap_usd || 0) : 0), 0);
  const uncertainCost = toolRuns.some(run => ['unknown', 'historical_observation'].includes(run.cost_status) || !run.cost_status);
  const monitorOnly = toolRuns.length > 0 && toolRuns.every(run => run.spending_mode === 'monitor_only');
  const causeLabels = {
    rate_limited: 'Limite temporário de requisições', rate_limit: 'Limite temporário de requisições',
    account_resources_busy: 'Recursos da conta ocupados', provider_unavailable: 'Fornecedor temporariamente indisponível',
    connection_not_established: 'Conexão não estabelecida', remote_result_uncertain: 'Resultado remoto pendente de confirmação',
    actor_terminal_failure: 'Coleta encerrada com falha', actor_configuration: 'Configuração da ferramenta indisponível',
    provider_configuration: 'Acesso ou configuração do fornecedor', invalid_contract_or_input: 'Parâmetros incompatíveis com a ferramenta'
  };
  const actionLabels = {
    backoff: 'Aguardar e tentar novamente', retry_after_backoff: 'Aguardar e tentar novamente',
    wait_and_reduce_concurrency: 'Aguardar e reduzir consultas simultâneas', wait_for_resources: 'Aguardar recursos da conta',
    reconcile_existing_run: 'Conferir a execução já iniciada', reduce_batch_and_retry: 'Reduzir o lote e tentar novamente',
    operator_configuration_required: 'Revisar configuração de acesso'
  };
  const blockingReason = job.blocking?.reason || job.error;
  const sourceLabels = {instagram:'Instagram',linkedin_jobs:'LinkedIn Jobs',linkedin:'LinkedIn',google_search:'Busca Google',web_crawler:'Páginas da web',meta_ads_library:'Biblioteca de anúncios Meta',tiktok:'TikTok',youtube_comments:'Comentários do YouTube',google_trends:'Google Trends'};
  const sourceGaps = toolRuns.filter(run => ['FAILED', 'EMPTY', 'PARTIAL', 'IN_DOUBT'].includes(run.status));
  const gapDescription = run => run.observation_status === 'budget_skipped' ? 'consulta não executada por limite de orçamento' : run.status === 'IN_DOUBT' ? 'resultado da execução pendente de reconciliação' : run.status === 'PARTIAL' ? 'consulta com retorno parcial; itens recuperados sujeitos à validação' : run.status === 'FAILED' ? 'falha na consulta' : run.observation_status === 'observed_empty' ? 'consulta concluída sem resultados' : run.observation_status === 'no_candidates_to_validate' ? 'busca concluída sem páginas elegíveis para validar' : 'nenhum conteúdo utilizável';
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
    ${sourceGaps.length ? `<div class="prometeus-card" role="status" style="border-color:#d99d35;margin-bottom:20px;"><strong>Coleta com dados parciais</strong><p>A análise usa as evidências disponíveis. Estas lacunas serão informadas no dossiê e consideradas na recomendação:</p><ul>${sourceGaps.map(run => `<li>${escapeHtml(sourceLabels[run.capability] || run.capability)}: ${gapDescription(run)} — ${escapeHtml(run.query)}${run.error_message ? ` (${escapeHtml(run.error_message)})` : ''}.</li>`).join('')}</ul><p>Uma lacuna de coleta não comprova ausência de demanda.</p></div>` : ''}

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
        <span class="prometeus-stat-mono">Custo observado: US$ ${totalCost.toFixed(4)} · ${monitorOnly ? 'Sem teto monetário da aplicação' : `Limites comprometidos: US$ ${committedCost.toFixed(2)}`}</span>
      </div>
      <p style="font-size:12px;color:var(--prometeus-text-muted);">O custo observado é provisório e pode mudar após a execução. ${monitorOnly ? 'A pesquisa segue o escopo de coleta e acompanha custos sem reservar um valor fixo por chamada.' : 'Os limites autorizados continuam reservados até reconciliação.'}${uncertainCost ? ' Há resultados ou custos pendentes de confirmação.' : ''}</p>
      ${toolRuns.length ? `<div class="prometeus-table-container"><table class="prometeus-table">
        <thead><tr><th>Fonte</th><th>Consulta</th><th>Actor / build</th><th>Status</th><th>Itens válidos</th><th>Run ID</th></tr></thead>
        <tbody>${toolRuns.map(run => `<tr>
          <td>${escapeHtml(run.capability)}${run.required ? ' *' : ''}</td>
          <td>${escapeHtml(run.query)}</td>
          <td><span class="prometeus-stat-mono">${escapeHtml(run.actor_id)}@${escapeHtml(run.actor_build)}</span></td>
          <td>${escapeHtml(statusLabel(run.status))}${run.error_message ? `<br><small>${escapeHtml(run.error_message)}</small>` : ''}
            ${(run.attempts || []).length ? `<details><summary>${escapeHtml(run.attempts_count ?? run.attempts.length)} tentativa(s) registrada(s)</summary><ul>${run.attempts.map(attempt => `<li>Tentativa ${escapeHtml(attempt.attempt_index)}: ${escapeHtml(statusLabel(attempt.status))}${attempt.cause ? `<br>${escapeHtml(causeLabels[attempt.cause] || 'Falha diagnosticada')}` : ''}${attempt.action ? `<br>${escapeHtml(actionLabels[attempt.action] || 'Recuperação registrada')}` : ''}${attempt.next_attempt_at ? `<br>Próxima verificação: ${escapeHtml(attempt.next_attempt_at)}` : ''}</li>`).join('')}</ul></details>` : ''}
          </td>
          <td>${escapeHtml(run.valid_items_count)}<br><small>${escapeHtml(run.raw_items_count)} registro(s) bruto(s)</small></td>
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
