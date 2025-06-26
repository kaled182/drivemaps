# app/routes/preview.py
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from app.utils.google import valida_rua_google
from app.utils.helpers import normalizar, registro_unico, CORES_IMPORTACAO
from app.utils import parser
import os
import logging

preview_bp = Blueprint('preview', __name__)
logger = logging.getLogger(__name__)

@preview_bp.route("/", methods=["GET"])
def home():
    """Exibe a página inicial e limpa a sessão para um novo começo."""
    session.clear()
    return render_template("index.html")

@preview_bp.route('/preview', methods=['GET', 'POST'])
def preview():
    """
    Página de visualização:
    - POST: Processa dados do formulário, salva na sessão e redireciona (PRG).
    - GET: Exibe os dados salvos na sessão para o usuário.
    """
    try:
        if request.method == "POST":
            session.clear()  # Sempre começa limpo
            
            enderecos_brutos = request.form.get('enderecos', '').strip()
            if not enderecos_brutos:
                raise ValueError("Nenhum endereço fornecido no formulário.")

            enderecos, ceps, order_numbers = parser.parse_paack(enderecos_brutos)
            if not enderecos:
                raise ValueError("Não foi possível extrair endereços do texto. Verifique o formato.")

            lista_processada = []
            for endereco, cep, numero_pacote in zip(enderecos, ceps, order_numbers):
                res_google = valida_rua_google(endereco, cep)
                novo_item = {
                    "order_number": numero_pacote,
                    "address": endereco,
                    "cep": cep,
                    "status_google": res_google.get('status', 'ERRO'),
                    "latitude": res_google.get('coordenadas', {}).get('lat', ''),
                    "longitude": res_google.get('coordenadas', {}).get('lng', ''),
                    "importacao_tipo": "paack",
                    "cor": CORES_IMPORTACAO.get("paack"),
                    "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
                    "endereco_formatado": res_google.get('endereco_formatado', ''),
                    "rua_google": res_google.get('route_encontrada', ''),
                    "cep_ok": cep == res_google.get('postal_code_encontrado', ''),
                    "rua_bate": normalizar(endereco.split(',')[0]) in normalizar(res_google.get('route_encontrada', '')),
                    "freguesia": res_google.get('sublocality', ''),
                    "locality": res_google.get('locality', '')
                }
                if registro_unico(lista_processada, novo_item):
                    lista_processada.append(novo_item)

            session['lista'] = lista_processada
            session.modified = True
            return redirect(url_for('preview.preview'))

        # GET: Renderiza a lista salva na sessão
        lista_atual = session.get('lista', [])
        origens = list(set(item.get('importacao_tipo', 'manual') for item in lista_atual))
        return render_template(
            "preview.html",
            lista=lista_atual,
            MAPBOX_TOKEN=os.environ.get("MAPBOX_TOKEN", ""),
            GOOGLE_API_KEY=os.environ.get("GOOGLE_API_KEY", ""),
            origens=origens
        )

    except Exception as e:
        logger.error(f"[preview] Erro ao processar: {str(e)}", exc_info=True)
        flash(f"Houve um erro ao processar os endereços: {e}. Tente novamente.", "danger")
        return redirect(url_for('preview.home'))


# --- NOVA ROTA PARA REMOVER ENDEREÇO ---
@preview_bp.route('/api/remover-endereco', methods=['POST'])
def remover_endereco():
    """Remove um endereço da lista de endereços na sessão, dado o índice."""
    data = request.get_json()
    idx = data.get('idx')

    # Recupera lista atual da sessão
    lista = session.get('lista', [])

    try:
        idx = int(idx)
        if 0 <= idx < len(lista):
            lista.pop(idx)
            session['lista'] = lista
            session.modified = True
            return jsonify({'success': True, 'lista': lista})
        else:
            return jsonify({'success': False, 'msg': 'Índice inválido.'}), 400
    except Exception as e:
        return jsonify({'success': False, 'msg': f'Erro ao remover: {str(e)}'}), 500
