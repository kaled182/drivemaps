from flask import Blueprint, render_template, request, redirect, url_for, session, send_file
import re
import csv
import io
import os
from .utils import valida_endereco_google

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
                resultado = valida_endereco_google(linha, cep)
                lista.append({
                    "order_number": numero_pacote,
                    "address": linha,
                    "cep": cep,
                    "status": resultado.get('status'),
                    "postal_code_encontrado": resultado.get('postal_code_encontrado', ''),
                    "endereco_formatado": resultado.get('endereco_formatado', ''),
                })
                i += 4
            else:
                i += 1
        else:
            i += 1
    session['lista'] = lista  # Salva para próxima etapa
    return render_template("preview.html", lista=lista)

@main_routes.route('/generate', methods=['POST'])
def generate():
    global csv_content
    total = int(request.form['total'])
    lista = []
    for i in range(total):
        numero_pacote = request.form.get(f'numero_pacote_{i}', '')
        endereco = request.form.get(f'endereco_{i}', '')
        cep = request.form.get(f'cep_{i}', '')
        resultado = valida_endereco_google(endereco, cep)
        postal_code_encontrado = resultado.get('postal_code_encontrado', '')
        lista.append({
            "order_number": numero_pacote,
            "address": endereco,
            "cep": cep,
            "status": resultado.get('status'),
            "postal_code_encontrado": postal_code_encontrado,
            "latitude": resultado.get('coordenadas', {}).get('lat', ''),
            "longitude": resultado.get('coordenadas', {}).get('lng', ''),
        })
    # Ordena pelo código postal encontrado, senão pelo informado
    lista_ordenada = sorted(lista, key=lambda x: x['postal_code_encontrado'] or x['cep'])
    # Gera CSV
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
