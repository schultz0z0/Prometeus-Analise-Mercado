/** Estado reativo da interface, alimentado exclusivamente pela API. */

import {
  INITIAL_TENANTS,
  INITIAL_SETTINGS,
  INITIAL_COURSES,
  INITIAL_HISTORICAL_COURSES
} from './mock-data.js?v=20261027';

const REAL_COURSES_STORAGE_KEY = 'prometeus_courses_real_v2';

function numericOrNull(value) {
  if (value === '' || value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function nowLabel() {
  return new Date().toLocaleTimeString('pt-BR');
}

class PrometeusStore {
  constructor() {
    this.listeners = [];
    this.loadState();
  }

  loadState() {
    let savedSettings = INITIAL_SETTINGS;
    let savedCourses = INITIAL_COURSES;
    try {
      savedSettings = JSON.parse(localStorage.getItem('prometeus_settings')) || INITIAL_SETTINGS;
      savedCourses = JSON.parse(localStorage.getItem(REAL_COURSES_STORAGE_KEY)) || INITIAL_COURSES;
    } catch (error) {
      console.warn('Estado local inválido; iniciando interface limpa.', error);
    }
    this.state = {
      tenants: INITIAL_TENANTS,
      currentTenantId: localStorage.getItem('prometeus_tenant') || 'ens',
      settings: savedSettings,
      courses: savedCourses,
      historicalCourses: INITIAL_HISTORICAL_COURSES,
      portfolioTab: 'historical',
      activeCourseId: null,
      currentDossier: null,
      currentView: 'portfolio',
      liveJob: null
    };
  }

  saveState() {
    try {
      localStorage.setItem('prometeus_tenant', this.state.currentTenantId);
      localStorage.setItem('prometeus_settings', JSON.stringify(this.state.settings));
      localStorage.setItem(REAL_COURSES_STORAGE_KEY, JSON.stringify(this.state.courses));
    } catch (error) {
      console.warn('Falha ao salvar preferências locais.', error);
    }
  }

  getState() { return this.state; }

  subscribe(listener) {
    this.listeners.push(listener);
    return () => { this.listeners = this.listeners.filter(item => item !== listener); };
  }

  notify() {
    this.saveState();
    this.listeners.forEach(listener => listener(this.state));
  }

  setTenant(tenantId) {
    if (this.state.tenants.some(tenant => tenant.id === tenantId)) {
      this.state.currentTenantId = tenantId;
      this.notify();
    }
  }

  setView(viewName, params = {}) {
    this.state.currentView = viewName;
    if (params.courseId) {
      this.state.activeCourseId = params.courseId;
      const course = this.state.courses.find(item => item.id === params.courseId);
      this.state.currentDossier = course?.dossier || null;
    }
    this.notify();
  }

  setPortfolioTab(tab) {
    this.state.portfolioTab = tab;
    this.notify();
  }

  async loadHistoricalCourses() {
    try {
      const response = await fetch(`/v1/institutional/courses?tenant_id=${encodeURIComponent(this.state.currentTenantId)}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      this.state.historicalCourses = Array.isArray(data.courses) ? data.courses : [];
      this.notify();
    } catch (error) {
      console.warn('Base histórica indisponível.', error);
      this.state.historicalCourses = [];
      this.notify();
    }
  }

  async loadCompletedAnalyses() {
    try {
      const response = await fetch(`/v1/analyses?tenant_id=${encodeURIComponent(this.state.currentTenantId)}`);
      if (!response.ok) return;
      const data = await response.json();
      this.analysisCatalog = Array.isArray(data.items) ? data.items : [];
      const verified = this.analysisCatalog.filter(
        item => item.status === 'COMPLETED' && item.dossier && item.dossier.status === 'VERIFIED'
      );
      if (verified.length > 0) {
        this.state.courses = verified;
        if (!this.state.activeCourseId) {
          this.state.activeCourseId = verified[0].id;
          this.state.currentDossier = verified[0].dossier;
        }
        this.notify();
      }
    } catch (error) {
      console.warn('Não foi possível sincronizar diagnósticos concluídos.', error);
    }
  }

  async seedInstitutionalData(reset = false) {
    try {
      const response = await fetch(`/v1/institutional/seed?tenant_id=${encodeURIComponent(this.state.currentTenantId)}&reset=${reset}`, { method: 'POST' });
      if (!response.ok) return false;
      await this.loadHistoricalCourses();
      return true;
    } catch (error) {
      console.error('Falha ao carregar a base histórica de teste.', error);
      return false;
    }
  }

  updateSettings(tenantId, newSettings, shouldNotify = true) {
    this.state.settings[tenantId] = { ...this.state.settings[tenantId], ...newSettings };
    if (shouldNotify) this.notify(); else this.saveState();
  }

  async syncBackendSettings() {
    if (this._syncingBackendSettings || this._hasSyncedBackendSettings) return;
    this._syncingBackendSettings = true;
    try {
      const response = await fetch('/v1/settings');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const settings = await response.json();
      this.updateSettings(this.state.currentTenantId, {
        gen_llm_provider: settings.gen_llm_provider || '',
        gen_llm_model: settings.gen_llm_model || '',
        ...(['openai', 'openrouter'].includes(settings.gen_llm_provider) ? { api_llm_model: settings.gen_llm_model || '' } : {}),
        gen_llm_reasoning_effort: settings.gen_llm_reasoning_effort || '',
        chatgpt_oauth_connected: Boolean(settings.chatgpt_oauth_connected),
        chatgpt_oauth_email: settings.chatgpt_oauth_email || '',
        chatgpt_oauth_model: settings.chatgpt_oauth_model || '',
        openai_api_key_masked: settings.openai_api_key_masked || '',
        apify_token_masked: settings.apify_token_masked || '',
        is_jev_configured: Boolean(settings.is_jev_configured),
        jev_model: settings.jev_model || '',
        apify_max_charge: settings.apify_max_charge ?? null
      }, false);
      this._hasSyncedBackendSettings = true;
    } catch (error) {
      console.warn('Configuração do backend indisponível.', error);
    } finally {
      this._syncingBackendSettings = false;
    }
  }

  async loadChatGPTModels(force = false) {
    if (this._chatgptModelRequest) return this._chatgptModelRequest;
    if (!force && this.chatgptModelsCatalog?.status === 'ready') return this.chatgptModelsCatalog;
    this.chatgptModelsCatalog = { status: 'loading', models: [], error: '' };
    this._chatgptModelRequest = (async () => {
      try {
        const response = await fetch('/v1/auth/chatgpt/models');
        const body = await response.json();
        if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : `HTTP ${response.status}`);
        const models = (Array.isArray(body.models) ? body.models : []).filter(model => typeof model.slug === 'string' && model.slug);
        if (!models.length) throw new Error('A conta não retornou modelos disponíveis. Atualize a lista.');
        this.chatgptModelsCatalog = { status: 'ready', models, error: '', selected_model: body.selected_model || '' };
      } catch (error) {
        this.chatgptModelsCatalog = { status: 'error', models: [], error: error.message || 'Não foi possível consultar os modelos da conta.' };
      } finally {
        this._chatgptModelRequest = null;
      }
      return this.chatgptModelsCatalog;
    })();
    return this._chatgptModelRequest;
  }

  async openAnalysis(analysisId) {
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(analysisId || '')) return false;
    const controller = new AbortController();
    const deadline = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(`/v1/analyses/${encodeURIComponent(analysisId)}`, {signal: controller.signal});
      if (!response.ok) return false;
      const data = await response.json();
      if (data.tenant_id !== this.state.currentTenantId) return false;
      this.state.liveJob = {
        id: data.analysis_id, name: data.course_name, status: data.status,
        created_at: data.created_at, steps: data.steps || [], toolRuns: data.tool_runs || [],
        blocking: data.blocking || null, error: data.blocking?.reason || null,
        logs: [`[${nowLabel()}] Acompanhamento reaberto a partir dos checkpoints persistidos.`]
      };
      this.state.currentView = 'live';
      this.notify();
      const catalogCourse = this.analysisCatalog?.find(item => item.id === analysisId);
      this.pollAnalysisStatus(analysisId, {
        name: data.course_name, area: catalogCourse?.area, level: catalogCourse?.level,
        modality: catalogCourse?.modality, ticket: catalogCourse?.ticket,
        duration: catalogCourse?.duration_months
      });
      return true;
    } catch (error) {
      return false;
    } finally {
      clearTimeout(deadline);
    }
  }

  async startAnalysis(courseInput) {
    const job = {
      id: `pending_${Date.now().toString(36)}`,
      name: courseInput.name,
      status: 'SUBMITTING',
      created_at: new Date().toISOString(),
      steps: [],
      toolRuns: [],
      blocking: null,
      error: null,
      logs: [`[${nowLabel()}] Enviando proposta para a API do Prometeus.`]
    };
    this.state.liveJob = job;
    this.state.currentView = 'live';
    this.notify();

    const payload = {
      course_name: courseInput.name,
      tenant_id: this.state.currentTenantId,
      proposal_data: {
        curriculum: courseInput.curriculum || '',
        curriculum_file_name: courseInput.curriculum_file_name || '',
        area: courseInput.area || '',
        level: courseInput.level || '',
        modality: courseInput.modality || '',
        ticket: numericOrNull(courseInput.ticket),
        price_period: courseInput.price_period || 'monthly',
        duration_months: numericOrNull(courseInput.duration),
        installments_count: numericOrNull(courseInput.installments),
        audience: courseInput.audience || '',
        competitors: courseInput.competitors || ''
      }
    };

    try {
      const response = await fetch('/v1/analyses', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Idempotency-Key': crypto.randomUUID() },
        body: JSON.stringify(payload)
      });
      if (!response.ok) throw new Error(`A API recusou a solicitação (HTTP ${response.status}).`);
      const data = await response.json();
      job.id = data.analysis_id;
      job.status = data.status;
      const url = new URL(window.location.href);
      url.searchParams.set('analysis', job.id);
      window.history.replaceState(null, '', url);
      job.logs.push(`[${nowLabel()}] Análise ${job.id} aceita e enviada ao worker.`);
      this.notify();
      this.pollAnalysisStatus(job.id, courseInput);
    } catch (error) {
      job.status = 'FAILED';
      job.error = error.message;
      job.logs.push(`[${nowLabel()}] Falha real: ${error.message}`);
      this.notify();
    }
  }

  pollAnalysisStatus(analysisId, courseInput) {
    let pending = false;
    const logged = new Set();
    const poll = setInterval(async () => {
      const job = this.state.liveJob;
      if (!job || job.id !== analysisId) return clearInterval(poll);
      if (pending) return;
      pending = true;
      const controller = new AbortController();
      const deadline = setTimeout(() => controller.abort(), 15000);
      try {
        const response = await fetch(`/v1/analyses/${analysisId}`, {signal: controller.signal});
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        job.status = data.status;
        job.steps = data.steps || [];
        job.toolRuns = data.tool_runs || [];
        job.blocking = data.blocking || null;
        job.connectionWarning = null;
        job.error = null;
        job.steps.forEach(step => {
          const key = `${step.step_number}:${step.status}`;
          if (!logged.has(key)) {
            logged.add(key);
            job.logs.push(`[${nowLabel()}] Etapa ${step.step_number} — ${step.name}: ${step.status}.`);
          }
        });
        this.notify();
        if (data.status === 'COMPLETED') {
          await this.completeRealAnalysis(analysisId, data, courseInput, controller.signal);
          clearInterval(poll);
        } else if (['BLOCKED', 'FAILED', 'WAITING_FOR_INPUT', 'CANCELLED'].includes(data.status)) {
          clearInterval(poll);
          job.error = data.blocking?.reason || `Processamento encerrado em ${data.status}.`;
          job.logs.push(`[${nowLabel()}] ${job.error}`);
          this.notify();
        }
      } catch (error) {
        job.connectionWarning = `Não foi possível atualizar o progresso: ${error.message}. Tentaremos novamente automaticamente.`;
        this.notify();
      } finally {
        clearTimeout(deadline);
        pending = false;
      }
    }, 2000);
  }

  async completeRealAnalysis(analysisId, analysisData, courseInput, signal) {
    const response = await fetch(`/v1/analyses/${analysisId}/dossier`, {signal});
    if (response.status >= 500 || response.status === 429) throw new Error(`Dossiê temporariamente indisponível (HTTP ${response.status})`);
    if (!response.ok) {
      this.state.liveJob.status = 'FAILED';
      this.state.liveJob.error = `Análise concluída sem dossiê verificável (HTTP ${response.status}).`;
      this.notify();
      return;
    }
    const dossier = await response.json();
    if (dossier.status !== 'VERIFIED' || !dossier.scoring) {
      this.state.liveJob.status = 'FAILED';
      this.state.liveJob.error = 'O backend não retornou um dossiê factual verificado com scoring.';
      this.notify();
      return;
    }
    const scoring = dossier.scoring;
    const course = {
      id: analysisId,
      name: courseInput.name,
      area: courseInput.area || '',
      level: courseInput.level || '',
      modality: courseInput.modality || '',
      ticket: numericOrNull(courseInput.ticket),
      duration_months: numericOrNull(courseInput.duration),
      status: analysisData.status,
      recommendation: scoring.recommendation,
      viability_score: scoring.viability_score,
      coverage_index: scoring.coverage_score,
      confidence_index: scoring.confidence_score,
      created_at: dossier.created_at,
      dossier
    };
    this.state.courses = [course, ...this.state.courses.filter(item => item.id !== analysisId)];
    this.state.activeCourseId = analysisId;
    this.state.currentDossier = dossier;
    this.state.liveJob = null;
    this.state.currentView = 'dossier';
    this.notify();
  }

  async registerHumanDecision(courseId, decision, notes, deciderName) {
    const response = await fetch(`/v1/analyses/${courseId}/decisions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: deciderName,
        user_role: 'academic_committee',
        decision,
        rationale: notes,
        adjustments: {}
      })
    });
    if (!response.ok) throw new Error(`Decisão não registrada (HTTP ${response.status}).`);
    return response.json();
  }
}

export const store = new PrometeusStore();
