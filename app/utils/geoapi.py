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
      1. CEP + Freguesia + Rua + Número
      2. CEP + Freguesia + Rua
      3. CEP + Freguesia
      4. CEP
    """
    try:
        # 1. Quebrar endereço: tenta extrair rua, número e freguesia se possível
        # Você pode passar esses campos em cada integração, mas para efeito demo, vou usar heurística
        partes = re.split(r',', endereco)
        rua = partes[0].strip() if partes else endereco
        numero = ""
        freguesia = ""
        if len(partes) >= 2:
            # Heurística para detectar número no fim da rua: "Rua XPTO 123"
            rua_parts = rua.split()
            if rua_parts and rua_parts[-1].isdigit():
                numero = rua_parts[-1]
                rua = " ".join(rua_parts[:-1])
            freguesia = partes[1].strip()
        else:
            freguesia = ""

        cep_limpo = cep.replace("-", "").replace(" ", "")
        # Se souber a freguesia, tenta buscar artérias (ruas) nela
        if freguesia:
            # Tenta buscar artérias da freguesia
            arterias_url = f"{BASE_URL}/freguesia/{freguesia}/arterias?key={GEOAPI_KEY}"
            art_resp = requests.get(arterias_url, timeout=5)
            if art_resp.status_code == 200:
                art_data = art_resp.json()
                for art in art_data:
                    if normaliza_nome(rua) in normaliza_nome(art.get("arteria", "")):
                        # Achou rua!
                        lat, lng = art.get("coordenadas", [None, None])
                        if lat and lng:
                            return {
                                "status": "OK",
                                "coordenadas": {"lat": float(lat), "lng": float(lng)},
                                "postal_code_encontrado": cep,
                                "endereco_formatado": f"{rua}, {freguesia}, {cep}",
                                "route_encontrada": art.get("arteria", rua),
                                "sublocality": "",
                                "locality": freguesia,
                            }
        # Tenta centroide da freguesia
        if freguesia:
            freg_url = f"{BASE_URL}/freguesia/{freguesia}?key={GEOAPI_KEY}"
            freg_resp = requests.get(freg_url, timeout=5)
            if freg_resp.status_code == 200:
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
        # Tenta centroide do CEP
        if cep:
            cep_url = f"{BASE_URL}/cp/{cep_limpo}?key={GEOAPI_KEY}"
            cep_resp = requests.get(cep_url, timeout=5)
            if cep_resp.status_code == 200:
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
        # Se nada
        return {"status": "NOT_FOUND", "msg": "Endereço não encontrado na base GEOAPI"}
    except Exception as e:
        return {"status": "ERRO", "msg": str(e)}
