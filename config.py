# config.py

import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'sua-chave-secreta')

    # Configurações de sessão
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_COOKIE_NAME = 'mapsdrive-session'
    SESSION_FILE_DIR = os.path.join(os.getcwd(), 'flask_session')

    # Segurança
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Altere para True se usar HTTPS
    SESSION_REFRESH_EACH_REQUEST = True
