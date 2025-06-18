let map, markers = [], markerCluster;
let enderecosData = window.enderecosData || [];

function makeSvgPin(numero, corHex) {
    let n = String(numero).substring(0, 3);
    let svg = `<svg width="44" height="54" viewBox="0 0 44 54" fill="none" xmlns="http://www.w3.org/2000/svg">
      <ellipse cx="22" cy="22" rx="21" ry="21" fill="${corHex}"/>
      <rect x="18" y="37" width="8" height="13" rx="4" fill="${corHex}"/>
      <text x="22" y="31" text-anchor="middle" font-size="20" fill="#fff" font-family="Arial" font-weight="bold" alignment-baseline="middle" dominant-baseline="middle">${n}</text>
    </svg>`;
    return "data:image/svg+xml;base64," + btoa(svg);
}

function criarMarker(idx, data) {
    if (markers[idx]) {
        markers[idx].setMap(null);
        if (markerCluster) markerCluster.removeMarker(markers[idx]);
    }
    if (!data.latitude || !data.longitude || isNaN(data.latitude) || isNaN(data.longitude)) return null;
    const position = {lat: parseFloat(data.latitude), lng: parseFloat(data.longitude)};
    const cor = data.cor || "#0074D9";
    const pinUrl = makeSvgPin(data.numero_pacote || (idx+1), cor);

    let marker = new google.maps.Marker({
        position: position,
        map: map,
        title: `${data.numero_pacote || (idx+1)} - ${data.address}`,
        icon: { url: pinUrl, scaledSize: new google.maps.Size(22, 27) },
        draggable: true,
        visible: true
    });

    markers[idx] = marker;
    if (markerCluster) markerCluster.addMarker(marker);
    return marker;
}

function initMap() {
    const coordenadasValidas = enderecosData.filter(e =>
        e.latitude !== null && e.longitude !== null && !isNaN(e.latitude) && !isNaN(e.longitude)
    );
    if (coordenadasValidas.length === 0) return;
    map = new google.maps.Map(document.getElementById('map'), {
        zoom: 12,
        center: {
            lat: parseFloat(coordenadasValidas[0].latitude),
            lng: parseFloat(coordenadasValidas[0].longitude)
        }
    });
    markerCluster = new markerClusterer.MarkerClusterer({ map, markers: [] });
    coordenadasValidas.forEach(e => criarMarker(e.idx, e));
    const bounds = new google.maps.LatLngBounds();
    coordenadasValidas.forEach(e => bounds.extend({lat: parseFloat(e.latitude), lng: parseFloat(e.longitude)}));
    if (!bounds.isEmpty()) map.fitBounds(bounds);
}

async function validarLinha(idx) {
    const linha = enderecosData[idx];
    try {
        const response = await fetch('/api/validar-linha', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                idx: idx,
                endereco: linha.address,
                cep: linha.cep,
                importacao_tipo: linha.importacao_tipo,
                numero_pacote: linha.order_number
            })
        });
        const data = await response.json();
        if (data.success) {
            enderecosData[idx] = data.item;
            criarMarker(idx, data.item);
            window.location.reload(); // Ou melhore com DOM diff
        } else {
            alert(data.msg || "Erro na validação");
        }
    } catch (error) {
        alert("Erro ao conectar com o servidor");
    }
}

async function validarTudo() {
    const progressBar = document.getElementById('progresso-barra');
    const progressContainer = document.getElementById('progresso-validacao');
    progressContainer.style.display = 'block';
    for (let i = 0; i < enderecosData.length; i++) {
        await validarLinha(i);
        progressBar.style.width = `${((i + 1) / enderecosData.length) * 100}%`;
        progressBar.textContent = `${Math.round(((i + 1) / enderecosData.length) * 100)}%`;
    }
}
