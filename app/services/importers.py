import re
from app.services.validators import validate_address_cep
from app.utils.normalize import normalize_cep
import csv
from io import StringIO
from app.services.geocode import get_lat_lng

GOOGLE_MAPS_API_KEY = "SUA_CHAVE_AQUI"  # Troque pela sua chave real

# Regex para validar o padrão exigido para PINs
PIN_ADDRESS_REGEX = re.compile(
    r'^\s*\d{4}-\d{3}\s*(?:-\s*[^-]*){0,2}\s*$', re.IGNORECASE
)

class PaackTextImporter:
    """
    Parser para listas coladas em texto do Paack.
    Só considera endereços que seguem o padrão para criar PIN.
    """
    def parse(self, text):
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        blocks = []
        i = 0
        while i < len(lines):
            # 1. Procura linha com CEP
            cep_match = re.search(r'\d{4}-\d{3}', lines[i])
            if cep_match:
                endereco = lines[i]
                normalized_endereco = endereco
                # Monta o endereço no formato "CEP - RUA - NUMERO" mesmo que rua/numero estejam faltando
                cep = cep_match.group(0)
                # Normaliza para garantir separador padrão
                after_cep = endereco.split(cep, 1)[1].strip(" ,")
                if after_cep:
                    # tenta extrair rua e numero
                    parts = [cep] + [p.strip(" ,") for p in re.split(r',|;', after_cep) if p.strip()]
                    normalized_endereco = " - ".join(parts)
                else:
                    normalized_endereco = cep

                # 2. Só aceita se seguir o padrão
                if PIN_ADDRESS_REGEX.match(normalized_endereco):
                    order_number = ''
                    if i+3 < len(lines) and re.match(r'^\d+$', lines[i+3]):
                        order_number = lines[i+3]
                    else:
                        order_number = ''
                    # normalização e validação
                    cep = normalize_cep(cep)
                    res = validate_address_cep(endereco, cep)
                    lat, lng = get_lat_lng(normalized_endereco, GOOGLE_MAPS_API_KEY)
                    blocks.append({
                        "address": normalized_endereco,
                        "order_number": order_number,
                        "cep": cep,
                        "lat": lat,
                        "lng": lng,
                        **res,
                        "importacao_tipo": "paack"
                    })
                # Senão, ignora (sem PIN)
            i += 7  # Pula bloco típico
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

            # Só PIN se endereço seguir padrão
            if address and PIN_ADDRESS_REGEX.match(address):
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
