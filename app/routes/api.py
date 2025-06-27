# app/routes/api.py

from flask import Blueprint, request, jsonify, session
from app.utils.geocoder import valida_rua, obter_endereco_por_coordenadas
from app.utils.helpers import normalizar, sanitizar_endereco, validar_cep, cor_por_tipo
import logging
from typing import Dict, Any

api_routes = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

# Fallback numérico para garantir que as coordenadas são sempre floats
FALLBACK_LAT, FALLBACK_LNG = 39.3999, -8.2245

def _comparar_ruas(rua1: str, rua2: str) -> bool:
    if not rua1 or not rua2: return False
    return normalizar(rua1) in normalizar(rua2) or normalizar(rua2) in normalizar(rua1)

def _update_item_com_geo_resultado(item: Dict, resultado: Dict, endereco: str, cep: str) -> None:
    """Função auxiliar para atualizar um item com dados geocodificados."""
    coordenadas = resultado.get('coordenadas', {})
    item.update({
        "address": endereco, "cep": cep,
        "status_google": resultado.get('status', 'ERRO'),
        "latitude": float(coordenadas.get('lat', FALLBACK_LAT)),
        "longitude": float(coordenadas.get('lng', FALLBACK_LNG)),
        "postal_code_encontrado": resultado.get('postal_code_encontrado', ''),
        "endereco_formatado": resultado.get('endereco_formatado', ''),
        "rua_google": resultado.get('route_encontrada', ''),
        "cep_ok": cep == resultado.get('postal_code_encontrado', ''),
        "rua_bate": _comparar_ruas(endereco.split(',')[0], resultado.get('route_encontrada', '')),
        "freguesia": resultado.get('sublocality', ''),
        "locality": resultado.get('locality', '')
    })

@api_routes.route('/api/validar-por-id', methods=['POST'])
def validar_por_id():
    """Valida um endereço a partir do seu order_number (ID)."""
    try:
        data = request.get_json()
        order_number = str(data.get('order_number', '')).strip()
        endereco = sanitizar_endereco(data.get('endereco', ''))
        cep = data.get('cep', '')

        if not order_number or not endereco: return jsonify({"success": False, "msg": "ID e endereço obrigatórios."}), 400
        if cep and not validar_cep(cep): return jsonify({"success": False, "msg": "Código Postal inválido."}), 400

        lista = session.get('lista', [])
        idx = next((i for i, item in enumerate(lista) if str(item.get('order_number')) == order_number), None)
        if idx is None: return jsonify({"success": False, "msg": "Endereço não encontrado."}), 404

        resultado_geo = valida_rua(endereco, cep)
        _update_item_com_geo_resultado(lista[idx], resultado_geo, endereco, cep)
        
        session['lista'] = lista
        session.modified = True
        return jsonify({"success": True, "item": lista[idx]})
    except Exception as e:
        logger.error(f"Erro ao validar por ID: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": "Erro interno ao validar."}), 500

@api_routes.route('/api/reverse-geocode', methods=['POST'])
def reverse_geocode_endpoint():
    """Recebe coordenadas e atualiza o endereço correspondente."""
    try:
        data = request.get_json()
        idx, lat, lng = int(data.get('idx')), float(data.get('lat')), float(data.get('lng'))
        lista = session.get('lista', [])
        if not (0 <= idx < len(lista)): return jsonify({'success': False, 'msg': 'Índice fora do alcance.'}), 404
        
        resultado = obter_endereco_por_coordenadas(lat, lng)
        if resultado.get('status') != 'OK': return jsonify({'success': False, 'msg': 'Endereço não encontrado.'}), 404
        
        novo_endereco = resultado.get('address', '')
        novo_cep = resultado.get('postal_code', '')
        _update_item_com_geo_resultado(lista[idx], resultado, novo_endereco, novo_cep)
        
        session['lista'] = lista
        session.modified = True
        return jsonify({"success": True, "item": lista[idx], "lista": lista})
    except Exception as e:
        logger.error(f"Erro no reverse-geocode: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'msg': 'Erro interno do servidor.'}), 500

@api_routes.route('/api/add-address', methods=['POST'])
def add_address_endpoint():
    """Adiciona um novo endereço à lista na sessão."""
    try:
        data = request.get_json()
        endereco = sanitizar_endereco(data.get('endereco', ''))
        cep = data.get('cep', '')
        id_fornecido = data.get('id')
        if not id_fornecido or not endereco or not cep: return jsonify({"success": False, "msg": "ID, Endereço e CEP obrigatórios."}), 400
        if not validar_cep(cep): return jsonify({"success": False, "msg": "Código Postal inválido."}), 400

        resultado_geo = valida_rua(endereco, cep)
        novo_item = {
            "order_number": id_fornecido, "importacao_tipo": "manual",
            "cor": cor_por_tipo("manual")
        }
        _update_item_com_geo_resultado(novo_item, resultado_geo, endereco, cep)
        
        lista = session.get('lista', [])
        lista.append(novo_item)
        session['lista'] = lista
        session.modified = True
        return jsonify({"success": True, "item": novo_item, "lista": lista})
    except Exception as e:
        logger.error(f"Erro ao adicionar novo endereço: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": "Erro interno ao adicionar endereço."}), 500

@api_routes.route('/api/remover-endereco', methods=['POST'])
def remover_endereco():
    """Remove um endereço da lista na sessão pelo order_number (ID)."""
    try:
        data = request.get_json()
        id_remover = str(data.get('order_number', '')).strip()
        if not id_remover: return jsonify({"success": False, "msg": "ID não informado."}), 400
        lista_original = session.get('lista', [])
        nova_lista = [item for item in lista_original if str(item.get('order_number')) != id_remover]
        if len(nova_lista) == len(lista_original): return jsonify({"success": False, "msg": "Endereço não encontrado."}), 404
        session['lista'] = nova_lista
        session.modified = True
        return jsonify({"success": True, "msg": "Endereço removido com sucesso.", "lista": nova_lista})
    except Exception as e:
        logger.error(f"Erro ao remover endereço: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": "Erro interno ao remover endereço."}), 500
