import requests
import os

def valida_endereco_google(endereco):
    api_key = os.getenv('GOOGLE_API_KEY')
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        'address': endereco,
        'key': api_key,
        'region': 'pt'  # Prioriza Portugal
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data['status'] == 'OK':
            return {
                'status': 'OK',
                'endereco_formatado': data['results'][0]['formatted_address'],
                'coordenadas': data['results'][0]['geometry']['location']
            }
        return {'status': 'ERRO', 'detalhes': data['status']}
    except Exception as e:
        return {'status': 'ERRO_API', 'detalhes': str(e)}