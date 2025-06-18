# app/routes/gerar.py

from flask import Blueprint, request, redirect, url_for, session, send_file
import csv
import io
from app.utils.helpers import normalizar
from app.utils.google import valida_rua_google, CORES_IMPORTACAO

gerar_routes = Blueprint('gerar', __name__)
csv_content = None

@gerar_routes.route('/generate', methods=['POST'])
def generate():
    try:
        global csv_content
        total = int(request.form['total'])
        lista = []

        for i in range(total):
            item = {
                "order_number": request.form.get(f'numero_pacote_{i}', ''),
                "address": request.form.get(f'endereco_{i}', ''),
                "cep": request.form.get(f'cep_{i}', ''),
                "importacao_tipo": request.form.get(f'importacao_tipo_{i}', 'manual'),
                "cor": request.form.get(f'cor_{i}', CORES_IMPORTACAO[0])
            }

            res_google = valida_rua_google(item["address"], item["cep"])
            item.update({
                "status_google": res_google.get('status'),
                "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
                "latitude": res_google.get('coordenadas', {}).get('lat'),
                "longitude": res_google.get('coordenadas', {}).get('lng'),
                "rua_google": res_google.get('route_encontrada', ''),
                "cep_ok": item["cep"] == res_google.get('postal_code_encontrado', ''),
                "rua_bate": normalizar(item["address"].split(',')[0]) in normalizar(res_google.get('route_encontrada', '')) if item["address"] else False,
                "freguesia": res_google.get('sublocality', '')
            })
            lista.append(item)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "order number", "name", "address", "latitude", "longitude", "duration",
            "start time", "end time", "phone", "contact", "notes", "color",
            "Group", "rua_google", "freguesia_google", "status"
        ])

        for row in lista:
            status = "Validado"
            if not row["cep_ok"]:
                status = "CEP divergente"
            elif not row["rua_bate"]:
                status = "Rua divergente"

            writer.writerow([
                row["order_number"], "", row["address"],
                row["latitude"], row["longitude"], "", "", "", "", "",
                row["postal_code_encontrado"] or row["cep"],
                row["cor"], "", row["rua_google"],
                row.get("freguesia", ""), status
            ])

        csv_content = output.getvalue()
        return redirect(url_for('gerar.download'))

    except Exception as e:
        return {"success": False, "msg": f"Erro ao gerar CSV: {str(e)}"}, 500

@gerar_routes.route('/download')
def download():
    global csv_content
    if not csv_content:
        return "Nenhum conteúdo gerado para download", 400
    return send_file(
        io.BytesIO(csv_content.encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='enderecos_validados.csv'
    )
