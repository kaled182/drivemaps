// Exemplo de integração do mapa com múltiplos pins vindos do backend, agora com InfoWindow (tooltip)

function initMap() {
    // Usa o primeiro endereço como centro, se houver, senão um padrão
    const center = locations.length > 0 ? { lat: locations[0].lat, lng: locations[0].lng } : { lat: -41.504073, lng: -8.761827 };

    const map = new google.maps.Map(document.getElementById("map"), {
        zoom: 12,
        center: center,
    });

    // Adiciona marcadores para cada endereço válido e tooltip ao clicar
    const markers = locations.map(loc => {
        const marker = new google.maps.Marker({
            position: { lat: loc.lat, lng: loc.lng },
            map: map,
            title: loc.title || "",
        });

        // InfoWindow (tooltip) ao clicar
        if (loc.title) {
            const infowindow = new google.maps.InfoWindow({
                content: `<div style="font-size:16px;">${loc.title}</div>`
            });
            marker.addListener("click", () => {
                infowindow.open(map, marker);
            });
        }
        return marker;
    });

    // Clusteriza os pins (opcional)
    if (markers.length > 0 && window.MarkerClusterer) {
        new MarkerClusterer({ markers, map });
    }
}

// Expõe globalmente (garante callback do Google)
window.initMap = initMap;
