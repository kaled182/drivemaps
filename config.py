# config.py

import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'super-secret-key')
    SESSION_TYPE = 'filesystem'  # Armazena sessões no disco
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_FILE_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'session_data')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # Limite de upload: 5MB
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')  # Usado no frontend via template
