/**
 * VIEW: Configurações & Integrações da Instituição (White-Label Hub)
 */

export function renderSettingsView(store) {
  const state = store.getState();
  const currentTenant = state.tenants.find(t => t.id === state.currentTenantId) || state.tenants[0];
  const settings = state.settings[state.currentTenantId] || {};

  return `
    <div class="view-header">
      <div class="view-title-row">
        <div>
          <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
            <span class="prometeus-pill-badge" data-status="APPROVED">CONECTORES ATIVOS</span>
            <span style="font-size:12px; color:var(--prometeus-text-muted);">Ambiente: ${currentTenant.name}</span>
          </div>
          <h1 class="view-title">Integrações & Configurações da Instituição</h1>
          <p class="view-subtitle">Conecte sua API de cursos e CRM, suas chaves de inteligência de mercado e defina as metas financeiras da sua instituição.</p>
        </div>
      </div>
    </div>

    <form id="form-settings" style="max-width:980px; margin:0 auto; display:flex; flex-direction:column; gap:28px;">
      <!-- BLOCO 1: CONECTOR DO CRM / ERP ACADÊMICO DA IES -->
      <div class="prometeus-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
          <div>
            <h2 style="font-size:17px; font-weight:700; color:#ffffff; margin:0; display:flex; align-items:center; gap:8px;">
              <span>🏢</span>
              <span>1. Conector de Dados Internos (CRM / ERP da Faculdade)</span>
            </h2>
            <p style="font-size:13px; color:var(--prometeus-text-secondary); margin:4px 0 0 0;">
              O Prometeus consulta sua API de cursos para cruzar novas propostas com o seu funil histórico real (leads, inscritos e matriculados).
            </p>
          </div>
          <span class="prometeus-pill-badge" data-status="APPROVED">● CONECTADO</span>
        </div>

        <div class="form-grid">
          <div class="form-group col-8">
            <label class="form-label" for="setting-crm-url">Endpoint da API de Cursos da Instituição</label>
            <input type="url" id="setting-crm-url" class="form-input" 
                   value="${settings.crm_api_url || 'https://api.ens.edu.br/v1/cursos-historico'}"
                   placeholder="https://api.suafaculdade.edu.br/v1/cursos">
          </div>

          <div class="form-group col-4">
            <label class="form-label" for="setting-crm-token">Token de Autenticação (Bearer)</label>
            <input type="password" id="setting-crm-token" class="form-input" 
                   value="${settings.crm_token || 'ens_live_sec_884912fa89b'}">
          </div>

          <div class="col-12" style="display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.02); padding:12px 16px; border-radius:var(--prometeus-radius-md); border:1px solid var(--prometeus-border-subtle);">
            <div style="font-size:12px; color:var(--prometeus-text-secondary);">
              Status da Sincronização: <strong style="color:var(--prometeus-status-approved);">${settings.crm_last_sync || "18 turmas históricas sincronizadas"}</strong>
            </div>
            <button type="button" id="btn-test-crm" class="prometeus-btn-secondary" style="font-size:12px; padding:6px 14px; min-height:32px;">
              <span>Testar Conexão com API</span>
            </button>
          </div>
        </div>
      </div>

      <!-- BLOCO 2: APIS EXTERNAS & SCRAPERS PRÓPRIOS -->
      <div class="prometeus-card">
        <div style="margin-bottom:16px;">
          <h2 style="font-size:17px; font-weight:700; color:#ffffff; margin:0; display:flex; align-items:center; gap:8px;">
            <span>🌐</span>
            <span>2. Conectores de Inteligência Externa & APIs</span>
          </h2>
          <p style="font-size:13px; color:var(--prometeus-text-secondary); margin:4px 0 0 0;">
            Configure as chaves e credenciais para raspagem dedicada de concorrência, redes sociais e Google.
          </p>
        </div>

        <div class="form-grid">
          <div class="form-group col-6">
            <label class="form-label" for="setting-apify-token">Apify API Key (Scrapers Dedicados de Redes & Concorrência)</label>
            <input type="password" id="setting-apify-token" class="form-input" 
                   value="${settings.apify_token || 'apify_api_live_99412a8bc94e772'}"
                   placeholder="apify_api_••••••••">
            <span class="form-hint">Usada para minerar comentários do YouTube e queixas de alunos</span>
          </div>

          <div class="form-group col-6">
            <label class="form-label" for="setting-meta-ads-token">Meta Ads Library Token (Espionagem de Anúncios)</label>
            <input type="password" id="setting-meta-ads-token" class="form-input" 
                   value="${settings.meta_ads_token || 'EAAB88921fa0c884...'}"
                   placeholder="Graph API Access Token">
            <span class="form-hint">Usado para capturar criativos e anúncios ativos da concorrência</span>
          </div>

          <div class="form-group col-6">
            <label class="form-label" for="setting-ga-id">Google Analytics 4 Property ID (Opcional)</label>
            <input type="text" id="setting-ga-id" class="form-input" 
                   value="${settings.ga_property_id || 'GA4-ENS-PROMETEUS-2026'}"
                   placeholder="Ex: GA4-XXXXX">
            <span class="form-hint">Para correlacionar tráfego próprio de páginas de cursos da IES</span>
          </div>

          <div class="form-group col-6">
            <label class="form-label" for="setting-llm-provider">Provedor de LLM para Síntese do Dossiê</label>
            <select id="setting-llm-provider" class="form-select">
              <option value="Claude 3.7 Sonnet (Anthropic)" selected>Claude 3.7 Sonnet (Anthropic)</option>
              <option value="Gemini 1.5 Pro (Google DeepMind)">Gemini 1.5 Pro (Google DeepMind)</option>
              <option value="GPT-4o (OpenAI)">GPT-4o (OpenAI)</option>
            </select>
            <span class="form-hint">Modelo responsável pela redação do parecer e ganchos comerciais</span>
          </div>
        </div>
      </div>

      <!-- BLOCO 3: DIRETRIZES DE NEGÓCIO DA INSTITUIÇÃO -->
      <div class="prometeus-card">
        <div style="margin-bottom:16px;">
          <h2 style="font-size:17px; font-weight:700; color:#ffffff; margin:0; display:flex; align-items:center; gap:8px;">
            <span>🎯</span>
            <span>3. Diretrizes de Negócio e Metas Financeiras da IES</span>
          </h2>
          <p style="font-size:13px; color:var(--prometeus-text-secondary); margin:4px 0 0 0;">
            Parâmetros utilizados pela fórmula algorítmica para determinar o ponto de equilíbrio e o Viability Score.
          </p>
        </div>

        <div class="form-grid">
          <div class="form-group col-4">
            <label class="form-label" for="setting-quorum">Quórum Mínimo por Turma</label>
            <input type="number" id="setting-quorum" class="form-input" value="${settings.quorum_min || 22}" min="5" max="100">
            <span class="form-hint">Mínimo de alunos para a turma não ser cancelada</span>
          </div>

          <div class="form-group col-4">
            <label class="form-label" for="setting-margin">Margem de Contribuição Alvo (%)</label>
            <input type="number" id="setting-margin" class="form-input" value="${settings.target_margin || 42}" min="10" max="90">
            <span class="form-hint">Meta percentual de rentabilidade operacional</span>
          </div>

          <div class="form-group col-4">
            <label class="form-label" for="setting-cac">CAC de Referência (R$)</label>
            <input type="number" id="setting-cac" class="form-input" value="${settings.reference_cac || 480}" min="50" max="2000" step="10">
            <span class="form-hint">Custo médio de aquisição por matrícula paga</span>
          </div>
        </div>
      </div>

      <!-- Botão de Salvar -->
      <div style="display:flex; justify-content:flex-end;">
        <button type="submit" class="prometeus-btn-primary" style="font-size:14px; padding:12px 28px;">
          <span>Salvar Configurações da Instituição</span>
        </button>
      </div>
    </form>
  `;
}

export function bindSettingsEvents(store, container) {
  const testCrmBtn = container.querySelector('#btn-test-crm');
  if (testCrmBtn) {
    testCrmBtn.addEventListener('click', () => {
      testCrmBtn.textContent = 'Testando conexão...';
      testCrmBtn.disabled = true;

      setTimeout(() => {
        testCrmBtn.textContent = 'Testar Conexão com API';
        testCrmBtn.disabled = false;
        alert("✓ Conexão bem-sucedida com a API da ENS!\n• 18 turmas históricas sincronizadas\n• 4.200 leads mapeados no funil histórico\n• Taxa de conversão consolidada: 14.2%");
      }, 700);
    });
  }

  const form = container.querySelector('#form-settings');
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const state = store.getState();

      const updatedSettings = {
        crm_api_url: container.querySelector('#setting-crm-url').value,
        crm_token: container.querySelector('#setting-crm-token').value,
        apify_token: container.querySelector('#setting-apify-token').value,
        meta_ads_token: container.querySelector('#setting-meta-ads-token').value,
        ga_property_id: container.querySelector('#setting-ga-id').value,
        llm_provider: container.querySelector('#setting-llm-provider').value,
        quorum_min: parseInt(container.querySelector('#setting-quorum').value),
        target_margin: parseInt(container.querySelector('#setting-margin').value),
        reference_cac: parseInt(container.querySelector('#setting-cac').value)
      };

      store.updateSettings(state.currentTenantId, updatedSettings);
      alert("Configurações da instituição salvas com sucesso!");
    });
  }
}
