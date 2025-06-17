// Centraliza o mapa em 41.504073, -8.761827, sem nenhum marcador/pin

function initMap() {
    const center = { lat: 41.504073, lng: -8.761827 };

    const map = new google.maps.Map(document.getElementById("map"), {
        zoom: 12,
        center: center,
    });

    // Não adiciona nenhum marcador!
}

window.initMap = initMap;
