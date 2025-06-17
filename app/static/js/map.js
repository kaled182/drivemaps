// Integração do mapa com múltiplos pins vindos do backend, agora com InfoWindow (tooltip ao clicar)

function initMap() {
    // Usa o primeiro endereço como centro, se houver, senão um padrão
    const center = locations.length > 0 ? { lat: locations[0].lat, lng: locations[0].lng } : { lat: -41.504073, lng: -8.761827 };

    const map = new google.maps.Map(document.getElementById("map"), {
        zoom: 12,
        center: center,
    });

    const infoWindow = new google.maps.InfoWindow();

    // Adiciona marcadores para cada endereço válido e tooltip ao clicar
    const markers = locations.map(loc => {
        const marker = new google.maps.Marker({
            position: { lat: loc.lat, lng: loc.lng },
            map: map,
            title: loc.title || "",
        });

        // InfoWindow (tooltip) ao clicar
        marker.addListener("click", () => {
            infoWindow.setContent(`<div style="font-size:16px;">${marker.getTitle()}</div>`);
            infoWindow.open(map, marker);
        });

        return marker;
    });

    // Clusteriza os pins (opcional)
    if (markers.length > 0 && window.MarkerClusterer) {
        new MarkerClusterer({ markers, map });
    }
}

// Expõe globalmente (garante callback do Google)
window.initMap = initMap;
