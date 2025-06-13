from flask import Blueprint, render_template, request, redirect, url_for, session, send_file, jsonify
import re
import csv
import io
import os
import pandas as pd
from .utils import valida_rua_google

main_routes = Blueprint('main', __name__)
csv_content = None

def normalizar(texto):
    import unicodedata
    if not texto:
        return ''
    return ''.join(
        c for c in unicodedata.normalize('NFKD', texto.lower()) if not unicodedata.combining(c)
    ).strip()

CORES_IMPORTACAO = {
    "manual": "#0074D9",  # Azul
    "delnext": "#FF851B", # Laranja
    "paack": "#2ECC40",   # Verde
    "outro": "#B10DC9"    # Roxo
}

def registro_unico(lista, novo):
    """Impede duplicidade de endereço + cep + tipo de importação."""
    for item in lista:
        if (
            normalizar(item["address"]) == normalizar(novo["address"]) and
            normalizar(item["cep"]) == normalizar(novo["cep"]) and
            item.get("importacao_tipo") == novo.get("importacao_tipo")
        ):
            return False
    return True

@main_routes.route('/', methods=['GET'])
def home():
    session.clear()
    return render_template("home.html")

@main_routes.route('/preview', methods=['POST'])
def preview():
    enderecos_brutos = request.form.get('enderecos', '')
    if not enderecos_brutos.strip():
        return redirect(url_for('main.home'))
    
    session['lista'] = []
    regex_cep = re.compile(r'(\d{4}-\d{3})')
    linhas = [linha.strip() for linha in enderecos_brutos.split('\n') if linha.strip()]
    lista_preview = []
    
    i = 0
    while i < len(linhas) - 2:
        linha = linhas[i]
        cep_match = regex_cep.search(linha)
        if cep_match:
            if i + 2 < len(linhas) and linhas[i+2] == linha:
                numero_pacote = linhas[i+3] if (i+3) < len(linhas) else ""
                cep = cep_match.group(1)
                res_google = valida_rua_google(linha, cep)
                rua_digitada = linha.split(',')[0] if linha else ''
                rua_google = res_google.get('route_encontrada', '')
                rua_bate = normalizar(rua_digitada) in normalizar(rua_google) or normalizar(rua_google) in normalizar(rua_digitada)
                cep_ok = cep == res_google.get('postal_code_encontrado', '')
                lista_preview.append({
                    "order_number": numero_pacote,
                    "address": linha,
                    "cep": cep,
                    "status_google": res_google.get('status'),
                    "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
                    "latitude": res_google.get('coordenadas', {}).get('lat'),
                    "longitude": res_google.get('coordenadas', {}).get('lng'),
                    "rua_google": rua_google,
                    "cep_ok": cep_ok,
                    "rua_bate": rua_bate,
                    "freguesia": res_google.get('sublocality', ''),
                    "importacao_tipo": "manual",
                    "cor": CORES_IMPORTACAO["manual"]
                })
                i += 4
            else:
                i += 1
        else:
            i += 1

    session['lista'] = lista_preview
    session.modified = True
    
    return render_template(
        "preview.html",
        lista=lista_preview,
        GOOGLE_API_KEY=os.environ.get("GOOGLE_API_KEY", ""),
        origens=["manual"] if lista_preview else []
    )

@main_routes.route('/import_planilha', methods=['POST'])
def import_planilha():
    file = request.files.get('planilha')
    empresa = request.form.get('empresa', '').lower()
    if not file or not empresa:
        return jsonify({"error": "Arquivo ou empresa não especificados"}), 400

    lista_atual = session.get('lista', [])
    nova_lista = lista_atual.copy()
    tipo_import = empresa
    cor = CORES_IMPORTACAO.get(tipo_import, CORES_IMPORTACAO["outro"])

    try:
        if empresa == "delnext":
            file.seek(0)
            if file.filename.lower().endswith('.csv'):
                df = pd.read_csv(file, header=1)
            else:
                df = pd.read_excel(file, header=1)
            
            col_end = next((c for c in df.columns if 'morada' in c.lower() or 'endereco' in c.lower()), None)
            col_cep = next((c for c in df.columns if 'codigo postal' in c.lower() or 'cod postal' in c.lower() or 'cep' in c.lower() or 'postal' in c.lower()), None)
            
            if not col_end or not col_cep:
                return jsonify({"error": "Colunas 'Morada' e 'Código Postal' não encontradas"}), 400

            for _, row in df.iterrows():
                endereco = str(row[col_end])
                cep = str(row[col_cep])
                res_google = valida_rua_google(endereco, cep)
                
                novo = {
                    "order_number": str(len(nova_lista) + 1),
                    "address": endereco,
                    "cep": cep,
                    "status_google": res_google.get('status'),
                    "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
                    "latitude": res_google.get('coordenadas', {}).get('lat'),
                    "longitude": res_google.get('coordenadas', {}).get('lng'),
                    "rua_google": res_google.get('route_encontrada', ''),
                    "cep_ok": cep == res_google.get('postal_code_encontrado', ''),
                    "rua_bate": normalizar(endereco.split(',')[0]) in normalizar(res_google.get('route_encontrada', '')) if endereco else False,
                    "freguesia": res_google.get('sublocality', ''),
                    "importacao_tipo": tipo_import,
                    "cor": cor
                }
                
                if registro_unico(nova_lista, novo):
                    nova_lista.append(novo)

        elif empresa == "paack":
            file.seek(0)
            if file.filename.lower().endswith(('.csv', '.txt')):
                conteudo = file.read().decode("utf-8")
                linhas = [linha.strip() for linha in conteudo.splitlines() if linha.strip()]
                
                i = 0
                while i < len(linhas) - 3:
                    if linhas[i+2] == linhas[i]:
                        endereco = linhas[i]
                        cep_match = re.search(r'(\d{4}-\d{3})', endereco)
                        cep = cep_match.group(1) if cep_match else ""
                        numero_pacote = linhas[i+3]
                        
                        res_google = valida_rua_google(endereco, cep)
                        novo = {
                            "order_number": numero_pacote,
                            "address": endereco,
                            "cep": cep,
                            "status_google": res_google.get('status'),
                            "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
                            "latitude": res_google.get('coordenadas', {}).get('lat'),
                            "longitude": res_google.get('coordenadas', {}).get('lng'),
                            "rua_google": res_google.get('route_encontrada', ''),
                            "cep_ok": cep == res_google.get('postal_code_encontrado', ''),
                            "rua_bate": normalizar(endereco.split(',')[0]) in normalizar(res_google.get('route_encontrada', '')) if endereco else False,
                            "freguesia": res_google.get('sublocality', ''),
                            "importacao_tipo": tipo_import,
                            "cor": cor
                        }
                        
                        if registro_unico(nova_lista, novo):
                            nova_lista.append(novo)
                        i += 4
                    else:
                        i += 1
            else:
                df = pd.read_excel(file, header=0)
                col_end = next((c for c in df.columns if 'endereco' in c.lower() or 'address' in c.lower()), None)
                col_cep = next((c for c in df.columns if 'cep' in c.lower() or 'postal' in c.lower()), None)
                
                if not col_end or not col_cep:
                    return jsonify({"error": "Colunas de endereço e CEP não encontradas"}), 400
                
                for _, row in df.iterrows():
                    endereco = str(row[col_end])
                    cep = str(row[col_cep])
                    res_google = valida_rua_google(endereco, cep)
                    
                    novo = {
                        "order_number": str(len(nova_lista) + 1),
                        "address": endereco,
                        "cep": cep,
                        "status_google": res_google.get('status'),
                        "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
                        "latitude": res_google.get('coordenadas', {}).get('lat'),
                        "longitude": res_google.get('coordenadas', {}).get('lng'),
                        "rua_google": res_google.get('route_encontrada', ''),
                        "cep_ok": cep == res_google.get('postal_code_encontrado', ''),
                        "rua_bate": normalizar(endereco.split(',')[0]) in normalizar(res_google.get('route_encontrada', '')) if endereco else False,
                        "freguesia": res_google.get('sublocality', ''),
                        "importacao_tipo": tipo_import,
                        "cor": cor
                    }
                    
                    if registro_unico(nova_lista, novo):
                        nova_lista.append(novo)

        else:
            return jsonify({"error": "Tipo de empresa não suportado"}), 400

        session['lista'] = nova_lista
        session.modified = True

        origens = list({item["importacao_tipo"] for item in nova_lista})
        return jsonify({
            "success": True,
            "total": len(nova_lista),
            "origens": origens,
            "lista": nova_lista
        })

    except Exception as e:
        return jsonify({"error": f"Erro ao processar arquivo: {str(e)}"}), 500

@main_routes.route('/api/validar-linha', methods=['POST'])
def validar_linha():
    try:
        data = request.get_json()
        idx = data.get('idx', -1)
        endereco = data.get('endereco', '')
        cep = data.get('cep', '')
        importacao_tipo = data.get('importacao_tipo', 'manual')
        numero_pacote = data.get('numero_pacote', str(len(session.get('lista', [])) + 1))
        
        res_google = valida_rua_google(endereco, cep)
        rua_digitada = endereco.split(',')[0] if endereco else ''
        rua_google = res_google.get('route_encontrada', '')
        rua_bate = normalizar(rua_digitada) in normalizar(rua_google) or normalizar(rua_google) in normalizar(rua_digitada)
        cep_ok = cep == res_google.get('postal_code_encontrado', '')
        
        lista_atual = session.get('lista', [])
        cor = CORES_IMPORTACAO.get(importacao_tipo, CORES_IMPORTACAO["outro"])
        
        novo_item = {
            "order_number": numero_pacote,
            "address": endereco,
            "cep": cep,
            "status_google": res_google.get('status'),
            "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
            "latitude": res_google.get('coordenadas', {}).get('lat'),
            "longitude": res_google.get('coordenadas', {}).get('lng'),
            "rua_google": rua_google,
            "cep_ok": cep_ok,
            "rua_bate": rua_bate,
            "freguesia": res_google.get('sublocality', ''),
            "importacao_tipo": importacao_tipo,
            "cor": cor
        }
        
        if idx >= 0 and idx < len(lista_atual):
            lista_atual[idx] = novo_item
        else:
            lista_atual.append(novo_item)
        
        session['lista'] = lista_atual
        session.modified = True
        
        return jsonify({
            "success": True,
            "item": novo_item,
            "idx": idx if idx >= 0 else len(lista_atual) - 1
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@main_routes.route('/api/get-session-data', methods=['GET'])
def get_session_data():
    lista_atual = session.get('lista', [])
    return jsonify({
        "lista": lista_atual,
        "origens": list({item["importacao_tipo"] for item in lista_atual}),
        "total": len(lista_atual)
    })

@main_routes.route('/generate', methods=['POST'])
def generate():
    global csv_content
    try:
        total = int(request.form['total'])
        lista = []
        
        for i in range(total):
            item = {
                "order_number": request.form.get(f'numero_pacote_{i}', ''),
                "address": request.form.get(f'endereco_{i}', ''),
                "cep": request.form.get(f'cep_{i}', ''),
                "importacao_tipo": request.form.get(f'importacao_tipo_{i}', 'manual'),
                "cor": request.form.get(f'cor_{i}', CORES_IMPORTACAO["manual"])
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
        return redirect(url_for('main.download'))
    
    except Exception as e:
        return jsonify({"error": f"Erro ao gerar CSV: {str(e)}"}), 500

@main_routes.route('/download')
def download():
    global csv_content
    return send_file(
        io.BytesIO(csv_content.encode("utf-8")),
        mimetype='text/csv',
        as_attachment=True,
        download_name="enderecos_myway.csv"
    )

@main_routes.route('/api/reverse-geocode', methods=['POST'])
def reverse_geocode():
    try:
        data = request.get_json()
        idx = data.get('idx')
        lat = data.get('lat')
        lng = data.get('lng')
        
        if not all([idx is not None, lat, lng]):
            return jsonify({"success": False, "error": "Dados incompletos"}), 400
        
        import requests
        api_key = os.environ.get('GOOGLE_API_KEY', '')
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {'latlng': f"{lat},{lng}", 'key': api_key, 'region': 'pt'}
        
        response = requests.get(url, params=params, timeout=7)
        data = response.json()
        
        if not data.get('results'):
            return jsonify({"success": False})
        
        result = data['results'][0]
        address = result['formatted_address']
        postal_code = next(
            (c['long_name'] for c in result['address_components'] if 'postal_code' in c['types']),
            ''
        )
        
        # Atualiza a sessão
        lista_atual = session.get('lista', [])
        if 0 <= idx < len(lista_atual):
            lista_atual[idx].update({
                "address": address,
                "cep": postal_code,
                "latitude": lat,
                "longitude": lng
            })
            session['lista'] = lista_atual
            session.modified = True
        
        return jsonify({
            "success": True,
            "address": address,
            "cep": postal_code
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
