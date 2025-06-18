# app/utils/helpers.py

import unicodedata

CORES_IMPORTACAO = {
    "manual": "#0074D9",   # Azul
    "delnext": "#FF851B",  # Laranja
    "paack": "#2ECC40",    # Verde
}

def normalizar(texto):
    """Remove acentos e normaliza a string para comparação."""
    if not texto:
        return ''
    return ''.join(
        c for c in unicodedata.normalize('NFKD', texto.lower()) if not unicodedata.combining(c)
    ).strip()

def registro_unico(lista, novo):
    """Impede duplicidade de endereço + cep + tipo de importação."""
    return not any(
        normalizar(item["address"]) == normalizar(novo["address"]) and
        normalizar(item["cep"]) == normalizar(novo["cep"]) and
        item.get("importacao_tipo") == novo.get("importacao_tipo")
        for item in lista
    )

def cor_por_tipo(tipo):
    """Retorna a cor padrão associada a um tipo de importação."""
    return CORES_IMPORTACAO.get(tipo, "#B10DC9")  # Roxo como cor fallback
