/** Configuração explícita dos provedores usados pelo worker. */

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#039;');
}

export function renderSettingsView(store) {
  const state = store.getState();
  const settings = state.settings[state.currentTenantId] || {};
  const oauthConnected = Boolean(settings.chatgpt_oauth_connected);
  const llmConfigured = Boolean(settings.openai_api_key_masked || oauthConnected);
  const apifyConfigured = Boolean(settings.apify_token_masked);
  const jevConfigured = Boolean(settings.is_jev_configured);
  return `<div class="view-header"><div>
      <h1 class="view-title">Configurações & conectores</h1>
      <p class="view-subtitle">Credenciais são enviadas ao backend e nunca salvas pelo navegador. Campos vazios preservam o valor já configurado.</p>
    </div></div>
    <form id="form-settings" style="max-width:920px;margin:0 auto;display:flex;flex-direction:column;gap:24px;">
      <div class="prometeus-card">
        <div style="display:flex;justify-content:space-between;gap:12px;"><h2>1. LLM tradicional</h2><span class="prometeus-pill-badge" data-status="${llmConfigured ? 'APPROVED' : 'ADJUSTMENTS'}">${llmConfigured ? 'CONFIGURADA' : 'NÃO CONFIGURADA'}</span></div>
        <p>Use sua conta ChatGPT via OAuth oficial ou uma chave da OpenAI API. Nos dois modos, o modelo interpreta o curso, planeja a pesquisa e sintetiza o dossiê; cálculos e mudanças de estado continuam validados em código.</p>
        <div class="form-grid">
          <div class="form-group col-4"><label class="form-label" for="setting-llm-provider">Provedor</label><select id="setting-llm-provider" class="form-select"><option value="chatgpt_oauth" ${settings.gen_llm_provider === 'chatgpt_oauth' ? 'selected' : ''}>Plano ChatGPT (OAuth)</option><option value="openai" ${settings.gen_llm_provider === 'openai' ? 'selected' : ''}>OpenAI API</option></select></div>
          <div class="form-group col-4"><label class="form-label" for="setting-llm-model">Modelo</label><input id="setting-llm-model" class="form-input" value="${escapeHtml(settings.chatgpt_oauth_model || settings.gen_llm_model || 'gpt-4o-mini')}"></div>
          <div class="form-group col-4"><label class="form-label" for="setting-reasoning-effort">Reasoning effort</label><input id="setting-reasoning-effort" class="form-input" value="${escapeHtml(settings.gen_llm_reasoning_effort || '')}" placeholder="opcional"></div>
          <div class="form-group col-12"><label class="form-label" for="setting-llm-token">OpenAI API key</label><input type="password" id="setting-llm-token" class="form-input" autocomplete="new-password" placeholder="${escapeHtml(settings.openai_api_key_masked || 'sk-...')}"></div>
          <div class="form-group col-12"><label class="form-label">Conta ChatGPT</label><div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;"><span>${oauthConnected ? `Conectada e validada${settings.chatgpt_oauth_email ? ` — ${escapeHtml(settings.chatgpt_oauth_email)}` : ''}` : 'Não conectada'}</span><button type="button" id="btn-chatgpt-connect" class="prometeus-btn-secondary">${oauthConnected ? 'Reconectar' : 'Continuar com ChatGPT'}</button>${oauthConnected ? '<button type="button" id="btn-chatgpt-disconnect" class="prometeus-btn-secondary">Desconectar</button>' : ''}</div><small>A conexão só é marcada como válida após listar os modelos reais da conta e concluir uma chamada à Responses API.</small></div>
        </div>
      </div>

      <div class="prometeus-card">
        <div style="display:flex;justify-content:space-between;gap:12px;"><h2>2. Apify</h2><span class="prometeus-pill-badge" data-status="${apifyConfigured ? 'APPROVED' : 'ADJUSTMENTS'}">${apifyConfigured ? 'CONFIGURADO' : 'NÃO CONFIGURADO'}</span></div>
        <p>Execuções reais e auditáveis para busca, crawling, Meta Ads Library, LinkedIn, vagas e redes sociais. Actors e builds são fixados pelo backend.</p>
        <div class="form-grid">
          <div class="form-group col-8"><label class="form-label" for="setting-apify-token">API token</label><input type="password" id="setting-apify-token" class="form-input" autocomplete="new-password" placeholder="${escapeHtml(settings.apify_token_masked || 'apify_api_...')}"></div>
          <div class="form-group col-4"><label class="form-label" for="setting-apify-max-charge">Limite por análise (USD)</label><input type="number" id="setting-apify-max-charge" class="form-input" min="0.1" step="0.1" value="${escapeHtml(settings.apify_max_charge ?? 5)}"></div>
        </div>
      </div>

      <div class="prometeus-card">
        <div style="display:flex;justify-content:space-between;gap:12px;"><h2>3. JEV opcional</h2><span class="prometeus-pill-badge" data-status="${jevConfigured ? 'APPROVED' : 'ADJUSTMENTS'}">${jevConfigured ? 'HÍBRIDO' : 'LLM TRADICIONAL'}</span></div>
        <p>Deixe a chave vazia para manter o modo tradicional aprovado para os testes atuais.</p>
        <div class="form-grid">
          <div class="form-group col-8"><label class="form-label" for="setting-jev-key">TypeSafe API key</label><input type="password" id="setting-jev-key" class="form-input" autocomplete="new-password" placeholder="não configurada"></div>
          <div class="form-group col-4"><label class="form-label" for="setting-jev-model">Modelo JEV</label><input id="setting-jev-model" class="form-input" value="${escapeHtml(settings.jev_model || 'jev-v1.2.0')}"></div>
        </div>
      </div>

      <div class="prometeus-card">
        <h2>4. Base histórica de teste</h2>
        <p>Esta é a única fonte sintética autorizada. Ela é persistida no PostgreSQL e usada apenas como comparação histórica da ENS.</p>
        <button type="button" id="btn-sync-crm-data" class="prometeus-btn-secondary">Carregar novamente a base histórica</button>
      </div>

      <div style="display:flex;justify-content:flex-end;"><button type="submit" id="btn-save-settings" class="prometeus-btn-primary">Salvar configuração</button></div>
      <p id="settings-result" role="status"></p>
    </form>`;
}

export function bindSettingsEvents(store, container) {
  container.querySelector('#btn-chatgpt-connect')?.addEventListener('click', () => {
    window.open('/v1/auth/chatgpt/login', 'prometeus-chatgpt-oauth', 'popup,width=620,height=760');
  });

  container.querySelector('#btn-chatgpt-disconnect')?.addEventListener('click', async event => {
    event.currentTarget.disabled = true;
    const response = await fetch('/v1/auth/chatgpt/disconnect', { method: 'POST' });
    if (response.ok) {
      store._hasSyncedBackendSettings = false;
      await store.syncBackendSettings();
      store.notify();
    }
  });

  if (!window.__prometeusOAuthListenerBound) {
    window.__prometeusOAuthListenerBound = true;
    window.addEventListener('message', async event => {
      if (event.origin !== window.location.origin || event.data?.type !== 'CHATGPT_OAUTH_SUCCESS') return;
      store._hasSyncedBackendSettings = false;
      await store.syncBackendSettings();
      store.notify();
    });
  }

  container.querySelector('#form-settings')?.addEventListener('submit', async event => {
    event.preventDefault();
    const button = container.querySelector('#btn-save-settings');
    const result = container.querySelector('#settings-result');
    button.disabled = true;
    result.textContent = 'Salvando...';
    const payload = {
      gen_llm_provider: container.querySelector('#setting-llm-provider').value,
      gen_llm_model: container.querySelector('#setting-llm-model').value.trim(),
      gen_llm_reasoning_effort: container.querySelector('#setting-reasoning-effort').value.trim() || null,
      jev_model: container.querySelector('#setting-jev-model').value.trim(),
      apify_max_charge: Number(container.querySelector('#setting-apify-max-charge').value)
    };
    const llmKey = container.querySelector('#setting-llm-token').value.trim();
    const apifyKey = container.querySelector('#setting-apify-token').value.trim();
    const jevKey = container.querySelector('#setting-jev-key').value.trim();
    if (llmKey) payload.openai_api_key = llmKey;
    if (apifyKey) payload.apify_token = apifyKey;
    if (jevKey) payload.typesafe_api_key = jevKey;
    try {
      const response = await fetch('/v1/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      result.textContent = 'Configuração persistida. Recrie o worker para aplicar credenciais alteradas ao processo Celery.';
      store._hasSyncedBackendSettings = false;
      await store.syncBackendSettings();
    } catch (error) {
      result.textContent = `Falha ao salvar: ${error.message}`;
    } finally {
      button.disabled = false;
    }
  });

  container.querySelector('#btn-sync-crm-data')?.addEventListener('click', async event => {
    event.currentTarget.disabled = true;
    const ok = await store.seedInstitutionalData(true);
    event.currentTarget.disabled = false;
    const result = container.querySelector('#settings-result');
    result.textContent = ok ? 'Base histórica de teste carregada.' : 'Falha ao carregar a base histórica.';
  });
}
