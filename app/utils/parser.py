# app/utils/parser.py
"""
Módulo dedicado ao parsing de diferentes formatos de dados (texto e DataFrames)
para extrair informações de endereço, CEP e número de encomenda de forma flexível.
"""

import re
import pandas as pd
from typing import List, Tuple, Optional

def _normalize_col_name(col: str) -> str:
    """Função auxiliar para normalizar nomes de colunas, removendo espaços,
    acentos comuns, underscores e convertendo para minúsculas para uma comparação robusta."""
    s = str(col).lower().replace(" ", "").replace("_", "")
    s = s.replace('ç', 'c').replace('ã', 'a').replace('á', 'a').replace('é', 'e')
    s = s.replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
    return s

def detectar_formato_df(df: pd.DataFrame) -> Optional[str]:
    """
    Deteta o formato dos dados ('delnext' ou 'paack') de forma flexível,
    procurando por palavras-chave nos nomes das colunas.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None

    cols = {_normalize_col_name(c) for c in df.columns}
    
    # Critério Delnext: procura por colunas que contenham 'morada' e 'codigopostal'
    if any('morada' in c for c in cols) and any('codigopostal' in c for c in cols):
        return 'delnext'
    
    # Critério Paack: procura por colunas que contenham 'endereco' e 'cep'
    if any('endereco' in c for c in cols) and any('cep' in c for c in cols):
        return 'paack'
        
    return None

def parse_paack_texto(text: str) -> Tuple[List[str], List[str], List[str]]:
    """
    Faz o parsing de um texto bruto no formato Paack.
    O formato esperado é um bloco de 4 linhas por encomenda.
    """
    regex_cep = re.compile(r'(\d{4}-\d{3})')
    linhas = [l.strip() for l in text.strip().splitlines() if l.strip()]
    
    enderecos, ceps, order_numbers = [], [], []
    i = 0
    while i <= len(linhas) - 4:
        endereco_linha = linhas[i]
        # Confirma se o bloco é válido verificando se o endereço é repetido na 3ª linha
        if i + 3 < len(linhas) and linhas[i+2] == endereco_linha:
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
    # Encontra as colunas relevantes procurando por palavras-chave
    col_end = next((c for c in df.columns if 'morada' in _normalize_col_name(c)), None)
    col_cep = next((c for c in df.columns if 'codigopostal' in _normalize_col_name(c)), None)
    col_order = next((c for c in df.columns if 'encomenda' in _normalize_col_name(c) or 'pedido' in _normalize_col_name(c)), None)

    if not col_end or not col_cep:
        return [], [], []
        
    enderecos = df[col_end].astype(str).tolist()
    ceps = df[col_cep].astype(str).tolist()
    order_numbers = df[col_order].astype(str).tolist() if col_order else [f"D{i+1}" for i in range(len(enderecos))]
    
    return enderecos, ceps, order_numbers

def _parse_paack_df(df: pd.DataFrame) -> Tuple[List[str], List[str], List[str]]:
    """Função interna para fazer o parsing de um DataFrame no formato Paack."""
    # Encontra as colunas relevantes procurando por palavras-chave
    col_end = next((c for c in df.columns if 'endereco' in _normalize_col_name(c)), None)
    col_cep = next((c for c in df.columns if 'cep' in _normalize_col_name(c)), None)
    col_order = next((c for c in df.columns if 'order' in _normalize_col_name(c)), None)
    
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
