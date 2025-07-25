import os
from datetime import timedelta

class Config:
    # Configurações essenciais
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24).hex())
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    
    # Configurações de API externa (agora corrigidas)
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
    MAPBOX_TOKEN = os.getenv('MAPBOX_TOKEN', '')
    MAP_ID = os.getenv('MAP_ID', '')

    # Configuração dinâmica para múltiplas APIs
    EXTERNAL_APIS = {
        "google": {
            "key": GOOGLE_API_KEY,
            "base_url": "https://maps.googleapis.com/maps/api"
        },
        "mapbox": {
            "token": MAPBOX_TOKEN,
            "base_url": "https://api.mapbox.com"
        },
        # Adicione outros provedores no futuro...
    }
    
    # Configurações de sessão
    SESSION_TYPE = os.getenv('SESSION_TYPE', 'filesystem')
    SESSION_FILE_DIR = os.path.join(os.getcwd(), 'flask_session')
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'session:'
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # Configurações de cookie
    SESSION_COOKIE_NAME = os.getenv('SESSION_COOKIE_NAME', 'mapsdrive_session')
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True') == 'True'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Configuração para Redis (se necessário)
    if SESSION_TYPE == 'redis':
        import redis
        REDIS_URL = os.getenv('REDIS_URL')
        if REDIS_URL:
            SESSION_REDIS = redis.from_url(REDIS_URL)
    
    @property
    def DEBUG(self):
        return self.FLASK_ENV.lower() == 'development'
