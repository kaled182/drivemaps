import re
from app.services.validators import validate_address_cep
from app.utils.normalize import normalize_cep

class PaackTextImporter:
    """
    Parser para listas coladas em texto do Paack, pegando apenas endereço e ID de pacote.
    O ID de pacote é o número sequencial (ex: 1, 2, 3...).
    """

    def parse(self, text):
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        blocks = []
        i = 0
        while i < len(lines):
            # 1. Procura endereço com CEP
            if re.search(r'\d{4}-\d{3}', lines[i]):
                endereco = lines[i]
                cep_match = re.search(r'(\d{4}-\d{3})', endereco)
                cep = cep_match.group(1) if cep_match else ''
            else:
                i += 1
                continue

            # 2. Pega o ID do pacote (linha 3 do bloco)
            order_number = ''
            if i+3 < len(lines) and re.match(r'^\d+$', lines[i+3]):
                order_number = lines[i+3]
            else:
                order_number = ''  # Fallback vazio se não encontrar

            # 3. Validação e normalização
            cep = normalize_cep(cep)
            res = validate_address_cep(endereco, cep)
            blocks.append({
                "address": endereco,
                "order_number": order_number,
                "cep": cep,
                **res,
                "importacao_tipo": "paack"
            })

            # 4. Pula bloco típico (7 linhas)
            i += 7
        return blocks

# Atualize sua função get_importer conforme necessário:
def get_importer(empresa, input_type='file'):
    if empresa == "paack" and input_type == 'file':
        return PaackImporter()
    if empresa == "paack" and input_type == 'text':
        return PaackTextImporter()
    if empresa == "delnext":
        return DelnextImporter()
    raise ValueError("Empresa não suportada")
