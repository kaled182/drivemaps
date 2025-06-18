# app/routes/api.py

from flask import Blueprint, request, jsonify, session
from app.utils.google import valida_rua_google_cache, obter_endereco_por_coordenadas
from app.utils.helpers import normalizar, sanitizar_endereco, validar_cep
import logging
from typing import Optional, Dict, Any

api_routes = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

@api_routes.route('/api/validar-linha', methods=['POST'])
def validar_linha():
    """Valida uma linha de endereço usando a API do Google Maps."""
    try:
        # Validação de entrada
        if not request.is_json:
            return jsonify({"success": False, "msg": "Content-Type deve ser application/json"}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "msg": "Dados JSON inválidos"}), 400

        # Extração e validação de parâmetros
        idx = data.get('idx')
        endereco_raw = data.get('endereco', '')
        cep = data.get('cep', '')
        tipo = data.get('importacao_tipo', 'manual')
        numero = data.get('numero_pacote')

        # Validações específicas
        if not endereco_raw or not isinstance(endereco_raw, str):
            return jsonify({"success": False, "msg": "Endereço é obrigatório"}), 400

        # Sanitização
        endereco = sanitizar_endereco(endereco_raw)
        if len(endereco) < 5:
            return jsonify({"success": False, "msg": "Endereço muito curto"}), 400

        # Validação de CEP se fornecido
        if cep and not validar_cep(cep):
            return jsonify({"success": False, "msg": "Formato de CEP inválido (deve ser xxxx-xxx)"}), 400

        # Validação de tipo
        tipos_validos = ['manual', 'delnext', 'paack']
        if tipo not in tipos_validos:
            tipo = 'manual'

        # Geração de número automático se não fornecido
        if numero is None:
            numero = str(idx + 1 if idx is not None else len(session.get('lista', [])) + 1)

        # Validação com Google Maps
        resultado = valida_rua_google_cache(endereco, cep)
        
        # Processamento dos resultados
        rua_digitada = endereco.split(',')[0] if endereco else ''
        rua_google = resultado.get('route_encontrada', '')
        cep_ok = cep == resultado.get('postal_code_encontrado', '') if cep else True
        
        # Comparação inteligente de ruas
        rua_bate = _comparar_ruas(rua_digitada, rua_google)

        # Mapeamento de cores por tipo
        cores_tipo = {
            'manual': "#0074D9",
            'delnext': "#FF851B", 
            'paack': "#2ECC40"
        }
        cor = cores_tipo.get(tipo, "#B10DC9")

        # Montagem do objeto resultado
        novo = {
            "order_number": str(numero),
            "address": endereco,
            "cep": cep,
            "status_google": resultado.get('status', 'ERROR'),
            "postal_code_encontrado": resultado.get('postal_code_encontrado', ''),
            "endereco_formatado": resultado.get('endereco_formatado', ''),
            "latitude": resultado.get('coordenadas', {}).get('lat'),
            "longitude": resultado.get('coordenadas', {}).get('lng'),
            "rua_google": rua_google,
            "cep_ok": cep_ok,
            "rua_bate": rua_bate,
            "freguesia": resultado.get('sublocality', ''),
            "locality": resultado.get('locality', ''),
            "importacao_tipo": tipo,
            "cor": cor,
            "error": resultado.get('error', '') if resultado.get('status') != 'OK' else ''
        }

        # Atualização da sessão
        lista = session.get('lista', [])
        if idx is not None and 0 <= idx < len(lista):
            lista[idx] = novo
            indice_retorno = idx
        else:
            lista.append(novo)
            indice_retorno = len(lista) - 1

        session['lista'] = lista
        session.modified = True

        return jsonify({
            "success": True,
            "item": novo,
            "idx": indice_retorno,
            "total": len(lista)
        })

    except Exception as e:
        logger.error(f"Erro ao validar linha: {str(e)}", exc_info=True)
        return jsonify({"success": False, "msg": "Erro interno do servidor"}), 500

@api_routes.route('/api/session-data', methods=['GET'])
def session_data():
    """Retorna dados da sessão atual."""
    try:
        lista = session.get('lista', [])
        
        # Estatísticas
        estatisticas = _calcular_estatisticas(lista)
        
        return jsonify({
            "success": True,
            "lista": lista,
            "total": len(lista),
            "origens": list({item.get("importacao_tipo", "manual") for item in lista}),
            "estatisticas": estatisticas
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter dados da sessão: {str(e)}")
        return jsonify({"success": False, "msg": "Erro ao carregar dados"}), 500

@api_routes.route('/api/reverse-geocode', methods=['POST'])
def reverse_geocode():
    """Proxy seguro para reverse geocoding do Google Maps."""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'msg': 'Content-Type deve ser application/json'}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'msg': 'Dados JSON inválidos'}), 400

        # Validação de parâmetros
        idx = data.get('idx')
        lat = data.get('lat')
        lng = data.get('lng')

        if any(param is None for param in [idx, lat, lng]):
            return jsonify({'success': False, 'msg': 'Parâmetros idx, lat e lng são obrigatórios'}), 400

        # Validação de tipos e ranges
        try:
            idx = int(idx)
            lat = float(lat)
            lng = float(lng)
            
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                return jsonify({'success': False, 'msg': 'Coordenadas fora do range válido'}), 400
                
        except (ValueError, TypeError):
            return jsonify({'success': False, 'msg': 'Coordenadas devem ser numéricas válidas'}), 400

        # Chamada para a API do Google
        resultado = obter_endereco_por_coordenadas(lat, lng)
        
        if resultado.get('status') != 'OK':
            error_msg = resultado.get('error', 'Endereço não encontrado')
            return jsonify({'success': False, 'msg': error_msg}), 404

        # Atualização da sessão
        lista = session.get('lista', [])
        if 0 <= idx < len(lista):
            lista[idx].update({
                "latitude": lat,
                "longitude": lng,
                "endereco_formatado": resultado.get('address', ''),
                "postal_code_encontrado": resultado.get('postal_code', '')
            })
            session['lista'] = lista
            session.modified = True

        return jsonify({
            "success": True,
            "address": resultado.get('address', ''),
            "cep": resultado.get('postal_code', ''),
            "coordinates": {"lat": lat, "lng": lng}
        })

    except Exception as e:
        logger.error(f"Erro no reverse-geocode: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'msg': 'Erro interno do servidor'}), 500

@api_routes.route('/api/limpar-sessao', methods=['POST'])
def limpar_sessao():
    """Limpa dados da sessão atual."""
    try:
        # Preserva dados importantes como configurações de usuário
        chaves_preservar = ['user_preferences', 'csrf_token']
        dados_preservados = {k: session.get(k) for k in chaves_preservar if k in session}
        
        session.clear()
        
        # Restaura dados preservados
        for k, v in dados_preservados.items():
            session[k] = v
        
        session['lista'] = []
        session.modified = True
        
        return jsonify({"success": True, "msg": "Sessão limpa com sucesso"})
        
    except Exception as e:
        logger.error(f"Erro ao limpar sessão: {str(e)}")
        return jsonify({"success": False, "msg": "Erro ao limpar sessão"}), 500

@api_routes.route('/api/estatisticas', methods=['GET'])
def estatisticas():
    """Retorna estatísticas detalhadas dos dados na sessão."""
    try:
        lista = session.get('lista', [])
        stats = _calcular_estatisticas(lista)
        
        return jsonify({
            "success": True,
            "estatisticas": stats
        })
        
    except Exception as e:
        logger.error(f"Erro ao calcular estatísticas: {str(e)}")
        return jsonify({"success": False, "msg": "Erro ao calcular estatísticas"}), 500

def _comparar_ruas(rua1: str, rua2: str) -> bool:
    """Compara duas ruas de forma inteligente."""
    if not rua1 or not rua2:
        return False
    
    norm1 = normalizar(rua1)
    norm2 = normalizar(rua2)
    
    # Comparação direta
    if norm1 == norm2:
        return True
    
    # Comparação por inclusão
    if norm1 in norm2 or norm2 in norm1:
        return True
    
    # Comparação por palavras-chave
    palavras1 = set(norm1.split())
    palavras2 = set(norm2.split())
    
    # Remove palavras comuns que não são significativas
    palavras_ignorar = {'rua', 'avenida', 'av', 'r', 'travessa', 'largo', 'praca', 'pc'}
    palavras1 -= palavras_ignorar
    palavras2 -= palavras_ignorar
    
    if palavras1 and palavras2:
        # Se pelo menos 50% das palavras coincidem
        intersecao = palavras1 & palavras2
        return len(intersecao) >= min(len(palavras1), len(palavras2)) * 0.5
    
    return False

def _calcular_estatisticas(lista: list) -> Dict[str, Any]:
    """Calcula estatísticas dos dados na lista."""
    if not lista:
        return {
            "total": 0,
            "por_tipo": {},
            "por_status": {},
            "validacao": {
                "cep_ok": 0,
                "rua_ok": 0,
                "completos": 0
            }
        }
    
    # Contadores
    por_tipo = {}
    por_status = {}
    cep_ok = 0
    rua_ok = 0
    completos = 0
    
    for item in lista:
        # Por tipo
        tipo = item.get('importacao_tipo', 'manual')
        por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
        
        # Por status
        status = item.get('status_google', 'UNKNOWN')
        por_status[status] = por_status.get(status, 0) + 1
        
        # Validações
        if item.get('cep_ok', False):
            cep_ok += 1
        if item.get('rua_bate', False):
            rua_ok += 1
        if item.get('latitude') and item.get('longitude'):
            completos += 1
    
    return {
        "total": len(lista),
        "por_tipo": por_tipo,
        "por_status": por_status,
        "validacao": {
            "cep_ok": cep_ok,
            "rua_ok": rua_ok,
            "completos": completos,
            "percentual_validados": round((completos / len(lista)) * 100, 1) if lista else 0
        }
    }
