# config.py

import os
from datetime import timedelta

class Config:
    # Configurações essenciais
    SECRET_KEY = os.getenv('SECRET_KEY', 'sua-chave-secreta-aqui-deve-ser-longa-e-aleatoria')
    
    # Configurações de sessão
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = os.path.join(os.getcwd(), 'flask_session')
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'session:'
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # Configurações de cookie
    SESSION_COOKIE_NAME = 'mapsdrive_session'
    SESSION_COOKIE_SECURE = False  # True em produção com HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Garante que o Flask-Session irá usar essas configurações
    SESSION_COOKIE_PATH = '/'
    SESSION_REFRESH_EACH_REQUEST = True
