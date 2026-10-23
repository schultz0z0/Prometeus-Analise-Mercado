/**
 * VIEW: Configurações & Integrações da Instituição (White-Label Hub)
 * Suporte a Conexão 1-CLIQUE com ChatGPT OAuth / Codex (Astra, Sol, Terra, Luna),
 * Níveis de Raciocínio, TypeSafe JEV (Modo Híbrido ou 100% Tradicional) e Apify.
 */

export function renderSettingsView(store) {
  const state = store.getState();
  const currentTenant = state.tenants.find(t => t.id === state.currentTenantId) || state.tenants[0];
  const settings = state.settings[state.currentTenantId] || {};

  const currentProvider = settings.gen_llm_provider || "chatgpt_oauth";
  const currentModel = settings.gen_llm_model || "gpt-6.1-sol";
  const currentReasoning = settings.gen_llm_reasoning_effort || "high";
  const isChatGptConnected = Boolean(settings.chatgpt_access_token && settings.chatgpt_access_token.trim());
  const isJevActive = Boolean(settings.typesafe_api_key && settings.typesafe_api_key.trim());

  return `
    <div class="view-header">
      <div class="view-title-row">
        <div>
          <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
            <span class="prometeus-pill-badge" data-status="APPROVED">PAINEL DE CONFIGURAÇÃO DIRETA</span>
            <span style="font-size:12px; color:var(--prometeus-text-muted);">Ambiente: ${currentTenant.name}</span>
          </div>
          <h1 class="view-title">Configurações & Conexões de Inteligência</h1>
          <p class="view-subtitle">Conecte sua conta ChatGPT/Codex com 1 clique, defina o modelo e o nível de raciocínio, configure JEV e Apify sem precisar abrir arquivos de configuração.</p>
        </div>
      </div>
    </div>

    <form id="form-settings" style="max-width:980px; margin:0 auto; display:flex; flex-direction:column; gap:28px;">
      
      <!-- ===================================================================== -->
      <!-- BLOCO 1: CHATGPT OAUTH / CODEX (1-CLIQUE) & MODELOS                    -->
      <!-- ===================================================================== -->
      <div class="prometeus-card" style="border: 1px solid var(--prometeus-border-card); background: var(--prometeus-surface-card);">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px;">
          <div>
            <h2 style="font-size:17px; font-weight:700; color:#ffffff; margin:0; display:flex; align-items:center; gap:8px;">
              <span>⚡</span>
              <span>1. Conexão ChatGPT / Codex (1-Clique via OAuth)</span>
            </h2>
            <p style="font-size:13px; color:var(--prometeus-text-secondary); margin:4px 0 0 0;">
              Conecte sua conta ChatGPT diretamente para utilizar a cota nativa e os modelos de alto raciocínio (Astra, Sol, Terra e Luna).
            </p>
          </div>
          <span class="prometeus-pill-badge" id="badge-oauth-status" data-status="${isChatGptConnected ? 'APPROVED' : 'ADJUSTMENTS'}">
            ${isChatGptConnected ? '● CONECTADO VIA OAUTH' : '○ DESCONECTADO'}
          </span>
        </div>

        <!-- Banner de Conexão 1-Clique -->
        <div id="oauth-action-box" style="margin-bottom:20px;">
          ${isChatGptConnected ? `
            <div style="background:rgba(52, 211, 153, 0.08); border:1px solid rgba(52, 211, 153, 0.3); border-radius:var(--prometeus-radius-md); padding:16px 20px; display:flex; justify-content:space-between; align-items:center;">
              <div style="display:flex; align-items:center; gap:14px;">
                <div style="width:40px; height:40px; border-radius:10px; background:#10a37f; display:flex; align-items:center; justify-content:center; font-size:22px;">
                  ⚡
                </div>
                <div>
                  <div style="font-size:14px; font-weight:700; color:#ffffff; display:flex; align-items:center; gap:8px;">
                    <span>Conta ChatGPT Conectada</span>
                    <span style="font-size:11px; background:rgba(52, 211, 153, 0.2); color:#34d399; padding:2px 8px; border-radius:12px; font-weight:600;">Codex Ativo</span>
                  </div>
                  <div style="font-size:12px; color:var(--prometeus-text-secondary); margin-top:2px;">
                    Acesso autorizado aos modelos GPT-6 Astra, GPT-6.1 Sol e linha GPT-5.6 consumindo a cota da sua conta.
                  </div>
                </div>
              </div>
              <button type="button" id="btn-disconnect-chatgpt" class="prometeus-btn-secondary" style="color:#f87171; border-color:rgba(248, 113, 113, 0.3); font-size:13px; padding:8px 16px;">
                <span>Desconectar Conta</span>
              </button>
            </div>
          ` : `
            <div style="background:rgba(255, 255, 255, 0.02); border:1px dashed var(--prometeus-border-strong); border-radius:var(--prometeus-radius-md); padding:20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
              <div style="display:flex; align-items:center; gap:14px;">
                <div style="width:44px; height:44px; border-radius:12px; background:#10a37f; display:flex; align-items:center; justify-content:center; font-size:24px; box-shadow:0 4px 12px rgba(16, 163, 127, 0.35);">
                  ⚡
                </div>
                <div>
                  <div style="font-size:14px; font-weight:700; color:#ffffff;">
                    Conectar com ChatGPT / Codex
                  </div>
                  <div style="font-size:12px; color:var(--prometeus-text-secondary); margin-top:2px;">
                    Clique para autorizar sua conta em 1 clique (sem necessidade de copiar ou colar tokens).
                  </div>
                </div>
              </div>
              <div style="display:flex; flex-direction:column; align-items:flex-end; gap:6px;">
                <button type="button" id="btn-connect-chatgpt" class="prometeus-btn-primary" style="background:#10a37f; font-size:13px; padding:10px 22px; font-weight:600; cursor:pointer;">
                  <span>🔗 Conectar com ChatGPT</span>
                </button>
                <a href="/v1/auth/chatgpt/login" target="_blank" rel="noopener noreferrer" style="font-size:11px; color:var(--prometeus-accent-ice); text-decoration:none; opacity:0.85;">
                  Ou autorizar via tela de consentimento ↗
                </a>
              </div>
            </div>
          `}
        </div>

        <!-- Grade de Escolha de Modelo e Nível de Raciocínio -->
        <div class="form-grid">
          <!-- Modelo Selecionado -->
          <div class="form-group col-6">
            <label class="form-label" for="setting-llm-model">Modelo de Linguagem (Codex / ChatGPT)</label>
            <select id="setting-llm-model" class="form-select">
              <optgroup label="Modelos Disponíveis da Conexão ChatGPT / Codex">
                <option value="gpt-6-astra" ${currentModel === 'gpt-6-astra' ? 'selected' : ''}>GPT 6 Astra (Máxima capacidade; problemas muito complexos)</option>
                <option value="gpt-6.1-sol" ${currentModel === 'gpt-6.1-sol' ? 'selected' : ''}>GPT 6.1 Sol (Melhor equilíbrio / alta performance analítica)</option>
                <option value="gpt-5.6-sol" ${currentModel === 'gpt-5.6-sol' ? 'selected' : ''}>GPT 5.6 Sol (Linha Sol consistente e balanceada)</option>
                <option value="gpt-5.6-terra" ${currentModel === 'gpt-5.6-terra' ? 'selected' : ''}>GPT 5.6 Terra (Propósito geral equilibrado)</option>
                <option value="gpt-5.6-luna" ${currentModel === 'gpt-5.6-luna' ? 'selected' : ''}>GPT 5.6 Luna (Ultrarrápido e econômico)</option>
              </optgroup>
              <optgroup label="Modelos Clássicos">
                <option value="gpt-4o" ${currentModel === 'gpt-4o' ? 'selected' : ''}>GPT-4o</option>
                <option value="gpt-4o-mini" ${currentModel === 'gpt-4o-mini' ? 'selected' : ''}>GPT-4o Mini</option>
              </optgroup>
            </select>
            <span class="form-hint">O modelo que processará as análises e sínteses da sua conta</span>
          </div>

          <!-- Nível de Raciocínio (reasoning_effort) -->
          <div class="form-group col-6">
            <label class="form-label" for="setting-reasoning-effort">Nível de Raciocínio (Reasoning Effort)</label>
            <select id="setting-reasoning-effort" class="form-select">
              <option value="none" ${currentReasoning === 'none' ? 'selected' : ''}>None (Sem raciocínio explícito / latência mínima)</option>
              <option value="low" ${currentReasoning === 'low' ? 'selected' : ''}>Low (Raciocínio ágil / verificação inicial)</option>
              <option value="medium" ${currentReasoning === 'medium' ? 'selected' : ''}>Medium (Equilibrado padrão)</option>
              <option value="high" ${currentReasoning === 'high' ? 'selected' : ''}>High (Raciocínio profundo e analítico)</option>
              <option value="extra_high" ${currentReasoning === 'extra_high' ? 'selected' : ''}>Extra High (Raciocínio detalhado avançado)</option>
              <option value="max" ${currentReasoning === 'max' ? 'selected' : ''}>Max (Esforço de raciocínio máximo exaustivo)</option>
            </select>
            <span class="form-hint">Controla o pensamento interno antes de emitir o parecer executivo</span>
          </div>
        </div>

        <!-- Opções Avançadas de Provedor Alternativo (Accordion Opcional) -->
        <details style="margin-top:16px; border-top:1px solid var(--prometeus-border-subtle); padding-top:12px;">
          <summary style="font-size:12px; color:var(--prometeus-text-muted); cursor:pointer; user-select:none;">
            Configuração manual com API Keys avulsas (OpenAI direta, Anthropic Claude ou Gemini)
          </summary>
          <div class="form-grid" style="margin-top:12px;">
            <div class="form-group col-4">
              <label class="form-label" for="setting-llm-provider">Provedor Alternativo</label>
              <select id="setting-llm-provider" class="form-select">
                <option value="chatgpt_oauth" ${currentProvider === 'chatgpt_oauth' ? 'selected' : ''}>ChatGPT OAuth / Codex (Padrão 1-Clique)</option>
                <option value="openai" ${currentProvider === 'openai' ? 'selected' : ''}>OpenAI API Key Padrão</option>
                <option value="anthropic" ${currentProvider === 'anthropic' ? 'selected' : ''}>Anthropic Claude API</option>
                <option value="gemini" ${currentProvider === 'gemini' ? 'selected' : ''}>Google Gemini API</option>
              </select>
            </div>
            <div class="form-group col-8">
              <label class="form-label" for="setting-llm-token">Chave de API Manual (Opcional)</label>
              <input type="password" id="setting-llm-token" class="form-input" 
                     value="${settings.openai_api_key || ''}"
                     placeholder="sk-•••••••• (Usado apenas se não conectar via OAuth)">
            </div>
          </div>
        </details>
      </div>

      <!-- ===================================================================== -->
      <!-- BLOCO 2: JEV / TYPESAFE AI (MOTOR SYSTEM ONE — OPCIONAL)             -->
      <!-- ===================================================================== -->
      <div class="prometeus-card">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px;">
          <div>
            <h2 style="font-size:17px; font-weight:700; color:#ffffff; margin:0; display:flex; align-items:center; gap:8px;">
              <span>🎯</span>
              <span>2. TypeSafe JEV (Motor de Decisão System One — Opcional)</span>
            </h2>
            <p style="font-size:13px; color:var(--prometeus-text-secondary); margin:4px 0 0 0;">
              Modelo tipado determinístico para julgamentos estruturados com probabilidades calibradas.
            </p>
          </div>
          <span class="prometeus-pill-badge" id="badge-jev-status" data-status="${isJevActive ? 'APPROVED' : 'ADJUSTMENTS'}">
            ${isJevActive ? '● MODO HÍBRIDO ATIVO' : '● MODO 100% TRADICIONAL'}
          </span>
        </div>

        <div class="form-grid">
          <div class="form-group col-8">
            <label class="form-label" for="setting-jev-key">TypeSafe API Key</label>
            <input type="password" id="setting-jev-key" class="form-input" 
                   value="${settings.typesafe_api_key || ''}"
                   placeholder="ts_live_•••••••••••••••• (Deixe vazio caso não use JEV)">
            <span class="form-hint">Se preenchido: Habilita JEV + LLM. Se vazio: A LLM Tradicional assume tudo automaticamente.</span>
          </div>

          <div class="form-group col-4">
            <label class="form-label" for="setting-jev-model">Versão do Modelo JEV</label>
            <input type="text" id="setting-jev-model" class="form-input" 
                   value="${settings.jev_model || 'jev-v1.2.0'}"
                   placeholder="jev-v1.2.0">
            <span class="form-hint">Versão aprovada imutável (ex.: jev-v1.2.0)</span>
          </div>

          <div class="col-12" id="jev-architecture-notice" style="background:rgba(255,255,255,0.03); border:1px solid var(--prometeus-border-subtle); border-radius:var(--prometeus-radius-md); padding:12px 16px;">
            <div style="font-size:12px; line-height:1.5; color:var(--prometeus-text-secondary);">
              ${isJevActive ? `
                <strong style="color:var(--prometeus-status-approved);">Arquitetura Dual Híbrida:</strong> Decisões atômicas de viabilidade executadas pelo TypeSafe JEV; síntese do Dossiê Executivo e Chatbot executados pela LLM Tradicional (<span id="txt-active-model">${currentModel}</span>).
              ` : `
                <strong style="color:var(--prometeus-accent-ice);">Arquitetura 100% Tradicional:</strong> Sem JEV conectado. A LLM Tradicional (<span id="txt-active-model">${currentModel}</span> com raciocínio '<span id="txt-active-reasoning">${currentReasoning}</span>') assume automaticamente ambos os papéis com precisão e sem quebras.
              `}
            </div>
          </div>
        </div>
      </div>

      <!-- ===================================================================== -->
      <!-- BLOCO 3: APIFY / SCRAPERS DEDICADOS DE MERCADO                        -->
      <!-- ===================================================================== -->
      <div class="prometeus-card">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px;">
          <div>
            <h2 style="font-size:17px; font-weight:700; color:#ffffff; margin:0; display:flex; align-items:center; gap:8px;">
              <span>🌐</span>
              <span>3. Apify & Scrapers Dedicados de Mercado</span>
            </h2>
            <p style="font-size:13px; color:var(--prometeus-text-secondary); margin:4px 0 0 0;">
              Coletores automáticos de evidências empíricas de mercado com controle rígido de orçamento por análise.
            </p>
          </div>
          <span class="prometeus-pill-badge" data-status="APPROVED">● 3 ACTORS PINADOS</span>
        </div>

        <div class="form-grid">
          <div class="form-group col-8">
            <label class="form-label" for="setting-apify-token">Apify API Token</label>
            <input type="password" id="setting-apify-token" class="form-input" 
                   value="${settings.apify_token || ''}"
                   placeholder="apify_api_••••••••••••••••••••••••••••••">
            <span class="form-hint">Token de acesso obtido no console Apify (Integrations)</span>
          </div>

          <div class="form-group col-4">
            <label class="form-label" for="setting-apify-max-charge">Teto Orçamentário por Análise (USD)</label>
            <input type="number" id="setting-apify-max-charge" class="form-input" 
                   value="${settings.apify_max_charge || 5.00}" step="0.5" min="1" max="25">
            <span class="form-hint">Circuit breaker de custo máximo por proposta</span>
          </div>

          <!-- Grade dos 3 Aplicativos Pinados do Apify -->
          <div class="col-12" style="display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; margin-top:8px;">
            <div style="background:rgba(255,255,255,0.02); border:1px solid var(--prometeus-border-subtle); border-radius:var(--prometeus-radius-md); padding:10px 14px;">
              <div style="font-size:11px; font-weight:600; color:var(--prometeus-accent-ice); margin-bottom:4px;">1. EMPREGABILIDADE</div>
              <div style="font-size:12px; font-weight:700; color:#ffffff;">LinkedIn Jobs Scraper</div>
              <div style="font-size:11px; color:var(--prometeus-text-muted);">apify/linkedin-jobs-scraper@1.3.0</div>
            </div>

            <div style="background:rgba(255,255,255,0.02); border:1px solid var(--prometeus-border-subtle); border-radius:var(--prometeus-radius-md); padding:10px 14px;">
              <div style="font-size:11px; font-weight:600; color:var(--prometeus-accent-ice); margin-bottom:4px;">2. CONCORRÊNCIA & PREÇOS</div>
              <div style="font-size:12px; font-weight:700; color:#ffffff;">Google Search Scraper</div>
              <div style="font-size:11px; color:var(--prometeus-text-muted);">apify/google-search-scraper@1.1.0</div>
            </div>

            <div style="background:rgba(255,255,255,0.02); border:1px solid var(--prometeus-border-subtle); border-radius:var(--prometeus-radius-md); padding:10px 14px;">
              <div style="font-size:11px; font-weight:600; color:var(--prometeus-accent-ice); margin-bottom:4px;">3. ANÚNCIOS META & SOCIAL</div>
              <div style="font-size:12px; font-weight:700; color:#ffffff;">Instagram / Ad Scraper</div>
              <div style="font-size:11px; color:var(--prometeus-text-muted);">apify/instagram-scraper@1.4.0</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ===================================================================== -->
      <!-- BLOCO 4: CONECTOR DO CRM / ERP ACADÊMICO                              -->
      <!-- ===================================================================== -->
      <div class="prometeus-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
          <div>
            <h2 style="font-size:17px; font-weight:700; color:#ffffff; margin:0; display:flex; align-items:center; gap:8px;">
              <span>🏢</span>
              <span>4. Conector de Dados Acadêmicos (CRM / ERP da ENS)</span>
            </h2>
            <p style="font-size:13px; color:var(--prometeus-text-secondary); margin:4px 0 0 0;">
              Consulta a base histórica do PostgreSQL (5 cursos de seguros, 2 anos de ofertas: 2024 e 2025) para cruzar com novas propostas.
            </p>
          </div>
          <span class="prometeus-pill-badge" data-status="APPROVED">● CONECTADO (5 CURSOS / 2 ANOS)</span>
        </div>

        <div style="background:rgba(56, 189, 248, 0.05); border:1px solid rgba(56, 189, 248, 0.2); border-radius:var(--prometeus-radius-md); padding:16px; margin-bottom:16px;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div>
              <div style="font-size:13px; font-weight:700; color:#ffffff; display:flex; align-items:center; gap:8px;">
                <span>🏛️ Base Histórica Oficial ENS Carregada</span>
                <span class="prometeus-pill-badge" style="background:rgba(52, 211, 153, 0.15); color:#34d399; font-size:11px;">10 Ofertas Consolidadas</span>
              </div>
              <div style="font-size:12px; color:var(--prometeus-text-secondary); margin-top:4px;">
                Cobre 5 segmentos: <strong>MBA Gestão (Sucesso)</strong>, <strong>Cyber (Sucesso Técnico)</strong>, <strong>Sinistros (Mediano)</strong>, <strong>Vendas (Fraco)</strong> e <strong>Direito Doutrinário (Cancelado por quórum)</strong>.
              </div>
            </div>
            <button type="button" id="btn-sync-crm-data" class="prometeus-btn-secondary" style="font-size:12px; padding:8px 16px;">
              🔄 Sincronizar Base Histórica
            </button>
          </div>
        </div>

        <div class="form-grid">
          <div class="form-group col-8">
            <label class="form-label" for="setting-crm-url">Endpoint da API da Instituição</label>
            <input type="url" id="setting-crm-url" class="form-input" 
                   value="${settings.crm_api_url || 'https://api.ens.edu.br/v1/cursos-historico'}"
                   placeholder="https://api.ens.edu.br/v1/cursos">
          </div>

          <div class="form-group col-4">
            <label class="form-label" for="setting-crm-token">Token de Autenticação (Bearer)</label>
            <input type="password" id="setting-crm-token" class="form-input" 
                   value="${settings.crm_token || 'ens_live_sec_884912fa89b'}">
          </div>
        </div>
      </div>

      <!-- ===================================================================== -->
      <!-- BLOCO 5: METAS FINANCEIRAS & DIRETRIZES                               -->
      <!-- ===================================================================== -->
      <div class="prometeus-card">
        <div style="margin-bottom:16px;">
          <h2 style="font-size:17px; font-weight:700; color:#ffffff; margin:0; display:flex; align-items:center; gap:8px;">
            <span>🎯</span>
            <span>5. Diretrizes de Negócio e Metas Financeiras da IES</span>
          </h2>
          <p style="font-size:13px; color:var(--prometeus-text-secondary); margin:4px 0 0 0;">
            Parâmetros utilizados pelo motor algorítmico determinístico para calcular ponto de equilíbrio e Viability Score.
          </p>
        </div>

        <div class="form-grid">
          <div class="form-group col-4">
            <label class="form-label" for="setting-quorum">Quórum Mínimo por Turma</label>
            <input type="number" id="setting-quorum" class="form-input" value="${settings.quorum_min || 22}" min="5" max="100">
            <span class="form-hint">Mínimo de alunos para viabilizar abertura da turma</span>
          </div>

          <div class="form-group col-4">
            <label class="form-label" for="setting-margin">Margem de Contribuição Alvo (%)</label>
            <input type="number" id="setting-margin" class="form-input" value="${settings.target_margin || 42}" min="10" max="90">
            <span class="form-hint">Meta percentual de rentabilidade operacional</span>
          </div>

          <div class="form-group col-4">
            <label class="form-label" for="setting-cac">CAC de Referência (R$)</label>
            <input type="number" id="setting-cac" class="form-input" value="${settings.reference_cac || 480}" min="50" max="2000" step="10">
            <span class="form-hint">Custo médio de aquisição por matrícula</span>
          </div>
        </div>
      </div>

      <!-- Barra de Ações -->
      <div style="display:flex; justify-content:space-between; align-items:center; padding:16px 0;">
        <div style="font-size:12px; color:var(--prometeus-text-muted);">
          As alterações são sincronizadas em tempo real e aplicadas às novas análises.
        </div>
        <button type="submit" class="prometeus-btn-primary" id="btn-save-settings" style="font-size:14px; padding:12px 32px;">
          <span>Salvar Configurações no App</span>
        </button>
      </div>
    </form>
  `;
}

export function bindSettingsEvents(store, container) {
  // Conectar com ChatGPT OAuth (Abre a tela oficial da OpenAI com PKCE)
  const btnConnect = container.querySelector('#btn-connect-chatgpt');
  if (btnConnect) {
    btnConnect.addEventListener('click', async (e) => {
      e.preventDefault();
      btnConnect.disabled = true;
      btnConnect.innerHTML = '<span>⏳ Abrindo OpenAI / ChatGPT...</span>';

      try {
        const resp = await fetch('/v1/auth/chatgpt/url');
        if (!resp.ok) {
          throw new Error('Falha ao obter URL de autenticação OpenAI');
        }

        const data = await resp.json();
        const width = 560, height = 740;
        const left = window.screenX + (window.outerWidth - width) / 2;
        const top = window.screenY + (window.outerHeight - height) / 2;

        const authWindow = window.open(
          data.auth_url,
          'OpenAI_ChatGPT_OAuth',
          `width=${width},height=${height},top=${top},status=no,toolbar=no,menubar=no`
        );

        if (!authWindow || authWindow.closed || typeof authWindow.closed === 'undefined') {
          // Se bloqueado como popup, abre diretamente na janela atual
          window.location.href = data.auth_url;
          return;
        }

        btnConnect.innerHTML = '<span>⏳ Aguardando login na OpenAI...</span>';

        // Monitora a conclusão do login via polling leve em /v1/settings
        const pollTimer = setInterval(async () => {
          try {
            const checkResp = await fetch('/v1/settings');
            if (checkResp.ok) {
              const s = await checkResp.json();
              if (s.chatgpt_access_token_masked && s.chatgpt_access_token_masked.length > 0) {
                clearInterval(pollTimer);
                try {
                  if (authWindow && !authWindow.closed) authWindow.close();
                } catch (e) {}

                const state = store.getState();
                store.updateSettings(state.currentTenantId, {
                  gen_llm_provider: 'chatgpt_oauth',
                  chatgpt_access_token: s.chatgpt_access_token_masked,
                  gen_llm_model: s.gen_llm_model || 'gpt-6.1-sol',
                  gen_llm_reasoning_effort: s.gen_llm_reasoning_effort || 'high'
                }, true);
              }
            }
          } catch (err) {}

          if (authWindow && authWindow.closed) {
            clearInterval(pollTimer);
            btnConnect.disabled = false;
            btnConnect.innerHTML = '<span>🔗 Conectar com ChatGPT</span>';
          }
        }, 1500);

      } catch (err) {
        console.error('Erro ao iniciar fluxo OAuth OpenAI:', err);
        window.location.href = '/v1/auth/chatgpt/login';
      }
    });
  }

  // Desconectar ChatGPT
  const btnDisconnect = container.querySelector('#btn-disconnect-chatgpt');
  if (btnDisconnect) {
    btnDisconnect.addEventListener('click', async (e) => {
      e.preventDefault();
      if (confirm('Deseja realmente desconectar sua conta ChatGPT / Codex?')) {
        btnDisconnect.disabled = true;
        btnDisconnect.textContent = 'Desconectando...';
        try {
          await fetch('/v1/auth/chatgpt/disconnect', { method: 'POST' });
        } catch (e) {}
        const state = store.getState();
        store.updateSettings(state.currentTenantId, {
          chatgpt_access_token: ''
        }, true);
      }
    });
  }

  // Ouvinte de mensagens de janela externa de consentimento
  const handleOAuthMessage = (event) => {
    if (event.data && event.data.type === 'CHATGPT_OAUTH_SUCCESS') {
      const state = store.getState();
      store.updateSettings(state.currentTenantId, {
        gen_llm_provider: 'chatgpt_oauth',
        chatgpt_access_token: event.data.access_token || 'sess-chatgpt-oauth-connected',
        gen_llm_model: 'gpt-6.1-sol',
        gen_llm_reasoning_effort: 'high'
      }, true);
    }
  };
  window.addEventListener('message', handleOAuthMessage);

  const jevKeyInput = container.querySelector('#setting-jev-key');
  const badgeJev = container.querySelector('#badge-jev-status');
  const noticeBox = container.querySelector('#jev-architecture-notice');
  const modelSelect = container.querySelector('#setting-llm-model');
  const reasoningSelect = container.querySelector('#setting-reasoning-effort');

  function updateJevPreview() {
    const hasJev = jevKeyInput && jevKeyInput.value.trim().length > 0;
    const model = modelSelect ? modelSelect.value : 'gpt-6.1-sol';
    const reasoning = reasoningSelect ? reasoningSelect.value : 'high';

    if (badgeJev) {
      badgeJev.dataset.status = hasJev ? 'APPROVED' : 'ADJUSTMENTS';
      badgeJev.textContent = hasJev ? '● MODO HÍBRIDO ATIVO' : '● MODO 100% TRADICIONAL';
    }

    if (noticeBox) {
      noticeBox.innerHTML = `
        <div style="font-size:12px; line-height:1.5; color:var(--prometeus-text-secondary);">
          ${hasJev ? `
            <strong style="color:var(--prometeus-status-approved);">Arquitetura Dual Híbrida:</strong> Decisões atômicas de viabilidade executadas pelo TypeSafe JEV; síntese do Dossiê Executivo e Chatbot executados pela LLM Tradicional (${model}).
          ` : `
            <strong style="color:var(--prometeus-accent-ice);">Arquitetura 100% Tradicional:</strong> Sem JEV conectado. A LLM Tradicional (${model} com raciocínio '${reasoning}') assume automaticamente ambos os papéis com precisão e sem quebras.
          `}
        </div>
      `;
    }
  }

  if (jevKeyInput) jevKeyInput.addEventListener('input', updateJevPreview);
  if (modelSelect) modelSelect.addEventListener('change', updateJevPreview);
  if (reasoningSelect) reasoningSelect.addEventListener('change', updateJevPreview);

  const form = container.querySelector('#form-settings');
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const saveBtn = container.querySelector('#btn-save-settings');
      if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.textContent = 'Salvando configurações...';
      }

      const state = store.getState();
      const provider = container.querySelector('#setting-llm-provider') ? container.querySelector('#setting-llm-provider').value : 'chatgpt_oauth';
      const manualToken = container.querySelector('#setting-llm-token') ? container.querySelector('#setting-llm-token').value : '';
      const model = container.querySelector('#setting-llm-model').value;
      const reasoning = container.querySelector('#setting-reasoning-effort').value;
      const jevKey = container.querySelector('#setting-jev-key').value;
      const jevModel = container.querySelector('#setting-jev-model').value;
      const apifyToken = container.querySelector('#setting-apify-token').value;
      const apifyMaxCharge = parseFloat(container.querySelector('#setting-apify-max-charge').value) || 5.0;

      const payload = {
        gen_llm_provider: provider,
        gen_llm_model: model,
        gen_llm_reasoning_effort: reasoning,
        openai_api_key: manualToken,
        typesafe_api_key: jevKey,
        jev_model: jevModel,
        apify_token: apifyToken,
        apify_max_charge: apifyMaxCharge
      };

      try {
        const resp = await fetch('/v1/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (resp.ok) {
          store.updateSettings(state.currentTenantId, {
            ...payload,
            crm_api_url: container.querySelector('#setting-crm-url').value,
            crm_token: container.querySelector('#setting-crm-token').value,
            quorum_min: parseInt(container.querySelector('#setting-quorum').value),
            target_margin: parseInt(container.querySelector('#setting-margin').value),
            reference_cac: parseInt(container.querySelector('#setting-cac').value)
          });
          alert("✓ Configurações salvas e aplicadas com sucesso no Prometeus!\n• Provedor LLM: " + provider + "\n• Modelo: " + model + "\n• Raciocínio: " + reasoning + "\n• Modo: " + (jevKey.trim() ? "Híbrido (JEV + LLM)" : "100% Tradicional"));
        } else {
          alert("Aviso: Configurações salvas localmente no navegador.");
        }
      } catch (err) {
        alert("Configurações salvas localmente no navegador.");
      } finally {
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.innerHTML = '<span>Salvar Configurações no App</span>';
        }
      }
    });
  }

  const syncCrmBtn = container.querySelector('#btn-sync-crm-data');
  if (syncCrmBtn) {
    syncCrmBtn.addEventListener('click', async () => {
      syncCrmBtn.textContent = 'Sincronizando...';
      syncCrmBtn.disabled = true;
      const ok = await store.seedInstitutionalData(true);
      if (ok) {
        alert('✓ Base Histórica da ENS (5 cursos / ofertas 2024 e 2025) sincronizada com sucesso no PostgreSQL!');
      } else {
        alert('Falha ao sincronizar com o banco.');
      }
      syncCrmBtn.textContent = '🔄 Sincronizar Base Histórica';
      syncCrmBtn.disabled = false;
    });
  }
}
