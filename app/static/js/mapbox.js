// static/js/mapbox.js

/**
 * MapsDrive - Utilitários de Mapa (Mapbox)
 * Exige que mapboxgl já tenha sido carregado no HTML antes deste arquivo.
 */

class MapboxManager {
    constructor(mapElementId, token) {
        this.mapElementId = mapElementId;
        this.token = token;
        this.map = null;
        this.markers = [];
    }

    initMap(enderecosData, corPadrao = "#4285F4") {
        if (!this.token) {
            this.showError("Mapbox Token não configurado.");
            return;
        }

        // Filtra coordenadas válidas
        const validCoords = (enderecosData || []).filter(e => {
            const lat = parseFloat(e.latitude);
            const lng = parseFloat(e.longitude);
            return !isNaN(lat) && !isNaN(lng) && lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180;
        });

        if (validCoords.length === 0) {
            this.showError("Nenhuma coordenada válida encontrada");
            return;
        }

        mapboxgl.accessToken = this.token;
        this.map = new mapboxgl.Map({
            container: this.mapElementId,
            style: 'mapbox://styles/mapbox/streets-v12',
            center: [parseFloat(validCoords[0].longitude), parseFloat(validCoords[0].latitude)],
            zoom: 12
        });

        // Adiciona marcadores
        validCoords.forEach((item, idx) => {
            const marker = new mapboxgl.Marker({ color: item.cor || corPadrao })
                .setLngLat([parseFloat(item.longitude), parseFloat(item.latitude)])
                .setPopup(
                    new mapboxgl.Popup({ offset: 25 })
                    .setHTML(`
                        <div class="map-infowindow">
                            <h6>${item.order_number || 'Sem ID'}</h6>
                            <p>${item.address}</p>
                            <p>CEP: ${item.cep || 'Não informado'}</p>
                            ${item.status_google === 'OK'
                                ? '<p class="text-success">✓ Validado</p>'
                                : `<p class="text-danger">${item.status_google || 'Não validado'}</p>`}
                        </div>
                    `)
                )
                .addTo(this.map);
            this.markers.push(marker);
        });

        // Ajusta o mapa para mostrar todos os marcadores
        if (validCoords.length > 1) {
            const bounds = new mapboxgl.LngLatBounds();
            validCoords.forEach(e => bounds.extend([parseFloat(e.longitude), parseFloat(e.latitude)]));
            this.map.fitBounds(bounds, { padding: 60, animate: true });
        }
    }

    showError(msg) {
        const mapDiv = document.getElementById(this.mapElementId);
        if (mapDiv) {
            mapDiv.innerHTML = `<div class="map-empty-message">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${msg}
            </div>`;
        }
        if (document.getElementById('map-status')) {
            document.getElementById('map-status').innerText = "Erro: " + msg;
        }
        console.error("MAPBOX: " + msg);
    }
}

// Permite usar no HTML:
// <script>window.MapboxManager = MapboxManager;</script>
window.MapboxManager = MapboxManager;
