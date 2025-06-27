/**
 * MapsDrive - Map Manager
 * Classe modular e reutilizável para gerir a lógica do mapa Mapbox GL.
 * Suporta temas dinâmicos (claro/escuro) e marcadores customizados com número do pacote.
 */
class MapManager {
    /**
     * @param {string} containerId - O ID do elemento HTML onde o mapa será renderizado.
     * @param {string} accessToken - Seu token do Mapbox.
     * @param {object} [options={}] - Opções extras (ex: callbacks).
     * @param {function} [options.onMarkerDragEnd] - Callback chamado ao arrastar marcador.
     */
    constructor(containerId, accessToken, options = {}) {
        this.containerId = containerId;
        this.accessToken = accessToken;
        this.options = { defaultZoom: 11, ...options };
        this.map = null;
        this.markers = {};
        this.addressData = []; // Estado interno dos dados de endereços.
        this.currentTheme = 'light';
    }

    /**
     * Valida se uma coordenada é um número válido.
     * @param {any} coord - A coordenada (latitude ou longitude).
     * @returns {boolean} - Verdadeiro se for um número válido.
     */
    _isValidCoordinate(coord) {
        const num = parseFloat(coord);
        return !isNaN(num);
    }

    /**
     * Inicializa o mapa Mapbox.
     * @param {Array} initialData - Lista de endereços para centralização inicial.
     */
    init(initialData = []) {
        if (!this.accessToken) {
            this.handleError("Token de acesso do Mapbox não fornecido.");
            return;
        }
        mapboxgl.accessToken = this.accessToken;
        this.addressData = initialData;

        const validCoords = this.addressData
            .filter(item => this._isValidCoordinate(item.latitude) && this._isValidCoordinate(item.longitude));
            
        const center = validCoords.length > 0
            ? [validCoords[0].longitude, validCoords[0].latitude]
            : [-9.1393, 38.7223]; // Fallback: Lisboa

        const theme = document.documentElement.getAttribute('data-bs-theme') || 'light';
        this.currentTheme = theme;

        this.map = new mapboxgl.Map({
            container: this.containerId,
            style: theme === 'dark'
                ? 'mapbox://styles/mapbox/dark-v11'
                : 'mapbox://styles/mapbox/streets-v12',
            center: center,
            zoom: this.options.defaultZoom
        });

        this.map.addControl(new mapboxgl.NavigationControl());
    }

    /**
     * Renderiza marcadores customizados, com círculo numerado e cor do pacote.
     * @param {Array} addressData - Lista de endereços (atualiza o estado interno).
     */
    renderMarkers(addressData) {
        if (!this.map) return;
        this.addressData = addressData;

        // Remove todos os marcadores antigos
        Object.values(this.markers).forEach(marker => marker.remove());
        this.markers = {};

        const validCoords = this.addressData.map((item, index) => ({ ...item, originalIndex: index }))
            .filter(item => this._isValidCoordinate(item.latitude) && this._isValidCoordinate(item.longitude));

        if (validCoords.length === 0) {
            this.handleError("Nenhum endereço com coordenadas válidas para exibir no mapa.");
            return;
        }

        validCoords.forEach(item => {
            // Define cor: vermelho para pendente/erro, cor do pacote para validado
            const markerColor = item.status_google !== "OK" ? "#E74C3C" : (item.cor || "#0d6efd");

            // Cria elemento HTML para marcador customizado
            const el = document.createElement('div');
            el.className = 'custom-marker-numbered';
            el.style.backgroundColor = markerColor;
            el.innerText = String(item.order_number || item.originalIndex + 1).substring(0, 4);

            const marker = new mapboxgl.Marker({
                element: el,
                draggable: true
            })
            .setLngLat([item.longitude, item.latitude])
            .setPopup(new mapboxgl.Popup({ offset: 25 }).setHTML(`
                <div class="map-infowindow">
                    <h6>${item.order_number || 'Sem ID'}</h6>
                    <p>${item.address}</p>
                    <p>CEP: ${item.cep || 'Não informado'}</p>
                    ${item.status_google === 'OK'
                        ? '<p class="text-success small">✓ Validado</p>'
                        : `<p class="text-danger small">${item.status_google || 'Não validado'}</p>`}
                </div>
            `))
            .addTo(this.map);

            // Callback para arrastar
            if (typeof this.options.onMarkerDragEnd === 'function') {
                marker.on('dragend', () => this.options.onMarkerDragEnd(item.originalIndex, marker));
            }
            this.markers[item.originalIndex] = marker;
        });

        this.fitToBounds(validCoords);
    }

    /**
     * Ajusta zoom/área do mapa para mostrar todos os pontos.
     * @param {Array} data - Lista de endereços válidos.
     */
    fitToBounds(data) {
        if (!this.map || data.length === 0) return;
        if (data.length === 1) {
            this.map.flyTo({ center: [data[0].longitude, data[0].latitude], zoom: 15 });
            return;
        }
        const bounds = new mapboxgl.LngLatBounds();
        data.forEach(item => bounds.extend([item.longitude, item.latitude]));
        this.map.fitBounds(bounds, { padding: 80, maxZoom: 15 });
    }

    /**
     * Foca e abre o popup do marcador pelo índice original.
     * @param {number} index - Índice na lista original.
     */
    focusMarker(index) {
        const marker = this.markers[index];
        if (marker) {
            this.map.flyTo({ center: marker.getLngLat(), zoom: 16 });
            marker.togglePopup();
        }
    }

    /**
     * Altera o tema do mapa (claro/escuro) e redesenha marcadores.
     * @param {'light' | 'dark'} theme
     */
    setTheme(theme) {
        if (!this.map || (theme !== 'dark' && theme !== 'light') || this.currentTheme === theme) return;
        this.currentTheme = theme;
        const styleUrl = theme === 'dark'
            ? 'mapbox://styles/mapbox/dark-v11'
            : 'mapbox://styles/mapbox/streets-v12';
        this.map.setStyle(styleUrl);

        // Após trocar o style, renderize novamente os marcadores (pois são apagados)
        this.map.once('styledata', () => {
            this.renderMarkers(this.addressData);
        });
    }

    /**
     * Mostra mensagem de erro no container do mapa.
     * @param {string} message
     */
    handleError(message) {
        const mapDiv = document.getElementById(this.containerId);
        if (mapDiv) {
            mapDiv.innerHTML = `<div class="d-flex h-100 align-items-center justify-content-center map-empty-message">
                <div class="text-center p-4">
                    <h5 class="text-danger"><i class="fas fa-exclamation-triangle me-2"></i>Mapa indisponível</h5>
                    <p class="text-muted small">${message}</p>
                </div>
            </div>`;
        }
        console.error("MapManager Error:", message);
    }
}

// Exporta globalmente
window.MapManager = MapManager;
