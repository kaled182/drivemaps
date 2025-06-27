/**
 * MapsDrive - Lógica da Página de Visualização (preview.js)
 * Organização modular, acessibilidade e padrões profissionais.
 */

// ========================
// 1. MÓDULO DE INTERNACIONALIZAÇÃO (i18n)
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
        saving: "Aguarde...",
        confirm: "Confirmar",
        add: "Adicionar Endereço",
        cancel: "Cancelar",
        success: "success",
        warning: "warning",
        danger: "danger"
    }
};
const locale = 'pt';
const t = (key, fallback = "") => (i18n[locale] && i18n[locale][key]) || fallback || key;


// ========================
// 2. ESTADO GLOBAL E INICIALIZAÇÃO
// ========================
let mapManager;
let enderecosData = [];

document.addEventListener('DOMContentLoaded', () => {
    const pageDataElement = document.getElementById('page-data');
    if (!pageDataElement) {
        console.error("Elemento de dados da página não encontrado. A aplicação não pode ser inicializada.");
        return;
    }

    try {
        enderecosData = JSON.parse(pageDataElement.dataset.enderecos || '[]');
    } catch (e) {
        window.MapsDrive?.showToast?.(t('error_load'), t('danger'));
        return;
    }

    // Inicializa os módulos da página
    previewUI.init();
    previewTable.rebuild();
    previewStats.update();
    
    const token = pageDataElement.dataset.mapboxToken;
    if (token) {
        mapManager = new MapManager('map', token, {
            onMarkerDragEnd: previewMap.onMarkerDragEnd
        });
        mapManager.init(enderecosData);
        mapManager.renderMarkers(enderecosData);
    } else {
        console.error("Mapbox Token não encontrado. O mapa não será inicializado.");
    }
    
    // Listener para a troca de tema (light/dark)
    document.addEventListener('mapsdrive:themechange', (e) => {
        mapManager?.setTheme?.(e.detail.theme);
    });
});


// ========================
// 3. MÓDULO DA TABELA (previewTable)
// ========================
const previewTable = {
    tbody: document.getElementById('address-table-body'),

    rebuild() {
        if (!this.tbody) return;
        this.tbody.innerHTML = '';
        enderecosData.forEach((item, idx) => this.appendRow(item, idx));
        window.MapsDrive?.initCEPMasks?.();
    },

    appendRow(item, idx) {
        if (!this.tbody) return;
        const row = this.tbody.insertRow();
        row.id = `row-${idx}`;
        this.updateRow(idx, item, row);
    },

    updateRow(idx, data, rowElement) {
        const row = rowElement || document.getElementById(`row-${idx}`);
        if (!row) return;

        enderecosData[idx] = data;
        const status = data.status_google || 'Pendente';
        const statusInfo = this.getStatusInfo(status);

        row.innerHTML = `
            <td><span class="badge bg-dark text-white rounded-pill">${data.order_number}</span></td>
            <td><input type="text" class="form-control form-control-sm" id="address-${idx}" value="${data.address}"></td>
            <td><input type="text" class="form-control form-control-sm cep-input" id="cep-${idx}" value="${data.cep || ''}"></td>
            <td id="status-${idx}"><span class="badge bg-${statusInfo.class}-subtle text-${statusInfo.class}-emphasis rounded-pill">${statusInfo.text}</span></td>
            <td class="text-center">
                <button class="btn btn-sm btn-icon" data-action="focus" data-idx="${idx}" title="Focar no mapa"><i class="fas fa-map-marker-alt text-info"></i></button>
                <button class="btn btn-sm btn-icon btn-validate" data-action="validate" data-idx="${idx}" title="Validar endereço"><i class="fas fa-search-location text-primary"></i></button>
                <button class="btn btn-sm btn-icon" data-action="remove" data-idx="${idx}" title="Remover endereço"><i class="fas fa-trash-alt text-danger"></i></button>
            </td>
        `;
    },

    getStatusInfo(status) {
        switch (status) {
            case 'OK': return { class: 'success', text: t('validated_label') };
            case 'Pendente': return { class: 'warning', text: t('pending') };
            default: return { class: 'danger', text: 'Erro' };
        }
    }
};


// ========================
// 4. MÓDULO DE ESTATÍSTICAS (previewStats)
// ========================
const previewStats = {
    update() {
        const statsBar = document.getElementById('stats-bar');
        if (!statsBar) return;
        const total = enderecosData.length;
        const validados = enderecosData.filter(e => e.status_google === 'OK').length;
        const pendentes = total - validados;
        statsBar.innerHTML = `<span aria-live="polite"><i class="fas fa-chart-pie me-2"></i><strong>${t('total')}: ${total}</strong> | <span class="text-success">${t('validated_label')}: ${validados}</span> | <span class="text-warning">${t('pending')}: ${pendentes}</span></span>`;
    }
};


// ========================
// 5. MÓDULO DO MAPA (previewMap)
// ========================
const previewMap = {
    async onMarkerDragEnd(idx, marker) {
        const row = document.getElementById(`row-${idx}`);
        row?.classList.add('table-info');
        try {
            const data = await api.fetch('/api/reverse-geocode', {
                method: "POST",
                body: { idx, lat: marker.getLngLat().lat, lng: marker.getLngLat().lng }
            });
            if (data.success) {
                previewTable.updateRow(idx, data.item);
                previewStats.update();
                mapManager.renderMarkers(enderecosData);
                window.MapsDrive?.showToast?.(t('updated'), t('success'));
            }
        } finally {
            row?.classList.remove('table-info');
        }
    }
};


// ========================
// 6. MÓDULO DE API (api)
// ========================
const api = {
    async fetch(endpoint, { method = 'GET', body = null } = {}) {
        previewUI.showSpinner(true);
        try {
            const options = {
                method,
                headers: { 'Content-Type': 'application/json' }
            };
            if (body) options.body = JSON.stringify(body);
            
            const resp = await fetch(endpoint, options);
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.msg || `Erro ${resp.status}`);
            return data;
        } catch (err) {
            window.MapsDrive?.showToast?.(`${t('error_comm')}${err.message}`, t('danger'));
            throw err; // Permite que a função chamadora trate o erro também.
        } finally {
            previewUI.showSpinner(false);
        }
    }
};


// ========================
// 7. MÓDULO DE UI E EVENTOS (previewUI)
// ========================
const previewUI = {
    init() {
        document.getElementById('address-table-body')?.addEventListener('click', this.handleTableClick);
        document.getElementById('btn-show-form')?.addEventListener('click', this.toggleNewAddressForm);
        document.getElementById('new-address-form')?.addEventListener('submit', this.saveNewAddress);
    },

    handleTableClick(event) {
        const button = event.target.closest('button');
        if (!button) return;
        
        const action = button.dataset.action;
        const idx = parseInt(button.dataset.idx, 10);

        switch(action) {
            case 'focus': mapManager?.focusMarker(idx); break;
            case 'validate': this.validateAddress(idx, button); break;
            case 'remove': this.removeAddress(idx); break;
        }
    },
    
    validateAddress: debounce(async function(idx, btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        try {
            const data = await api.fetch('/api/validar-linha', {
                method: "POST",
                body: { 
                    idx, 
                    endereco: document.getElementById(`address-${idx}`).value,
                    cep: document.getElementById(`cep-${idx}`).value
                }
            });
            if (data.success) {
                previewTable.updateRow(idx, data.item);
                mapManager.renderMarkers(enderecosData);
                previewStats.update();
                window.MapsDrive?.showToast?.(t('validated'), t('success'));
            }
        } catch(e) { /* Erro já tratado pela API */ }
        finally {
            btn.innerHTML = '<i class="fas fa-search-location text-primary"></i>';
            btn.disabled = false;
        }
    }, 600),

    async removeAddress(idx) {
        if (!confirm(t('error_remove'))) return;
        try {
            const data = await api.fetch('/api/remover-endereco', {
                method: "POST",
                body: { idx }
            });
            if (data.success) {
                enderecosData = data.lista;
                previewTable.rebuild();
                mapManager.renderMarkers(enderecosData);
                previewStats.update();
                window.MapsDrive?.showToast?.(t('removed'), t('warning'));
            }
        } catch(e) { /* Erro já tratado */ }
    },

    async saveNewAddress(event) {
        event.preventDefault();
        const form = event.target;
        if (!form.checkValidity()) { form.classList.add('was-validated'); return; }
        
        const submitBtn = form.querySelector('button[type=submit]');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> ${t('saving')}`;

        try {
            const data = await api.fetch('/api/add-address', {
                method: "POST",
                body: { 
                    id: document.getElementById('new_id').value,
                    endereco: document.getElementById('new_address').value,
                    cep: document.getElementById('new_cep').value
                }
            });
            if (data.success) {
                enderecosData.push(data.item);
                previewTable.appendRow(data.item, enderecosData.length - 1);
                mapManager.renderMarkers(enderecosData);
                previewStats.update();
                previewUI.toggleNewAddressForm();
                form.reset();
                form.classList.remove('was-validated');
                window.MapsDrive?.showToast?.(t('added'), t('success'));
            }
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    },

    toggleNewAddressForm() {
        const form = document.getElementById('new-address-form');
        const btn = document.getElementById('btn-show-form');
        const isHidden = form.style.display === 'none';
        form.style.display = isHidden ? 'block' : 'none';
        btn.innerHTML = isHidden ? `<i class="fas fa-times me-1"></i> ${t('cancel')}` : `<i class="fas fa-plus-circle me-1"></i> ${t('add')}`;
        btn.classList.toggle('btn-secondary', isHidden);
        btn.classList.toggle('btn-success', !isHidden);
        if (isHidden) form.querySelector('input').focus();
    },
    
    showSpinner(show = true) {
        let el = document.getElementById('global-spinner');
        if (show && !el) {
            el = document.createElement('div');
            el.id = 'global-spinner';
            el.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.1);z-index:2000;display:flex;align-items:center;justify-content:center;';
            el.innerHTML = `<div class="spinner-border text-primary" style="width:3rem;height:3rem;"></div>`;
            document.body.appendChild(el);
        } else if (!show && el) {
            el.remove();
        }
    }
};
