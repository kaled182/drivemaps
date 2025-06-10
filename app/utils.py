import requests
import os

def valida_endereco_google(endereco, codigo_postal):
    api_key = os.getenv('GOOGLE_API_KEY')
    # Monta endereço priorizando CEP/PT
    query = f"{endereco}, {codigo_postal}, Portugal"
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {'address': query, 'key': api_key, 'region': 'pt'}
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data['status'] == 'OK':
            result = data['results'][0]
            postal_code = None
            for comp in result['address_components']:
                if 'postal_code' in comp['types']:
                    postal_code = comp['long_name']
                    break
            return {
                'status': 'OK',
                'endereco_formatado': result['formatted_address'],
                'coordenadas': result['geometry']['location'],
                'postal_code_encontrado': postal_code
            }
        return {'status': data['status'], 'detalhes': data.get('error_message', '')}
    except Exception as e:
        return {'status': 'ERRO_API', 'detalhes': str(e)}
