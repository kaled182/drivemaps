import os
import requests

def valida_rua_google(endereco, cep):
    """
    Consulta a Google Geocoding API para validar endereço e CEP.
    Retorna informações estruturadas:
    {
        'status': str,
        'endereco_formatado': str,
        'postal_code_encontrado': str,
        'route_encontrada': str,
        'sublocality': str,
        'coordenadas': {'lat': float, 'lng': float}
    }
    """
    api_key = os.environ.get('GOOGLE_API_KEY', '')
    if not api_key:
        return {
            'status': 'SEM_API_KEY',
            'endereco_formatado': '',
            'postal_code_encontrado': '',
            'route_encontrada': '',
            'sublocality': '',
            'coordenadas': {'lat': None, 'lng': None}
        }
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {'address': f"{endereco}, {cep}", 'key': api_key, 'region': 'pt'}
    try:
        r = requests.get(url, params=params, timeout=(3.05, 7))
        r.raise_for_status()
        data = r.json()
        if not data.get('results'):
            return {
                'status': 'NÃO ENCONTRADO',
                'endereco_formatado': '',
                'postal_code_encontrado': '',
                'route_encontrada': '',
                'sublocality': '',
                'coordenadas': {'lat': None, 'lng': None}
            }
        res = data['results'][0]
        address_components = res.get('address_components', [])
        route = ''
        sublocality = ''
        postal_code = ''
        for c in address_components:
            if 'route' in c['types']:
                route = c['long_name']
            if 'postal_code' in c['types']:
                postal_code = c['long_name']
            if 'sublocality' in c['types']:
                sublocality = c['long_name']
        coordenadas = res.get('geometry', {}).get('location', {'lat': None, 'lng': None})
        return {
            'status': data.get('status', 'OK'),
            'endereco_formatado': res.get('formatted_address', ''),
            'postal_code_encontrado': postal_code,
            'route_encontrada': route,
            'sublocality': sublocality,
            'coordenadas': coordenadas
        }
    except requests.Timeout:
        return {
            'status': 'TIMEOUT',
            'endereco_formatado': '',
            'postal_code_encontrado': '',
            'route_encontrada': '',
            'sublocality': '',
            'coordenadas': {'lat': None, 'lng': None}
        }
    except Exception as e:
        return {
            'status': f'ERRO: {str(e)}',
            'endereco_formatado': '',
            'postal_code_encontrado': '',
            'route_encontrada': '',
            'sublocality': '',
            'coordenadas': {'lat': None, 'lng': None}
        }
