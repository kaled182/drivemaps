# app/routes/api.py

from flask import Blueprint, request, jsonify, session
from app.utils.geocoder import (
    valida_rua,  # <- Dispatcher dinâmico (NÃO mais google direto)
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
    Agora usa sempre o dispatcher valida_rua!
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "msg": "Dados JSON inválidos."}), 400

        try:
            idx = int(data.get('idx'))
        except (TypeError, ValueError):
            return jsonify({"success": False, "msg": "Índice (idx) inválido ou faltando."}), 400

        endereco = sanitizar_endereco(data.get('endereco', ''))
        cep = data.get('cep', '')

        if not endereco or len(endereco) < 5:
            return jsonify({"success": False, "msg": "Endereço inválido ou muito curto."}), 400
        
        if cep and not validar_cep(cep):
            return jsonify({"success": False, "msg": "Código Postal inválido (deve ser no formato 1234-567)."}), 400

        lista = session.get('lista', [])
        if not (0 <= idx < len(lista)):
            return jsonify({"success": False, "msg": "Índice fora do alcance da lista."}), 404
        
        item_para_atualizar = lista[idx]

        resultado = valida_rua(endereco, cep)
        
        item_para_atualizar.update({
            "address": endereco,
            "cep": cep,
            "status_google": resultado.get('status', 'ERRO'),
            "postal_code_encontrado": resultado.get('postal_code_encontrado', ''),
            "endereco_formatado": resultado.get('endereco_formatado', ''),
            "latitude": resultado.get('coordenadas', {}).get('lat'),
            "longitude": resultado.get('coordenadas', {}).get('lng'),
            "rua_google": resultado.get('route_encontrada', ''),
            "cep_ok": cep == resultado.get('postal_code_encontrado', ''),
            "rua_bate": _comparar_ruas(endereco.split(',')[0], resultado.get('route_encontrada', '')),
            "freguesia": resultado.get('sublocality', ''),
            "locality": resultado.get('locality', '')
        })
        
        session['lista'] = lista
        session.modified = True

        return jsonify({"success": True, "item": item_para_atualizar})

    except Exception as e:
        logger.error(f"Erro ao validar linha: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": "Erro interno do servidor ao validar."}), 500


@api_routes.route('/api/validar-por-id', methods=['POST'])
def validar_por_id():
    """
    Valida um endereço a partir do seu order_number (ID), útil para AJAX dinâmico.
    Usa sempre o dispatcher valida_rua!
    """
    try:
        data = request.get_json()
        order_number = str(data.get('order_number', '')).strip()
        endereco = sanitizar_endereco(data.get('endereco', ''))
        cep = data.get('cep', '')

        if not order_number or not endereco:
            return jsonify({"success": False, "msg": "ID e endereço obrigatórios."}), 400
        if cep and not validar_cep(cep):
            return jsonify({"success": False, "msg": "Código Postal inválido (deve ser no formato 1234-567)."}), 400

        lista = session.get('lista', [])
        idx = next((i for i, item in enumerate(lista) if str(item.get('order_number')) == order_number), None)
        if idx is None:
            return jsonify({"success": False, "msg": "Endereço não encontrado."}), 404

        resultado = valida_rua(endereco, cep)
        lista[idx].update({
            "address": endereco,
            "cep": cep,
            "status_google": resultado.get('status', 'ERRO'),
            "postal_code_encontrado": resultado.get('postal_code_encontrado', ''),
            "endereco_formatado": resultado.get('endereco_formatado', ''),
            "latitude": resultado.get('coordenadas', {}).get('lat'),
            "longitude": resultado.get('coordenadas', {}).get('lng'),
            "rua_google": resultado.get('route_encontrada', ''),
            "cep_ok": cep == resultado.get('postal_code_encontrado', ''),
            "rua_bate": _comparar_ruas(endereco.split(',')[0], resultado.get('route_encontrada', '')),
            "freguesia": resultado.get('sublocality', ''),
            "locality": resultado.get('locality', '')
        })
        session['lista'] = lista
        session.modified = True
        return jsonify({"success": True, "item": lista[idx]})

    except Exception as e:
        logger.error(f"Erro ao validar por ID: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": "Erro interno ao validar por ID."}), 500


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
            return jsonify({'success': False, 'msg': resultado.get('msg', 'Endereço não encontrado para estas coordenadas.')}), 404
        
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
    Agora valida endereço usando o dispatcher (valida_rua)!
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

        if not validar_cep(cep):
            return jsonify({"success": False, "msg": "Código Postal inválido (deve ser no formato 1234-567)."}), 400

        lista = session.get('lista', [])
        
        max_id = 0
        for item in lista:
            if item.get('importacao_tipo') == 'manual' and str(item.get('order_number')).isdigit():
                max_id = max(max_id, int(item['order_number']))
        
        novo_order_number = str(max_id + 1)

        # ---- NOVO: Valida endereço já na adição, usando o dispatcher ----
        resultado = valida_rua(endereco, cep)

        novo_item = {
            "order_number": id_fornecido or novo_order_number,
            "address": endereco,
            "cep": cep,
            "status_google": resultado.get('status', 'ERRO'),
            "latitude": resultado.get('coordenadas', {}).get('lat'),
            "longitude": resultado.get('coordenadas', {}).get('lng'),
            "cor": cor_por_tipo("manual"),
            "importacao_tipo": "manual",
            "postal_code_encontrado": resultado.get('postal_code_encontrado', ''),
            "endereco_formatado": resultado.get('endereco_formatado', ''),
            "rua_google": resultado.get('route_encontrada', ''),
            "cep_ok": cep == resultado.get('postal_code_encontrado', ''),
            "rua_bate": _comparar_ruas(endereco.split(',')[0], resultado.get('route_encontrada', '')),
            "freguesia": resultado.get('sublocality', ''),
            "locality": resultado.get('locality', '')
        }
        
        lista.append(novo_item)
        session['lista'] = lista
        session.modified = True

        return jsonify({"success": True, "item": novo_item, "total": len(lista)})
    except Exception as e:
        logger.error(f"Erro ao adicionar novo endereço: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": "Erro interno ao adicionar endereço."}), 500


@api_routes.route('/api/remover-endereco', methods=['POST'])
def remover_endereco():
    """
    Remove um endereço da lista na sessão pelo order_number (ID).
    """
    try:
        data = request.get_json()
        id_remover = str(data.get('order_number', '')).strip()
        if not id_remover:
            return jsonify({"success": False, "msg": "ID não informado."}), 400

        lista = session.get('lista', [])
        nova_lista = [item for item in lista if str(item.get('order_number')) != id_remover]

        if len(nova_lista) == len(lista):
            return jsonify({"success": False, "msg": "Endereço não encontrado."}), 404

        session['lista'] = nova_lista
        session.modified = True
        return jsonify({"success": True, "msg": "Endereço removido com sucesso.", "total": len(nova_lista)})

    except Exception as e:
        logger.error(f"Erro ao remover endereço: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": "Erro interno ao remover endereço."}), 500

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
