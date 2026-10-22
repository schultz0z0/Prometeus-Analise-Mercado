/**
 * VIEW: Validar Novo Curso (Intake Rápido e Descomplicado)
 */

export function renderIntakeView(store) {
  const state = store.getState();
  const currentTenant = state.tenants.find(t => t.id === state.currentTenantId) || state.tenants[0];

  return `
    <div class="view-header">
      <div class="view-title-row">
        <div>
          <h1 class="view-title">Validar Novo Curso</h1>
          <p class="view-subtitle">Submeta a ideia ou ementa de um novo curso para análise imediata de demanda, concorrência, precificação e breakeven.</p>
        </div>
        <button class="prometeus-btn-secondary" id="btn-cancel-intake" style="font-size:13px;">
          ← Voltar ao Portfólio
        </button>
      </div>
    </div>

    <form id="form-validate-course" class="prometeus-card" style="max-width:960px; margin:0 auto;">
      <!-- Bloco 1: A Ideia -->
      <div style="margin-bottom:28px;">
        <h2 style="font-size:18px; font-weight:600; color:#ffffff; margin:0 0 16px 0; display:flex; align-items:center; gap:8px;">
          <span style="display:inline-flex; width:24px; height:24px; border-radius:50%; background:var(--prometeus-primary); color:#ffffff; font-size:12px; align-items:center; justify-content:center; font-weight:700;">1</span>
          Conte-nos sobre o curso que você pretende ofertar
        </h2>

        <div class="form-grid">
          <div class="form-group col-12">
            <label class="form-label" for="course-name">
              Nome ou Tema do Curso <span class="form-label-required">*</span>
              <span class="form-hint">Como você planeja divulgar o curso</span>
            </label>
            <input type="text" id="course-name" class="form-input" required 
                   placeholder="Ex: MBA em Inteligência Artificial Aplicada a Seguros e Gestão de Riscos"
                   value="MBA em Inteligência Artificial Aplicada a Seguros e Gestão de Riscos">
          </div>

          <div class="form-group col-6">
            <label class="form-label" for="course-area">Grande Área Acadêmica / Cine Brasil</label>
            <input type="text" id="course-area" class="form-input" 
                   placeholder="Ex: Negócios, Administração e Dados"
                   value="Ciências de Dados & Mercado Financeiro">
          </div>

          <div class="form-group col-6">
            <label class="form-label" for="course-level">Nível da Formação</label>
            <select id="course-level" class="form-select">
              <option value="MBA Executivo" selected>MBA Executivo</option>
              <option value="Pós-Graduação Lato Sensu">Pós-Graduação Lato Sensu</option>
              <option value="Extensão / Aperfeiçoamento">Extensão / Aperfeiçoamento</option>
              <option value="Graduação Tecnológica">Graduação Tecnológica</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Bloco 2: Ementa ou Grade Curricular -->
      <div style="margin-bottom:28px;">
        <h2 style="font-size:18px; font-weight:600; color:#ffffff; margin:0 0 16px 0; display:flex; align-items:center; gap:8px;">
          <span style="display:inline-flex; width:24px; height:24px; border-radius:50%; background:var(--prometeus-primary); color:#ffffff; font-size:12px; align-items:center; justify-content:center; font-weight:700;">2</span>
          Ementa Proposta ou Grade Curricular
        </h2>

        <div class="dropzone-box" id="dropzone-curriculum">
          <div class="dropzone-icon">📄</div>
          <strong style="color:#ffffff; font-size:14px;">Arraste o PDF/Word da ementa aqui ou clique para selecionar</strong>
          <span style="color:var(--prometeus-text-muted); font-size:12px;">O JEV analisa automaticamente as competências, ferramentas e matérias propostas</span>
        </div>

        <div style="margin-top:14px;">
          <label class="form-label" for="curriculum-text">Ou cole o texto dos módulos e disciplinas:</label>
          <textarea id="curriculum-text" class="form-textarea" placeholder="Módulo 1: Fundamentos de IA e Big Data&#10;Módulo 2: Machine Learning na Prevenção de Sinistros&#10;Módulo 3: Modelos Estatísticos de Risco&#10;Módulo 4: Governança, LGPD e SUSEP...">Módulo 1: Fundamentos de IA e Big Data no Setor Segurador (40h)
Módulo 2: Machine Learning na Prevenção e Detecção de Sinistros Fraudulentos (40h)
Módulo 3: Modelagem Teórica de Riscos e Séries Temporais (40h)
Módulo 4: Automação de Subscrição com Processamento de Linguagem Natural (40h)
Módulo 5: Governança Algorítmica e Regulação SUSEP (30h)
Módulo 6: Projeto Aplicado de Inteligência de Seguros (50h)</textarea>
        </div>
      </div>

      <!-- Bloco 3: Premissas Comerciais da Oferta -->
      <div style="margin-bottom:32px;">
        <h2 style="font-size:18px; font-weight:600; color:#ffffff; margin:0 0 16px 0; display:flex; align-items:center; gap:8px;">
          <span style="display:inline-flex; width:24px; height:24px; border-radius:50%; background:var(--prometeus-primary); color:#ffffff; font-size:12px; align-items:center; justify-content:center; font-weight:700;">3</span>
          Premissas da Oferta & Concorrência
        </h2>

        <div style="margin-bottom:18px;">
          <label class="form-label" style="margin-bottom:8px;">Modalidade Pretendida</label>
          <div class="radio-cards-grid">
            <div class="radio-card selected" data-value="EAD Síncrono">
              <span class="radio-card-title">EAD Síncrono</span>
              <span class="radio-card-desc">Aulas ao vivo online</span>
            </div>
            <div class="radio-card" data-value="100% EAD">
              <span class="radio-card-title">100% EAD</span>
              <span class="radio-card-desc">Aulas gravadas</span>
            </div>
            <div class="radio-card" data-value="Híbrido">
              <span class="radio-card-title">Híbrido</span>
              <span class="radio-card-desc">Online + Encontros</span>
            </div>
            <div class="radio-card" data-value="Presencial">
              <span class="radio-card-title">Presencial</span>
              <span class="radio-card-desc">Em campus físico</span>
            </div>
          </div>
        </div>

        <div class="form-grid">
          <div class="form-group col-4">
            <label class="form-label" for="course-ticket">Mensalidade Alvo (R$)</label>
            <input type="number" id="course-ticket" class="form-input" value="980" step="10" required>
            <span class="form-hint">Valor por mês cobrado do aluno</span>
          </div>

          <div class="form-group col-4">
            <label class="form-label" for="course-duration">Duração (Meses)</label>
            <input type="number" id="course-duration" class="form-input" value="12" min="1" max="48" required>
            <span class="form-hint">Total de parcelas / meses</span>
          </div>

          <div class="form-group col-4">
            <label class="form-label" for="course-audience">Público-alvo Previsto</label>
            <input type="text" id="course-audience" class="form-input" 
                   value="Analistas de risco, atuários e líderes de seguradoras"
                   placeholder="Ex: Gestores de seguros, TI">
          </div>

          <div class="form-group col-12">
            <label class="form-label" for="course-competitors">Concorrentes Conhecidos (Opcional)</label>
            <input type="text" id="course-competitors" class="form-input" 
                   value="FGV, FIA Business School, PUC Minas"
                   placeholder="Ex: FGV, PUC, Insper, cursos online da Alura/Udemy">
            <span class="form-hint">O Prometeus também varre automaticamente novas ofertas via Meta Ads e Google</span>
          </div>
        </div>
      </div>

      <!-- Barra de Ação de Disparo -->
      <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--prometeus-border-subtle); padding-top:24px;">
        <div style="font-size:12px; color:var(--prometeus-text-muted);">
          🏢 Conectado à API do CRM da <strong>${currentTenant.name}</strong> para cruzar com seu histórico interno.
        </div>
        <button type="submit" class="prometeus-btn-primary" style="font-size:15px; padding:12px 28px;">
          <span>✦ Analisar Viabilidade da Oferta</span>
          <span aria-hidden="true">→</span>
        </button>
      </div>
    </form>
  `;
}

export function bindIntakeEvents(store, container) {
  const cancelBtn = container.querySelector('#btn-cancel-intake');
  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      store.setView('portfolio');
    });
  }

  // Radio cards de modalidade
  const radioCards = container.querySelectorAll('.radio-card');
  let selectedModality = 'EAD Síncrono';
  radioCards.forEach(card => {
    card.addEventListener('click', () => {
      radioCards.forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      selectedModality = card.getAttribute('data-value');
    });
  });

  // Dropzone visual feedback
  const dropzone = container.querySelector('#dropzone-curriculum');
  if (dropzone) {
    dropzone.addEventListener('click', () => {
      alert("Simulação: Ementa 'Ementa_MBA_IA_Seguros_2026.pdf' carregada e processada pelo JEV com 6 módulos identificados.");
    });
  }

  // Submit form
  const form = container.querySelector('#form-validate-course');
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      
      const payload = {
        name: container.querySelector('#course-name').value,
        area: container.querySelector('#course-area').value,
        level: container.querySelector('#course-level').value,
        modality: selectedModality,
        ticket: container.querySelector('#course-ticket').value,
        duration: container.querySelector('#course-duration').value,
        curriculum: container.querySelector('#curriculum-text').value,
        audience: container.querySelector('#course-audience').value,
        competitors: container.querySelector('#course-competitors').value
      };

      store.startAnalysis(payload);
    });
  }
}
