# app/utils/parser.py
"""
Módulo dedicado ao parsing de diferentes formatos de dados (texto e DataFrames)
para extrair informações de endereço, CEP e número de encomenda.
"""

import re
import pandas as pd
from typing import List, Tuple, Optional

def _normalize_col_name(col: str) -> str:
    """Função auxiliar para normalizar nomes de colunas, removendo espaços,
    underscores e convertendo para minúsculas para uma comparação robusta."""
    return str(col).lower().replace(" ", "").replace("_", "")

def detectar_formato_df(df: pd.DataFrame) -> Optional[str]:
    """
    Deteta o formato dos dados de entrada ('delnext' ou 'paack') com base nas
    colunas do DataFrame.

    Args:
        df (pd.DataFrame): O DataFrame a ser analisado.

    Returns:
        Optional[str]: O formato detetado ou None se não for reconhecido.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None

    cols = {_normalize_col_name(c) for c in df.columns}
    
    # Critérios de deteção baseados em nomes de coluna comuns
    if 'morada' in cols and ('códigopostal' in cols or 'codigopostal' in cols):
        return 'delnext'
    if 'endereco' in cols and 'cep' in cols:
        return 'paack'
        
    return None

def parse_paack_texto(text: str) -> Tuple[List[str], List[str], List[str]]:
    """
    Faz o parsing de um texto bruto no formato Paack.

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
        # Confirma se o bloco é válido verificando se o endereço é repetido na 3ª linha
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

def _parse_delnext_df(df: pd.DataFrame) -> Tuple[List[str], List[str], List[str]]:
    """Função interna para fazer o parsing de um DataFrame no formato Delnext."""
    col_end = next((c for c in df.columns if _normalize_col_name(c) == 'morada'), None)
    col_cep = next((c for c in df.columns if _normalize_col_name(c) in ('códigopostal', 'codigopostal')), None)
    col_order = next((c for c in df.columns if _normalize_col_name(c) in ('order', 'pedido', 'encomenda', 'numero')), None)

    if not col_end or not col_cep:
        return [], [], []
        
    enderecos = df[col_end].astype(str).tolist()
    ceps = df[col_cep].astype(str).tolist()
    order_numbers = df[col_order].astype(str).tolist() if col_order else [f"D{i+1}" for i in range(len(enderecos))]
    
    return enderecos, ceps, order_numbers

def _parse_paack_df(df: pd.DataFrame) -> Tuple[List[str], List[str], List[str]]:
    """Função interna para fazer o parsing de um DataFrame no formato Paack."""
    col_end = next((c for c in df.columns if _normalize_col_name(c) == 'endereco'), None)
    col_cep = next((c for c in df.columns if _normalize_col_name(c) == 'cep'), None)
    col_order = next((c for c in df.columns if _normalize_col_name(c) == 'order'), None)
    
    if not col_end or not col_cep:
        return [], [], []
        
    enderecos = df[col_end].astype(str).tolist()
    ceps = df[col_cep].astype(str).tolist()
    order_numbers = df[col_order].astype(str).tolist() if col_order else [f"P{i+1}" for i in range(len(enderecos))]
    
    return enderecos, ceps, order_numbers

def parse_dataframe(df: pd.DataFrame, formato: Optional[str] = None) -> Tuple[List[str], List[str], List[str]]:
    """
    Função "dispatcher" que deteta o formato do DataFrame e chama o parser correto.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return [], [], []

    formato_detectado = formato or detectar_formato_df(df)
    
    if formato_detectado == 'delnext':
        return _parse_delnext_df(df)
    elif formato_detectado == 'paack':
        return _parse_paack_df(df)
        
    # Retorna vazio se nenhum formato for reconhecido
    return [], [], []
