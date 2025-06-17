function initMap() {
    // Centraliza no primeiro endereço, ou em um ponto padrão se não houver
    const center = (typeof locations !== "undefined" && locations.length > 0)
        ? { lat: locations[0].lat, lng: locations[0].lng }
        : { lat: 41.504073, lng: -8.761827 };

    const map = new google.maps.Map(document.getElementById("map"), {
        zoom: 12,
        center: center,
    });

    // Adiciona um marcador para cada localização
    if (typeof locations !== "undefined") {
        locations.forEach(loc => {
            new google.maps.Marker({
                position: { lat: loc.lat, lng: loc.lng },
                map: map,
                title: `ID: ${loc.id} - ${loc.title || ""}`,
                label: `${loc.id}`
            });
        });
    }
}

window.initMap = initMap;
