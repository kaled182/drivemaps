# app/utils/parser.py

import re
import pandas as pd

def parse_paack(text):
    """
    Recebe texto bruto (caixa de texto) no formato Paack e retorna listas:
    - enderecos: lista de endereços
    - ceps: lista de CEPs (XXXX-XXX)
    - order_numbers: lista de números sequenciais (ID do pacote)
    """
    regex_cep = re.compile(r'(\d{4}-\d{3})')
    linhas = [linha.strip() for linha in text.strip().splitlines() if linha.strip()]
    enderecos, ceps, order_numbers = [], [], []
    i = 0
    while i < len(linhas) - 3:
        endereco_linha = linhas[i]
        # Formato: linha[i] = endereço, linha[i+1] = ignorar, linha[i+2] = endereço repetido, linha[i+3] = número sequencial
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

def parse_delnext(df):
    """
    Recebe um DataFrame pandas do arquivo Delnext.
    Ignora a primeira linha, busca colunas de endereço e CEP.
    Retorna listas: enderecos, ceps, order_numbers (sequenciais).
    """
    if df.shape[0] > 1:
        df = df.iloc[1:]  # Ignora a primeira linha, se houver cabeçalho
    col_end = [c for c in df.columns if 'morada' in c.lower()]
    col_cep = [c for c in df.columns if 'código postal' in c.lower() or 'codigo postal' in c.lower()]
    enderecos = df[col_end[0]].astype(str).tolist() if col_end else []
    ceps = df[col_cep[0]].astype(str).tolist() if col_cep else []
    order_numbers = [str(i+1) for i in range(len(enderecos))]
    return enderecos, ceps, order_numbers

# Exemplo de expansão para outros formatos:
# def parse_nome_empresa(df): ...
