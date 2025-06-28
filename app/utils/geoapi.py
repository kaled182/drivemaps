# app/utils/geoapi.py

import requests
import os
import re

GEOAPI_KEY = os.environ.get("GEOAPI_KEY", "SUA_CHAVE_API_GEOAPI")
BASE_URL = "https://json.geoapi.pt"

def normaliza_nome(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())

def extrai_cep(partes):
    # Encontra o último que parece um CEP
    for parte in reversed(partes):
        match = re.search(r"\d{4}-\d{3}", parte)
        if match:
            return match.group(0)
    return ""

def extrai_freguesia(partes, cep_idx):
    # Heurística: pega o primeiro termo ANTES do cep, que não parece um número
    # Normalmente, para Delnext, a freguesia está logo antes do CEP
    if cep_idx > 0:
        # Pega o item imediatamente anterior ao CEP, que não é numérico
        freg = partes[cep_idx-1].strip()
        # Remove termos comuns que não são freguesia
        if freg.lower() in ["portugal", "viana do castelo"]:
            # Pega o anterior
            if cep_idx > 1:
                freg = partes[cep_idx-2].strip()
        return freg
    return ""

def valida_rua_geoapi(endereco, cep):
    """
    Busca por:
      1. CEP + Freguesia + Rua (+ Número)
      2. Centroide da Freguesia (se pertence ao CEP)
      3. Centroide do CEP
    """
    try:
        # Quebra endereço por vírgula
        partes = [p.strip() for p in re.split(r',', endereco) if p.strip()]
        # Extrai o último CEP presente
        cep_final = extrai_cep(partes)
        if not cep_final and cep:
            cep_final = cep
        cep_limpo = cep_final.replace("-", "").replace(" ", "")

        # Encontra índice do CEP e tenta pegar a freguesia imediatamente anterior
        try:
            cep_idx = next(i for i, p in enumerate(partes) if cep_final in p)
        except StopIteration:
            cep_idx = len(partes) - 1

        freguesia = extrai_freguesia(partes, cep_idx)
        rua = partes[0] if partes else endereco.strip()
        # Heurística número (último número na rua)
        numero = ""
        rua_parts = rua.split()
        if rua_parts and rua_parts[-1].isdigit():
            numero = rua_parts[-1]
            rua = " ".join(rua_parts[:-1])

        # LOG PARA DEBUG
        print(f"[GEOAPI] Busca: Rua='{rua}' Número='{numero}' Freguesia='{freguesia}' CEP='{cep_final}'")

        # Busca artérias da freguesia, mas só valida se pertence ao mesmo CEP
        if freguesia:
            arterias_url = f"{BASE_URL}/freguesia/{freguesia}/arterias?key={GEOAPI_KEY}"
            art_resp = requests.get(arterias_url, timeout=5)
            if art_resp.ok:
                art_data = art_resp.json()
                for art in art_data:
                    if normaliza_nome(rua) in normaliza_nome(art.get("arteria", "")):
                        # Checa se artéria tem coordenada e o mesmo CEP
                        art_ceps = art.get("codigos_postais", [])
                        if any(normaliza_nome(cep_limpo) == normaliza_nome(str(c.get("codigo_postal", "")).replace("-", "")) for c in art_ceps):
                            lat, lng = art.get("coordenadas", [None, None])
                            if lat and lng:
                                return {
                                    "status": "OK",
                                    "coordenadas": {"lat": float(lat), "lng": float(lng)},
                                    "postal_code_encontrado": cep_final,
                                    "endereco_formatado": f"{rua} {numero}, {freguesia}, {cep_final}" if numero else f"{rua}, {freguesia}, {cep_final}",
                                    "route_encontrada": art.get("arteria", rua),
                                    "sublocality": "",
                                    "locality": freguesia,
                                }

        # Centroide da freguesia (só se pertence ao CEP)
        if freguesia:
            freg_url = f"{BASE_URL}/freguesia/{freguesia}?key={GEOAPI_KEY}"
            freg_resp = requests.get(freg_url, timeout=5)
            if freg_resp.ok:
                freg_data = freg_resp.json()
                centro = freg_data.get("centroide")
                codigos_postais = freg_data.get("codigos_postais", [])
                if centro and any(normaliza_nome(cep_limpo) == normaliza_nome(c.get("codigo_postal", "")) for c in codigos_postais):
                    lat, lng = map(float, centro.split(","))
                    return {
                        "status": "OK_FREGUESIA",
                        "coordenadas": {"lat": lat, "lng": lng},
                        "postal_code_encontrado": cep_final,
                        "endereco_formatado": f"{freguesia}, {cep_final}",
                        "route_encontrada": rua,
                        "sublocality": "",
                        "locality": freguesia,
                    }

        # Centroide do CEP
        if cep_final:
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
                        "postal_code_encontrado": cep_final,
                        "endereco_formatado": f"{cep_final}",
                        "route_encontrada": rua,
                        "sublocality": "",
                        "locality": "",
                    }
        return {"status": "NOT_FOUND", "msg": "Endereço não encontrado na base GEOAPI"}
    except Exception as e:
        return {"status": "ERRO", "msg": str(e)}

def obter_endereco_por_coordenadas_geoapi(lat, lng):
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
