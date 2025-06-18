import unicodedata
import re

def normalize_text(text):
    if not text:
        return ''
    return ''.join(
        c for c in unicodedata.normalize('NFKD', text.lower())
        if not unicodedata.combining(c)
    ).strip()

def normalize_cep(cep):
    cep = re.sub(r'[^\d-]', '', cep)
    if len(cep) == 8 and '-' not in cep:
        return f"{cep[:4]}-{cep[4:]}"
    if len(cep) == 7 and '-' not in cep:
        return f"{cep[:4]}-{cep[4:]}"
    if len(cep) == 9 and cep.count('-') == 1 and len(cep.replace('-', '')) == 8:
        return cep[:8]
    if len(cep) > 8 and '-' in cep and len(cep.replace('-', '')) > 7:
        numbers = re.sub(r'\D', '', cep)
        if len(numbers) >= 7:
            return f"{numbers[:4]}-{numbers[4:7]}"
    return cep

def linhas_para_enderecos(linhas):
    """
    Recebe uma lista de linhas (preenchidas), retorna lista de tuplas (endereco, numero_pacote)
    Processa em blocos de 3 linhas:
      bloco[0]: endereço
      bloco[1]: descarta
      bloco[2]: número do pacote
    """
    res = []
    linhas = [l.strip() for l in linhas if l.strip()]
    for i in range(0, len(linhas), 3):
        bloco = linhas[i:i+3]
        if len(bloco) == 3:
            endereco = bloco[0]
            numero_pacote = bloco[2]
            res.append((endereco, numero_pacote))
    return res
