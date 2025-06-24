/**
 * MapsDrive - Main JavaScript File
 * Funções utilitárias globais e inicialização comum para a aplicação.
 */

// ==========================================================================
// ===== FUNÇÕES UTILITÁRIAS
// ==========================================================================

/**
 * Mostra uma notificação toast usando Bootstrap 5.
 * @param {string} message - Mensagem a ser exibida.
 * @param {string} [type='info'] - Tipo do alerta: success, danger, warning, info.
 * @param {number} [duration=5000] - Duração em milissegundos para o toast desaparecer.
 */
function showToast(message, type = 'info', duration = 5000) {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    const toastId = `toast-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
    const toastColor = {
        info: "primary",
        success: "success",
        warning: "warning",
        danger: "danger"
    }[type] || "info";

    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-bg-${toastColor} border-0" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="${duration}">
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Fechar"></button>
            </div>
        </div>
    `;

    toastContainer.insertAdjacentHTML('beforeend', toastHtml);

    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    
    // Limpa o elemento do DOM após o toast ser escondido
    toastElement.addEventListener('hidden.bs.toast', () => toastElement.remove());
    
    // Acessibilidade: Foca no toast para leitores de tela
    setTimeout(() => { toastElement.focus?.(); }, 100);
    
    toast.show();
}

/**
 * Cria o container de toasts se ainda não existir no DOM.
 * @returns {HTMLElement} O elemento do container de toasts.
 */
function createToastContainer() {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'position-fixed top-0 end-0 p-3';
        container.style.zIndex = '1100';
        document.body.appendChild(container);
    }
    return container;
}

/**
 * Formata uma string para o formato de CEP português (1234-567).
 * @param {string} cep - String do CEP a ser formatada.
 * @returns {string} CEP formatado.
 */
function formatCEP(cep) {
    if (!cep) return '';
    return cep.replace(/\D/g, '')
        .replace(/^(\d{4})(\d{0,3}).*$/, (m, g1, g2) => g2 ? `${g1}-${g2}` : g1)
        .substr(0, 8);
}

/**
 * Valida se uma string corresponde ao formato de CEP português.
 * @param {string} cep - CEP a ser validado.
 * @returns {boolean} Verdadeiro se válido.
 */
function isValidCEP(cep) {
    if (!cep) return false;
    return /^\d{4}-\d{3}$/.test(cep.trim());
}

/**
 * Handler para o evento de input da máscara de CEP.
 */
function maskCepHandler() {
    const original = this.value;
    const masked = formatCEP(original);
    if (original !== masked) {
        this.value = masked;
    }
}

/**
 * Aplica a máscara de CEP a todos os campos com classe .cep-input.
 */
function initCEPMasks() {
    document.querySelectorAll('.cep-input').forEach(input => {
        input.removeEventListener('input', maskCepHandler); // Evita múltiplos listeners
        input.addEventListener('input', maskCepHandler);
        input.value = formatCEP(input.value); // Aplica no carregamento
    });
}

// ==========================================================================
// ===== LÓGICA DE TEMA (DARK/LIGHT MODE)
// ==========================================================================

/**
 * Aplica o tema claro ou escuro ao documento e salva no localStorage.
 * @param {string} mode - 'light' ou 'dark'
 */
function setTheme(mode) {
    const validMode = mode === 'dark' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-bs-theme', validMode);
    localStorage.setItem('theme', validMode);
    const themeToggleBtn = document.getElementById('toggle-theme-btn');
    if (themeToggleBtn) {
        const icon = themeToggleBtn.querySelector('i');
        if (icon) {
            icon.className = validMode === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
        themeToggleBtn.setAttribute('aria-label', validMode === 'dark' ? 'Ativar modo claro' : 'Ativar modo escuro');
    }
}

/**
 * Alterna entre tema claro e escuro.
 */
function toggleDarkMode() {
    const currentTheme = document.documentElement.getAttribute('data-bs-theme');
    setTheme(currentTheme === 'dark' ? 'light' : 'dark');
}

// ==========================================================================
// ===== INICIALIZAÇÃO GLOBAL (DOM Ready)
// ==========================================================================

document.addEventListener('DOMContentLoaded', function () {
    // Inicializa componentes do Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(el => new bootstrap.Tooltip(el));

    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(el => new bootstrap.Popover(el));

    // Configura o botão de alternar tema
    const themeToggleBtn = document.getElementById('toggle-theme-btn');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', toggleDarkMode);
    }

    // Aplica o tema salvo ou a preferência do sistema
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        setTheme(savedTheme);
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        setTheme('dark');
    } else {
        setTheme('light');
    }

    // Aplica máscaras de CEP aos inputs existentes e futuros
    initCEPMasks();
    const observer = new MutationObserver(() => initCEPMasks());
    observer.observe(document.body, { childList: true, subtree: true });

    // Delegação de eventos para validação de formulários
    document.addEventListener('submit', function (event) {
        if (event.target.classList && event.target.classList.contains('needs-validation')) {
            if (!event.target.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            event.target.classList.add('was-validated');
        }
    }, true);
});

// ==========================================================================
// ===== EXPORT GLOBAL (Opcional para uso em outras partes do projeto) =====
window.MapsDrive = {
    showToast,
    formatCEP,
    isValidCEP,
    initCEPMasks,
    setTheme,
    toggleDarkMode
};
