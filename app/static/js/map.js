function initMap() {
    // Centro fixo em Portugal continental (aprox. centro geográfico)
    const center = { lat: 39.630, lng: -8.620 };

    const map = new google.maps.Map(document.getElementById("map"), {
        zoom: 7,
        center: center,
    });

    if (typeof locations !== "undefined") {
        locations.forEach(loc => {
            if (
                typeof loc.lat === "number" &&
                typeof loc.lng === "number" &&
                !isNaN(loc.lat) &&
                !isNaN(loc.lng)
            ) {
                new google.maps.Marker({
                    position: { lat: loc.lat, lng: loc.lng },
                    map: map,
                    title: `ID: ${loc.id} - ${loc.title || ""}`,
                    label: `${loc.id}`
                });
            }
        });
    }
}

window.initMap = initMap;
