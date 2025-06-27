# app/utils/geoapi.py

import requests
import os
import re

GEOAPI_KEY = os.environ.get("GEOAPI_KEY", "SUA_CHAVE_API_GEOAPI")
BASE_URL = "https://json.geoapi.pt"

def normaliza_nome(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())

def valida_rua_geoapi(endereco, cep):
    """
    Busca nas seguintes ordens:
      1. CEP + Freguesia + Rua + Número (rua só se existir NAQUELA freguesia)
      2. CEP + Freguesia (centroide da freguesia)
      3. CEP (centroide do CEP)
    Se não encontrar, retorna NOT_FOUND.
    """
    try:
        # Extrai rua, número, freguesia
        partes = [p.strip() for p in re.split(r',', endereco) if p.strip()]
        rua = partes[0] if partes else endereco.strip()
        numero = ""
        freguesia = ""
        if len(partes) >= 2:
            rua_parts = rua.split()
            if rua_parts and rua_parts[-1].isdigit():
                numero = rua_parts[-1]
                rua = " ".join(rua_parts[:-1])
            freguesia = partes[1]
        cep_limpo = cep.replace("-", "").replace(" ", "")

        # 1. Busca artérias (ruas) dentro da freguesia - SÓ SE EXISTIR FREGUESIA
        if freguesia:
            arterias_url = f"{BASE_URL}/freguesia/{freguesia}/arterias?key={GEOAPI_KEY}"
            art_resp = requests.get(arterias_url, timeout=5)
            if art_resp.ok:
                art_data = art_resp.json()
                for art in art_data:
                    # Só casa a rua NAQUELA freguesia, não busca nacional!
                    if normaliza_nome(rua) in normaliza_nome(art.get("arteria", "")):
                        lat, lng = art.get("coordenadas", [None, None])
                        if lat and lng:
                            return {
                                "status": "OK",
                                "coordenadas": {"lat": float(lat), "lng": float(lng)},
                                "postal_code_encontrado": cep,
                                "endereco_formatado": f"{rua} {numero}, {freguesia}, {cep}" if numero else f"{rua}, {freguesia}, {cep}",
                                "route_encontrada": art.get("arteria", rua),
                                "sublocality": "",
                                "locality": freguesia,
                            }
        # 2. Se não achou a rua, retorna CENTROIDE da freguesia
        if freguesia:
            freg_url = f"{BASE_URL}/freguesia/{freguesia}?key={GEOAPI_KEY}"
            freg_resp = requests.get(freg_url, timeout=5)
            if freg_resp.ok:
                freg_data = freg_resp.json()
                centro = freg_data.get("centroide")
                if centro:
                    lat, lng = map(float, centro.split(","))
                    return {
                        "status": "OK_FREGUESIA",
                        "coordenadas": {"lat": lat, "lng": lng},
                        "postal_code_encontrado": cep,
                        "endereco_formatado": f"{freguesia}, {cep}",
                        "route_encontrada": rua,
                        "sublocality": "",
                        "locality": freguesia,
                    }
        # 3. Se não tem freguesia, busca só o CEP (centroide do CEP)
        if cep:
            cep_url = f"{BASE_URL}/cp/{cep_limpo}?key={GEOAPI_KEY}"
            cep_resp = requests.get(cep_url, timeout=5)
            if cep_resp.ok:
                cep_data = cep_resp.json()
                centroide = cep_data.get("centroide")
                if centroide:
                    lat, lng = map(float, centroide.split(","))
                    return {
                        "status": "OK_CEP",
                        "coordenadas": {"lat": lat, "lng": lng},
                        "postal_code_encontrado": cep,
                        "endereco_formatado": f"{cep}",
                        "route_encontrada": rua,
                        "sublocality": "",
                        "locality": "",
                    }
        # Não achou nada
        return {"status": "NOT_FOUND", "msg": "Endereço não encontrado na base GEOAPI"}
    except Exception as e:
        return {"status": "ERRO", "msg": str(e)}

def obter_endereco_por_coordenadas_geoapi(lat, lng):
    """
    Faz geocodificação reversa usando GeoAPI.pt (coordenadas para endereço).
    """
    try:
        url = f"{BASE_URL}/gps/{lat},{lng}"
        params = {"key": GEOAPI_KEY}
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        d = resp.json()
        if isinstance(d, dict) and d.get("cp4"):
            return {
                "status": "OK",
                "address": d.get("address", ""),
                "postal_code": d.get("cp4", "") + ("-" + d.get("cp3", "") if d.get("cp3") else ""),
                "route_encontrada": d.get("arteria", ""),
                "sublocality": d.get("freguesia", ""),
                "locality": d.get("municipio", ""),
                "coordenadas": {"lat": lat, "lng": lng},
            }
        else:
            return {"status": "NOT_FOUND"}
    except Exception as e:
        return {"status": "ERRO", "msg": str(e)}
