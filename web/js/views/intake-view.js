/**
 * VIEW: Validar Novo Curso (Intake Rápido e Descomplicado)
 */

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function renderEcosystemFieldBlock(eco, existingExtraSeed = '') {
  const competitors = Array.isArray(eco?.competitors) ? eco.competitors : [];
  const sectorRadar = Array.isArray(eco?.sector_radar) ? eco.sector_radar : [];

  if (!competitors.length && !sectorRadar.length) {
    return `
      <label class="form-label" for="course-competitors">Concorrentes Conhecidos (Opcional)</label>
      <input type="text" id="course-competitors" class="form-input"
             value="${escapeHtml(existingExtraSeed)}"
             placeholder="Ex: FGV, PUC, Insper, cursos online da Alura/Udemy">
      <span class="form-hint">O Prometeus também varre automaticamente novas ofertas via Meta Ads e Google</span>
    `;
  }

  const radarStatus = eco?.radar_status || {};
  let radarBadge = 'Coleta sob demanda ativa';
  if (radarStatus.has_snapshot && radarStatus.is_fresh) {
    radarBadge = `Snapshot ativo (${Number(radarStatus.signals_count || 0)} sinais)`;
  } else if (radarStatus.has_snapshot) {
    radarBadge = `Snapshot expirado — renovação automática`;
  }

  const allowExtra = eco?.allow_extra_intake_competitors !== false;

  return `
    <div class="intake-ecosystem-panel">
      <div class="intake-ecosystem-header">
        <div class="intake-ecosystem-title">
          <span>🎯 Ecossistema Monitorado Automaticamente</span>
        </div>
        <span style="font-size:11px; padding:3px 10px; border-radius:999px; background:rgba(16,185,129,0.12); color:#34d399; border:1px solid rgba(16,185,129,0.28); font-weight:600;">
          Radar Setorial: ${escapeHtml(radarBadge)}
        </span>
      </div>
      <p style="margin:0 0 12px 0; font-size:12.5px; color:var(--prometeus-text-secondary); line-height:1.5;">
        Você não precisa listar concorrentes manualmente: o Prometeus varre automaticamente os portais dos concorrentes educacionais abaixo (oferta, ementa, carga horária e preço) e isola as seguradoras do Radar Setorial como termômetro de demanda e dores de corretores.
      </p>

      ${competitors.length ? `
        <div style="margin-bottom:10px;">
          <div style="font-size:11.5px; font-weight:600; color:#e2e8f0; margin-bottom:6px;">
            Concorrentes Educacionais Fixos (${competitors.length})
          </div>
          <div class="intake-ecosystem-chips">
            ${competitors.map(item => `
              <span class="intake-eco-chip" title="${escapeHtml(item.website_url || '')}">${escapeHtml(item.name)}</span>
            `).join('')}
          </div>
        </div>
      ` : ''}

      ${sectorRadar.length ? `
        <div>
          <div style="font-size:11.5px; font-weight:600; color:#93c5fd; margin-bottom:6px;">
            Radar Setorial Permanente — Seguradoras &amp; Mercado Empregador (${sectorRadar.length})
          </div>
          <div class="intake-ecosystem-chips">
            ${sectorRadar.map(item => `
              <span class="intake-eco-chip radar" title="${escapeHtml(item.website_url || '')}">${escapeHtml(item.name)}</span>
            `).join('')}
          </div>
        </div>
      ` : ''}

      ${allowExtra ? `
        <details class="intake-extra-seed-details"${existingExtraSeed ? ' open' : ''}>
          <summary>+ Adicionar concorrente extra pontual para esta análise (opcional)</summary>
          <div style="margin-top:10px;">
            <input type="text" id="course-competitors" class="form-input"
                   value="${escapeHtml(existingExtraSeed)}"
                   placeholder="Ex: Curso nichado específico fora dos concorrentes fixos monitorados">
            <span class="form-hint">Use apenas para incluir uma oferta pontual além do catálogo institucional fixo e da descoberta aberta em Google e Meta Ads.</span>
          </div>
        </details>
      ` : `
        <input type="hidden" id="course-competitors" value="">
      `}
    </div>
  `;
}

export function renderIntakeView(store) {
  const state = store.getState();
  const currentTenant = state.tenants.find(t => t.id === state.currentTenantId) || state.tenants[0];
  const eco = state.tenantEcosystems?.[state.currentTenantId] || null;

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

        <input type="file" id="curriculum-file-input" accept=".pdf,.docx,.md,.txt" style="display:none;">
        <div class="dropzone-box" id="dropzone-curriculum" style="cursor:pointer; transition:all 0.2s ease;">
          <div class="dropzone-icon" id="dropzone-icon">📄</div>
          <strong id="dropzone-title" style="color:#ffffff; font-size:14px;">Clique para anexar ou arraste o arquivo da ementa (.pdf, .docx, .md, .txt)</strong>
          <span id="dropzone-desc" style="color:var(--prometeus-text-muted); font-size:12px;">Selecione o arquivo do seu computador para ser analisado</span>
          <div id="dropzone-file-badge" style="display:none; margin-top:8px; padding:4px 10px; background:rgba(16,185,129,0.15); color:#34d399; border-radius:6px; font-size:12px; font-weight:600; border:1px solid rgba(16,185,129,0.3);"></div>
        </div>

        <div style="margin-top:14px;">
          <label class="form-label" for="curriculum-text">Ou edite / cole o conteúdo da grade curricular e módulos:</label>
          <textarea id="curriculum-text" class="form-textarea" style="min-height:120px;" placeholder="Módulo 1: Fundamentos de IA e Big Data&#10;Módulo 2: Machine Learning na Prevenção de Sinistros&#10;Módulo 3: Modelos Estatísticos de Risco&#10;Módulo 4: Governança, LGPD e SUSEP...">Módulo 1: Fundamentos de IA e Big Data no Setor Segurador (40h)
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
            <label class="form-label" for="course-ticket">Valor da Parcela (R$)</label>
            <input type="number" id="course-ticket" class="form-input" value="980" min="0.01" step="0.01" required>
            <span class="form-hint">Valor mensal cobrado do aluno</span>
          </div>

          <div class="form-group col-4">
            <label class="form-label" for="course-duration">Duração (Meses)</label>
            <input type="number" id="course-duration" class="form-input" value="12" min="1" max="48" required>
            <span class="form-hint">Duração acadêmica do curso</span>
          </div>

          <div class="form-group col-4">
            <label class="form-label" for="course-installments">Número de Parcelas</label>
            <input type="number" id="course-installments" class="form-input" min="1" max="120" placeholder="Ex: 20">
            <span class="form-hint">Prazo de pagamento, independente da duração</span>
          </div>

          <div class="form-group col-4">
            <label class="form-label" for="course-audience">Público-alvo Previsto</label>
            <input type="text" id="course-audience" class="form-input" 
                   value="Analistas de risco, atuários e líderes de seguradoras"
                   placeholder="Ex: Gestores de seguros, TI">
          </div>

          <div class="form-group col-12" id="intake-ecosystem-mount" data-eco-ready="${eco ? 'true' : 'false'}">
            ${renderEcosystemFieldBlock(eco)}
          </div>
        </div>
      </div>

      <!-- Barra de Ação de Disparo -->
      <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--prometeus-border-subtle); padding-top:24px;">
        <div style="font-size:12px; color:var(--prometeus-text-muted);">
          🏢 A comparação histórica usa a base sintética autorizada de <strong>${currentTenant.name}</strong>, persistida no backend.
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

  // Caso o usuário tenha aberto a tela antes do fetch inicial de /ecosystem terminar,
  // atualiza apenas o painel #intake-ecosystem-mount sem tocar no restante do formulário.
  const currentState = store.getState();
  const activeTenantId = currentState.currentTenantId;
  if (!currentState.tenantEcosystems?.[activeTenantId] && typeof store.loadTenantEcosystem === 'function') {
    store.loadTenantEcosystem(activeTenantId).then((loaded) => {
      if (!loaded) return;
      const mount = container.querySelector('#intake-ecosystem-mount');
      if (!mount) return;
      const existingVal = container.querySelector('#course-competitors')?.value || '';
      mount.innerHTML = renderEcosystemFieldBlock(loaded, existingVal);
      mount.setAttribute('data-eco-ready', 'true');
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

  // File upload and dropzone handling
  const fileInput = container.querySelector('#curriculum-file-input');
  const dropzone = container.querySelector('#dropzone-curriculum');
  const fileBadge = container.querySelector('#dropzone-file-badge');
  const curriculumTextArea = container.querySelector('#curriculum-text');
  curriculumTextArea?.addEventListener('input', () => curriculumTextArea.setCustomValidity(''));
  let attachedFileName = null;

  function handleFile(file) {
    if (!file) return;
    attachedFileName = file.name;
    if (fileBadge) {
      fileBadge.style.display = 'inline-block';
      fileBadge.textContent = `✓ Arquivo anexado: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    }
    const dropzoneTitle = container.querySelector('#dropzone-title');
    if (dropzoneTitle) {
      dropzoneTitle.textContent = `Arquivo selecionado: ${file.name}`;
    }

    // Se for arquivo de texto, carrega o conteúdo diretamente no textarea
    if (/\.(txt|md)$/i.test(file.name) || file.type.startsWith('text/')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        if (e.target?.result && curriculumTextArea) {
          curriculumTextArea.value = e.target.result;
        }
      };
      reader.readAsText(file);
    } else {
      // Para PDF/DOCX, avisa o usuário e prefixa a ementa com o nome do arquivo auditável
      if (/\.(pdf|docx)$/i.test(file.name)) {
        curriculumTextArea.value = '';
        const submit = container.querySelector('button[type="submit"]');
        if (submit) submit.disabled = true;
        fileBadge.textContent = `Extraindo conteúdo de ${file.name}…`;
        const reader = new FileReader();
        reader.onload = async (e) => {
          const dataUrl = e.target?.result;
          if (!dataUrl || !curriculumTextArea) return;
          try {
            const resp = await fetch('/v1/intake/extract-document', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ filename: file.name, content_base64: dataUrl })
            });
            if (resp.ok) {
              const parsed = await resp.json();
              if (parsed.text) {
                curriculumTextArea.value = parsed.text;
                fileBadge.textContent = `✓ Conteúdo extraído: ${file.name}`;
                if (submit) submit.disabled = false;
                return;
              }
            }
          } catch (err) {
            console.warn('Falha ao extrair texto do documento:', err);
          }
          curriculumTextArea.value = '';
          fileBadge.textContent = `Não foi possível extrair ${file.name}. Cole a ementa antes de analisar.`;
          if (submit) submit.disabled = false;
        };
        reader.onerror = () => {
          fileBadge.textContent = 'Não foi possível ler o arquivo. Cole a ementa antes de analisar.';
          if (submit) submit.disabled = false;
        };
        reader.readAsDataURL(file);
        return;
      }
      if (curriculumTextArea && !curriculumTextArea.value.includes(file.name)) {
        curriculumTextArea.value = `[Documento Anexado: ${file.name} (${(file.size / 1024).toFixed(1)} KB)]\n` + curriculumTextArea.value;
      }
    }
  }

  if (dropzone && fileInput) {
    dropzone.addEventListener('click', () => {
      fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
      const file = e.target.files?.[0];
      handleFile(file);
    });

    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.style.borderColor = 'var(--prometeus-primary)';
      dropzone.style.background = 'rgba(6, 82, 197, 0.1)';
    });

    dropzone.addEventListener('dragleave', () => {
      dropzone.style.borderColor = '';
      dropzone.style.background = '';
    });

    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.style.borderColor = '';
      dropzone.style.background = '';
      const file = e.dataTransfer?.files?.[0];
      handleFile(file);
    });
  }

  // Submit form
  const form = container.querySelector('#form-validate-course');
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      if (!curriculumTextArea.value.trim()) {
        curriculumTextArea.setCustomValidity('Informe a ementa ou anexe um documento com texto extraível.');
        curriculumTextArea.reportValidity();
        return;
      }
      
      const payload = {
        name: container.querySelector('#course-name').value,
        area: container.querySelector('#course-area').value,
        level: container.querySelector('#course-level').value,
        modality: selectedModality,
        ticket: container.querySelector('#course-ticket').value,
        duration: container.querySelector('#course-duration').value,
        installments: container.querySelector('#course-installments').value,
        curriculum: container.querySelector('#curriculum-text').value,
        audience: container.querySelector('#course-audience').value,
        competitors: container.querySelector('#course-competitors')?.value || '',
        curriculum_file_name: attachedFileName
      };

      store.startAnalysis(payload);
    });
  }
}
