# app/routes/gerar.py
from flask import Blueprint, request, redirect, url_for, session, send_file, flash
import csv
import io
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
gerar_bp = Blueprint('gerar', __name__)

@gerar_bp.route('/generate', methods=['POST'])
def generate():
    """
    Gera um CSV a partir dos dados JÁ VALIDADOS na sessão.
    Não revalida endereços, apenas exporta.
    """
    try:
        lista_final = session.get('lista', [])

        if not lista_final:
            flash("Não há endereços na sessão para gerar o arquivo.", "warning")
            return redirect(url_for('preview.preview'))

        # Gera o conteúdo do CSV usando os dados da sessão
        csv_content = _gerar_csv_content(lista_final)

        # Usa um ID único para o CSV na sessão, permitindo múltiplos downloads simultâneos
        csv_id = str(uuid.uuid4())
        session[f'csv_{csv_id}'] = {
            'content': csv_content,
            'timestamp': datetime.now().isoformat(),
            'filename': f'enderecos_validados_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
        }
        session.modified = True

        return redirect(url_for('gerar.download', csv_id=csv_id))

    except Exception as e:
        logger.error(f"Erro ao gerar CSV: {str(e)}", exc_info=True)
        flash(f"Ocorreu um erro inesperado ao gerar o arquivo CSV: {e}", "danger")
        return redirect(url_for('preview.preview'))

@gerar_bp.route('/download/<csv_id>')
def download(csv_id):
    """
    Fornece o download do CSV gerado e armazenado na sessão.
    """
    csv_data_key = f'csv_{csv_id}'
    csv_data = session.get(csv_data_key)

    if not csv_data or not csv_data.get('content'):
        flash("Arquivo CSV não encontrado ou expirado. Por favor, gere novamente.", "warning")
        return redirect(url_for('preview.preview'))

    # Remove o CSV da sessão após o uso para não acumular dados
    session.pop(csv_data_key, None)
    session.modified = True

    return send_file(
        io.BytesIO(csv_data['content'].encode('utf-8-sig')),  # utf-8-sig para Excel
        mimetype='text/csv',
        as_attachment=True,
        download_name=csv_data.get('filename', 'enderecos.csv')
    )

def _gerar_csv_content(lista):
    """
    Função auxiliar que cria a string do CSV a partir da lista de dados.
    """
    output = io.StringIO()
    fieldnames = [
        "order number", "name", "address", "latitude", "longitude", "duration",
        "start time", "end time", "phone", "contact", "notes", "color",
        "Group", "rua_google", "freguesia_google", "status",
        "cep_original", "cep_google"
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()

    for row in lista:
        status = "Validado"
        if row.get("status_google") != "OK":
            status = f"Erro Google: {row.get('status_google', 'UNKNOWN')}"
        elif not row.get("cep_ok", False):
            status = "CEP divergente"
        elif not row.get("rua_bate", False):
            status = "Rua divergente"
        
        csv_row = {
            'order number': row.get("order_number", ""),
            'name': "",  # Se quiser popular no futuro
            'address': row.get("address", ""),
            'latitude': row.get("latitude", ""),
            'longitude': row.get("longitude", ""),
            'duration': "",
            'start time': "",
            'end time': "",
            'phone': "",
            'contact': "",
            'notes': row.get("postal_code_encontrado") or row.get("cep", ""),
            'color': row.get("cor", "#0074D9"),
            'Group': row.get("importacao_tipo", "manual"),
            'rua_google': row.get("rua_google", ""),
            'freguesia_google': row.get("freguesia", ""),
            'status': status,
            'cep_original': row.get("cep", ""),
            'cep_google': row.get("postal_code_encontrado", "")
        }
        writer.writerow(csv_row)

    return output.getvalue()
