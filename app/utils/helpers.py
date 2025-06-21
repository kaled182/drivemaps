# app/utils/helpers.py
"""
Módulo com funções auxiliares (helpers) utilizadas em toda a aplicação.
Inclui normalização de texto, validação de dados, gestão de cores e constantes.
"""
import unicodedata
import re
from typing import List, Dict, Any

# Paleta de cores padronizada para os tipos de importação (usada nos mapas/frontends)
CORES_IMPORTACAO = {
    "manual": "#0074D9",     # Azul
    "delnext": "#FF851B",    # Laranja
    "paack": "#2ECC40",      # Verde
    "divergente": "#DC143C", # Vermelho (divergências/erros)
    "default": "#B10DC9"     # Roxo (fallback)
}

def normalizar(texto: str) -> str:
    """
    Remove acentos, pontuação e excesso de espaços para comparação consistente.

    Args:
        texto (str): String de entrada.

    Returns:
        str: String normalizada, minúscula e sem acentos.
    """
    if not texto:
        return ''
    texto = str(texto).lower()
    # Remove acentos
    texto = ''.join(
        c for c in unicodedata.normalize('NFKD', texto)
        if not unicodedata.combining(c)
    )
    # Remove pontuação
    texto = re.sub(r'[^\w\s]', '', texto)
    # Espaços únicos e limpa bordas
    return re.sub(r'\s+', ' ', texto).strip()

def registro_unico(lista: List[Dict[str, Any]], novo: Dict[str, Any]) -> bool:
    """
    Verifica se um novo registro é único na lista (por endereço, CEP e tipo).

    Args:
        lista (list): Lista de registros existentes.
        novo (dict): Novo registro a verificar.

    Returns:
        bool: True se for único, False se duplicado.
    """
    endereco_novo = normalizar(novo.get("address", ""))
    cep_novo = normalizar(novo.get("cep", ""))
    tipo_novo = novo.get("importacao_tipo", "")
    for item in lista:
        if (
            normalizar(item.get("address", "")) == endereco_novo and
            normalizar(item.get("cep", "")) == cep_novo and
            item.get("importacao_tipo") == tipo_novo
        ):
            return False
    return True

def cor_por_tipo(tipo: str) -> str:
    """
    Retorna a cor hexadecimal associada ao tipo de importação.

    Args:
        tipo (str): Tipo de importação.

    Returns:
        str: Cor hexadecimal.
    """
    return CORES_IMPORTACAO.get(tipo, CORES_IMPORTACAO["default"])

def validar_cep(cep: str) -> bool:
    """
    Valida formato de CEP português (xxxx-xxx).

    Args:
        cep (str): CEP a validar.

    Returns:
        bool: True se válido, False caso contrário.
    """
    if not isinstance(cep, str):
        return False
    padrao = r'^\d{4}-\d{3}$'
    return bool(re.match(padrao, cep.strip()))

def sanitizar_endereco(endereco: str) -> str:
    """
    Limpa uma string de endereço, removendo caracteres perigosos e limitando o tamanho.

    Args:
        endereco (str): Endereço original.

    Returns:
        str: Endereço seguro e sanitizado.
    """
    if not endereco:
        return ""
    endereco = str(endereco)
    # Remove caracteres de controle e outros perigosos para segurança
    endereco = re.sub(r'[<>"\'\\\x00-\x1f\x7f-\x9f]', '', endereco)
    # (Opcional) remove emojis/caracteres não BMP — pode ativar se desejar
    # endereco = re.sub(r'[^\u0000-\uFFFF]', '', endereco)
    return endereco.strip()[:500]
