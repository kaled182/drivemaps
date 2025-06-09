from flask import Flask, request, render_template_string, send_file
import re
import csv
import io
import requests
import os

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

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>PAACK - Gerador de CSV</title>
    <style>
        body { background: #f2f6ff; font-family: Arial; }
        textarea { width: 100%; font-size: 1.1em; }
        .container { max-width: 700px; margin: auto; background: #fff; border-radius: 8px; padding: 30px; box-shadow: 0 0 16px #bbb; }
        button { background: #1976d2; color: white; padding: 12px 26px; border: none; border-radius: 5px; font-size: 1.1em; margin-top: 12px; }
    </style>
</head>
<body>
<div class="container">
    <h2>PAACK – Gerador de CSV para MyWay com Validação Google</h2>
    <form method="post">
        <label>Cole sua lista de endereços:</label><br>
        <textarea name="enderecos" rows="16" placeholder="Cole aqui sua lista bruta..."></textarea><br>
        <button type="submit">Gerar CSV para MyWay</button>
    </form>
    {% if file_ready %}
        <br>
        <a href="{{ url_for('download') }}" style="color: #1976d2; font-weight: bold;">Clique aqui para baixar seu CSV</a>
    {% endif %}
</div>
</body>
</html>
"""

csv_content = None

@app.route('/', methods=['GET', 'POST'])
def index():
    global csv_content
    file_ready = False
    if request.method == 'POST':
        enderecos_brutos = request.form['enderecos']
        regex_cep = re.compile(r'(\d{4}-\d{3})')
        linhas = [linha.strip() for linha in enderecos_brutos.split('\n') if linha.strip()]
        saida = []
        i = 0
        while i < len(linhas) - 2:
            linha = linhas[i]
            cep_match = regex_cep.search(linha)
            if cep_match:
                if i + 2 < len(linhas) and linhas[i+2] == linha:
                    numero_pacote = linhas[i+3] if (i+3) < len(linhas) else ""
                    # Valida no Google
                    status, endereco_validado, location = valida_endereco_google(linha)
                    saida.append({
                        "order_number": numero_pacote,
                        "address": linha,
                        "latitude": location["lat"] if status == "OK" and location else "",
                        "longitude": location["lng"] if status == "OK" and location else "",
                        "status": status,
                        "formatted_address": endereco_validado,
                        "notes": cep_match.group(1)  # Exemplo: salvar o código postal em notes
                    })
                    i += 4
                else:
                    i += 1
            else:
                i += 1
        # --- Gera CSV no padrão MyWay ---
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "order number", "name", "address", "latitude", "longitude", "duration", "start time",
            "end time", "phone", "contact", "notes", "color", "Group"
        ])
        for row in saida:
            writer.writerow([
                row["order_number"],  # order number
                "",                   # name
                row["address"],       # address (original)
                row["latitude"],      # latitude (do Google)
                row["longitude"],     # longitude (do Google)
                "",                   # duration
                "",                   # start time
                "",                   # end time
                "",                   # phone
                "",                   # contact
                row["notes"],         # notes (coloquei o código postal)
                "",                   # color
                ""                    # Group
            ])
        csv_content = output.getvalue()
        file_ready = True
    return render_template_string(HTML, file_ready=file_ready)

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
    app.run(host='0.0.0.0', port=10000)
