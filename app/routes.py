from flask import Blueprint, render_template, request, jsonify, send_file
from app.utils import valida_endereco_google
import json
import csv
import io

main_routes = Blueprint('main', __name__)

@main_routes.route('/generate_csv', methods=['POST'])
def generate_csv():
    resultados = json.loads(request.form['enderecos_json'])
    
    # Gera CSV em memória
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Endereço', 'Latitude', 'Longitude', 'CEP'])
    
    for r in resultados:
        if r['status'] == 'OK':
            writer.writerow([
                r['endereco_formatado'],
                r['coordenadas']['lat'],
                r['coordenadas']['lng'],
                # Extrai CEP do endereço (adapte conforme sua lógica)
                re.search(r'\d{4}-\d{3}', r['endereco_formatado']).group(0) if re.search(r'\d{4}-\d{3}', r['endereco_formatado']) else ''
            ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='enderecos_validados.csv'
    )
