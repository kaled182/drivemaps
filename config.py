# config.py

import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'sua-chave-secreta')
    
    # Sessão com Flask-Session
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_COOKIE_NAME = 'mapsdrive-session'  # ✅ Substitui o antigo app.session_cookie_name

    # Caminho onde sessões são armazenadas (opcional)
    SESSION_FILE_DIR = os.path.join(os.getcwd(), 'flask_session')

    # Segurança de sessão
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # altere para True em produção com HTTPS
    SESSION_REFRESH_EACH_REQUEST = True
