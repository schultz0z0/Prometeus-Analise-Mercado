/**
 * PROMETEUS INTELLIGENCE PLATFORM — APP CONTROLLER
 * Orquestrador principal da aplicação SPA, roteamento e renderização reativa.
 */

import { store } from './store.js?v=20261027';
import { renderPortfolioView, bindPortfolioEvents } from './views/portfolio-view.js?v=20261027';
import { renderIntakeView, bindIntakeEvents } from './views/intake-view.js?v=20261027';
import { renderLiveView, bindLiveEvents } from './views/live-view.js?v=20261027';
import { renderDossierView, bindDossierEvents } from './views/dossier-view.js?v=20261027';
import { renderSettingsView, bindSettingsEvents } from './views/settings-view.js?v=20261027';
import { renderEvidenceDrawer, bindEvidenceDrawerEvents } from './components/evidence-drawer.js?v=20261027';

class PrometeusApp {
  constructor() {
    this.root = document.getElementById('app-root');
    this.init();
  }

  init() {
    // Inscreve no store para re-renderizar quando o estado mudar
    store.subscribe((state) => {
      this.render(state);
    });

    // Render inicial
    this.render(store.getState());

    // Sincroniza configurações persistidas no backend apenas uma vez
    store.syncBackendSettings();
    store.loadHistoricalCourses();
  }

  render(state) {
    const currentTenant = state.tenants.find(t => t.id === state.currentTenantId) || state.tenants[0];
    const coursesCount = state.courses.length;

    this.root.innerHTML = `
      <div class="app-container">
        <!-- Header Corporativo -->
        <header class="app-header">
          <div class="header-brand-group">
            <img src="./assets/brand/prometeus-logo-primary.png" 
                 alt="Prometeus — Inteligência para Produtos Educacionais" 
                 class="header-logo" 
                 id="logo-home">

            <!-- Seletor de Tenant da Instituição -->
            <div class="tenant-selector" id="tenant-dropdown-trigger" title="Alternar ambiente institucional">
              <span aria-hidden="true">🏛️</span>
              <span>Ambiente: <strong>${currentTenant.name}</strong></span>
              <span style="font-size:10px; color:var(--prometeus-text-muted);">▼</span>
            </div>
          </div>

          <div class="header-actions">
            <div style="display:flex; align-items:center; gap:8px; font-size:13px; color:var(--prometeus-text-secondary);">
              <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--prometeus-status-approved); box-shadow:0 0 8px var(--prometeus-status-approved);"></span>
              <span>Status detalhado disponível durante cada análise</span>
            </div>

            <button class="prometeus-btn-secondary" id="btn-header-settings" style="padding:6px 14px; font-size:13px; min-height:36px;">
              <span>⚙️ Integrações</span>
            </button>
          </div>
        </header>

        <!-- Barra de Navegação Superior (Tabs de Módulos) -->
        <nav class="app-nav-bar" aria-label="Navegação Principal">
          <div class="nav-tabs-container">
            <button class="nav-tab-item ${state.currentView === 'validate' || state.currentView === 'live' ? 'active' : ''}" id="nav-tab-validate">
              <span>🚀 Validar Novo Curso</span>
            </button>

            <button class="nav-tab-item ${state.currentView === 'portfolio' ? 'active' : ''}" id="nav-tab-portfolio">
              <span>📊 Minhas Análises & Portfólio</span>
              <span class="nav-tab-badge">${coursesCount}</span>
            </button>

            ${state.activeCourseId ? `
              <button class="nav-tab-item ${state.currentView === 'dossier' ? 'active' : ''}" id="nav-tab-dossier">
                <span>📄 Dossiê da Oferta</span>
              </button>
            ` : ''}

            <button class="nav-tab-item ${state.currentView === 'settings' ? 'active' : ''}" id="nav-tab-settings">
              <span>⚙️ Configurações & Conectores</span>
            </button>
          </div>
        </nav>

        <!-- Área Principal de Visualização Dinâmica -->
        <main class="app-main" id="view-container">
          ${this.renderActiveView(state)}
        </main>

        <!-- Evidence Drawer Off-Canvas -->
        <div id="evidence-drawer-mount">
          ${renderEvidenceDrawer(store)}
        </div>
      </div>
    `;

    this.bindEvents(state);
  }

  renderActiveView(state) {
    switch (state.currentView) {
      case 'validate':
        return renderIntakeView(store);
      case 'live':
        return renderLiveView(store);
      case 'dossier':
        return renderDossierView(store);
      case 'settings':
        return renderSettingsView(store);
      case 'portfolio':
      default:
        return renderPortfolioView(store);
    }
  }

  bindEvents(state) {
    const viewContainer = document.getElementById('view-container');
    const drawerMount = document.getElementById('evidence-drawer-mount');

    // Logo vai para o portfólio
    const logo = document.getElementById('logo-home');
    if (logo) {
      logo.addEventListener('click', () => store.setView('portfolio'));
    }

    // Navegação de tabs
    const tabValidate = document.getElementById('nav-tab-validate');
    const tabPortfolio = document.getElementById('nav-tab-portfolio');
    const tabDossier = document.getElementById('nav-tab-dossier');
    const tabSettings = document.getElementById('nav-tab-settings');
    const btnHeaderSettings = document.getElementById('btn-header-settings');

    if (tabValidate) tabValidate.addEventListener('click', () => store.setView('validate'));
    if (tabPortfolio) tabPortfolio.addEventListener('click', () => store.setView('portfolio'));
    if (tabDossier) tabDossier.addEventListener('click', () => store.setView('dossier'));
    if (tabSettings) tabSettings.addEventListener('click', () => store.setView('settings'));
    if (btnHeaderSettings) btnHeaderSettings.addEventListener('click', () => store.setView('settings'));

    // Binda eventos da view ativa
    if (state.currentView === 'portfolio') {
      bindPortfolioEvents(store, viewContainer);
    } else if (state.currentView === 'validate') {
      bindIntakeEvents(store, viewContainer);
    } else if (state.currentView === 'live') {
      bindLiveEvents(store, viewContainer);
    } else if (state.currentView === 'dossier') {
      bindDossierEvents(store, viewContainer);
    } else if (state.currentView === 'settings') {
      bindSettingsEvents(store, viewContainer);
    }

    // Binda eventos do drawer de evidências
    bindEvidenceDrawerEvents(store, drawerMount);
  }
}

// Inicializa a aplicação quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
  new PrometeusApp();
});
