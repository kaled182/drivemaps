# app/utils/helpers.py

import unicodedata
import re
from typing import List, Dict, Any

# Constantes de cores padronizadas
CORES_IMPORTACAO = {
    "manual": "#0074D9",     # Azul
    "delnext": "#FF851B",    # Laranja
    "paack": "#2ECC40",      # Verde
    "divergente": "#DC143C",  # Vermelho
    "default": "#B10DC9"     # Roxo
}


def normalizar(texto: str) -> str:
    """
    Remove acentos e normaliza a string para comparação.
    Args:
        texto: String a ser normalizada
    Returns:
        String normalizada em minúsculas sem acentos
    """
    if not texto:
        return ''
    # Converte para string se não for
    texto = str(texto)

    # Remove acentos e normaliza
    normalizado = ''.join(
        c for c in unicodedata.normalize('NFKD', texto.lower())
        if not unicodedata.combining(c)
    ).strip()

    return normalizado


def registro_unico(lista: List[Dict[str, Any]], novo: Dict[str, Any]) -> bool:
    """
    Verifica se um registro é único na lista baseado em endereço, CEP e tipo.
    Args:
        lista: Lista de registros existentes
        novo: Novo registro a ser verificado
    Returns:
        True se o registro for único, False caso contrário
    """
    if not isinstance(lista, list) or not isinstance(novo, dict):
        return True
    endereco_novo = normalizar(novo.get("address", ""))
    cep_novo = normalizar(novo.get("cep", ""))
    tipo_novo = novo.get("importacao_tipo", "")

    for item in lista:
        if not isinstance(item, dict):
            continue
        endereco_existente = normalizar(item.get("address", ""))
        cep_existente = normalizar(item.get("cep", ""))
        tipo_existente = item.get("importacao_tipo", "")
        if (
            endereco_existente == endereco_novo and
            cep_existente == cep_novo and
            tipo_existente == tipo_novo
        ):
            return False
    return True


def cor_por_tipo(tipo: str) -> str:
    """
    Retorna a cor padrão associada a um tipo de importação.
    Args:
        tipo: Tipo de importação
    Returns:
        Código de cor hexadecimal
    """
    return CORES_IMPORTACAO.get(tipo, CORES_IMPORTACAO["default"])


def validar_cep(cep: str) -> bool:
    """
    Valida formato de CEP português (xxxx-xxx).
    Args:
        cep: CEP a ser validado
    Returns:
        True se válido, False caso contrário
    """
    if not cep:
        return False
    # Padrão para CEP português
    padrao = r'^\d{4}-\d{3}$'
    return bool(re.match(padrao, str(cep).strip()))


def sanitizar_endereco(endereco: str) -> str:
    """
    Sanitiza endereço removendo caracteres perigosos.
    Args:
        endereco: Endereço a ser sanitizado
    Returns:
        Endereço sanitizado
    """
    if not endereco:
        return ""
    # Remove caracteres potencialmente perigosos
    endereco = str(endereco).strip()
    endereco = re.sub(r'[<>"\'\\\x00-\x1f\x7f-\x9f]', '', endereco)
    return endereco[:500]  # Limita tamanho
