/**
 * MapsDrive - Lógica da Página de Visualização (preview.js)
 * Organização modular, acessibilidade e padrões profissionais.
 */

// ========================
// 1. Mensagens e Internacionalização (i18n)
// ========================
const i18n = {
    'pt': {
        error_load: "Erro ao carregar dados dos endereços.",
        error_comm: "Erro de comunicação: ",
        error_remove: "Tem a certeza que deseja remover este endereço?",
        removed: "Endereço removido.",
        added: "Novo endereço adicionado!",
        updated: "Endereço atualizado com sucesso!",
        validated: "Endereço validado com sucesso!",
        total: "Total",
        validated_label: "Validados",
        pending: "Pendentes",
        saving: "Salvando...",
        confirm: "Confirmar",
        add: "Adicionar Novo Endereço",
        cancel: "Cancelar",
        success: "success",
        warning: "warning",
        danger: "danger"
    }
};
const locale = 'pt';

function t(key, fallback = "") {
    return (i18n[locale] && i18n[locale][key]) || fallback || key;
}

// ========================
// 2. Funções Utilitárias
// ========================
function maskCEP(value) {
    return (window.MapsDrive && window.MapsDrive.formatCEP)
        ? window.MapsDrive.formatCEP(value)
        : value.replace(/\D/g, '').replace(/^(\d{4})(\d{0,3}).*$/, (m, g1, g2) => g2 ? `${g1}-${g2}` : g1).substr(0, 8);
}

function applyInputMask(selector, maskFn) {
    document.querySelectorAll(selector).forEach(input => {
        input.removeEventListener('input', input._maskHandler || (() => {}));
        input._maskHandler = function() { this.value = maskFn(this.value); };
        input.addEventListener('input', input._maskHandler);
        input.value = maskFn(input.value);
    });
}

function debounce(fn, delay = 500) {
    let timer;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

function showGlobalSpinner(show = true) {
    let el = document.getElementById('global-spinner');
    if (show && !el) {
        el = document.createElement('div');
        el.id = 'global-spinner';
        el.setAttribute('role', 'status');
        el.setAttribute('aria-live', 'polite');
        el.innerHTML = `<div class="spinner-border text-primary" style="position:fixed;top:45%;left:48%;z-index:2000;width:3rem;height:3rem;"></div>`;
        document.body.appendChild(el);
    } else if (!show && el) {
        el.remove();
    }
}

// ========================
// 3. Estado Global da Página
// ========================
let mapManager;
let enderecosData = [];

// ========================
// 4. Inicialização Principal
// ========================
document.addEventListener('DOMContentLoaded', () => {
    const pageDataElement = document.getElementById('page-data');
    try {
        enderecosData = JSON.parse(pageDataElement?.dataset?.enderecos || '[]');
    } catch (e) {
        window.MapsDrive?.showToast?.(t('error_load'), t('danger'));
        return;
    }
    if (!Array.isArray(enderecosData) || enderecosData.length === 0) {
        console.warn("Nenhum dado de endereço encontrado para inicializar a página.");
        previewTable.rebuild(); // Chama para mostrar a mensagem de tabela vazia.
        previewStats.update();
        return;
    };

    previewTable.rebuild();
    previewStats.update();
    applyInputMask('.cep-input', maskCEP);

    const token = pageDataElement.dataset.mapboxToken;
    mapManager = new MapManager('map', token, {
        onMarkerDragEnd: previewMap.onMarkerDragEnd
    });
    mapManager.init(enderecosData);

    // *** CORREÇÃO: A função renderMarkers do map.js é agora chamada diretamente, sem ser sobrescrita. ***
    mapManager.renderMarkers(enderecosData);

    // Listener para a troca de tema (light/dark)
    document.addEventListener('mapsdrive:themechange', (e) => {
        mapManager.setTheme?.(e.detail.theme);
    });
});

// ========================
// 5. Módulo para a Tabela
// ========================
const previewTable = {
    rebuild() {
        const tbody = document.getElementById('address-table-body');
        if (!tbody) return;
        tbody.innerHTML = '';
        if (enderecosData.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center p-4">Nenhum endereço para exibir.</td></tr>';
            return;
        }
        enderecosData.forEach((item, idx) => this.appendRow(item, idx));
    },
    appendRow(item, idx) {
        const tbody = document.getElementById('address-table-body');
        const row = document.createElement('tr');
        row.id = `row-${idx}`;
        tbody.appendChild(row);
        this.updateRow(idx, item);
    },
    updateRow(idx, data) {
        const row = document.getElementById(`row-${idx}`);
        if (!row) return;
        enderecosData[idx] = data;
        const status_google = data.status_google || 'Pendente';
        let statusClass, statusText;
        if (status_google === 'OK') {
            statusClass = 'success'; statusText = t('validated_label');
        } else if (status_google === 'Pendente') {
            statusClass = 'warning'; statusText = t('pending', 'Pendente');
        } else {
            statusClass = 'danger'; statusText = 'Erro';
        }
        row.innerHTML = `
            <td><span class="badge bg-primary-subtle text-primary-emphasis rounded-pill">${data.order_number}</span></td>
            <td><input type="text" class="form-control form-control-sm" id="address-${idx}" value="${data.address}" oninput="previewTable.enableValidate(${idx})"></td>
            <td><input type="text" class="form-control form-control-sm cep-input" id="cep-${idx}" value="${data.cep || ''}" oninput="previewTable.enableValidate(${idx})"></td>
            <td id="status-${idx}"><span class="badge bg-${statusClass}-subtle text-${statusClass}-emphasis rounded-pill">${statusText}</span></td>
            <td class="text-center">
                <button class="btn btn-primary btn-sm btn-icon btn-validate" id="btn-validate-${idx}" onclick="debouncedValidateAddress(${idx})" disabled title="Validar endereço"><i class="fas fa-search-location"></i></button>
                <button class="btn btn-secondary btn-sm btn-icon" onclick="focusMarker(${idx})" title="Focar no mapa"><i class="fas fa-map-marker-alt"></i></button>
                <button class="btn btn-danger btn-sm btn-icon" onclick="removeAddress(${idx})" title="Remover endereço"><i class="fas fa-trash-alt"></i></button>
            </td>
        `;
        applyInputMask(`#cep-${idx}`, maskCEP);
    },
    enableValidate(idx) {
        document.getElementById(`btn-validate-${idx}`).disabled = false;
    }
};
window.previewTable = previewTable;

// ========================
// 6. Módulo de Estatísticas
// ========================
const previewStats = {
    update() {
        const total = enderecosData.length;
        const validados = enderecosData.filter(e => e.status_google === 'OK').length;
        const pendentes = total - validados;
        document.getElementById('stats-bar').innerHTML = `<span aria-live="polite" aria-atomic="true"><i class="fas fa-chart-pie me-2"></i><strong>${t('total')}: ${total}</strong> | <span class="text-success">${t('validated_label')}: ${validados}</span> | <span class="text-warning">${t('pending')}: ${pendentes}</span></span>`;
    }
};

// ========================
// 7. Módulo do Mapa (Handlers)
// ========================
const previewMap = {
    async onMarkerDragEnd(idx, marker) {
        const newLngLat = marker.getLngLat();
        const row = document.getElementById(`row-${idx}`);
        row?.classList.add('table-info');
        try {
            const data = await fetchAPI('/api/reverse-geocode', {
                method: "POST", headers: {"Content-Type": "application/json"},
                body: JSON.stringify({ idx, lat: newLngLat.lat, lng: newLngLat.lng })
            });
            if (data.success) {
                previewTable.updateRow(idx, data.item);
                previewStats.update();
                window.MapsDrive?.showToast?.(t('updated'), t('success'));
                mapManager.renderMarkers(enderecosData);
            }
        } catch(e) { /* Erro já tratado pela fetchAPI */ }
        finally { row?.classList.remove('table-info'); }
    }
};

// ========================
// 8. Funções de Comunicação com API
// ========================
async function fetchAPI(endpoint, options) {
    showGlobalSpinner(true);
    try {
        const resp = await fetch(endpoint, options);
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.msg || `Erro ${resp.status}`);
        return data;
    } catch (err) {
        window.MapsDrive?.showToast?.(t('error_comm') + err.message, t('danger'));
        throw err;
    } finally {
        showGlobalSpinner(false);
    }
}

const debouncedValidateAddress = debounce(validateAddress, 600);
window.debouncedValidateAddress = debouncedValidateAddress;

async function validateAddress(idx) {
    const btn = document.getElementById(`btn-validate-${idx}`);
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    try {
        const data = await fetchAPI('/api/validar-linha', {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ 
                idx, 
                endereco: document.getElementById(`address-${idx}`).value,
                cep: document.getElementById(`cep-${idx}`).value
            })
        });
        if (data.success) {
            previewTable.updateRow(idx, data.item);
            mapManager.renderMarkers(enderecosData);
            previewStats.update();
            window.MapsDrive?.showToast?.(t('validated'), t('success'));
        }
    } catch(e) {
        previewTable.updateRow(idx, enderecosData[idx]);
    } finally {
        btn.innerHTML = '<i class="fas fa-search-location"></i>';
    }
}

async function removeAddress(idx) {
    if (!confirm(t('error_remove'))) return;
    try {
        const data = await fetchAPI('/api/remover-endereco', {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ idx })
        });
        if (data.success) {
            enderecosData = data.lista;
            previewTable.rebuild();
            mapManager.renderMarkers(enderecosData);
            previewStats.update();
            window.MapsDrive?.showToast?.(t('removed'), t('warning'));
        }
    } catch(e) { /* Erro já tratado */ }
}

async function saveNewAddress(event) {
    event.preventDefault();
    const form = event.target;
    if (!form.checkValidity()) { form.classList.add('was-validated'); return; }
    
    const submitBtn = form.querySelector('button[type=submit]');
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> ${t('saving')}`;

    try {
        const data = await fetchAPI('/api/add-address', {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ 
                id: document.getElementById('new_id').value,
                endereco: document.getElementById('new_address').value,
                cep: document.getElementById('new_cep').value
            })
        });
        if (data.success) {
            enderecosData.push(data.item);
            previewTable.appendRow(data.item, enderecosData.length - 1);
            mapManager.renderMarkers(enderecosData);
            previewStats.update();
            toggleNewAddressForm();
            form.reset();
            form.classList.remove('was-validated');
            window.MapsDrive?.showToast?.(t('added'), t('success'));
        }
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Salvar Endereço';
    }
}

// ========================
// 9. Funções de UI Auxiliares
// ========================
function toggleNewAddressForm() {
    const form = document.getElementById('new-address-form');
    const btn = document.getElementById('btn-show-form');
    const isHidden = form.style.display === 'none';
    form.style.display = isHidden ? 'block' : 'none';
    btn.innerHTML = isHidden ? `<i class="fas fa-times me-1"></i> ${t('cancel')}` : `<i class="fas fa-plus-circle me-1"></i> ${t('add')}`;
    btn.classList.toggle('btn-secondary', isHidden);
    btn.classList.toggle('btn-success', !isHidden);
    if (!isHidden) form.querySelector('input').focus();
}

function focusMarker(idx) {
    if (mapManager && mapManager.markers && mapManager.markers[idx]) {
        mapManager.markers[idx].togglePopup();
    }
}

// ========================
// 10. Exports para uso em HTML (onclick)
// ========================
window.removeAddress = removeAddress;
window.saveNewAddress = saveNewAddress;
window.toggleNewAddressForm = toggleNewAddressForm;
window.focusMarker = focusMarker;
window.validateAddress = validateAddress;
