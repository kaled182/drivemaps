import re
import csv
from io import StringIO
from app.services.geocode import get_lat_lng

GOOGLE_MAPS_API_KEY = "SUA_CHAVE_AQUI"  # Troque pela sua chave real

class PaackTextImporter:
    """
    Parser para listas coladas em texto do Paack.
    Mantém o endereço original, apenas extrai CEP para validação/geocodificação.
    """
    def parse(self, text):
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        blocks = []
        for i, line in enumerate(lines):
            # Procura pelo CEP (padrão PT)
            cep_match = re.search(r'\d{4}-\d{3}', line)
            if cep_match:
                cep = cep_match.group(0)
                # NÃO modifica o endereço original
                endereco_original = line
                # Geocodifica usando o endereço original
                lat, lng = get_lat_lng(endereco_original, GOOGLE_MAPS_API_KEY)
                blocks.append({
                    "address": endereco_original,
                    "order_number": "",  # Adapte se precisar extrair pedido
                    "cep": cep,
                    "lat": lat,
                    "lng": lng,
                    "importacao_tipo": "paack"
                })
        return blocks

class DelnextImporter:
    """
    Importador de planilhas Delnext.
    Mantém o endereço original.
    """
    def parse(self, file):
        lista = []

        raw = file.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8-sig")
        content = raw

        f = StringIO(content)
        reader = csv.DictReader(f)

        for row in reader:
            order_number = row.get("Order Number") or row.get("order_number") or row.get("ID") or ""
            address = row.get("Address") or row.get("address") or row.get("Endereço") or ""
            lat = row.get("Latitude") or row.get("lat") or ""
            lng = row.get("Longitude") or row.get("lng") or ""

            try:
                lat = float(lat)
            except Exception:
                lat = None
            try:
                lng = float(lng)
            except Exception:
                lng = None

            # NÃO altera o endereço original
            if address:
                item = {
                    "order_number": order_number,
                    "address": address,
                    "lat": lat,
                    "lng": lng,
                    "importacao_tipo": "delnext"
                }
                lista.append(item)
        return lista

def get_importer(empresa, input_type='file'):
    if empresa == "paack":
        return PaackTextImporter()
    if empresa == "delnext":
        return DelnextImporter()
    raise ValueError("Empresa não suportada")
