import csv
import io

def export_to_myway(address_list):
    """
    Gera um arquivo CSV no formato aceito pelo MyWay a partir de uma lista de endereços.
    Cada item da lista deve ser um dicionário com os campos necessários.

    Retorna: bytes (conteúdo do CSV)
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Cabeçalho do MyWay (ajuste as colunas conforme necessário)
    writer.writerow([
        "order number",      # ID do pacote (ex: 1, 2, 3...)
        "address",           # Endereço completo
        "latitude",          # Coordenada (se disponível)
        "longitude",         # Coordenada (se disponível)
        "postal_code",       # CEP
        "notes",             # Campo livre/observação
        "importacao_tipo",   # Tipo de importação (paack, delnext, manual)
    ])

    for item in address_list:
        writer.writerow([
            item.get("order_number", ""),
            item.get("address", ""),
            item.get("latitude", ""),
            item.get("longitude", ""),
            item.get("cep", ""),
            "",  # notes (vazio por padrão)
            item.get("importacao_tipo", ""),
        ])

    return output.getvalue().encode("utf-8")
