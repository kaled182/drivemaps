# app/routes/gerar.py

from flask import Blueprint, request, redirect, url_for, session, send_file, jsonify
import csv
import io
import uuid
from datetime import datetime
from app.utils.helpers import normalizar, CORES_IMPORTACAO
from app.utils.google import valida_rua_google
import logging

logger = logging.getLogger(__name__)
gerar_routes = Blueprint('gerar', __name__)

@gerar_routes.route('/generate', methods=['POST'])
def generate():
    """Gera CSV com dados validados e armazena na sessão."""
    try:
        # Validação de entrada
        total_str = request.form.get('total', '0')
        try:
            total = int(total_str)
            if total <= 0 or total > 1000:  # Limite de segurança
                return jsonify({"success": False, "msg": "Número de itens inválido"}), 400
        except ValueError:
            return jsonify({"success": False, "msg": "Total deve ser um número"}), 400

        lista = []

        # Processa cada item
        for i in range(total):
            item = {
                "order_number": request.form.get(f'numero_pacote_{i}', str(i + 1)),
                "address": request.form.get(f'endereco_{i}', ''),
                "cep": request.form.get(f'cep_{i}', ''),
                "importacao_tipo": request.form.get(f'importacao_tipo_{i}', 'manual'),
                "cor": request.form.get(f'cor_{i}', CORES_IMPORTACAO.get('manual', '#0074D9'))
            }

            # Validação básica do item
            if not item["address"].strip():
                continue  # Pula itens sem endereço

            # Validação com Google Maps
            res_google = valida_rua_google(item["address"], item["cep"])
            
            # Processamento dos resultados
            rua_digitada = item["address"].split(',')[0] if item["address"] else ''
            rua_google = res_google.get('route_encontrada', '')
            cep_ok = item["cep"] == res_google.get('postal_code_encontrado', '')
            
            # Comparação de ruas
            rua_bate = False
            if rua_digitada and rua_google:
                rua_bate = (normalizar(rua_digitada) in normalizar(rua_google) or 
                           normalizar(rua_google) in normalizar(rua_digitada))

            # Atualiza item com dados do Google
            item.update({
                "status_google": res_google.get('status', 'ERROR'),
                "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
                "latitude": res_google.get('coordenadas', {}).get('lat', ''),
                "longitude": res_google.get('coordenadas', {}).get('lng', ''),
                "rua_google": rua_google,
                "cep_ok": cep_ok,
                "rua_bate": rua_bate,
                "freguesia": res_google.get('sublocality', ''),
                "error": res_google.get('error', '')
            })
            
            lista.append(item)

        if not lista:
            return jsonify({"success": False, "msg": "Nenhum item válido para processar"}), 400

        # Gera CSV em memória
        csv_content = _gerar_csv_content(lista)
        
        # Armazena na sessão com ID único
        csv_id = str(uuid.uuid4())
        session[f'csv_{csv_id}'] = {
            'content': csv_content,
            'timestamp': datetime.now().isoformat(),
            'total_items': len(lista)
        }
        session.modified = True

        return redirect(url_for('gerar.download', csv_id=csv_id))

    except Exception as e:
        logger.error(f"Erro ao gerar CSV: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": f"Erro interno: {str(e)}"}), 500

@gerar_routes.route('/download')
def download():
    """Faz download do CSV gerado."""
    csv_id = request.args.get('csv_id')
    
    if not csv_id:
        return jsonify({"error": "ID do CSV não fornecido"}), 400
    
    # Recupera da sessão
    csv_data = session.get(f'csv_{csv_id}')
    if not csv_data:
        return jsonify({"error": "CSV não encontrado ou expirado"}), 404
    
    csv_content = csv_data.get('content', '')
    if not csv_content:
        return jsonify({"error": "Conteúdo CSV vazio"}), 400
    
    # Remove da sessão após o uso
    session.pop(f'csv_{csv_id}', None)
    session.modified = True
    
    # Gera nome do arquivo com timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'enderecos_validados_{timestamp}.csv'
    
    return send_file(
        io.BytesIO(csv_content.encode('utf-8-sig')),  # BOM para Excel
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

def _gerar_csv_content(lista):
    """Gera o conteúdo do CSV a partir da lista de itens."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    
    # Cabeçalho
    writer.writerow([
        "order number", "name", "address", "latitude", "longitude", "duration",
        "start time", "end time", "phone", "contact", "notes", "color",
        "Group", "rua_google", "freguesia_google", "status", "cep_original", "cep_google"
    ])

    # Dados
    for row in lista:
        # Determina status
        status = "Validado"
        if row.get("status_google") != "OK":
            status = f"Erro Google: {row.get('status_google', 'UNKNOWN')}"
        elif not row.get("cep_ok", False):
            status = "CEP divergente"
        elif not row.get("rua_bate", False):
            status = "Rua divergente"

        writer.writerow([
            row.get("order_number", ""),
            "",  # name
            row.get("address", ""),
            row.get("latitude", ""),
            row.get("longitude", ""),
            "",  # duration
            "",  # start time
            "",  # end time
            "",  # phone
            "",  # contact
            row.get("postal_code_encontrado", "") or row.get("cep", ""),  # notes
            row.get("cor", "#0074D9"),
            row.get("importacao_tipo", "manual"),  # Group
            row.get("rua_google", ""),
            row.get("freguesia", ""),
            status,
            row.get("cep", ""),
            row.get("postal_code_encontrado", "")
        ])

    return output.getvalue()

@gerar_routes.route('/api/limpar-csv-antigos', methods=['POST'])
def limpar_csv_antigos():
    """Remove CSVs antigos da sessão para evitar acúmulo."""
    try:
        chaves_removidas = []
        
        # Lista todas as chaves de CSV na sessão
        chaves_csv = [k for k in session.keys() if k.startswith('csv_')]
        
        # Remove chaves antigas (mais de 1 hora)
        limite_tempo = datetime.now().timestamp() - 3600  # 1 hora
        
        for chave in chaves_csv:
            csv_data = session.get(chave, {})
            timestamp_str = csv_data.get('timestamp', '')
            
            try:
                timestamp = datetime.fromisoformat(timestamp_str).timestamp()
                if timestamp < limite_tempo:
                    session.pop(chave, None)
                    chaves_removidas.append(chave)
            except:
                # Remove se não conseguir parsear timestamp
                session.pop(chave, None)
                chaves_removidas.append(chave)
        
        if chaves_removidas:
            session.modified = True
        
        return jsonify({
            "success": True,
            "removidos": len(chaves_removidas),
            "restantes": len([k for k in session.keys() if k.startswith('csv_')])
        })
        
    except Exception as e:
        logger.error(f"Erro ao limpar CSVs antigos: {str(e)}")
        return jsonify({"success": False, "msg": str(e)}), 500
