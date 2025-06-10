from flask import Blueprint, render_template, request, redirect, url_for, session, send_file, jsonify
import re
import csv
import io
from .utils import validar_rua_codigo_postal, valida_rua_google

main_routes = Blueprint('main', __name__)
csv_content = None

@main_routes.route('/', methods=['GET'])
def home():
    return render_template("home.html")

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
                cep = cep_match.group(1)
                lista.append({
                    "order_number": numero_pacote,
                    "address": linha,
                    "cep": cep,
                    # Novidade: NÃO valida status aqui! Campos em branco para status
                    "status_geoapi": "",
                    "rua_existe_geoapi": False,
                    "ruas_validas": [],
                    "status_google": "",
                    "postal_code_encontrado": "",
                    "endereco_formatado": "",
                    "latitude": "",
                    "longitude": "",
                })
                i += 4
            else:
                i += 1
        else:
            i += 1
    session['lista'] = lista
    return render_template("preview.html", lista=lista)

@main_routes.route('/api/validar-linha', methods=['POST'])
def validar_linha():
    endereco = request.form.get('endereco')
    cep = request.form.get('cep')
    numero_pacote = request.form.get('numero_pacote')
    nome_rua = endereco.split(',')[0].strip()
    res_geoapi = validar_rua_codigo_postal(nome_rua, cep)
    res_google = valida_rua_google(endereco, cep)
    return jsonify({
        'order_number': numero_pacote,
        'address': endereco,
        'cep': cep,
        'status_geoapi': res_geoapi['status'],
        'rua_existe_geoapi': res_geoapi['existe'],
        'ruas_validas': res_geoapi['ruas_validas'],
        'status_google': res_google.get('status'),
        'postal_code_encontrado': res_google.get('postal_code_encontrado', ''),
        'endereco_formatado': res_google.get('endereco_formatado', ''),
        'latitude': res_google.get('coordenadas', {}).get('lat', ''),
        'longitude': res_google.get('coordenadas', {}).get('lng', ''),
    })

@main_routes.route('/generate', methods=['POST'])
def generate():
    global csv_content
    total = int(request.form['total'])
    lista = []
    for i in range(total):
        numero_pacote = request.form.get(f'numero_pacote_{i}', '')
        endereco = request.form.get(f'endereco_{i}', '')
        cep = request.form.get(f'cep_{i}', '')
        nome_rua = endereco.split(',')[0].strip()
        res_geoapi = validar_rua_codigo_postal(nome_rua, cep)
        res_google = valida_rua_google(endereco, cep)
        postal_code_encontrado = res_google.get('postal_code_encontrado', '')
        lista.append({
            "order_number": numero_pacote,
            "address": endereco,
            "cep": cep,
            "status_geoapi": res_geoapi['status'],
            "rua_existe_geoapi": res_geoapi['existe'],
            "ruas_validas": res_geoapi['ruas_validas'],
            "status_google": res_google.get('status'),
            "postal_code_encontrado": postal_code_encontrado,
            "latitude": res_google.get('coordenadas', {}).get('lat', ''),
            "longitude": res_google.get('coordenadas', {}).get('lng', ''),
        })
    # Só gera se todos estiverem validados!
    todos_ok = all(row['status_geoapi'] == "OK" and row['status_google'] == "OK" and row['cep'] == row['postal_code_encontrado'] for row in lista)
    if not todos_ok:
        return "Existem endereços não validados corretamente. Corrija antes de gerar o CSV.", 400
    # Ordena pelo código postal encontrado, senão pelo informado
    lista_ordenada = sorted(lista, key=lambda x: x['postal_code_encontrado'] or x['cep'])
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "order number", "name", "address", "latitude", "longitude", "duration", "start time",
        "end time", "phone", "contact", "notes", "color", "Group"
    ])
    for row in lista_ordenada:
        writer.writerow([
            row["order_number"], "", row["address"], row["latitude"], row["longitude"], "", "", "", "", "", row["postal_code_encontrado"] or row["cep"], "", ""
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
