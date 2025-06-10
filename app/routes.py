from flask import Blueprint, render_template, request, redirect, url_for, session
import re
import csv
import io
import requests
import os

main_routes = Blueprint('main', __name__)

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

def valida_endereco_google(address, api_key=GOOGLE_API_KEY):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "region": "pt", "key": api_key}
    try:
        response = requests.get(url, params=params, timeout=8)
        data = response.json()
        if data.get('status') == 'OK':
            result = data['results'][0]
            return "OK", result['formatted_address'], result['geometry']['location']
        else:
            return "NÃO ENCONTRADO", "", ""
    except Exception:
        return "ERRO API", "", ""

# --- HTML templates (simples, recomenda-se usar arquivos em /templates) ---
HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>MapsDrive – Gerador de CSV para MyWay</title>
</head>
<body>
    <h2>MapsDrive – Gerador de CSV para MyWay</h2>
    <form action="/preview" method="post">
        <label>Cole sua lista de endereços:</label><br>
        <textarea name="enderecos" rows="16" style="width:100%; font-size:1.1em" placeholder="Cole aqui sua lista bruta..."></textarea><br>
        <button type="submit">Pré-visualizar</button>
    </form>
</body>
</html>
"""

HTML_PREVIEW = """
<!DOCTYPE html>
<html>
<head>
    <title>MapsDrive – Pré-visualização</title>
</head>
<body>
    <h2>Pré-visualização dos Endereços</h2>
    <form action="/generate" method="post">
        <table border="1" style="width:100%">
            <tr>
                <th>#</th>
                <th>Endereço</th>
                <th>Status</th>
                <th>Corrigir/Confirmar</th>
            </tr>
            {% for item in lista %}
            <tr style="background: {% if item['status'] == 'OK' %}#e3faea{% else %}#f9d7d7{% endif %};">
                <td>{{ loop.index }}</td>
                <td>
                    <input type="hidden" name="numero_pacote_{{ loop.index0 }}" value="{{item['order_number']}}">
                    <input type="hidden" name="cep_{{ loop.index0 }}" value="{{item['cep']}}">
                    <input type="text" name="endereco_{{ loop.index0 }}" value="{{item['address']}}" {% if item['status']=='OK' %}readonly{% endif %}>
                </td>
                <td>{{ item['status'] }}</td>
                <td>
                    {% if item['status'] != 'OK' %}
                        <button type="submit" name="revalidar" value="{{ loop.index0 }}">Validar novamente</button>
                    {% else %}
                        ✔️
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
        <input type="hidden" name="total" value="{{lista|length}}">
        <button type="submit" name="finalizar" value="1">Gerar CSV para MyWay</button>
    </form>
</body>
</html>
"""

csv_content = None

@main_routes.route('/', methods=['GET'])
def home():
    return render_template_string(HTML_FORM)

@main_routes.route('/preview', methods=['POST'])
def preview():
    enderecos_brutos = request.form['enderecos']
    regex_cep = re.compile(r'(\d{4}-\d{3})')
    linhas = [linha.strip() for linha in enderecos_brutos.split('\n') if linha.strip()]
    lista = []
    i = 0
    while i < len(linhas) - 2:
        linha = linhas[i]
        cep_match = regex_cep.search(linha)
        if cep_match:
            if i + 2 < len(linhas) and linhas[i+2] == linha:
                numero_pacote = linhas[i+3] if (i+3) < len(linhas) else ""
                status, endereco_validado, location = valida_endereco_google(linha)
                lista.append({
                    "order_number": numero_pacote,
                    "address": linha,
                    "cep": cep_match.group(1),
                    "status": status,
                })
                i += 4
            else:
                i += 1
        else:
            i += 1
    session['lista'] = lista  # Salva para próxima etapa
    return render_template_string(HTML_PREVIEW, lista=lista)

@main_routes.route('/generate', methods=['POST'])
def generate():
    global csv_content
    total = int(request.form['total'])
    lista = []
    for i in range(total):
        numero_pacote = request.form.get(f'numero_pacote_{i}', '')
        endereco = request.form.get(f'endereco_{i}', '')
        cep = request.form.get(f'cep_{i}', '')
        status, endereco_validado, location = valida_endereco_google(endereco)
        lista.append({
            "order_number": numero_pacote,
            "address": endereco,
            "cep": cep,
            "status": status,
            "latitude": location["lat"] if status == "OK" and location else "",
            "longitude": location["lng"] if status == "OK" and location else "",
        })
    # Gera CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "order number", "name", "address", "latitude", "longitude", "duration", "start time",
        "end time", "phone", "contact", "notes", "color", "Group"
    ])
    for row in lista:
        writer.writerow([
            row["order_number"], "", row["address"], row["latitude"], row["longitude"], "", "", "", "", "", row["cep"], "", ""
        ])
    csv_content = output.getvalue()
    return redirect(url_for('main.download'))

@main_routes.route('/download')
def download():
    global csv_content
    return send_file(
        io.BytesIO(csv_content.encode("utf-8")),
        mimetype='text/csv',
        as_attachment=True,
        download_name="enderecos_myway.csv"
    )
