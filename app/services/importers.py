import re
from app.services.validators import validate_address_cep
from app.utils.normalize import normalize_cep
import csv
from io import StringIO
from app.services.geocode import get_lat_lng  # <-- Adicionado para geocodificação

GOOGLE_MAPS_API_KEY = "SUA_CHAVE_AQUI"  # Substitua pela sua chave real ou importe de config/env

class PaackTextImporter:
    """
    Parser para listas coladas em texto do Paack.
    Faz geocodificação do endereço para preencher lat/lng.
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

            # 4. Geocodificação do endereço para obter lat/lng
            lat, lng = get_lat_lng(endereco, GOOGLE_MAPS_API_KEY)

            blocks.append({
                "address": endereco,
                "order_number": order_number,
                "cep": cep,
                "lat": lat,
                "lng": lng,
                **res,
                "importacao_tipo": "paack"
            })

            # 5. Pula bloco típico (7 linhas)
            i += 7
        return blocks

class DelnextImporter:
    """
    Importador de planilhas Delnext.
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
