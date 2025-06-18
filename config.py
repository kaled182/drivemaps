import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-secret-key')
    
    # Sessão com arquivos no servidor
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True

    # Diretório de sessão temporário
    SESSION_FILE_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'flask_session')

    # Debug desabilitado por padrão
    DEBUG = os.environ.get('FLASK_DEBUG', 'False') == 'True'

    # Chave da API do Google (não é usada diretamente aqui, mas pode ser acessada pela aplicação)
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')

    # Outras variáveis customizadas podem ser adicionadas conforme necessário
