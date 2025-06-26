# app/utils/mapbox.py

import requests
import os
import re

MAPBOX_TOKEN = os.environ.get("MAPBOX_TOKEN", "SEU_TOKEN_MAPBOX_AQUI")

def _extrai_numero_rua(endereco):
    """
    Se possível, extrai número do endereço.
    Exemplo: "Rua X n123" -> "123"
    """
    m = re.search(r'(\d+)[^\d]*$', endereco)
    return m.group(1) if m else None

def _monta_query(endereco, cep, nivel):
    """Gera a query para cada nível de busca."""
    cep = cep.strip() if cep else ""
    if nivel == 1:
        # Tenta CEP + rua + número
        numero = _extrai_numero_rua(endereco)
        if cep and numero:
            # Ex: "Rua ABC 123, 1234-567"
            return f"{endereco}, {cep}"
    if nivel == 2:
        # Tenta CEP + rua (sem número)
        if cep:
            rua_sem_numero = re.sub(r'\s*\d+[^\d]*$', '', endereco)
            return f"{rua_sem_numero}, {cep}"
    if nivel == 3:
        # Só CEP
        if cep:
            return cep
    return endereco

def _get_context(feat, ctx_id):
    return next((c['text'] for c in feat.get('context', []) if c['id'].startswith(ctx_id)), "")

def _cep_normalizado(cep):
    """Normaliza para comparação (só números)."""
    return re.sub(r'\D', '', cep or '')

def valida_rua_mapbox(endereco, cep):
    """
    Valida endereço usando Mapbox Geocoding API.
    Sempre prioriza CEP, depois CEP+rua, depois só CEP.
    Só aceita resultado no mesmo CEP.
    """
    params_base = {
        "access_token": MAPBOX_TOKEN,
        "country": "PT",
        "limit": 1
    }
    # Busca hierárquica: (1) CEP+rua+num, (2) CEP+rua, (3) só CEP
    for nivel in [1, 2, 3]:
        query = _monta_query(endereco, cep, nivel)
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json"
        params = dict(params_base)
        if nivel == 3:
            params["types"] = "postcode"
        try:
            r = requests.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            if data.get('features'):
                feat = data['features'][0]
                postal_code_encontrado = _get_context(feat, "postcode")
                # Aceita só se o CEP encontrado for igual ao solicitado (quando foi fornecido)
                if cep:
                    if _cep_normalizado(postal_code_encontrado) != _cep_normalizado(cep):
                        continue  # Não aceita resultados de outro CEP!
                return {
                    "status": "OK" if nivel < 3 else "OK_CEP_ONLY",
                    "coordenadas": {"lat": feat['center'][1], "lng": feat['center'][0]},
                    "postal_code_encontrado": postal_code_encontrado,
                    "endereco_formatado": feat['place_name'],
                    "route_encontrada": _get_context(feat, "street"),
                    "sublocality": "",
                    "locality": _get_context(feat, "place"),
                    "msg": None if nivel < 3 else f"Endereço não encontrado, PIN colocado no centro do CEP ({cep})"
                }
        except Exception:
            continue
    return {"status": "NOT_FOUND", "msg": "Endereço e CEP não encontrados ou não existem juntos no Mapbox."}

def obter_endereco_por_coordenadas(lat, lng):
    """
    Busca reversa de endereço (coordenadas para endereço) usando Mapbox Geocoding API.
    """
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lng},{lat}.json"
    params = {
        "access_token": MAPBOX_TOKEN,
        "country": "PT",
        "limit": 1
    }
    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        if data.get('features'):
            feat = data['features'][0]
            def get_context(ctx_id):
                return next((c['text'] for c in feat.get('context', []) if c['id'].startswith(ctx_id)), "")

            return {
                "status": "OK",
                "address": feat['place_name'],
                "postal_code": get_context("postcode"),
                "sublocality": "",
                "locality": get_context("place"),
                "coordenadas": {"lat": lat, "lng": lng},
            }
        else:
            return {"status": "NOT_FOUND"}
    except Exception as e:
        return {"status": "ERRO", "erro": str(e)}
