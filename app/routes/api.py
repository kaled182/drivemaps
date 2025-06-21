# app/routes/api.py

from flask import Blueprint, request, jsonify, session
from app.utils.google import (
    valida_rua_google_cache,
    obter_endereco_por_coordenadas,
)
from app.utils.helpers import normalizar, sanitizar_endereco, validar_cep, cor_por_tipo
import logging
from typing import Dict, Any

api_routes = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

# --- ENDPOINTS PRINCIPAIS DA API ---

@api_routes.route('/api/validar-linha', methods=['POST'])
def validar_linha_endpoint():
    """
    Valida um endereço (novo ou existente) a partir do seu índice na lista da sessão.
    Recebe um índice, endereço e CEP, consulta a API do Google e atualiza
    o item na sessão com os novos dados geocodificados.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "msg": "Dados JSON inválidos."}), 400

        # Conversão explícita dos tipos para maior robustez
        try:
            idx = int(data.get('idx'))
        except (TypeError, ValueError):
            return jsonify({"success": False, "msg": "Índice (idx) inválido ou faltando."}), 400

        endereco = sanitizar_endereco(data.get('endereco', ''))
        cep = data.get('cep', '')

        if not endereco or len(endereco) < 5:
            return jsonify({"success": False, "msg": "Endereço inválido ou muito curto."}), 400

        lista = session.get('lista', [])
        if not (0 <= idx < len(lista)):
            return jsonify({"success": False, "msg": "Índice fora do alcance da lista."}), 404
        
        item_para_atualizar = lista[idx]

        resultado_google = valida_rua_google_cache(endereco, cep)
        
        item_para_atualizar.update({
            "address": endereco,
            "cep": cep,
            "status_google": resultado_google.get('status', 'ERRO'),
            "postal_code_encontrado": resultado_google.get('postal_code_encontrado', ''),
            "endereco_formatado": resultado_google.get('endereco_formatado', ''),
            "latitude": resultado_google.get('coordenadas', {}).get('lat'),
            "longitude": resultado_google.get('coordenadas', {}).get('lng'),
            "rua_google": resultado_google.get('route_encontrada', ''),
            "cep_ok": cep == resultado_google.get('postal_code_encontrado', ''),
            "rua_bate": _comparar_ruas(endereco.split(',')[0], resultado_google.get('route_encontrada', '')),
            "freguesia": resultado_google.get('sublocality', ''),
            "locality": resultado_google.get('locality', '')
        })
        
        session['lista'] = lista
        session.modified = True

        return jsonify({"success": True, "item": item_para_atualizar})

    except Exception as e:
        logger.error(f"Erro ao validar linha: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": "Erro interno do servidor ao validar."}), 500


@api_routes.route('/api/reverse-geocode', methods=['POST'])
def reverse_geocode_endpoint():
    """
    Recebe coordenadas (lat, lng) e um índice, encontra o endereço correspondente
    e atualiza o item na sessão. Essencial para a funcionalidade de arrastar o PIN.
    """
    try:
        data = request.get_json()
        try:
            idx = int(data.get('idx'))
            lat = float(data.get('lat'))
            lng = float(data.get('lng'))
        except (TypeError, ValueError):
            return jsonify({'success': False, 'msg': 'Parâmetros idx, lat e lng são obrigatórios e devem ser numéricos.'}), 400

        lista = session.get('lista', [])
        if not (0 <= idx < len(lista)):
            return jsonify({'success': False, 'msg': 'Índice fora do alcance.'}), 404

        resultado = obter_endereco_por_coordenadas(lat, lng)
        if resultado.get('status') != 'OK':
            return jsonify({'success': False, 'msg': resultado.get('error', 'Endereço não encontrado para estas coordenadas.')}), 404
        
        item_atualizado = lista[idx]
        novo_endereco = resultado.get('address', '')
        novo_cep = resultado.get('postal_code', '')

        item_atualizado.update({
            "latitude": lat,
            "longitude": lng,
            "address": novo_endereco,
            "cep": novo_cep,
            "status_google": "OK",
            "postal_code_encontrado": novo_cep,
            "endereco_formatado": novo_endereco,
            "cep_ok": True,
            "rua_bate": True,
            "freguesia": resultado.get('sublocality', ''),
            "locality": resultado.get('locality', '')
        })

        session['lista'] = lista
        session.modified = True

        return jsonify({"success": True, "item": item_atualizado})

    except Exception as e:
        logger.error(f"Erro no reverse-geocode: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'msg': 'Erro interno do servidor.'}), 500


@api_routes.route('/api/add-address', methods=['POST'])
def add_address_endpoint():
    """
    Adiciona um novo endereço à lista na sessão. O 'order_number' é gerado automaticamente.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "msg": "Dados JSON inválidos."}), 400

        endereco = sanitizar_endereco(data.get('endereco', ''))
        cep = data.get('cep', '')
        id_fornecido = data.get('id')

        if not endereco or not cep:
            return jsonify({"success": False, "msg": "Endereço e CEP são obrigatórios."}), 400

        lista = session.get('lista', [])
        
        max_id = 0
        for item in lista:
            if item.get('importacao_tipo') == 'manual' and str(item.get('order_number')).isdigit():
                max_id = max(max_id, int(item['order_number']))
        
        novo_order_number = str(max_id + 1)
        
        novo_item = {
            "order_number": id_fornecido or novo_order_number,
            "address": endereco, "cep": cep, "status_google": "Pendente",
            "latitude": None, "longitude": None, "cor": cor_por_tipo("manual"),
            "importacao_tipo": "manual", "rua_google": "", "postal_code_encontrado": "",
            "endereco_formatado": "", "cep_ok": False, "rua_bate": False, "freguesia": "", "locality": ""
        }
        
        lista.append(novo_item)
        session['lista'] = lista
        session.modified = True

        return jsonify({"success": True, "item": novo_item, "total": len(lista)})
    except Exception as e:
        logger.error(f"Erro ao adicionar novo endereço: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": "Erro interno ao adicionar endereço."}), 500


@api_routes.route('/api/limpar-sessao', methods=['POST'])
def limpar_sessao():
    """Limpa todos os endereços da sessão atual."""
    session['lista'] = []
    session.modified = True
    return jsonify({"success": True, "msg": "Sessão limpa com sucesso"})


@api_routes.route('/api/session-data', methods=['GET'])
def get_session_data():
    """Retorna todos os dados da sessão, incluindo a lista e estatísticas."""
    try:
        lista = session.get('lista', [])
        stats = _calcular_estatisticas(lista)
        return jsonify({
            "success": True,
            "lista": lista,
            "estatisticas": stats
        })
    except Exception as e:
        logger.error(f"Erro ao obter dados da sessão: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": "Erro ao carregar dados da sessão."}), 500

@api_routes.route('/api/estatisticas', methods=['GET'])
def estatisticas():
    """Retorna estatísticas detalhadas dos dados na sessão (para dashboards ou uso futuro)."""
    try:
        lista = session.get('lista', [])
        stats = _calcular_estatisticas(lista)
        return jsonify({"success": True, "estatisticas": stats})
    except Exception as e:
        logger.error(f"Erro ao calcular estatísticas: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": "Erro ao calcular estatísticas"}), 500

# --- FUNÇÕES AUXILIARES ---

def _comparar_ruas(rua1: str, rua2: str) -> bool:
    """Compara duas strings de rua de forma flexível."""
    if not rua1 or not rua2:
        return False
    norm1, norm2 = normalizar(rua1), normalizar(rua2)
    return norm1 in norm2 or norm2 in norm1

def _calcular_estatisticas(lista: list) -> Dict[str, Any]:
    """Calcula e retorna um resumo estatístico da lista de endereços."""
    if not lista: return {"total": 0, "por_tipo": {}, "completos": 0, "percentual_validados": 0}
    
    total = len(lista)
    por_tipo = {}
    completos = 0
    
    for item in lista:
        tipo = item.get('importacao_tipo', 'manual')
        por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
        if item.get('latitude') and item.get('longitude'):
            completos += 1
            
    return {
        "total": total,
        "por_tipo": por_tipo,
        "completos": completos,
        "percentual_validados": round((completos / total) * 100, 1) if total > 0 else 0
    }
