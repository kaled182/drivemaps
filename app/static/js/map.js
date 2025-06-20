/**
 * MapsDrive - Map Utilities
 * Contém funções específicas para manipulação do mapa
 */

class MapManager {
  constructor(mapElementId, options = {}) {
    this.mapElement = document.getElementById(mapElementId);
    this.options = {
      defaultZoom: 12,
      clusterStyles: {
        url: 'https://developers.google.com/maps/documentation/javascript/examples/markerclusterer/m1.png',
        width: 56,
        height: 56,
        textColor: '#fff',
        textSize: 12
      },
      ...options
    };
    
    this.map = null;
    this.markers = [];
    this.markerCluster = null;
    this.infoWindow = null;
  }
  
  /**
   * Inicializa o mapa
   * @param {Object} initialPosition - Posição inicial { lat, lng }
   * @returns {Promise} Resolve quando o mapa está pronto
   */
  init(initialPosition) {
    return new Promise((resolve) => {
      if (!this.mapElement) {
        console.error('Map element not found');
        return;
      }
      
      const center = initialPosition || { lat: -15.793889, lng: -47.882778 }; // Brasília como fallback
      
      this.map = new google.maps.Map(this.mapElement, {
        zoom: this.options.defaultZoom,
        center,
        gestureHandling: 'greedy',
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: true,
        styles: this.options.mapStyles
      });
      
      this.infoWindow = new google.maps.InfoWindow();
      resolve(this.map);
    });
  }
  
  /**
   * Adiciona um marcador ao mapa
   * @param {Object} position - Posição { lat, lng }
   * @param {Object} options - Opções do marcador
   * @returns {google.maps.Marker} O marcador criado
   */
  addMarker(position, options = {}) {
    if (!this.map) {
      console.error('Map not initialized');
      return null;
    }
    
    const marker = new google.maps.Marker({
      position,
      map: this.map,
      title: options.title || '',
      icon: options.icon || null,
      draggable: options.draggable || false,
      zIndex: options.zIndex || 0
    });
    
    if (options.content) {
      marker.addListener('click', () => {
        this.infoWindow.setContent(options.content);
        this.infoWindow.open(this.map, marker);
      });
    }
    
    this.markers.push(marker);
    return marker;
  }
  
  /**
   * Remove um marcador do mapa
   * @param {google.maps.Marker} marker - Marcador a ser removido
   */
  removeMarker(marker) {
    const index = this.markers.indexOf(marker);
    if (index > -1) {
      marker.setMap(null);
      this.markers.splice(index, 1);
      
      if (this.markerCluster) {
        this.markerCluster.removeMarker(marker);
      }
    }
  }
  
  /**
   * Limpa todos os marcadores do mapa
   */
  clearMarkers() {
    this.markers.forEach(marker => marker.setMap(null));
    this.markers = [];
    
    if (this.markerCluster) {
      this.markerCluster.clearMarkers();
    }
  }
  
  /**
   * Atualiza o cluster de marcadores
   */
  updateCluster() {
    if (!this.markerCluster && this.markers.length > 0) {
      this.markerCluster = new markerClusterer.MarkerClusterer({
        map: this.map,
        markers: this.markers,
        renderer: {
          render: ({ count, position }) => {
            return new google.maps.Marker({
              position,
              label: { text: String(count), color: 'white' },
              icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 10 + Math.min(count, 10),
                fillColor: this.options.clusterColor || '#4285F4',
                fillOpacity: 0.8,
                strokeWeight: 2
              }
            });
          }
        }
      });
    } else if (this.markerCluster) {
      this.markerCluster.repaint();
    }
  }
  
  /**
   * Ajusta o zoom para mostrar todos os marcadores
   * @param {number} padding - Espaçamento opcional em pixels
   */
  fitToMarkers(padding = 50) {
    if (!this.map || this.markers.length === 0) return;
    
    const bounds = new google.maps.LatLngBounds();
    this.markers.forEach(marker => bounds.extend(marker.getPosition()));
    
    // Se houver apenas um marcador, centraliza com zoom padrão
    if (this.markers.length === 1) {
      this.map.setCenter(bounds.getCenter());
      this.map.setZoom(this.options.defaultZoom);
    } else {
      this.map.fitBounds(bounds, padding);
    }
  }
  
  /**
   * Cria um ícone personalizado para marcador
   * @param {string|number} label - Rótulo do marcador
   * @param {string} color - Cor do marcador em hexadecimal
   * @param {number} size - Tamanho do marcador
   * @returns {Object} Objeto de ícone para o marcador
   */
  static createPinIcon(label, color = '#4285F4', size = 40) {
    return {
      path: google.maps.SymbolPath.CIRCLE,
      fillColor: color,
      fillOpacity: 1,
      strokeColor: '#fff',
      strokeWeight: 2,
      scale: size / 10,
      label: {
        text: String(label).substr(0, 3),
        color: '#fff',
        fontSize: '12px'
      }
    };
  }
}

window.MapManager = MapManager;

// ========== Integração MapsDrive ==========
function initDefaultMap() {
  if (!window.enderecosData || !Array.isArray(window.enderecosData) || window.enderecosData.length === 0) {
    console.warn('Nenhum dado de endereço para exibir no mapa.');
    return;
  }
  const first = window.enderecosData.find(e => e.latitude && e.longitude);
  if (!first) {
    document.getElementById('map').innerHTML = '<div class="alert alert-warning m-3">Nenhuma localização válida para exibir</div>';
    return;
  }
  const mapManager = new MapManager('map');
  mapManager.init({ lat: parseFloat(first.latitude), lng: parseFloat(first.longitude) }).then(() => {
    // Cria marcadores
    window.enderecosData.forEach((item, idx) => {
      if (item.latitude && item.longitude) {
        mapManager.addMarker(
          { lat: parseFloat(item.latitude), lng: parseFloat(item.longitude) },
          {
            title: `${item.order_number || (idx + 1)} - ${item.address}`,
            icon: MapManager.createPinIcon(item.order_number || idx + 1, item.cor || "#4285F4", 40),
            content: `<div class="map-infowindow">
                <h6>${item.order_number || 'Sem ID'}</h6>
                <p>${item.address}</p>
                <p>CEP: ${item.cep || 'Não informado'}</p>
                ${item.status_google === 'OK' ? 
                  '<p class="text-success">✓ Validado</p>' : 
                  `<p class="text-danger">${item.status_google || 'Não validado'}</p>`}
              </div>`
          }
        );
      }
    });
    mapManager.updateCluster();
    mapManager.fitToMarkers();
  });
}
window.initDefaultMap = initDefaultMap;
