function initMap() {
    const center = { lat: 41.504073, lng: -8.761827 };

    const map = new google.maps.Map(document.getElementById("map"), {
        zoom: 12,
        center: center,
    });

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
