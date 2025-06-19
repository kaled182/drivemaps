/**
 * MapsDrive - Main JavaScript File
 * Contém funções utilitárias e inicialização comum
 */

// ===== FUNÇÕES UTILITÁRIAS =====

/**
 * Mostra uma notificação toast
 * @param {string} message - Mensagem a ser exibida
 * @param {string} type - Tipo de alerta (success, danger, warning, info)
 * @param {number} duration - Duração em milissegundos (opcional)
 */
function showToast(message, type = 'info', duration = 3000) {
  const toastContainer = document.getElementById('toast-container') || createToastContainer();
  const toast = document.createElement('div');
  
  toast.className = `toast show fade-in bg-${type} text-white`;
  toast.innerHTML = `
    <div class="d-flex align-items-center">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2" data-bs-dismiss="toast"></button>
    </div>
  `;
  
  toastContainer.appendChild(toast);
  
  // Remove o toast após o tempo especificado
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 150);
  }, duration);
}

/**
 * Cria um container para toasts se não existir
 * @returns {HTMLElement} O container de toasts
 */
function createToastContainer() {
  const container = document.createElement('div');
  container.id = 'toast-container';
  container.className = 'position-fixed bottom-0 end-0 p-3';
  container.style.zIndex = '1100';
  document.body.appendChild(container);
  return container;
}

/**
 * Formata um CEP (adiciona hífen)
 * @param {string} cep - CEP a ser formatado
 * @returns {string} CEP formatado
 */
function formatCEP(cep) {
  if (!cep) return '';
  return cep.replace(/\D/g, '')
            .replace(/^(\d{5})(\d)/, '$1-$2')
            .substr(0, 9);
}

/**
 * Valida um CEP
 * @param {string} cep - CEP a ser validado
 * @returns {boolean} Verdadeiro se o CEP for válido
 */
function isValidCEP(cep) {
  return /^\d{5}-?\d{3}$/.test(cep);
}

/**
 * Inicializa máscaras para campos de CEP
 */
function initCEPMasks() {
  document.querySelectorAll('.cep-input').forEach(input => {
    input.addEventListener('input', function(e) {
      this.value = formatCEP(this.value);
    });
  });
}

/**
 * Alterna o tema claro/escuro
 */
function toggleDarkMode() {
  const html = document.documentElement;
  const currentTheme = html.getAttribute('data-bs-theme');
  const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
  
  html.setAttribute('data-bs-theme', newTheme);
  localStorage.setItem('theme', newTheme);
  
  showToast(`Tema ${newTheme === 'dark' ? 'escuro' : 'claro'} ativado`);
}

// ===== MANIPULAÇÃO DE FORMULÁRIOS =====

/**
 * Valida um formulário com Bootstrap
 * @param {string} formId - ID do formulário
 */
function initFormValidation(formId) {
  const form = document.getElementById(formId);
  if (!form) return;

  form.addEventListener('submit', function(event) {
    if (!form.checkValidity()) {
      event.preventDefault();
      event.stopPropagation();
    }
    form.classList.add('was-validated');
  }, false);
}

/**
 * Habilita o envio de formulários via AJAX
 * @param {string} formId - ID do formulário
 * @param {function} callback - Função de callback após sucesso
 */
function initAjaxForm(formId, callback) {
  const form = document.getElementById(formId);
  if (!form) return;

  form.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const submitBtn = form.querySelector('[type="submit"]');
    const originalText = submitBtn.innerHTML;
    
    try {
      // Mostra estado de carregamento
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processando...';
      submitBtn.disabled = true;
      
      const formData = new FormData(form);
      const response = await fetch(form.action, {
        method: form.method,
        body: form.enctype === 'multipart/form-data' ? formData : new URLSearchParams(formData),
        headers: {
          'Accept': 'application/json'
        }
      });
      
      const data = await response.json();
      
      if (response.ok) {
        if (typeof callback === 'function') {
          callback(data);
        } else {
          showToast(data.message || 'Operação realizada com sucesso!', 'success');
          if (data.redirect) {
            setTimeout(() => window.location.href = data.redirect, 1500);
          }
        }
      } else {
        showToast(data.message || 'Erro ao processar requisição', 'danger');
      }
    } catch (error) {
      showToast('Erro de conexão com o servidor', 'danger');
      console.error('Error:', error);
    } finally {
      submitBtn.innerHTML = originalText;
      submitBtn.disabled = false;
    }
  });
}

// ===== INICIALIZAÇÃO =====

document.addEventListener('DOMContentLoaded', function() {
  // Inicializa máscaras de CEP
  initCEPMasks();
  
  // Configura tooltips
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(function(tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });
  
  // Configura popovers
  const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
  popoverTriggerList.map(function(popoverTriggerEl) {
    return new bootstrap.Popover(popoverTriggerEl);
  });
  
  // Botão de tema escuro/claro
  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', toggleDarkMode);
  }
  
  // Verifica tema salvo no localStorage
  const savedTheme = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-bs-theme', savedTheme);
  
  // Inicializa todos os formulários com classe 'needs-validation'
  document.querySelectorAll('.needs-validation').forEach(form => {
    initFormValidation(form.id);
  });
  
  // Configura listeners para elementos dinâmicos
  document.body.addEventListener('click', function(e) {
    // Exemplo: Fechar toasts ao clicar
    if (e.target.classList.contains('btn-close')) {
      const toast = e.target.closest('.toast');
      if (toast) {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 150);
      }
    }
  });
});

// ===== FUNÇÕES PARA O MAPA =====

/**
 * Inicializa o mapa (será sobrescrito pelas páginas específicas)
 */
window.initMap = function() {
  console.log('Map initialization function not overridden');
};

/**
 * Carrega a API do Google Maps
 * @param {string} apiKey - Chave da API do Google Maps
 * @param {function} callback - Função de callback quando carregado
 */
function loadGoogleMapsAPI(apiKey, callback) {
  if (typeof google === 'undefined' || typeof google.maps === 'undefined') {
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places&callback=${callback}`;
    script.async = true;
    script.defer = true;
    document.head.appendChild(script);
  } else {
    if (typeof window[callback] === 'function') {
      window[callback]();
    }
  }
}

// Exporta funções para uso global (se necessário)
window.MapsDrive = {
  showToast,
  formatCEP,
  isValidCEP,
  initCEPMasks,
  initFormValidation,
  initAjaxForm,
  loadGoogleMapsAPI
};
