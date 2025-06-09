from flask import Flask, request, render_template_string, send_file, redirect, url_for, session
import re
import csv
import io
import requests
import os

app = Flask(__name__)
app.secret_key = "umasecretqualquer123"  # Segurança mínima para session

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
    except Exception as e:
        return "ERRO API", "", ""

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>MapsDrive – Gerador de CSV para MyWay</title>
    <style>
        body { background: #f2f6ff; font-family: Arial; }
        .container { max-width: 700px; margin: auto; background: #fff; border-radius: 8px; padding: 30px; box-shadow: 0 0 16px #bbb; }
        button { background: #1976d2; color: white; padding: 12px 26px; border: none; border-radius: 5px; font-size: 1.1em; margin-top: 12px; }
        h2 { color: #1976d2; }
    </style>
</head>
<body>
<div class="container">
    <h2>MapsDrive – Gerador de CSV para MyWay</h2>
    <form action="/preview" method="post">
        <label>Cole sua lista de endereços:</label><br>
        <textarea name="enderecos" rows="16" style="width:100%; font-size:1.1em" placeholder="Cole aqui sua lista bruta..."></textarea><br>
        <button type="submit">Pré-visualizar</button>
    </form>
</div>
</body>
</html>
"""

HTML_PREVIEW = """
<!DOCTYPE html>
<html>
<head>
    <title>MapsDrive – Pré-visualização</title>
    <style>
        body { background: #f2f6ff; font-family: Arial; }
        .container { max-width: 900px; margin: auto; background: #fff; border-radius: 8px; padding: 30px; box-shadow: 0 0 16px #bbb; }
        table { border-collapse: collapse; width: 100%; margin-top: 18px; }
        th, td { border: 1px solid #ccc; padding: 7px; text-align: left; }
        .ok { background: #e3faea; }
        .erro { background: #f9d7d7; }
        input[type="text"] { width: 98%; font-size:1.08em; }
        button { background: #1976d2; color: white; padding: 10px 24px; border: none; border-radius: 5px; font-size: 1em; margin-top: 12px; }
        h2 { color: #1976d2; }
    </style>
</head>
<body>
<div class="container">
    <h2>Pré-visualização dos Endereços</h2>
    <form action="/generate" method="post">
        <table>
            <tr>
                <th>#</th>
                <th>Endereço</th>
                <th>Status</th>
                <th>Corrigir/Confirmar</th>
            </tr>
            {% for i, item in enumerate(lista) %}
            <tr class="{{ 'ok' if item['status'] == 'OK' else 'erro' }}">
                <td>{{ i+1 }}</td>
                <td>
                    <input type="hidden" name="numero_pacote_{{i}}" value="{{item['order_number']}}">
                    <input type="hidden" name="cep_{{i}}" value="{{item['cep']}}">
                    <input type="text" name="endereco_{{i}}" value="{{item['address']}}" {% if item['status']=='OK' %}readonly{% endif %}>
                </td>
                <td>{{ item['status'] }}</td>
                <td>
                    {% if item['status'] != 'OK' %}
                        <button type="submit" name="revalidar" value="{{i}}">Validar novamente</button>
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
</div>
</body>
</html>
"""

csv_content = None

@app.route('/', methods=['GET'])
def form():
    return render_template_string(HTML_FORM)

@app.route('/preview', methods=['POST'])
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

@app.route('/generate', methods=['POST'])
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
    return redirect(url_for('download'))

@app.route('/download')
def download():
    global csv_content
    return send_file(
        io.BytesIO(csv_content.encode("utf-8")),
        mimetype='text/csv',
        as_attachment=True,
        download_name="enderecos_myway.csv"
    )

if __name__ == '__main__':
    app.secret_key = "umasecretqualquer123"
    app.run(host='0.0.0.0', port=10000)
