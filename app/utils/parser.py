# app/utils/parser.py
"""
Módulo dedicado ao parsing de diferentes formatos de dados (texto e DataFrames)
para extrair informações de endereço, CEP e número de encomenda.
"""

import re
import pandas as pd
from typing import List, Tuple

def parse_paack(text: str) -> Tuple[List[str], List[str], List[str]]:
    """
    Faz o parsing de um texto bruto no formato Paack para extrair dados.

    O formato esperado é um bloco de 4 linhas por encomenda:
        1. Endereço completo (deve conter o CEP)
        2. Código interno (ignorado)
        3. Endereço completo (repetido)
        4. ID da encomenda (order number)
    
    Args:
        text (str): O texto bruto com os dados.

    Returns:
        Tuple[List[str], List[str], List[str]]: Uma tupla contendo as listas
        de endereços, CEPs e números de encomenda.
    """
    regex_cep = re.compile(r'(\d{4}-\d{3})')
    # Remove linhas vazias para um parsing mais seguro
    linhas = [l.strip() for l in text.strip().splitlines() if l.strip()]
    
    enderecos, ceps, order_numbers = [], [], []
    i = 0
    # Itera sobre as linhas em blocos de 4
    while i <= len(linhas) - 4:
        endereco_linha = linhas[i]
        # Confirma se o bloco é válido verificando o endereço repetido
        if linhas[i+2] == endereco_linha:
            order = linhas[i+3].strip()
            cep_match = regex_cep.search(endereco_linha)
            cep = cep_match.group(1) if cep_match else ""
            
            enderecos.append(endereco_linha)
            ceps.append(cep)
            order_numbers.append(order)
            i += 4
        else:
            i += 1
            
    return enderecos, ceps, order_numbers

def parse_delnext(df: pd.DataFrame) -> Tuple[List[str], List[str], List[str]]:
    """
    Faz o parsing de um DataFrame do Delnext, procurando de forma flexível
    pelas colunas de endereço e CEP.

    Args:
        df (pd.DataFrame): O DataFrame carregado do ficheiro Delnext.

    Returns:
        Tuple[List[str], List[str], List[str]]: Uma tupla contendo as listas
        de endereços, CEPs e números de encomenda gerados sequencialmente.
    """
    # Proteção contra DataFrame inválido ou vazio
    if not isinstance(df, pd.DataFrame) or df.empty:
        return [], [], []

    # Procura por nomes de coluna comuns, ignorando maiúsculas/minúsculas
    col_end_names = ['morada', 'endereco', 'address']
    col_cep_names = ['código postal', 'codigo postal', 'cep', 'postal_code']

    col_end = next((c for c in df.columns if str(c).lower().strip() in col_end_names), None)
    col_cep = next((c for c in df.columns if str(c).lower().strip() in col_cep_names), None)

    # Se a coluna de endereço não for encontrada, não há o que fazer
    if not col_end:
        return [], [], []

    enderecos = df[col_end].astype(str).tolist()
    
    # Se a coluna de CEP for encontrada, extrai os dados. Senão, cria uma lista de strings vazias.
    if col_cep:
        ceps = df[col_cep].astype(str).tolist()
    else:
        ceps = [""] * len(enderecos)

    # Gera números de encomenda sequenciais para o Delnext
    order_numbers = [str(i+1) for i in range(len(enderecos))]

    return enderecos, ceps, order_numbers

# --- Template para Futuros Parsers ---
# Para adicionar suporte a uma nova empresa, basta criar uma função seguindo este modelo.
#
# def parse_nova_empresa(df: pd.DataFrame) -> Tuple[List[str], List[str], List[str]]:
#     """
#     Faz o parsing de um DataFrame da Nova Empresa.
#     """
#     # 1. Validação de entrada
#     if df.empty:
#         return [], [], []
#
#     # 2. Lógica para encontrar colunas de endereço e CEP
#     # ...
#
#     # 3. Extração dos dados
#     # ...
#
#     # 4. Retorno das três listas alinhadas
#     return enderecos, ceps, order_numbers
