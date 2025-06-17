let map;
let markers = [];

function initMap() {
    // Define a posição inicial (centro do Brasil por padrão)
    const initialCenter = { lat: -14.235004, lng: -51.92528 };

    map = new google.maps.Map(document.getElementById('map'), {
        center: initialCenter,
        zoom: 5,
    });

    // Adiciona os marcadores dos endereços
    if (Array.isArray(locations)) {
        locations.forEach((loc) => {
            if (loc.lat && loc.lng) {
                const marker = new google.maps.Marker({
                    position: { lat: loc.lat, lng: loc.lng },
                    map: map,
                    title: loc.address_atual || loc.address_original || "",
                });
                markers.push(marker);
            }
        });

        // Se tiver ao menos um endereço, centraliza no primeiro
        if (locations.length > 0 && locations[0].lat && locations[0].lng) {
            map.setCenter({ lat: locations[0].lat, lng: locations[0].lng });
            map.setZoom(12);
        }
    }
}

// Função chamada ao clicar em "Validar"
function validarEndereco(address) {
    alert("Endereço para validar:\n" + address);
    // Aqui você pode implementar a lógica de validação (ex: chamada AJAX)
}

// Se o Google Maps já carregou, chama initMap
if (typeof google !== "undefined" && typeof google.maps !== "undefined") {
    initMap();
}
