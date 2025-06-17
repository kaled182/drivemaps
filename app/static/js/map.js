function initMap() {
    // Centraliza o mapa em Portugal continental
    const center = { lat: 39.630, lng: -8.620 };

    const map = new google.maps.Map(document.getElementById("map"), {
        zoom: 7,
        center: center,
    });

    // Adiciona marcadores (PINs) para cada endereço válido
    if (typeof locations !== "undefined") {
        locations.forEach(loc => {
            if (
                typeof loc.lat === "number" &&
                typeof loc.lng === "number" &&
                !isNaN(loc.lat) &&
                !isNaN(loc.lng)
            ) {
                const marker = new google.maps.Marker({
                    position: { lat: loc.lat, lng: loc.lng },
                    map: map,
                    title: loc.address_atual ?? loc.address_original ?? "",
                    label: loc.id ? String(loc.id) : undefined,
                    draggable: true // permite mover o PIN para correção manual
                });

                // Evento para atualizar backend ao mover o PIN
                marker.addListener('dragend', function (event) {
                    const novaLat = event.latLng.lat();
                    const novaLng = event.latLng.lng();

                    // Prompt para editar o endereço, se desejado
                    let novoEndereco = prompt(
                        "Deseja atualizar o endereço? (Deixe em branco para manter o atual)",
                        loc.address_atual ?? loc.address_original ?? ""
                    );
                    if (novoEndereco === null) {
                        // Cancelado pelo usuário, volta PIN para local original
                        marker.setPosition({ lat: loc.lat, lng: loc.lng });
                        return;
                    }
                    if (!novoEndereco.trim()) {
                        novoEndereco = loc.address_atual ?? loc.address_original ?? "";
                    }

                    fetch("/atualizar_endereco", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            id: loc.id,
                            address_atual: novoEndereco,
                            lat: novaLat,
                            lng: novaLng
                        })
                    })
                    .then(res => res.json())
                    .then(data => {
                        if (data.status === "ok") {
                            alert("Endereço atualizado com sucesso!");
                            // Opcional: atualizar a linha da tabela, recarregar, etc.
                            location.reload();
                        } else {
                            alert("Erro ao atualizar endereço.");
                            marker.setPosition({ lat: loc.lat, lng: loc.lng });
                        }
                    })
                    .catch(() => {
                        alert("Erro ao comunicar com o servidor.");
                        marker.setPosition({ lat: loc.lat, lng: loc.lng });
                    });
                });
            }
        });
    }
}

window.initMap = initMap;
