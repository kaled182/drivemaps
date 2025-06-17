// Função que será chamada pelo callback do Google Maps
function initMap() {
    // Define o centro inicial do mapa
    const center = { lat: -23.55052, lng: -46.633308 }; // Use aqui a localização desejada

    // Cria o mapa no elemento com id 'map'
    const map = new google.maps.Map(document.getElementById("map"), {
        zoom: 12,
        center: center,
    });

    // Exemplo de adição de um PIN (marcador)
    new google.maps.Marker({
        position: center,
        map: map,
        title: "Centro do mapa",
    });

    // Se você quiser adicionar vários pins, pode usar um array de posições:
    /*
    const locations = [
        { lat: -23.55052, lng: -46.633308, title: "Pin 1" },
        { lat: -23.56052, lng: -46.643308, title: "Pin 2" }
    ];
    locations.forEach(loc => {
        new google.maps.Marker({
            position: { lat: loc.lat, lng: loc.lng },
            map: map,
            title: loc.title
        });
    });
    */
}

// Garante que a função está no escopo global
window.initMap = initMap;
