from .validators import validate_address_cep
from app.utils.normalize import normalize_text, normalize_cep
import pandas as pd
import re

class BaseImporter:
    def parse(self, file):
        raise NotImplementedError

class PaackImporter(BaseImporter):
    def parse(self, file):
        file.seek(0)
        filename = file.filename.lower()
        if filename.endswith(('xlsx', 'xls')):
            df = pd.read_excel(file)
        else:
            df = pd.read_csv(file)
        col_end = next((c for c in df.columns if 'endereco' in c.lower()), None)
        col_cep = next((c for c in df.columns if 'cep' in c.lower()), None)
        if not col_end or not col_cep:
            raise ValueError("Colunas 'Endereço' e 'CEP' não encontradas")
        result = []
        for _, row in df.iterrows():
            address = str(row[col_end]).strip()
            cep = normalize_cep(str(row[col_cep]))
            res = validate_address_cep(address, cep)
            result.append({
                "address": address,
                "cep": cep,
                **res,
                "importacao_tipo": "paack"
            })
        return result

class DelnextImporter(BaseImporter):
    def parse(self, file):
        file.seek(0)
        filename = file.filename.lower()
        if filename.endswith(('xlsx', 'xls')):
            df = pd.read_excel(file, header=1)
        else:
            df = pd.read_csv(file, header=1)
        col_morada = next((c for c in df.columns if 'morada' in c.lower()), None)
        col_cep = next((c for c in df.columns if 'código postal' in c.lower() or 'codigo postal' in c.lower()), None)
        if not col_morada or not col_cep:
            raise ValueError("Colunas 'Morada' e 'Código Postal' não encontradas")
        result = []
        for _, row in df.iterrows():
            address = str(row[col_morada]).strip()
            cep = normalize_cep(str(row[col_cep]))
            res = validate_address_cep(address, cep)
            result.append({
                "address": address,
                "cep": cep,
                **res,
                "importacao_tipo": "delnext"
            })
        return result

def get_importer(empresa):
    if empresa == "paack":
        return PaackImporter()
    if empresa == "delnext":
        return DelnextImporter()
    raise ValueError("Empresa não suportada")
