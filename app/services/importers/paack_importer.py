import csv
from io import StringIO, BytesIO

def parse_paack(file_or_text):
    """
    Recebe um arquivo (FileStorage) ou texto (str) da Paack e devolve uma lista de dicts:
    Cada dict contém: lat, lng, importacao_tipo ("paack"), order_number, address

    - O geocoding real pode ser implementado aqui ou em outro serviço.
    - Supondo que a planilha/texto já venha com latitude/longitude (ideal),
      ou então retornar lat/lng em branco/call para geocodificação posterior.
    """
    lista = []

    # Detecta se é arquivo ou texto
    if hasattr(file_or_text, 'read'):
        # Trata como arquivo (FileStorage)
        raw = file_or_text.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8-sig")
        content = raw
    else:
        # Trata como texto bruto colado
        content = file_or_text

    # Tenta ler com csv.DictReader
    f = StringIO(content)
    reader = csv.DictReader(f)

    for row in reader:
        # Ajuste os campos conforme as colunas reais da planilha/texto da Paack
        order_number = row.get("Order Number") or row.get("order_number") or row.get("ID") or ""
        address = row.get("Address") or row.get("address") or row.get("Endereço") or ""
        lat = row.get("Latitude") or row.get("lat") or ""
        lng = row.get("Longitude") or row.get("lng") or ""

        # Converte lat/lng para float se possível, senão None
        try:
            lat = float(lat)
        except Exception:
            lat = None
        try:
            lng = float(lng)
        except Exception:
            lng = None

        item = {
            "order_number": order_number,
            "address": address,
            "lat": lat,
            "lng": lng,
            "importacao_tipo": "paack"
        }
        lista.append(item)
    return lista
