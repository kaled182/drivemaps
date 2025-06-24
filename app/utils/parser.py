# app/utils/parser.py
"""
Módulo dedicado ao parsing de diferentes formatos de dados (texto e DataFrames)
para extrair informações de endereço, CEP e número de encomenda.
"""

import re
import pandas as pd
from typing import List, Tuple, Optional

def detectar_formato_df(df: pd.DataFrame) -> Optional[str]:
    """
    Detecta o formato dos dados de entrada baseado nas colunas.
    Retorna: 'delnext', 'paack' ou None.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None
    cols = {str(c).lower().strip() for c in df.columns}
    if 'morada' in cols and ('código postal' in cols or 'codigo postal' in cols):
        return 'delnext'
    if 'endereco' in cols and 'cep' in cols:
        return 'paack'
    return None

def parse_paack(text: str) -> Tuple[List[str], List[str], List[str]]:
    """
    Faz o parsing de um texto bruto no formato Paack para extrair dados.

    O formato esperado é um bloco de 4 linhas por encomenda:
        1. Endereço completo (deve conter o CEP)
        2. Código interno (ignorado)
        3. Endereço completo (repetido)
        4. ID da encomenda (order number)
    """
    regex_cep = re.compile(r'(\d{4}-\d{3})')
    linhas = [l.strip() for l in text.strip().splitlines() if l.strip()]
    enderecos, ceps, order_numbers = [], [], []
    i = 0
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
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return [], [], []

    col_end_names = ['morada', 'endereco', 'address']
    col_cep_names = ['código postal', 'codigo postal', 'cep', 'postal_code']

    col_end = next((c for c in df.columns if str(c).lower().strip() in col_end_names), None)
    col_cep = next((c for c in df.columns if str(c).lower().strip() in col_cep_names), None)

    if not col_end:
        return [], [], []

    enderecos = df[col_end].astype(str).tolist()
    ceps = df[col_cep].astype(str).tolist() if col_cep else [""] * len(enderecos)
    order_numbers = [str(i+1) for i in range(len(enderecos))]
    return enderecos, ceps, order_numbers

def parse_paack_df(df: pd.DataFrame) -> Tuple[List[str], List[str], List[str]]:
    """
    Faz parsing de um DataFrame PAACK (importado de planilha, não texto).
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return [], [], []
    col_end = next((c for c in df.columns if 'endereco' in str(c).lower()), None)
    col_cep = next((c for c in df.columns if 'cep' in str(c).lower()), None)
    col_order = next((c for c in df.columns if 'order' in str(c).lower()), None)
    if not col_end or not col_cep:
        return [], [], []
    enderecos = df[col_end].astype(str).tolist()
    ceps = df[col_cep].astype(str).tolist()
    order_numbers = df[col_order].astype(str).tolist() if col_order else [f"P{i+1}" for i in range(len(enderecos))]
    return enderecos, ceps, order_numbers

def parse_df(df: pd.DataFrame, formato: Optional[str]=None) -> Tuple[List[str], List[str], List[str]]:
    """
    Faz parsing de DataFrame automaticamente, tentando detectar o formato.
    """
    formato_detectado = formato or detectar_formato_df(df)
    if formato_detectado == 'delnext':
        return parse_delnext(df)
    elif formato_detectado == 'paack':
        return parse_paack_df(df)
    return [], [], []

# --- Template para Futuros Parsers ---
# Para adicionar suporte a uma nova empresa, basta criar uma função seguindo este modelo.
# def parse_nova_empresa(df: pd.DataFrame) -> Tuple[List[str], List[str], List[str]]:
#     ...
