from app.utils.normalize import normalize_text

def validate_address_cep(address, cep):
    # Aqui você pode chamar seu serviço real de geocodificação.
    # No exemplo, uso coordenadas de São Paulo para todos como dummy.
    res_google = {
        "status": "OK",
        "postal_code_encontrado": cep,
        "endereco_formatado": address.upper(),
        "coordenadas": {"lat": 41.504073, "lng": -8.761827},  # Dummy: Fao, Esposende, 
        "route_encontrada": address.split(',')[0] if address else '',
        "sublocality": "",
    }
    rua_digitada = address.split(',')[0] if address else ''
    rua_google = res_google.get('route_encontrada', '')
    rua_bate = (normalize_text(rua_digitada) in normalize_text(rua_google) or
                normalize_text(rua_google) in normalize_text(rua_digitada))
    cep_ok = cep == res_google.get('postal_code_encontrado', '')
    return {
        "status_google": res_google.get('status'),
        "postal_code_encontrado": res_google.get('postal_code_encontrado', ''),
        "endereco_formatado": res_google.get('endereco_formatado', ''),
        "lat": res_google.get('coordenadas', {}).get('lat', ''),
        "lng": res_google.get('coordenadas', {}).get('lng', ''),
        "rua_google": rua_google,
        "cep_ok": cep_ok,
        "rua_bate": rua_bate,
        "freguesia": res_google.get('sublocality', '')
    }
