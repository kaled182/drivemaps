# config.py

import os
import tempfile

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'sua-chave-secreta')

    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_COOKIE_NAME = 'mapsdrive-session'

    # Diretório temporário compatível com Render
    SESSION_FILE_DIR = os.path.join(tempfile.gettempdir(), 'flask_session')

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # altere para True em produção com HTTPS
    SESSION_REFRESH_EACH_REQUEST = True
