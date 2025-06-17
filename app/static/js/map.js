<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <title>DriveMaps</title>
    <style>
        #map { width: 100%; height: 400px; margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #ccc; padding: 6px 10px; font-size: 15px; }
        th { background: #f4f4f4; }
    </style>
    <!-- Google Maps API (a chave é passada do backend) -->
    <script src="https://maps.googleapis.com/maps/api/js?key={{ maps_api_key }}&callback=initMap" defer></script>
</head>
<body>
    <h1>DriveMaps</h1>
    <div id="map"></div>

    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Endereço Original</th>
                <th>Endereço Atual</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {% for loc in locations %}
            <tr>
                <td>{{ loc.id }}</td>
                <td>{{ loc.address_original }}</td>
                <td>{{ loc.address_atual }}</td>
                <td>{{ loc.status }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <script>
        // Passa os dados do backend para o JS
        const locations = {{ locations|tojson }};
    </script>
    <script src="{{ url_for('static', filename='js/map.js') }}"></script>
</body>
</html>
