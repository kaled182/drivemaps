import os
from datetime import timedelta

class Config:
    # Configurações essenciais
    SECRET_KEY = os.getenv(
        'SECRET_KEY',
        'sua-chave-secreta-aqui-deve-ser-longa-e-aleatoria'  # Substitua em produção!
    )
    
    DEBUG = os.getenv('DEBUG', 'False') == 'True'
    
    # Configurações de sessão
    SESSION_TYPE = os.getenv('SESSION_TYPE', 'filesystem')
    SESSION_FILE_DIR = os.path.join(os.getcwd(), 'flask_session')
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'session:'
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # Configurações de cookie
    SESSION_COOKIE_NAME = 'mapsdrive_session'
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False') == 'True'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_PATH = '/'
    SESSION_REFRESH_EACH_REQUEST = True
    
    # Configuração para Redis (se necessário)
    if SESSION_TYPE == 'redis':
        import redis
        REDIS_URL = os.getenv('REDIS_URL')
        if REDIS_URL:
            SESSION_REDIS = redis.from_url(REDIS_URL)
