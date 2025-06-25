/**
 * MapsDrive - Map Manager
 * Classe modular e reutilizável para gerir a lógica do mapa Mapbox GL.
 * Esta classe é responsável por inicializar o mapa, renderizar marcadores
 * e comunicar eventos (como o arrastar de um marcador) de volta para o script principal.
 */
class MapManager {
    /**
     * @param {string} containerId - O ID do elemento HTML onde o mapa será renderizado.
     * @param {string} accessToken - O seu token de acesso do Mapbox.
     * @param {object} [options={}] - Opções de configuração adicionais.
     * @param {function} [options.onMarkerDragEnd] - Callback a ser executado quando um marcador é arrastado.
     */
    constructor(containerId, accessToken, options = {}) {
        this.containerId = containerId;
        this.accessToken = accessToken;
        this.options = { defaultZoom: 11, ...options };
        this.map = null;
        this.markers = {}; // Usar um objeto para associar marcadores a um ID único (ex: originalIndex)
    }

    /**
     * Inicializa o mapa Mapbox.
     * @param {Array} initialData - Os dados iniciais dos endereços para encontrar um ponto central.
     */
    init(initialData = []) {
        if (!this.accessToken) {
            this.handleError("Token de acesso do Mapbox não fornecido.");
            return;
        }
        mapboxgl.accessToken = this.accessToken;

        const validCoords = initialData.filter(item => item.latitude && item.longitude);
        const center = validCoords.length > 0 ? [validCoords[0].longitude, validCoords[0].latitude] : [-9.1393, 38.7223]; // Lisboa como fallback

        this.map = new mapboxgl.Map({
            container: this.containerId,
            style: 'mapbox://styles/mapbox/streets-v12',
            center: center,
            zoom: this.options.defaultZoom
        });
        this.map.addControl(new mapboxgl.NavigationControl());
    }

    /**
     * Limpa todos os marcadores existentes e renderiza novos com base nos dados fornecidos.
     * @param {Array} addressData - A lista completa de endereços para renderizar.
     */
    renderMarkers(addressData) {
        if (!this.map) return;

        // Limpa marcadores antigos
        Object.values(this.markers).forEach(marker => marker.remove());
        this.markers = {};

        const validCoords = addressData.map((item, index) => ({...item, originalIndex: index}))
                                       .filter(item => item.latitude && item.longitude);
        
        if (validCoords.length === 0) {
            this.handleError("Nenhum endereço com coordenadas válidas para exibir no mapa.");
            return;
        }

        validCoords.forEach(item => {
            // *** AQUI ACONTECE A MAGIA ***
            // 1. Criar um elemento div para ser o nosso marcador customizado.
            const el = document.createElement('div');
            el.className = 'custom-marker'; // Aplicar a classe CSS que criámos
            el.style.backgroundColor = item.cor || '#0d6efd'; // Definir a cor dinamicamente
            el.innerText = String(item.order_number || item.originalIndex + 1).substring(0, 4); // Inserir o ID

            // 2. Criar o marcador do Mapbox usando o nosso elemento HTML.
            const marker = new mapboxgl.Marker({
                element: el,
                draggable: true
            })
            .setLngLat([item.longitude, item.latitude])
            .setPopup(new mapboxgl.Popup({ offset: 25 }).setHTML(`
                <div class="map-infowindow">
                  <h6>ID: ${item.order_number || 'Sem ID'}</h6>
                  <p>${item.address}</p>
                  <p>CEP: ${item.cep || 'Não informado'}</p>
                  ${item.status_google === 'OK'
                    ? '<p class="text-success small">✓ Validado</p>'
                    : `<p class="text-danger small">${item.status_google || 'Não validado'}</p>`}
                </div>
            `))
            .addTo(this.map);

            // Se um callback para o 'drag end' foi fornecido, associa-o
            if (typeof this.options.onMarkerDragEnd === 'function') {
                marker.on('dragend', () => this.options.onMarkerDragEnd(item.originalIndex, marker));
            }
            
            this.markers[item.originalIndex] = marker;
        });
        
        this.fitToBounds(validCoords);
    }

    /**
     * Ajusta o zoom e o centro do mapa para mostrar todos os endereços.
     * @param {Array} data - A lista de endereços com coordenadas.
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
     * Foca o mapa num marcador específico.
     * @param {number} index - O índice do marcador a focar.
     */
    focusMarker(index) {
        const marker = this.markers[index];
        if (marker) {
            this.map.flyTo({ center: marker.getLngLat(), zoom: 16 });
            marker.togglePopup();
        }
    }
    
    /**
     * Mostra uma mensagem de erro no container do mapa.
     * @param {string} message - A mensagem de erro a ser exibida.
     */
    handleError(message) {
        const mapDiv = document.getElementById(this.containerId);
        if (mapDiv) {
            mapDiv.innerHTML = `<div class="d-flex h-100 align-items-center justify-content-center">
                <div class="text-center p-4 bg-white rounded shadow">
                    <h5 class="text-danger"><i class="fas fa-exclamation-triangle me-2"></i>Mapa indisponível</h5>
                    <p class="text-muted small">${message}</p>
                </div>
            </div>`;
        }
        console.error("MapManager Error:", message);
    }
}
